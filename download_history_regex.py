import requests
import re
import sqlite3
import os
import time
from datetime import datetime, timedelta

def init_db(db_path="data/boatrace.db"):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS race_results (
            date TEXT,
            place_no TEXT,
            race_no INTEGER,
            rank1_teiban INTEGER,
            rank2_teiban INTEGER,
            rank3_teiban INTEGER,
            sanrentan_money INTEGER,
            UNIQUE(date, place_no, race_no)
        )
    ''')
    conn.commit()
    return conn

def scrape_race_result(date_str, place_no, race_no, conn):
    url = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return False
            
        html = res.text.replace('\n', '').replace('\r', '').replace('\t', '')
        
        # 着順の取得 (正規表現で 1着, 2着, 3着 の行を探す)
        # HTMLの構造: <td class="is-fs14 is-fBold is-lh24 is-pB0">1</td> <td class="is-fs14 is-fBold is-lh24 is-pB0"><span class="is-boatColor1">1</span></td>
        # かなり複雑なので、よりシンプルに「着」と「艇番」を並び順で取得する
        
        ranks = []
        # <tbody class="is-p10-0"> の中の最初の <tr> ブロック群が着順
        match_tbody = re.search(r'<tbody class=\"is-p10-0\">(.*?)</tbody>', html)
        if match_tbody:
            tbody_html = match_tbody.group(1)
            # 各行の tr を取得
            trs = re.findall(r'<tr.*?>(.*?)</tr>', tbody_html)
            for tr in trs:
                # tdの中のテキストを抽出
                tds = re.findall(r'<td.*?>(.*?)</td>', tr)
                if len(tds) >= 3:
                    # 最初のtdが着順(例: '1'), 2番目が艇番(例: '<span class="...">1</span>')
                    rank_str = re.sub(r'<[^>]+>', '', tds[0]).strip()
                    teiban_str = re.sub(r'<[^>]+>', '', tds[1]).strip()
                    
                    if rank_str in ['1', '2', '3'] and teiban_str in ['1', '2', '3', '4', '5', '6']:
                        ranks.append((int(rank_str), int(teiban_str)))

        if len(ranks) < 3:
            return False
            
        # 1着,2着,3着をソートして確保
        r1 = next((r[1] for r in ranks if r[0] == 1), None)
        r2 = next((r[1] for r in ranks if r[0] == 2), None)
        r3 = next((r[1] for r in ranks if r[0] == 3), None)
        
        if not r1 or not r2 or not r3:
            return False
            
        # 3連単の払戻金の取得
        # 3連単の行: <th ...>3連単</th> <td ...> <div ...> <span ...>1-2-3</span> ... </div> </td> <td ...> <div ...> <span ...>¥1,230</span> ...
        sanrentan_money = 0
        match_3rentan = re.search(r'3連単.*?¥([0-9,]+)', html)
        if match_3rentan:
            # カンマを除去して数値に変換
            money_str = match_3rentan.group(1).replace(',', '')
            sanrentan_money = int(money_str)
                
        if sanrentan_money > 0:
            cur = conn.cursor()
            cur.execute('''
                INSERT OR IGNORE INTO race_results 
                (date, place_no, race_no, rank1_teiban, rank2_teiban, rank3_teiban, sanrentan_money)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (date_str, place_no, race_no, r1, r2, r3, sanrentan_money))
            conn.commit()
            return True
        else:
            return False

    except Exception as e:
        # print(f"[{place_no}R{race_no}] Error: {e}")
        return False

def collect_historical_data(start_date, end_date):
    conn = init_db()
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        print(f"--- Collecting data for {date_str} ---")
        
        for place_no in range(1, 25):
            place_str = str(place_no).zfill(2)
            success_count = 0
            for race_no in range(1, 13):
                if scrape_race_result(date_str, place_str, race_no, conn):
                    success_count += 1
                time.sleep(0.3)
                
            if success_count > 0:
                print(f"  Saved {success_count} races for place {place_str}")
                
        current_date += timedelta(days=1)
        
    conn.close()

if __name__ == "__main__":
    today = datetime.now()
    start = today - timedelta(days=2)
    end = today - timedelta(days=1)
    collect_historical_data(start, end)
