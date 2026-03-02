import argparse
import pickle
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import sys
import warnings
import os

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────
# 直前情報（展示タイム・チルト角度）取得
# ──────────────────────────────────────────
def get_beforeinfo(place_no, race_no, date_str):
    """直前情報ページから展示タイム・チルト角度を正確に取得する。"""
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    result = {i: {'show_time': 0.0, 'tilt': 0.0} for i in range(1, 7)}
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # 1. 展示タイムの抽出 (is-pSクラス)
        # 通常、展示タイムは is-pS クラスの td に格納されている
        show_times = soup.select('td.is-pS')
        if len(show_times) >= 6:
            for i in range(6):
                try:
                    val = float(show_times[i].get_text(strip=True))
                    if 6.0 <= val <= 8.0:
                        result[i+1]['show_time'] = val
                except: pass

        # 2. チルト角度の抽出 (is-pAクラスの特定列)
        # 児島等の構成では、is-pA クラスの中にチルトが含まれる。
        # 行ごとに精査し、展示タイムの直後の数値またはチルト列を特定
        rows = soup.select('div.contentsFrame table tbody tr')
        # 選手ごとに複数行ある場合があるため、艇番でフィルタリング
        teiban_count = 0
        for row in rows:
            # 艇番セル(1-6)を確認
            td_teiban = row.find('td', class_=re.compile(r'is-boatColor'))
            if td_teiban:
                try:
                    t_num = int(td_teiban.get_text(strip=True))
                    if 1 <= t_num <= 6:
                        # その行の中の数値をスキャン。チルトは通常「-0.5」〜「3.0」
                        # is-pA クラスの td を優先的に見る
                        pA_cells = row.find_all('td', class_='is-pA')
                        for cell in pA_cells:
                            val_str = cell.get_text(strip=True)
                            # チルトっぽい数値形式 (-0.5, 0.0, 0.5, 1, 1.0 等)
                            if re.match(r'^-?\d(\.\d)?$', val_str):
                                val = float(val_str)
                                if -0.5 <= val <= 3.0:
                                    result[t_num]['tilt'] = val
                                    break
                except: pass

    except Exception as e:
        print(f"[BEFOREINFO] Error: {e}")
    
    return result

import json
import os

CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)

def get_odds3t(place_no, race_no, date_str):
    """3連単オッズ取得。キャッシュ & 強靭化版"""
    cache_path = os.path.join(CACHE_DIR, f"odds_{place_no}_{race_no}_{date_str}.json")
    url = f"https://www.boatrace.jp/owpc/pc/race/odds3t?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    odds_dict = {}
    
    for attempt in range(5):
        try:
            print(f"  [ODDS] Fetching {place_no}#{race_no} Attempt {attempt+1}...")
            res = requests.get(url, headers=headers, timeout=20)
            res.encoding = res.apparent_encoding
            soup = BeautifulSoup(res.content, 'html.parser')
            
            # テーブル解析
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
            
            # 正規表現バックアップ (120件に満たない場合)
            if len(odds_dict) < 120:
                all_text = soup.get_text(separator=' ')
                patterns = [r'(\d)\s*-\s*(\d)\s*-\s*(\d)\s+([\d\.]+)', r'(\d)\s*-\s*(\d)\s*-\s*(\d)\s*[\r\n]+\s*([\d\.]+)']
                for p in patterns:
                    matches = re.findall(p, all_text)
                    for m in matches:
                        combo = f"{m[0]}-{m[1]}-{m[2]}"
                        if combo not in odds_dict:
                            try: odds_dict[combo] = float(m[3])
                            except: pass
            
            if odds_dict:
                print(f"  [ODDS] Success: Found {len(odds_dict)} odds.")
                # キャッシュ保存
                with open(cache_path, "w") as f: json.dump(odds_dict, f)
                return odds_dict
        except Exception as e:
            print(f"  [ODDS] Attempt {attempt+1} failed: {e}")
    
    # 最終フォールバック：キャッシュがあれば返す
    if os.path.exists(cache_path):
        print(f"  [ODDS] ERROR: All attempts failed. Returning cached data.")
        with open(cache_path, "r") as f: return json.load(f)
        
    return odds_dict
def get_race_result(place_no, race_no, date_str):
    """レース結果（着順・配当）を取得する（正規表現による頑健な抽出）"""
    url = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    result = {"rank": [], "dividends": {}}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        full_text = soup.get_text(separator=' ')
        
        # 着順の抽出 (1着〜3着の艇番を探す)
        # 通常「1着 n 2着 n 3着 n」のような並び
        rank_matches = re.finditer(r'([1-3])着\s+(\d)', full_text)
        temp_ranks = {}
        for m in rank_matches:
            r = int(m.group(1)) # 順位
            t = int(m.group(2)) # 艇番
            temp_ranks[r] = t
        
        if temp_ranks:
            result["rank"] = [temp_ranks.get(i, 0) for i in range(1, 4) if i in temp_ranks]

        # 配当の抽出 (3連単)
        # 例: "3連単 1-2-3 1,230"
        div_match = re.search(r'3連単\s+(\d\s*-\s*\d\s*-\s*\d)\s+([\d,]+)円?', full_text)
        if div_match:
            result["dividends"]["3連単"] = {
                "combo": div_match.group(1).replace(' ', ''),
                "price": div_match.group(2)
            }
            
        # fallback: テーブルからの抽出も試みる
        if not result["rank"]:
            rows = soup.find_all('tr')
            for row in rows:
                txt = row.get_text(separator=' ').strip()
                m = re.match(r'^([1-3])\s+\d{4}\s+.*?\s+(\d)', txt) # 順位 登番 名前 艇番
                if m:
                    result["rank"].append(int(m.group(2)))
            if result["rank"]: result["rank"] = result["rank"][:3]

    except Exception as e:
        print(f"Error scraping results: {e}")
    return result

CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)

def get_kimari_te(toban):
    """選手のコース別決まり手データを取得する（キャッシュ対応）"""
    cache_path = os.path.join(CACHE_DIR, f"racer_{toban}.json")
    if os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        if datetime.now().timestamp() - mtime < 86400: # 1日有効
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass

    url = f"https://www.boatrace.jp/owpc/pc/meta/racerdata7?toban={toban}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    stats = {str(i): {"逃げ": 0, "差し": 0, "まくり": 0, "まくり差し": 0, "抜き": 0, "恵まれ": 0} for i in range(1, 7)}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.content, 'html.parser')
        table = None
        for t in soup.find_all('table'):
            if "コース別決まり手" in t.get_text():
                table = t
                break
        
        if table:
            rows = table.find_all('tr')[1:]
            for i, row in enumerate(rows[:6]):
                course = str(i + 1)
                tds = row.find_all('td')
                if len(tds) >= 6:
                    stats[course]["逃げ"] = int(re.sub(r'\D', '', tds[0].text) or 0)
                    stats[course]["差し"] = int(re.sub(r'\D', '', tds[1].text) or 0)
                    stats[course]["まくり"] = int(re.sub(r'\D', '', tds[2].text) or 0)
                    stats[course]["まくり差し"] = int(re.sub(r'\D', '', tds[3].text) or 0)
                    stats[course]["抜き"] = int(re.sub(r'\D', '', tds[4].text) or 0)
                    stats[course]["恵まれ"] = int(re.sub(r'\D', '', tds[5].text) or 0)
        
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False)
    except: pass
    return stats

import json
import os

import re

def analyze_race_tactics(df_pred, kimari_te_data=None):
    """
    戦術データ（まくり率、展示タイム変化等）に基づきAI評価を補正する
    """
    df_pred['custom_prob'] = df_pred['ai_prob'].copy()
    df_pred['reasoning'] = ""
    
    print(f"\n[TACTICS] Starting tactical analysis...")
    
    # 1. 基礎能力（勝率・ST・モーター）の反映
    # 勝率の比重を少し強めに (0.04 -> 0.05)
    df_pred['custom_prob'] += df_pred['win_rate'] * 0.05
    # ST評価 (0.16秒標準。速いほどプラス)
    df_pred['custom_prob'] += (0.16 - df_pred['ST']) * 0.5
    # モーター評価 (40%以上なら大幅プラス)
    df_pred.loc[df_pred['motor_2ren'] >= 40.0, 'custom_prob'] += 0.08
    
    # 2. 展示タイムの「変化」を評価（よりダイナミックに）
    if 'show_time' in df_pred.columns:
         valid_times = df_pred.loc[df_pred['show_time'] > 0, 'show_time']
         if not valid_times.empty:
             avg_time = valid_times.mean()
             # タイムが平均より速いほど大幅加点 (係数 0.5 -> 1.5)
             diff = (avg_time - df_pred['show_time'])
             # 0.03秒以上の差がある場合に強調反映
             df_pred.loc[df_pred['show_time'] > 0, 'custom_prob'] += diff * 1.5
             
             for i, row in df_pred.iterrows():
                 if row['show_time'] > 0 and (avg_time - row['show_time']) >= 0.03:
                     df_pred.at[i, 'reasoning'] += "【機力良】展示好時計 "

    # 3. 戦術指標（決まり手）の反映
    if kimari_te_data:
        for teiban, stats in kimari_te_data.items():
            course = str(teiban)
            # コース別の決まり手を合計
            makuri_pts = stats.get(course, {}).get("まくり", 0) + stats.get(course, {}).get("まくり差し", 0)
            
            # 3, 4, 5号艇が「まくり」屋なら評価を大胆にアップ
            if teiban in [3, 4, 5] and makuri_pts >= 3:
                bonus = 0.04 + (makuri_pts * 0.015)
                df_pred.loc[df_pred['teiban'] == teiban, 'custom_prob'] += bonus
                # 展開：外が攻めるなら1号艇のプレッシャー増
                df_pred.loc[df_pred['teiban'] == 1, 'custom_prob'] -= (bonus * 0.4)
                
                idx = df_pred[df_pred['teiban'] == teiban].index[0]
                df_pred.at[idx, 'reasoning'] += f"【まくり注目】{course}コース実績あり "
                idx1 = df_pred[df_pred['teiban'] == 1].index[0]
                df_pred.at[idx1, 'reasoning'] += f"【展開注意】{teiban}の攻め警戒 "

            # 2号艇の「差し」適正
            if teiban == 2 and stats.get(course, {}).get("差し", 0) >= 3:
                df_pred.loc[df_pred['teiban'] == 2, 'custom_prob'] += 0.06
                idx2 = df_pred[df_pred['teiban'] == 2].index[0]
                df_pred.at[idx2, 'reasoning'] += "【差し妙味】2コース差し実績あり "

    # 正規化とクリップ
    df_pred['custom_prob'] = df_pred['custom_prob'].clip(lower=0.01)
    
    for _, row in df_pred.iterrows():
        print(f"  - Boat {row['teiban']}: AI:{row['ai_prob']:.3f} -> Custom:{row['custom_prob']:.3f} Reasoning: {row['reasoning']}")
        
    return df_pred

def apply_user_intuition(df_pred):
    return analyze_race_tactics(df_pred)


def get_today_players(place_no, race_no, date_str):
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, 'html.parser')
        
        results = []
        tbodies = soup.find_all('tbody', class_='is-fs12')
        for i, tbody in enumerate(tbodies[:6]): 
            player_data = {"teiban": i + 1}
            
            # 選手名と登録番号の抽出
            name_el = tbody.find('div', class_='is-fs18')
            if name_el and name_el.find('a'):
                player_data['name'] = name_el.text.strip().replace(' ', '').replace('\u3000', '')
                # href="...toban=4502" から 4502 を抽出
                href = name_el.find('a').get('href', '')
                m_toban = re.search(r'toban=(\d+)', href)
                player_data['toban'] = m_toban.group(1) if m_toban else "0"
            else:
                player_data['name'] = f"Player {i+1}"
                player_data['toban'] = "0"
            
            # 全国期別成績のリンクから決まり手データを取得（今回は簡易的にリストから推測、または別途取得）
            # 本来は選手ページへの遷移が必要だが、まずは直近の決まり手（前走等）があるか確認
            # ここでは将来の拡張用にプレースホルダを置くか、勝率等から簡易的に「差し」「まくり」適性を計算する
            # ※今回は「差し」「まくり」の判断基準として、勝率と展示タイム、スリット隊形をJavaScript側でロジック化する。
            
            trs = tbody.find_all('tr')
            if len(trs) > 0:
                tds = trs[0].find_all('td')
                if len(tds) >= 8:
                    st_text = tds[3].text.strip()
                    player_data['F'] = int(st_text.split('F')[1].split()[0]) if 'F' in st_text else 0
                    player_data['L'] = int(st_text.split('L')[1].split()[0]) if 'L' in st_text else 0
                    try:
                        player_data['ST'] = float(st_text.split()[-1])
                    except:
                        player_data['ST'] = 0.15
                        
                    national_parts = tds[4].text.split()
                    player_data['win_rate'] = float(national_parts[0]) if len(national_parts) > 0 else 0.0
                    
                    motor_parts = tds[6].text.split()
                    player_data['motor_2ren'] = float(motor_parts[1]) if len(motor_parts) > 1 else 0.0
            
            if 'ST' not in player_data: player_data.update({'ST':0.15, 'F':0, 'L':0, 'win_rate':0.0, 'motor_2ren':0.0})
            results.append(player_data)
            
        return results if len(results) == 6 else None
    except Exception as e:
        print(f"Failed to scrape racelist: {e}")
        return None

def draw_slit_diagram(players):
    print("\n【スリット隊形予想 (平均STに基づく)】")
    print("スタートライン")
    print(" |----------------------------------------")
    
    # STが早いほど右に進む (ST 0.10 -> もっとも右。 0.25 -> 左)
    # 仮に ST 0.10 を 30文字目、ST 0.25 を 0文字目とする
    for p in players:
        st = p['ST']
        # スケーリング計算
        distance = max(0, min(30, int((0.25 - st) / 0.15 * 30)))
        
        f_mark = f"[F{p['F']}]" if p['F'] > 0 else ""
        space = " " * distance
        print(f" |{space}{p['teiban']}号艇> (ST {st:.2f}) {p['name']} {f_mark}")
    print(" |----------------------------------------")

def draw_turn_mark_diagram(top_teiban):
    if top_teiban == 1:
        print("                 ^")
        print("      +-------------+")
        print("      |      (2)")
        print("      |  (1)      (3)")
        print("      |      (4)")
        print("      +-- O       (5)")
        print("      |           (6)")
    elif top_teiban == 2:
        print("                 ^")
        print("      +-------------+")
        print("      |  (2)")
        print("      |      (1) (3)")
        print("      |      (4)")
        print("      +-- O       (5)")
        print("      |           (6)")
    else:
        top_str = f"({top_teiban})"
        inside = " ".join([f"({i})" for i in range(1, int(top_teiban))])
        outside = " ".join([f"({i})" for i in range(int(top_teiban) + 1, 7)])
        
        print("                  ^")
        print("      +-----------------+")
        print(f"      |   {top_str} (まくり!)")
        print(f"      |       {inside} (残される)")
        print("      +-- O")
        print(f"      |               {outside}")

def main():
    print("========================================")
    print("       競艇 AI x 直感 予想システム       ")
    print("========================================")
    
    # 対話形式で入力を受付
    print("予想したいレースを入力してください。")
    place_input = input("開催地のコードまたは名前 (例: 04, 平和島, 芦屋) -> ").strip()
    race_input = input("レース番号 (1〜12) -> ").strip()
    
    today_str = datetime.now().strftime("%Y%m%d")
    
    PLACE_DICT = {
        "桐生": "01", "戸田": "02", "江戸川": "03", "平和島": "04",
        "多摩川": "05", "浜名湖": "06", "蒲郡": "07", "常滑": "08",
        "津": "09", "三国": "10", "びわこ": "11", "住之江": "12",
        "尼崎": "13", "鳴門": "14", "丸亀": "15", "児島": "16",
        "宮島": "17", "徳山": "18", "下関": "19", "若松": "20",
        "芦屋": "21", "福岡": "22", "唐津": "23", "大村": "24"
    }
    
    try:
        if place_input in PLACE_DICT:
            place_no = PLACE_DICT[place_input]
        else:
            place_no = str(int(place_input)).zfill(2)
        race_no = int(race_input)
    except:
        print("入力が正しくありません。終了します。")
        return
        
    print(f"\n[{place_no}場 {race_no}R] のデータを確認中...")
    
    # ライブデータ（選手名）の取得
    players = get_today_players(place_no, race_no, today_str)
    
    # 直前情報（展示タイム・チルト角度）を取得
    print("  直前情報を取得中...")
    beforeinfo = get_beforeinfo(place_no, race_no, today_str)
    
    # AIモデルの読み込み
    try:
        with open("models/lgb_model.pkl", "rb") as f:
            model = pickle.load(f)
    except FileNotFoundError:
        print("エラー: 学習済みモデルが見つかりません。先に train_model.py を実行してください。")
        return
        
    # 推論用データの作成
    records = []
    for i, p in enumerate(players):
        bi = beforeinfo.get(p['teiban'], {'show_time': 0.0, 'tilt': 0.0})
        records.append({
            'place_no': int(place_no),
            'race_no': race_no,
            'teiban': p['teiban'],
            'ST': p['ST'],
            'F': p['F'],
            'L': p['L'],
            'win_rate': p['win_rate'],
            'motor_2ren': p['motor_2ren'],
            'show_time': bi['show_time'],   # 展示タイム
            'tilt': bi['tilt'],              # チルト角度
        })
        
    df_pred = pd.DataFrame(records)
    for col in ['place_no', 'race_no', 'teiban']:
        df_pred[col] = df_pred[col].astype('category')
        
    # AIによる純粋な予測
    # ※現在のAI(lgb_model.pkl)は place, race, teiban のみで学習しているので不要な列を落として推論
    predictions = model.predict(df_pred[['place_no', 'race_no', 'teiban']])
    df_pred['ai_prob'] = predictions
    
    # ユーザー独自の直感ルールを重ね掛け（ここでWinRateやSTなどを使える）
    df_pred = apply_user_intuition(df_pred)
    df_pred['final_score'] = df_pred['custom_prob']
    
    # --- オッズの取得と期待値計算 ---
    print("  オッズ情報を取得中...")
    odds3t = get_odds3t(place_no, race_no, today_str)
    
    # 買い目ごとの確率計算（簡易版。1着x2着x3着の独立確率ベース）
    # 理想的には3連単の同時確率モデルが必要だが、まずは直感的に合成
    bet_results = []
    if odds3t:
        for combo, odds in odds3t.items():
            t1, t2, t3 = map(int, combo.split('-'))
            # 各艇のスコアを正規化して確率っぽく扱う
            total_score = df_pred['final_score'].sum()
            p1 = df_pred.loc[df_pred['teiban'] == t1, 'final_score'].values[0] / total_score
            p2 = df_pred.loc[df_pred['teiban'] == t2, 'final_score'].values[0] / (total_score - p1*total_score)
            p3 = df_pred.loc[df_pred['teiban'] == t3, 'final_score'].values[0] / (total_score - (p1+p2)*total_score)
            
            prob = p1 * p2 * p3
            ev = prob * odds # 期待値
            
            bet_results.append({
                'combo': combo,
                'prob': prob,
                'odds': odds,
                'ev': ev
            })
    
    df_bets = pd.DataFrame(bet_results)
    
    # --- 結果の表示 ---
    print("\n【出走表・概要】")
    if players:
        for p in players:
            bi = beforeinfo.get(p['teiban'], {})
            show_t = bi.get('show_time', 0)
            tilt   = bi.get('tilt', 0.0)
            show_str = f"展示T:{show_t:.2f}" if show_t > 0 else ""
            tilt_str = f"チルト:{tilt:+.1f}" if tilt != 0 else "チルト:±0"
            print(f"{p['teiban']}号艇: {p['name']} "
                  f"(勝率:{p['win_rate']:.2f} ST:{p['ST']:.2f} "
                  f"モーター:{p['motor_2ren']:.0f}% {show_str} {tilt_str})")
        draw_slit_diagram(players)
    else:
        print("（公式サイトから選手情報が取得できませんでした）")
        
    print("\n【各艇の1着予測スコア（AI + 直感ブレンド）】")
    for _, row in df_pred.sort_values(by='final_score', ascending=False).iterrows():
        t = int(row['teiban'])
        score = row['final_score'] * 100
        ai_score = row['ai_prob'] * 100
        st_mark  = f" ST:{row['ST']:.2f}"
        show_t   = row.get('show_time', 0)
        show_str = f" 展示T:{show_t:.2f}" if show_t > 0 else ""
        print(f"{t}号艇: {score:>5.1f} pt (AI:{ai_score:>5.1f}){st_mark}{show_str}")
        
    # ── 8点買い目出力 ─────────────────────────────────────────
    df_sorted = df_pred.sort_values(by='final_score', ascending=False)
    top6 = list(df_sorted['teiban'].values.astype(int))
    # --- 買い目表示（期待値ベース） ---
    print("\n======= 【買い目 推奨8点 (期待値重視)】 =======")
    if not df_bets.empty:
        # 本命: 期待値が高く、かつ的中確率も高いもの (上位2点)
        honmei = df_bets.sort_values(by=['prob', 'ev'], ascending=False).head(2)
        for _, r in honmei.iterrows():
            print(f"  [本命] {r['combo']} (確率:{r['prob']*100:4.1f}% 期待値:{r['ev']:.2f} オッズ:{r['odds']:.1f})")
            
        # ヒモ: 期待値が1.0を超えているもの、または上位 (4点)
        himo = df_bets[~df_bets['combo'].isin(honmei['combo'])].sort_values(by='ev', ascending=False).head(4)
        for _, r in himo.iterrows():
            print(f"  [ヒモ] {r['combo']} (確率:{r['prob']*100:4.1f}% 期待値:{r['ev']:.2f} オッズ:{r['odds']:.1f})")
            
        # 穴: オッズが30倍以上で、期待値が比較的高いもの (2点)
        ana = df_bets[(~df_bets['combo'].isin(honmei['combo'])) & (~df_bets['combo'].isin(himo['combo']))]
        ana = ana[ana['odds'] >= 30].sort_values(by='ev', ascending=False).head(2)
        for _, r in ana.iterrows():
            print(f"  [ 穴 ] {r['combo']} (期待値:{r['ev']:.2f} オッズ:{r['odds']:.1f})")
    else:
        print("  (オッズが取得できなかったため、基本スコアベースで推奨します)")
        # 従来の簡易ロジック
        top3 = df_sorted['teiban'].astype(int).tolist()[:4]
        print(f"  [本命] {top3[0]}-{top3[1]}-{top3[2]}")
        print(f"  [本命] {top3[0]}-{top3[1]}-{top3[3]}")
    print("==================================================")
    
    t1 = top6[0] if top6 else 1
    draw_turn_mark_diagram(t1)
    print("========================================")

if __name__ == "__main__":
    main()
