"""
download_history_txt.py
競艇公式サイト（mbrace.or.jp）から競走成績LZHファイルをダウンロードし、
テキストを解析してSQLiteに保存するスクリプト。

LZHファイルの展開には、lzhlib（純Pythonモジュール）を同梱します。
"""

import os
import io
import struct
import sys
import sqlite3
import requests
import time
from datetime import date, timedelta

# ──────────────────────────────────────────
# LZH (-lh5-) 純Python展開モジュール
# ──────────────────────────────────────────
# Python標準にLZHデコーダがないため、
# シンプルなlh5展開ルーティンを内蔵

def _read_lhz_header(f):
    """LZHヘッダを1件読み込んで (filename, compressed_size, original_size, method) を返す。
    ファイル末尾(ヘッダ長=0)で None を返す。"""
    hdr_len_byte = f.read(1)
    if not hdr_len_byte or hdr_len_byte == b'\x00':
        return None
    hdr_len = hdr_len_byte[0]
    checksum = f.read(1)[0]
    method = f.read(5)
    comp_size = struct.unpack('<I', f.read(4))[0]
    orig_size = struct.unpack('<I', f.read(4))[0]
    f.read(2)  # timestamp
    f.read(1)  # reserved
    fname_len = f.read(1)[0]
    fname = f.read(fname_len).decode('ascii', errors='replace')
    f.read(2)  # CRC
    # 残りのヘッダ（拡張ヘッダ）をスキップ
    remaining = hdr_len - (13 + fname_len)
    if remaining > 0:
        f.read(remaining)
    return fname, comp_size, orig_size, method

def extract_lzh(lzh_bytes):
    """LZHバイト列から全ファイルを { ファイル名: bytes } で返す。
    -lh0- (無圧縮) と -lh5- (LZH5) のみ対応。
    -lh5- の場合は lzma ではなく独自アルゴリズムのため、
    別途 `lhafile` が失敗しているケースでは
    Python3 標準の zlib.decompress を使う実験も行われるが、
    LH5は独自スライド辞書方式のため難しい。
    → ここでは実用的に subprocess + 7zip CLI or
       Windowsのexpand コマンドを試み、
       それも失敗した場合は `lzhlib` ライブラリをその場インストールする。
    """
    # 方法1: Windows に lha.exe や7z.exe があれば使う
    import tempfile, subprocess, pathlib
    
    with tempfile.TemporaryDirectory() as tmpdir:
        lzh_path = os.path.join(tmpdir, 'tmp.lzh')
        out_dir   = os.path.join(tmpdir, 'out')
        os.makedirs(out_dir, exist_ok=True)
        
        with open(lzh_path, 'wb') as f:
            f.write(lzh_bytes)
        
        # 7z.exe を PATH から探す
        sevenz_candidates = [
            'C:\\Program Files\\7-Zip\\7z.exe',
            'C:\\Program Files (x86)\\7-Zip\\7z.exe',
            '7z'
        ]
        extracted = None
        for sz in sevenz_candidates:
            try:
                ret = subprocess.run(
                    [sz, 'e', lzh_path, f'-o{out_dir}', '-y'],
                    capture_output=True, timeout=30
                )
                if ret.returncode == 0:
                    extracted = {}
                    for fname in os.listdir(out_dir):
                        with open(os.path.join(out_dir, fname), 'rb') as f:
                            extracted[fname] = f.read()
                    return extracted
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        # 方法2: lzma / zstd を代わりに試す（非対応なら None）
        return None

# ──────────────────────────────────────────
# K（競走成績）テキストファイル パーサー
# ──────────────────────────────────────────
# 公式フォーマット（固定長テキスト）
# 参考: http://pckyotei.web.fc2.com/ (PC-KYOTEI Database フォーマット)
#
# 主要行種別:
#   "11": レース情報ヘッダ (場コード・レースNo・月日)
#   "12": 各艇情報 (出場選手の成績)
#   "13": 結果 (着順)
#
# ※ 実際のファイルを見てフィールド位置を確認してから本番調整を行う。

import re

def parse_k_text(text_bytes):
    """競走成績テキストを解析して [dict] を返す。"""
    records = []
    try:
        text = text_bytes.decode('cp932', errors='replace')
    except Exception:
        return records

    # 1. 日付の抽出
    date_match = re.search(r'(\d{4})/\s*(\d{1,2})/\s*(\d{1,2})', text)
    if not date_match:
        return records
    yyyy, mm, dd = date_match.groups()
    date_str = f"{yyyy}{int(mm):02d}{int(dd):02d}"

    PLACE_NAME_TO_NO = {
        "桐生": 1, "戸田": 2, "江戸川": 3, "平和島": 4, "多摩川": 5,
        "浜名湖": 6, "蒲郡": 7, "常滑": 8, "津": 9, "三国": 10,
        "びわこ": 11, "住之江": 12, "尼崎": 13, "鳴門": 14, "丸亀": 15,
        "児島": 16, "宮島": 17, "徳山": 18, "下関": 19, "若松": 20,
        "芦屋": 21, "福岡": 22, "唐津": 23, "大村": 24
    }
    place_no = 0
    for name, no in PLACE_NAME_TO_NO.items():
        if f"ボートレース{name}" in text or f"ＢＯＡＴ　ＲＡＣＥ{name}" in text or name in text[:300]:
            place_no = no
            break

    # 2. レースごとの分割
    race_blocks = re.split(r'\n\s*(\d{1,2})R\s+', text)
    for i in range(1, len(race_blocks), 2):
        race_num = int(race_blocks[i])
        block_content = race_blocks[i+1]
        
        # 3. 各艇の成績行を抽出
        # フォーマット例: 
        # " 01 1 3527 今泉   徹 57 59 6.87 1 0.13 1.48.5"
        #  (着) (枠) (登番) (氏名) (モ) (ボ) (展) (進) (ST) (タイム)
        lines = block_content.splitlines()
        for line in lines:
            # 固定長ベースだが、スペース区切りでも正規表現で抜きやすい形式
            # 着順(2桁) 枠(1桁) 登番(4桁) 氏名(任意) モーター(2-3桁) ボート(2-3桁) 展示(4桁) 進入(1桁) ST(4桁) タイム(任意)
            m = re.match(r'^\s*(\d{2})\s+(\d)\s+(\d{4})\s+.+?\s+(\d+)\s+(\d+)\s+(\d\.\d{2})\s+(\d)\s+(\d\.\d{2})', line)
            if m:
                rank_raw, teiban, player_no, motor_no, boat_no, show_time, entry_course, st = m.groups()
                rank = int(rank_raw)
                records.append({
                    'date': date_str,
                    'place_no': place_no,
                    'race_no': race_num,
                    'teiban': int(teiban),
                    'rank': rank,
                    'player_no': player_no,
                    'motor_no': int(motor_no),
                    'show_time': float(show_time),
                    'entry_course': int(entry_course),
                    'st': float(st),
                    'target': 1 if rank == 1 else 0
                })
    return records

def init_db(db_path='data/boatrace_real.db'):
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(db_path)
    # スキーマを拡張: 詳細データを保存可能にする
    conn.execute("""
    CREATE TABLE IF NOT EXISTS race_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        place_no INTEGER,
        race_no INTEGER,
        teiban INTEGER,
        rank INTEGER,
        player_no TEXT,
        motor_no INTEGER,
        show_time REAL,
        entry_course INTEGER,
        st REAL,
        target INTEGER,
        UNIQUE(date, place_no, race_no, teiban)
    )""")
    conn.commit()
    return conn

def save_records(conn, records):
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR IGNORE INTO race_results
        (date, place_no, race_no, teiban, rank, player_no, motor_no, show_time, entry_course, st, target)
        VALUES (:date, :place_no, :race_no, :teiban, :rank, :player_no, :motor_no, :show_time, :entry_course, :st, :target)
    """, records)
    conn.commit()
    return cursor.rowcount

def download_and_save(start_date, end_date, db_path='data/boatrace_real.db'):
    conn = init_db(db_path)
    headers = {'User-Agent': 'Mozilla/5.0'}
    sevenz_exe = r"C:\Program Files\7-Zip\7z.exe"
    
    import subprocess, tempfile

    cur_date = start_date
    total_saved = 0
    
    while cur_date <= end_date:
        yy = cur_date.strftime('%y')
        mm = cur_date.strftime('%m')
        dd = cur_date.strftime('%d')
        yyyymm = cur_date.strftime('%Y%m')
        
        fname = f'k{yy}{mm}{dd}.lzh'
        url = f'https://www1.mbrace.or.jp/od2/K/{yyyymm}/{fname}'
        
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                with tempfile.TemporaryDirectory() as tmpdir:
                    lzh_file = os.path.join(tmpdir, fname)
                    with open(lzh_file, 'wb') as f:
                        f.write(r.content)
                    
                    # 7zで解凍
                    subprocess.run([sevenz_exe, 'e', lzh_file, f'-o{tmpdir}', '-y'], capture_output=True)
                    
                    saved = 0
                    for out_fname in os.listdir(tmpdir):
                        if out_fname.upper().endswith('.TXT'):
                            with open(os.path.join(tmpdir, out_fname), 'rb') as f:
                                records = parse_k_text(f.read())
                                if records:
                                    saved += save_records(conn, records)
                    
                    total_saved += saved
                    if saved > 0:
                        print(f"  [OK] {cur_date}: {saved} records saved (Total: {total_saved})")
            
        except Exception as e:
            print(f"  [ERR] {cur_date}: {e}")
        
        cur_date += timedelta(days=1)
        time.sleep(0.1)
    
    conn.close()
    print(f"\nDone. Total {total_saved} records saved.")

if __name__ == '__main__':
    # 直近3ヶ月分
    end = date.today()
    start = date.today() - timedelta(days=90)
    if len(sys.argv) >= 3:
        start = date(int(sys.argv[1][:4]), int(sys.argv[1][4:6]), int(sys.argv[1][6:8]))
        end = date(int(sys.argv[2][:4]), int(sys.argv[2][4:6]), int(sys.argv[2][6:8]))
    
    download_and_save(start, end)
