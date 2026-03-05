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

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────
# 共通設定
# ──────────────────────────────────────────
CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)

# ──────────────────────────────────────────
# データ取得系
# ──────────────────────────────────────────

def get_beforeinfo(place_no, race_no, date_str):
    """直前情報ページから展示タイム・チルト角度・プロペラ交換情報を取得"""
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    # propeller: 新プロペラの場合は True
    result = {i: {'show_time': 0.0, 'tilt': 0.0, 'propeller': False, 'lap_time': 0.0, 'turn_time': 0.0, 'straight_time': 0.0} for i in range(1, 7)}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # 1. 展示タイムとチルトの取得
        tbodies = soup.find_all('tbody', class_='is-fs12')
        for tbody in tbodies:
            td_teiban = tbody.find('td', class_=re.compile(r'is-boatColor'))
            if not td_teiban: continue
            try:
                t_num = int(td_teiban.get_text(strip=True))
                if not (1 <= t_num <= 6): continue
                
                all_tds = tbody.find_all('td')
                for td in all_tds:
                    val_str = td.get_text(strip=True)
                    # 展示タイム: 6.xx (6.00 〜 8.00)
                    if re.match(r'^\d\.\d{2}$', val_str):
                        val = float(val_str)
                        if 6.0 <= val <= 8.0: result[t_num]['show_time'] = val
                    # チルト角度: -0.5, 0.0, 0, 1, 1.5, 2, 3 等
                    # 正規表現を緩和: 符号(任意) + 数字1桁 + 小数点部分(任意)
                    elif re.match(r'^[-+]?\d(\.\d)?$', val_str):
                        try:
                            val = float(val_str)
                            # 競艇のチルト範囲（通常 -0.5 〜 3.0）
                            # 展示タイムと誤認しないように 5.0 未満に限定
                            if -0.5 <= val <= 3.0: 
                                result[t_num]['tilt'] = val
                        except: pass
            except: pass

        # 2. プロペラ交換情報の取得 (別のtableにある場合が多い)
        # 「プロペラ」というテキストを含むセクションを探す
        propeller_table = soup.find('th', string=re.compile(r'プロペラ'))
        if propeller_table:
            target_table = propeller_table.find_parent('table')
            if target_table:
                # 「新」という文字が入っている艇番を探す
                for tr in target_table.find_all('tr'):
                    tds = tr.find_all('td')
                    if len(tds) >= 2:
                        try:
                            t_num = int(tds[0].get_text(strip=True))
                            if "新" in tds[1].get_text():
                                result[t_num]['propeller'] = True
                        except: pass
        # 3. オリジナル展示タイムの取得 (Boatcastのテキストデータから取得)
        try:
            race_no_str = str(race_no).zfill(2)
            place_no_str = str(place_no).zfill(2)
            boatcast_url = f"https://race.boatcast.jp/txt/{place_no_str}/bc_oriten_{date_str}_{place_no_str}_{race_no_str}.txt"
            
            text = ""
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    res_bc = page.goto(boatcast_url, timeout=10000)
                    if res_bc and res_bc.ok:
                        text = page.evaluate("() => document.body.innerText")
                    else:
                        status = res_bc.status if res_bc else "Timeout"
                        print(f"[BeforeInfo] Boatcast Original Times not found (Status {status})")
                    browser.close()
            except Exception as e:
                print(f"[Playwright Error] {e}")
            
            if text:
                lines = text.strip().split('\n')
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            # フォーマット: 1  岩瀬  裕亮  36.30  6.03  6.43
                            t_num = int(parts[0])
                            if 1 <= t_num <= 6:
                                result[t_num]['straight_time'] = float(parts[-1])
                                result[t_num]['turn_time'] = float(parts[-2])
                                result[t_num]['lap_time'] = float(parts[-3])
                        except ValueError:
                            pass
        except Exception as e:
            print(f"[BeforeInfo] Original Times Error: {e}")

    except Exception as e:
        print(f"[BeforeInfo] Error: {e}")
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
        res = requests.get(url, headers=headers, timeout=20)
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
        res = requests.get(url, headers=headers, timeout=10)
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
        res = requests.get(url, headers=headers)
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

        results = []
        tbodies = soup.find_all('tbody', class_='is-fs12')
        for i, tbody in enumerate(tbodies[:6]): 
            p = {"teiban": i + 1}
            name_el = tbody.find('div', class_='is-fs18')
            p['name'] = name_el.text.strip().replace(' ', '').replace('\u3000', '') if name_el else f"Player{i+1}"
            trs = tbody.find_all('tr')
            if trs:
                tds = trs[0].find_all('td')
                if len(tds) >= 8:
                    st_txt = tds[3].text.strip()
                    try:
                        p['ST'] = float(st_txt.split()[-1]) if st_txt.split() and st_txt.split()[-1] != '-' else 0.15
                    except:
                        p['ST'] = 0.15
                        
                    try:
                        wr_txt = tds[4].text.split()[0]
                        p['win_rate'] = float(wr_txt) if wr_txt != '-' else 0.0
                    except:
                        p['win_rate'] = 0.0
                        
                    try:
                        m2_txt = tds[6].text.split()[1] if len(tds[6].text.split()) > 1 else '0.0'
                        p['motor_2ren'] = float(m2_txt) if m2_txt != '-' else 0.0
                    except:
                        p['motor_2ren'] = 0.0
            results.append(p)
        return {"players": results, "deadline": deadline} if len(results) == 6 else None
    except Exception as e:
        print(f"[TodayPlayers] Error: {e}")
        return None

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
    except:
        players_df['ai_prob'] = 1/6
        players_df['show_time'] = 0.0
        players_df['propeller'] = False
        players_df['lap_time'] = 0.0
        players_df['turn_time'] = 0.0
        players_df['straight_time'] = 0.0
    return players_df

def apply_user_intuition(df_pred):
    """直感ルール（展示タイム・プロペラ・チルト等）を適用しスコアを補正"""
    df_pred['custom_prob'] = df_pred['ai_prob'].copy()
    
    # 1. 展示タイムによる補正
    if 'show_time' in df_pred.columns:
        valid = df_pred[df_pred['show_time'] > 0]
        if not valid.empty:
            avg, best = valid['show_time'].mean(), valid['show_time'].min()
            for i, row in df_pred.iterrows():
                if row['show_time'] <= 0: continue
                # 展示タイムの差分に応じた補正（一番時計に近いほど加点）
                diff = avg - row['show_time']
                df_pred.at[i, 'custom_prob'] += diff * 2.0  # 重みを 1.5 -> 2.0 に強化
                if row['show_time'] == best and diff >= 0.03:
                    df_pred.at[i, 'custom_prob'] += 0.07  # 一番時計ボーナスを 0.05 -> 0.07 に強化

    # 2. プロペラ交換による補正
    if 'propeller' in df_pred.columns:
        for i, row in df_pred.iterrows():
            if row['propeller']:
                # 新プロペラ交換後は気配が変わることが多いため、少しスコアを下げる（または要警戒とする）
                # ここでは保守的に -3% の補正
                df_pred.at[i, 'custom_prob'] -= 0.03
                
    # 3. オリジナル展示タイムによる補正
    if 'lap_time' in df_pred.columns:
        valid = df_pred[df_pred['lap_time'] > 0]
        if len(valid) >= 3:
            avg = valid['lap_time'].mean()
            for i, row in df_pred.iterrows():
                if row['lap_time'] <= 0: continue
                # 一周タイムの差分 (総合力: 係数0.2)
                diff = avg - row['lap_time']
                df_pred.at[i, 'custom_prob'] += diff * 0.2

    if 'turn_time' in df_pred.columns:
        valid = df_pred[df_pred['turn_time'] > 0]
        if len(valid) >= 3:
            avg = valid['turn_time'].mean()
            for i, row in df_pred.iterrows():
                if row['turn_time'] <= 0: continue
                # まわり足の差分 (出足: 係数0.5)
                diff = avg - row['turn_time']
                df_pred.at[i, 'custom_prob'] += diff * 0.5

    if 'straight_time' in df_pred.columns:
        valid = df_pred[df_pred['straight_time'] > 0]
        if len(valid) >= 3:
            avg = valid['straight_time'].mean()
            for i, row in df_pred.iterrows():
                if row['straight_time'] <= 0: continue
                # 直線タイムの差分 (伸び: 係数1.0)
                diff = avg - row['straight_time']
                df_pred.at[i, 'custom_prob'] += diff * 1.0

    df_pred['custom_prob'] = df_pred['custom_prob'].clip(lower=0.01)
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

def main():
    print("\n" + "="*60 + "\n   KEITEI AI - Phase 3 (UI凝縮 & 的中判定)\n" + "="*60)
    places = {"桐生":"01","戸田":"02","江戸川":"03","平和島":"04","多摩川":"05","浜名湖":"06","蒲郡":"07","常滑":"08","津":"09","三国":"10","びわこ":"11","住之江":"12","尼崎":"13","鳴門":"14","丸亀":"15","児島":"16","宮島":"17","徳山":"18","下関":"19","若松":"20","芦屋":"21","福岡":"22","唐津":"23","大村":"24"}
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

    if not df_bets.empty:
        # オッズがある場合（レース前）
        tops = df_bets.sort_values(by=['prob','ev'], ascending=False).head(2)
        for _, r in tops.iterrows():
            final_bets.append(fmt_bet("本命", r['combo'], f"({r['odds']:.1f}倍)"))
        himos = df_bets[~df_bets['combo'].isin(final_bets)].sort_values(by='ev', ascending=False).head(4)
        for _, r in himos.iterrows():
            final_bets.append(fmt_bet("期待", r['combo'], f"(期待値:{r['ev']:.2f})"))
        anas = df_bets[~df_bets['combo'].isin(final_bets) & (df_bets['odds']>=35)].sort_values(by='ev', ascending=False).head(2)
        for _, r in anas.iterrows():
            final_bets.append(fmt_bet(" 穴 ", r['combo'], f"({r['odds']:.1f}倍)"))
    else:
        # オッズなし（レース終了後）：AIスコア上位を1着軸に、2〜3着を全方位カバー
        top6 = df.sort_values(by='final_score', ascending=False)['teiban'].astype(int).tolist()
        axis = top6[0]  # スコア1位を1着軸に固定
        others = top6[1:]  # 残り5艇
        bets = []
        # 2〜3着を全組み合わせ (5C2 × 2方向 = 20通り) → スコア順で上位8点
        for j in others:
            for k in others:
                if j == k: continue
                c = f"{axis}-{j}-{k}"
                if c not in bets: bets.append(c)
                if len(bets) >= 8: break
            if len(bets) >= 8: break
        label_map = {0:"本命",1:"本命",2:"期待",3:"期待",4:"期待",5:"期待",6:" 穴 ",7:" 穴 "}
        for idx, c in enumerate(bets[:8]):
            final_bets.append(fmt_bet(label_map.get(idx,"期待"), c, f"(AI軸:{axis})"))
    print("=" * 30)

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
