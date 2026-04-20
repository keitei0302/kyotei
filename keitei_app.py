from playwright.sync_api import sync_playwright
import numpy as np
import warnings
import os
import re
import json
import sys
import argparse
import pickle
import pandas as pd
from datetime import datetime, timedelta, timezone

def get_jst_now():
    """日本標準時 (JST) を取得"""
    return datetime.now(timezone(timedelta(hours=9)))

from bs4 import BeautifulSoup
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

def create_session():
    """リトライ設定付きのrequestsセッションを作成"""
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))
    return session

session = create_session()

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────
# 共通設定・ロギング
# ──────────────────────────────────────────
CACHE_DIR = "cache"
DATA_DIR = "data"
if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

class ConfidenceManager:
    """ベイズ更新によるユーザー確信度（Confidence Score）の管理"""
    def __init__(self, log_path="data/daily_features.jsonl"):
        self.log_path = log_path
        self.base_confidence = 1.0

    def get_confidence_score(self, teiban):
        """
        過去のログから『ユーザーがn号艇を推した時の的中率』を算出し、
        確信度係数を算出する。的中率が高いほど係数が強化される。
        """
        try:
            if not os.path.exists(self.log_path):
                return self.base_confidence

            # 簡易的な的中率分析（プロトタイプ）
            # 本来はレース結果(rank)と照合して的中・不的中を判定するが、
            # 現状はデータ蓄積を優先し、デフォルト値を返す基盤として実装
            # ※将来的にスプレッドシートやJSONLを解析して動的に更新
            return self.base_confidence # 学習データが蓄積されるまで1.0
        except:
            return self.base_confidence

confidence_manager = ConfidenceManager()

# ──────────────────────────────────────────
# データ取得系
# ──────────────────────────────────────────

def get_beforeinfo(place_no, race_no, date_str):
    """直前情報ページから展示タイム・チルト角度・プロペラ交換情報を取得（動的カラム特定版）"""
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    result = {i: {'show_time': 0.0, 'tilt': 0.0, 'propeller': False, 'lap_time': 0.0, 'turn_time': 0.0, 'straight_time': 0.0, 'parts_exchange': 'なし', 'start_exhibition': None} for i in range(1, 7)}
    try:
        res = session.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.content, 'html.parser')

        # 1. ヘッダーから列インデックスを特定
        show_idx = 4  # デフォルト
        tilt_idx = 5  # デフォルト
        parts_idx = 7 # デフォルト
        
        table = soup.find('div', class_='contentsFrame')
        if table:
            table = table.find('table')
        if table:
            thead = table.find('thead')
            if thead:
                ths = thead.find_all('th')
                for i, th in enumerate(ths):
                    txt = th.get_text(strip=True)
                    if '展示タイム' in txt: show_idx = i
                    elif 'チルト' in txt: tilt_idx = i
                    elif '部品' in txt: parts_idx = i

        # 2. 展示タイム・チルト・部品交換の取得
        tbodies = soup.find_all('tbody', class_='is-fs12')
        for tbody in tbodies[:6]:
            td_teiban = tbody.find('td', class_=re.compile(r'is-boatColor'))
            if not td_teiban: continue
            try:
                t_num = int(td_teiban.get_text(strip=True))
                if not (1 <= t_num <= 6): continue
                
                # 最初に行（tr）を取得し、その中の1行目（展示タイムがある行）を対象にする
                rows = tbody.find_all('tr')
                if rows:
                    tds = rows[0].find_all('td')
                    if len(tds) > max(show_idx, tilt_idx):
                        show_time_str = tds[show_idx].get_text(strip=True)
                        tilt_str = tds[tilt_idx].get_text(strip=True)
                        
                        try:
                            val = float(show_time_str)
                            if 6.0 <= val <= 8.0: result[t_num]['show_time'] = val
                        except: pass
                        
                        try:
                            # チルトは "-0.5" などの形式
                            val = float(tilt_str)
                            if -0.5 <= val <= 3.0: result[t_num]['tilt'] = val
                        except: pass

                    # 部品交換は1行目か2行目にある可能性があるが、通常は1行目のパーツ列
                    if len(tds) > parts_idx:
                        p_txt = tds[parts_idx].get_text(strip=True)
                        if p_txt and p_txt != 'なし':
                            result[t_num]['parts_exchange'] = p_txt
            except: pass

        # 3. プロペラ交換情報の取得
        prop_th = soup.find('th', string=re.compile(r'プロペラ'))
        if prop_th:
            p_table = prop_th.find_parent('table')
            if p_table:
                for tr in p_table.find_all('tr'):
                    tds = tr.find_all('td')
                    if len(tds) >= 2:
                        try:
                            num = int(tds[0].get_text(strip=True))
                            if "新" in tds[1].get_text(): result[num]['propeller'] = True
                        except: pass

        # 4. オリジナル展示タイム（Boatcast）の取得
        try:
            r_str, p_str = str(race_no).zfill(2), str(place_no).zfill(2)
            bc_url = f"https://race.boatcast.jp/txt/{p_str}/bc_oriten_{date_str}_{p_str}_{r_str}.txt"
            res_bc = session.get(bc_url, timeout=10)
            if res_bc.status_code == 200:
                res_bc.encoding = res_bc.apparent_encoding
                lines = res_bc.text.strip().split('\n')
                
                cols = {"lap": None, "turn": None, "strt": None}
                for line in lines:
                    if "周" in line or "まわり" in line:
                        parts = line.split('\t') if '\t' in line else line.split()
                        for i, p in enumerate(parts):
                            if "周" in p: cols["lap"] = i
                            if "まわり" in p: cols["turn"] = i
                            if "直" in p: cols["strt"] = i
                        break
                
                for line in lines:
                    # 数字で始まる行を探す
                    if re.match(r'^\d+', line.strip()):
                        parts = line.split('\t') if '\t' in line else line.split()
                        try:
                            t_num = int(parts[0].strip())
                            if 1 <= t_num <= 6:
                                # 数値（小数点あり・なし両方）を抽出
                                nums = re.findall(r'\d+\.\d+|\d+', line)
                                # 最初の要素（艇番）を除外
                                values = nums[1:]
                                if len(values) >= 3:
                                    # [Lap, Turn, Straight] の順で並ぶことが多い
                                    # 前段階で取得した tilt を破壊しないよう、慎重に代入
                                    try: result[t_num]['lap_time'] = float(values[0])
                                    except: pass
                                    try: result[t_num]['turn_time'] = float(values[1])
                                    except: pass
                                    try: result[t_num]['straight_time'] = float(values[2])
                                    except: pass
                        except: pass
        except: pass

        # 5. スタート展示の取得
        try:
            times = soup.find_all('span', class_=re.compile('table1_boatImage1Time'))
            boat_icons = soup.find_all('span', class_=re.compile('table1_boatImage1My'))
            if len(times) == len(boat_icons) and len(times) >= 6:
                for b, t in zip(boat_icons, times):
                    cls = b.get('class', [])
                    for c in cls:
                        if c.startswith('is-type'):
                            b_num = int(c[-1])
                            txt = t.get_text(strip=True)
                            is_f = 'F' in txt
                            val_str = txt.replace('F', '').replace('L', '').strip()
                            try:
                                val = float(val_str)
                                if is_f: val = -val
                                result[b_num]['start_exhibition'] = val
                            except: pass
        except Exception as e:
            print(f"[StartExhibition] Error: {e}")

    except Exception as e:
        print(f"[BeforeInfo] Error: {e}")
    return result

    return result

def get_odds3t(place_no, race_no, date_str):
    """3連単オッズ取得（キャッシュ対応）"""
    cache_path = os.path.join(CACHE_DIR, f"odds_{place_no}_{race_no}_{date_str}.json")
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f: return json.load(f)

    url = f"https://www.boatrace.jp/owpc/pc/race/odds3t?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    odds_dict = {}
    try:
        res = session.get(url, headers=headers, timeout=25)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.content, 'html.parser')
        tables = soup.select('div.contentsFrame table')
        if tables:
            for table in tables:
                rows = table.find_all('tr')
                cur_1, cur_2 = None, None
                for row in rows:
                    tds = row.find_all(['th', 'td'])
                    if not tds: continue
                    if 'is-boatColor' in str(tds[0]):
                        cur_1 = tds[0].get_text(strip=True); start_idx = 1
                    else: start_idx = 0
                    p2 = None
                    for td in tds[start_idx:]:
                        if 'is-boatColor' in str(td) and td.get_text(strip=True) != cur_1:
                            cur_2 = td.get_text(strip=True); p2 = td; break
                    cells = tds[tds.index(p2)+1:] if p2 else (tds if (cur_1 and cur_2) else [])
                    for i in range(0, len(cells)-1, 2):
                        t3 = cells[i].get_text(strip=True)
                        v = cells[i+1].get_text(strip=True).replace(',', '')
                        if t3.isdigit() and v.replace('.', '').isdigit():
                            odds_dict[f"{cur_1}-{cur_2}-{t3}"] = float(v)
        if odds_dict:
            with open(cache_path, "w") as f: json.dump(odds_dict, f)
    except: pass
    return odds_dict

def get_race_result(place_no, race_no, date_str):
    """レース結果を取得（3連単組番から着順を逆引き）"""
    url = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    result = {"rank": [], "dividends": {}}
    try:
        res = session.get(url, headers=headers, timeout=30)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.content, 'html.parser')
        full_text = soup.get_text(separator=' ')

        # ── 3連単配当の取得 ──
        # より柔軟な正規表現（セパレータが ハイフン、エンダッシュ、マイナス等に対応）
        div_pat = re.search(
            r'3連単\s+(\d)\s*[-–－—]\s*(\d)\s*[-–－—]\s*(\d)\s+[¥￥]?([\d,]+)',
            full_text
        )
        if div_pat:
            t1 = int(div_pat.group(1))
            t2 = int(div_pat.group(2))
            t3 = int(div_pat.group(3))
            combo = f"{t1}-{t2}-{t3}"
            result["rank"] = [t1, t2, t3]  # 3連単の組番 = 1〜3着
            # カンマを除去せずに、表示用としてそのまま保存（または統一して数字のみにする）
            price_clean = div_pat.group(4).replace(',', '')
            result["dividends"]["3連単"] = {"combo": combo, "price": f"{int(price_clean):,}"}

        # ── フォールバック: CSSクラス is-isN から着順を取得 ──
        if not result["rank"]:
            ZENKAKU_MAP = {'１':1,'２':2,'３':3,'４':4,'５':5,'６':6}
            ranks = {}
            for table in soup.find_all('table'):
                for tr in table.find_all('tr'):
                    tds = tr.find_all('td')
                    if len(tds) < 1: continue
                    # 1着〜3着の文字を探す
                    raw = tds[0].get_text(strip=True)
                    rank_num = ZENKAKU_MAP.get(raw) or (int(raw) if raw.isdigit() and 1 <= int(raw) <= 3 else None)
                    if rank_num is None: continue
                    
                    # その行から艇番を探す
                    for td in tds:
                        cls_str = ' '.join(td.get('class', []))
                        for k in range(1, 7):
                            if f'is-is{k}' in cls_str:
                                ranks[rank_num] = k; break
                        if rank_num in ranks: break
            if ranks and len(ranks) >= 3:
                result["rank"] = [ranks[i] for i in sorted(ranks.keys()) if i in ranks][:3]

    except Exception as e:
        print(f"[Result] Error: {e}")
    return result

def get_today_players(place_no, race_no, date_str):
    """当日の出走表を取得"""
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = session.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # 締切予定時刻の取得
        deadline = ""
        th = soup.find('th', string=lambda s: s and '締切予定時刻' in s)
        if th:
            table = th.find_parent('table')
            if table:
                trs = table.find_all('tr')
                if len(trs) >= 2:
                    times = [td.text.strip() for td in trs[1].find_all('td')]
                    if len(times) >= int(race_no):
                        deadline = times[int(race_no)-1]

        def _safe_float(s, default=0.0):
            try: return float(s)
            except (ValueError, TypeError): return default

        results = []
        tbodies = soup.find_all('tbody', class_='is-fs12')
        for i, tbody in enumerate(tbodies[:6]): 
            p = {"teiban": i + 1}
            # 選手名の取得
            name_el = tbody.find('div', class_='is-fs18')
            p['name'] = name_el.text.strip().replace(' ', '').replace('\u3000', '') if name_el else f"Player{i+1}"
            
            # 登録番号の取得
            toban_el = tbody.find('div', class_='is-fs11')
            if toban_el:
                p['toban'] = toban_el.text.strip().split('/')[0] # 「4444 / A1」などから抽出
            
            # 勝率等の取得
            trs = tbody.find_all('tr')
            if trs:
                tds = trs[0].find_all('td')
                if len(tds) >= 8:
                    st_txt = tds[3].text.strip()
                    p['ST'] = _safe_float(st_txt.split()[-1], 0.15) if st_txt.split() else 0.15
                    p['win_rate'] = _safe_float(tds[4].text.split()[0], 0.0) if tds[4].text.split() else 0.0 # 全国勝率
                    p['local_win_rate'] = _safe_float(tds[5].text.split()[0], 0.0) if len(tds) > 5 and tds[5].text.split() else 0.0 # 当地勝率
                    p['motor_2ren'] = _safe_float(tds[6].text.split()[1], 0.0) if len(tds[6].text.split()) > 1 else 0.0
            
            # 節間成績の取得 (着順の平均と節間ST平均)
            p['section_results'] = []
            p['section_st_avg'] = 0.0
            if len(trs) >= 3:
                # 3行目が節間成績であることが多い（公式ページ構造）
                results_tds = trs[2].find_all('td')
                # ※必要に応じて詳細なスクレイピングを補強
            
            results.append(p)
        return {"players": results, "deadline": deadline} if len(results) == 6 else None
    except Exception as e:
        print(f"[TodayPlayers] Error: {e}")
        return None

import urllib.request
def get_player_course_data(toban):
    # 選手のコース別成績（1〜6コースの1着率、2着率等）を取得
    # （逃げ率、差し率等として活用）
    url = f"https://www.boatrace.jp/owpc/pc/data/racersearch/course?toban={toban}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            soup = BeautifulSoup(res.read(), 'html.parser')
            
        course_stats = {}
        # 1着回数、出走回数などを探す
        tbodies = soup.find_all('tbody', class_='is-p10-0')
        for tbody in tbodies:
            tds = tbody.find_all('td')
            if len(tds) > 10:
                # コース番号は行の最初の方にあるか、表の構造から推定
                pass # 詳細パースは後続で
        return course_stats
    except Exception as e:
        print(f"[CourseData] Error ({toban}): {e}")
        return {}

# ──────────────────────────────────────────
# AI予測・戦術解析
# ──────────────────────────────────────────

def predict_race(place_no, race_no, date_str, players_df):
    """新AIモデル(LGBM)による予測 + 直前情報の反映"""
    try:
        model_path, encoder_path = "models/lgb_model.pkl", "models/label_encoders.pkl"
        if not os.path.exists(model_path): return players_df
        with open(model_path, "rb") as f: model = pickle.load(f)
        with open(encoder_path, "rb") as f: encoders = pickle.load(f)
        
        before_info = get_beforeinfo(place_no, race_no, date_str)
        records = []
        for i, row in players_df.iterrows():
            t = int(row['teiban'])
            bi = before_info.get(t, {'show_time': 6.8, 'propeller': False})
            records.append({
                'place_no': str(place_no), 'teiban': str(t), 'motor_no': '1',
                'show_time': float(bi['show_time']), 'entry_course': t, 'st': 0.15
            })
        X = pd.DataFrame(records)
        for col, le in encoders.items():
            X[col] = X[col].map(lambda s: s if s in le.classes_ else le.classes_[0])
            X[col] = le.transform(X[col].astype(str))
        
        players_df['ai_prob'] = model.predict(X.values.astype(np.float32))
        players_df['show_time'] = [before_info.get(int(t), {}).get('show_time', 0.0) for t in players_df['teiban']]
        players_df['propeller'] = [before_info.get(int(t), {}).get('propeller', False) for t in players_df['teiban']]
        players_df['lap_time'] = [before_info.get(int(t), {}).get('lap_time', 0.0) for t in players_df['teiban']]
        players_df['turn_time'] = [before_info.get(int(t), {}).get('turn_time', 0.0) for t in players_df['teiban']]
        players_df['straight_time'] = [before_info.get(int(t), {}).get('straight_time', 0.0) for t in players_df['teiban']]
        players_df['start_exhibition'] = [before_info.get(int(t), {}).get('start_exhibition', None) for t in players_df['teiban']]
    except:
        players_df['ai_prob'] = 1/6
        players_df['show_time'] = 0.0
        players_df['propeller'] = False
        players_df['lap_time'] = 0.0
        players_df['turn_time'] = 0.0
        players_df['straight_time'] = 0.0
        players_df['start_exhibition'] = None
    return players_df


def apply_user_intuition(df_pred):
    # 新しい強力な補正ロジック (AIスコア + 各種最新データのダイナミック補正)
    df_pred['custom_prob'] = df_pred['ai_prob'].copy()
    
    # 型安全の保証 (スクレイピングデータ由来の文字列混入を防ぎ、比較演算でのTypeErrorを防止)
    for col in ['show_time', 'lap_time', 'turn_time', 'straight_time']:
        if col in df_pred.columns:
            df_pred[col] = pd.to_numeric(df_pred[col], errors='coerce').fillna(0.0)

    # 全艇の平均値を計算して偏差を評価しやすくする
    valid_show = df_pred[df_pred['show_time'] > 0]['show_time']
    avg_st = valid_show.mean() if not valid_show.empty else 0
    valid_lap = df_pred[df_pred['lap_time'] > 0]['lap_time']
    avg_lap = valid_lap.mean() if not valid_lap.empty else 0
    valid_turn = df_pred[df_pred['turn_time'] > 0]['turn_time']
    avg_turn = valid_turn.mean() if not valid_turn.empty else 0
    valid_straight = df_pred[df_pred['straight_time'] > 0]['straight_time']
    avg_straight = valid_straight.mean() if not valid_straight.empty else 0

    for i, row in df_pred.iterrows():
        score = row['ai_prob']
        
        # --- 1. 勝率アドバンテージ ---
        win_rate = row.get('win_rate', 0.0)
        local_win = row.get('local_win_rate', win_rate)
        avg_win_rate = (win_rate + local_win) / 2
        
        # A1級や勝率上位レーサーへのベース加点
        if avg_win_rate >= 7.0: score += 0.15
        elif avg_win_rate >= 6.0: score += 0.08
        elif avg_win_rate < 4.0: score -= 0.08
        
        # 当地が極端に高い（当地巧者）
        if local_win - win_rate >= 1.0 and local_win >= 6.0:
            score += 0.08
            
        # --- 2. 展示タイムとオリジナル展示タイム (Boatcast) ---
        # 展示(行き足~伸び)の評価
        if avg_st > 0 and row.get('show_time', 0) > 0:
            diff_st = avg_st - row['show_time']
            score += diff_st * 3.0  # 展示1番時計は大きく加点
            
        # 一周タイム(総合力)の評価
        if avg_lap > 0 and row.get('lap_time', 0) > 0:
            diff_lap = avg_lap - row['lap_time']
            score += diff_lap * 2.5
            
        # まわり足(ターン回り)の評価
        if avg_turn > 0 and row.get('turn_time', 0) > 0:
            diff_turn = avg_turn - row['turn_time']
            score += diff_turn * 3.0
            
        # 直線タイム(伸び)の評価
        if avg_straight > 0 and row.get('straight_time', 0) > 0:
            diff_straight = avg_straight - row['straight_time']
            score += diff_straight * 1.5

        # --- 3. コース・モーター・ST（スタート想定）と能力評価の連動 ---
        course = int(row['teiban'])
        motor_2ren = row.get('motor_2ren', 0.0)
        st_timing = row.get('ST', 0.15)
        st_ex = row.get('start_exhibition', None)
        
        diff_st = 0
        is_fast_but_low_skill = False
        
        if pd.notna(st_ex):
            # 前提(展示ST)よりも想定ST(平均ST)が早い(差分が-0.03より小さい)場合
            diff_st = st_timing - st_ex
            
            if diff_st <= -0.03:
                # 突き抜け(とても有利)
                if avg_win_rate >= 6.0:
                    score += 0.20
                else:
                    score += 0.05
                    is_fast_but_low_skill = True # 後続艇が有利になる展開フラグ
            
            # 展示STが早い(スリット優勢、握り率が高い)場合の捲り・捲り差し
            if st_ex < 0.10 and course in [3, 4, 5]:
                if avg_win_rate >= 5.5:
                    score += 0.15
                else:
                    score += 0.05
                    is_fast_but_low_skill = True
        
        # 1号艇・2号艇の評価（ST予測は早いだけで有利とはならない。能力が高ければ多少遅くても逃げる/差す）
        if course == 1:
            if avg_win_rate >= 6.5:
                # STが少々遅くても(0.18等)逃げ切れる
                if st_timing <= 0.18:
                    score += 0.20
            else:
                if st_timing < 0.15:
                    score += 0.15
            
            if motor_2ren >= 40.0:
                score += 0.10
            elif motor_2ren < 30.0:
                score -= 0.10
        elif course == 2:
            if avg_win_rate >= 6.0:
                score += 0.15 # 2コースの差し
        else:
            if st_timing < 0.14 and avg_win_rate >= 6.0:
                score += 0.12 # ダッシュ・センターの一発
                
        # 後で後続艇を加点するためのフラグをDataFrameに記録
        df_pred.at[i, 'is_fast_but_low_skill'] = is_fast_but_low_skill
                
        # --- 4. 部品交換情報 ---
        parts = str(row.get('parts_exchange', 'なし'))
        if parts != 'なし':
            if 'リング' in parts:
                score += 0.03 # 整備での良化期待
            elif 'ピストン' in parts or 'シリンダ' in parts or 'クランク' in parts:
                score -= 0.08 # 大掛かりな整備は機力難の証拠であることが多い
            elif 'キャブレタ' in parts or 'キャリアボデ' in parts:
                score -= 0.04
                
        if row.get('propeller', False):
            # 新ペラは原則マイナスだが、勝率が高い(A1級)なら調整合わせてくる可能性
            if avg_win_rate < 6.0:
                score -= 0.05
            else:
                score -= 0.02
        
        # --- 5. ベイズ更新エンジンによる確信度補正 (Slider_Value x Confidence_Score) ---
        # ユーザーがスライダー（フロントエンド）で調整した際の「効き目」を過去実績から強化する基盤
        confidence_score = confidence_manager.get_confidence_score(int(row['teiban']))
        # 最終スコアへの反映（内部エンジン側での基本重み付け）
        score = score * confidence_score

        df_pred.at[i, 'custom_prob'] = max(0.01, score)
        
    # --- 後続艇への波及評価 ---
    # is_fast_but_low_skill フラグが立っている艇の外側艇の期待値を上げる
    for i, row in df_pred.iterrows():
        if row.get('is_fast_but_low_skill', False):
            c = int(row['teiban'])
            for j, r in df_pred.iterrows():
                if int(r['teiban']) == c + 1:
                    df_pred.at[j, 'custom_prob'] += 0.10 # 捲りの展開に乗る
                elif int(r['teiban']) == c + 2:
                    df_pred.at[j, 'custom_prob'] += 0.05
                    
    # スコアの正規化
    total = df_pred['custom_prob'].sum()
    if total > 0:
        df_pred['custom_prob'] = df_pred['custom_prob'] / total
        
    # FastAPIやJSON出力でエラーにならないようNumPy型をネイティブfloatに変換し、NaNを除去
    df_pred['ai_prob'] = df_pred['ai_prob'].astype(float)
    df_pred['custom_prob'] = df_pred['custom_prob'].astype(float)
    df_pred = df_pred.fillna(0)
    
    return df_pred
# ──────────────────────────────────────────
# UI・描画
# ──────────────────────────────────────────

def draw_slit_diagram(players):
    print("\n【スリット隊形予想】")
    for p in players:
        dist = max(0, min(30, int((0.25 - p.get('ST', 0.15)) / 0.15 * 30)))
        print(f" |{' '*dist}{p['teiban']}号艇> (ST {p.get('ST',0.15):.2f}) {p['name']}")
    print(" |" + "-"*40)

def display_condensed_info(players, beforeinfo, df_pred):
    """情報を1行に凝縮表示（ヘッダーはmain側で出力）"""
    show_times = [bi.get('show_time', 0.0) for bi in beforeinfo.values() if bi.get('show_time', 0.0) > 0]
    avg = sum(show_times) / len(show_times) if show_times else 0
    for p in players:
        t = int(p['teiban'])
        bi = beforeinfo.get(t, {})
        st = bi.get('show_time', 0.0)
        diff = st - avg if avg > 0 and st > 0 else 0
        diff_str = f"({diff:+.2f})" if st > 0 else "(--)"
        score = df_pred[df_pred['teiban'] == t]['final_score'].iloc[0] * 100
        tags = []
        if diff < -0.05: tags.append("★一番時計")
        elif diff < 0: tags.append("気配良")
        if p.get('win_rate', 0) > 6.5: tags.append("格上")
        print(f"{t:<2} {p['name']:<15} {p['win_rate']:>4.2f}/{p['ST']:>4.2f}  "
              f"{st:>4.2f}{diff_str:<6} {score:>5.1f}pt     {' '.join(tags)}")
    print("="*85)

places = {"桐生":"01","戸田":"02","江戸川":"03","平和島":"04","多摩川":"05","浜名湖":"06","蒲郡":"07","常滑":"08","津":"09","三国":"10","びわこ":"11","住之江":"12","尼崎":"13","鳴門":"14","丸亀":"15","児島":"16","宮島":"17","徳山":"18","下関":"19","若松":"20","芦屋":"21","福岡":"22","唐津":"23","大村":"24"}

def main():
    print("\n" + "="*60 + "\n   KEITEI AI - Phase 3 (UI凝縮 & 的中判定)\n" + "="*60)
    place_in = input("場名またはコード: ").strip()
    race_in = input("レース(1-12): ").strip()
    try:
        p_no = places[place_in] if place_in in places else place_in.zfill(2)
        r_no = int(race_in)
    except: return

    # 日本時間 (JST) を取得して日付を判定
    now_jst = get_jst_now()
    # 午前5時までは前日扱いとする（ナイター・ミッドナイト開催考慮）
    target_date = now_jst - (timedelta(days=1) if now_jst.hour < 5 else timedelta(0))
    d_str = target_date.strftime("%Y%m%d")

    p_data = get_today_players(p_no, r_no, d_str)
    if not p_data:
        place_name = [k for k, v in places.items() if v == p_no]
        p_name = place_name[0] if place_name else p_no
        print(f"\n[エラー] {p_name} {r_no}R の出走表データが取得できませんでした。")
        print("本日の開催がないか、レースが終了している可能性があります。対象のレース場が本日開催しているかご確認ください。")
        return
    players = p_data["players"]
    deadline = p_data["deadline"]
    
    before = get_beforeinfo(p_no, r_no, d_str)
    df = pd.DataFrame(players)
    df = predict_race(p_no, r_no, d_str, df)
    df = apply_user_intuition(df)
    df['final_score'] = df['custom_prob']
    
    odds = get_odds3t(p_no, r_no, d_str)
    bet_results = []
    if odds:
        ts = df['final_score'].sum()
        for c, v in odds.items():
            t1, t2, t3 = map(int, c.split('-'))
            p1 = df[df['teiban']==t1]['final_score'].iloc[0]/ts
            p2 = df[df['teiban']==t2]['final_score'].iloc[0]/(ts-p1*ts)
            p3 = df[df['teiban']==t3]['final_score'].iloc[0]/(ts-(p1+p2)*ts)
            bet_results.append({'combo':c, 'prob':p1*p2*p3, 'odds':v, 'ev':p1*p2*p3*v})
    
    df_bets = pd.DataFrame(bet_results)
    
    # 締切時刻をヘッダーに表示
    time_header = f"  【 {deadline} 締切 】" if deadline else ""
    print(f"\n{'='*30}{time_header}{'='*(55-len(time_header))}")
    print(f"{'艇':<2} {'選手名':<15} {'勝率/ST':<12} {'展示(差)':<13} {'総合スコア':<12} {'気配'}")
    print("-" * 85)
    display_condensed_info(players, before, df)
    draw_slit_diagram(players)

    # ── 結果を先に取得（買い目表示に使う）──
    hit_combo = None
    hit_price = None
    try:
        res = get_race_result(p_no, r_no, d_str)
        if res and res.get("rank"):
            hit_combo = "-".join(map(str, res["rank"]))
            hit_price = res.get("dividends", {}).get("3連単", {}).get("price", "---")
    except Exception as e:
        print(f"[Debug] Result Check Error: {e}")

    # ── 買い目表示（的中をインラインで表示）──
    print("\n======= 【 推奨 8点 】 =======")
    final_bets = []

    def fmt_bet(label, combo, detail):
        mark = f"  ← \033[32m★的中！ ¥{hit_price}\033[0m" if combo == hit_combo else ""
        print(f"  [{label}] \033[1m{combo}\033[0m {detail}{mark}")
        return combo

    def get_suji_multiplier(combo):
        try:
            r1, r2, r3 = map(int, combo.split('-'))
            suji_patterns = {
                "1-23-234": lambda: r1==1 and r2 in [2,3] and r3 in [2,3,4],
                "1-3-245": lambda: r1==1 and r2==3 and r3 in [2,4,5],
                "1-4-235": lambda: r1==1 and r2==4 and r3 in [2,3,5],
                "1-5-全": lambda: r1==1 and r2==5,
                "2-1-34": lambda: r1==2 and r2==1 and r3 in [3,4],
                "2-34-345": lambda: r1==2 and r2 in [3,4] and r3 in [3,4,5],
                "2-56-全": lambda: r1==2 and r2 in [5,6],
                "3-1-24": lambda: r1==3 and r2==1 and r3 in [2,4],
                "3-2-45": lambda: r1==3 and r2==2 and r3 in [4,5],
                "3-45-126": lambda: r1==3 and r2 in [4,5] and r3 in [1,2,6],
                "4-12-125": lambda: r1==4 and r2 in [1,2] and r3 in [1,2,5],
                "4-5-16": lambda: r1==4 and r2==5 and r3 in [1,6],
                "5-16-全": lambda: r1==5 and r2 in [1,6],
                "5-4-16": lambda: r1==5 and r2==4 and r3 in [1,6],
                "6-12-全": lambda: r1==6 and r2 in [1,2],
                "6-145-全": lambda: r1==6 and (r2 in [4,5] or r2==1)
            }
            for name, condition in suji_patterns.items():
                if condition(): return 1.35, name
        except: pass
        return 1.0, ""

    if not df_bets.empty:
        # オッズあり: EV（期待値）に対してスジ補正をかける
        df_bets['adjusted_ev'] = 0.0
        df_bets['suji_name'] = ""
        for i, r in df_bets.iterrows():
            mul, s_name = get_suji_multiplier(r['combo'])
            df_bets.at[i, 'adjusted_ev'] = r['ev'] * mul
            df_bets.at[i, 'suji_name'] = s_name
            
        # スコア上位8点を抽出
        tops = df_bets.sort_values(by='adjusted_ev', ascending=False).head(8)
        
        for idx, (i, r) in enumerate(tops.iterrows()):
            label = "本命" if idx < 2 else ("期待" if idx < 6 else " 穴 ")
            s_name = r['suji_name']
            detail = f"(期待値:{r['ev']:.2f})"
            if s_name: detail += f" [スジ:{s_name}]"
            else: detail += f" ({r['odds']:.1f}倍)"
            final_bets.append(fmt_bet(label, r['combo'], detail))
            
    else:
        # オッズなし: すべての3連単(120通り)についてAIスコアを計算しスジ補正
        all_combos = []
        import itertools
        score_map = dict(zip(df['teiban'].astype(int), df['final_score']))
        total_s = sum(score_map.values()) if sum(score_map.values()) > 0 else 1.0
        
        for c in itertools.permutations([1,2,3,4,5,6], 3):
            combo = f"{c[0]}-{c[1]}-{c[2]}"
            p1 = score_map[c[0]] / total_s
            p2 = score_map[c[1]] / max(total_s - score_map[c[0]], 0.001)
            p3 = score_map[c[2]] / max(total_s - score_map[c[0]] - score_map[c[1]], 0.001)
            score = p1 * p2 * p3
            
            mul, s_name = get_suji_multiplier(combo)
            adj_score = score * mul
            all_combos.append({'combo': combo, 'score': score, 'adjusted_score': adj_score, 'suji_name': s_name})
            
        df_all = pd.DataFrame(all_combos)
        tops = df_all.sort_values(by='adjusted_score', ascending=False).head(8)
        
        for idx, (i, r) in enumerate(tops.iterrows()):
            label = "本命" if idx < 2 else ("期待" if idx < 6 else " 穴 ")
            s_name = r['suji_name']
            detail = f"(スコア:{r['score']*100:.2f})"
            if s_name: detail += f" [スジ:{s_name}]"
            final_bets.append(fmt_bet(label, r['combo'], detail))

    print("=" * 30)

    # ── 今後のAI精度向上のためのデータ蓄積 ──
    # 当日のレース特徴量と予測スコアをローカルに保存し、翌日の結果結合→再学習に備える
    try:
        os.makedirs("data", exist_ok=True)
        # 不要なオブジェクト（関数など）が混ざらないよう、必要な列だけ抽出して辞書化
        save_df = df.copy()
        # teiban等のカテゴリが残っている場合は文字列化
        for col in save_df.columns:
            if str(save_df[col].dtype) == 'category':
                save_df[col] = save_df[col].astype(str)
                
        # レース全体のメタデータを付与
        save_df['eval_date'] = d_str
        save_df['eval_place'] = p_no
        save_df['eval_race'] = r_no
        
        # JSONLines 形式で保存 (1行1レコード)
        with open("data/daily_features.jsonl", "a", encoding="utf-8") as f:
            for _, r in save_df.iterrows():
                f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\\n")
    except Exception as e:
        print(f"[Debug] Failed to save daily features: {e}")

    # ── 結果サマリー ──
    if hit_combo:
        if hit_combo in final_bets:
            print(f"\n\033[32m★的中！！ {hit_combo}  払戻金: ¥{hit_price}\033[0m")
        else:
            print(f"\n確定: {hit_combo} → 不的中")
    else:
        print("\n（レース結果未確定）")

    print("\n" + "="*60)

if __name__ == "__main__":
    main()
