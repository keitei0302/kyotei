import json
from bs4 import BeautifulSoup

html_path = "test_racelist.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
results = []

# 各プレーヤーのtbodyを取得
tbodies = soup.find_all('tbody', class_='is-fs12')
for i, tbody in enumerate(tbodies[:6]): 
    player_data = {"teiban": i + 1}
    
    # 選手名
    name_el = tbody.find('div', class_='is-fs18')
    player_data['name'] = name_el.text.strip().replace(' ', '').replace('\u3000', '') if name_el else ""
    
    # 級別, 年齢, 体重, F/L などが入ったテキストを取得
    # これらは最初の行 (tr) に分散しているか、tdごとに入っている
    trs = tbody.find_all('tr')
    
    # trs[0] が基本情報 (名前, 年齢, F/L, ST, 全国勝率, 当地勝率, モーター, ボートなど)
    # td を順番に取り出してパースする
    if len(trs) > 0:
        tds = trs[0].find_all('td')
        # 構造の仮説 (実際のサイト構造による)
        # 1: 艇番・枠色
        # 2: 写真
        # 3: 登録番号, 級別, 氏名, 支部/出身地, 年齢/体重
        # 4: F数, L数, 平均ST
        # 5: 全国勝率, 2連率, 3連率
        # 6: 当地勝率, 2連率, 3連率
        # 7: モーター番号, 2連率, 3連率
        # 8: ボート番号, 2連率, 3連率
        
        if len(tds) >= 8:
            # 4: F, L, ST
            st_text = tds[3].text.strip()
            player_data['F'] = int(st_text.split('F')[1].split()[0]) if 'F' in st_text else 0
            player_data['L'] = int(st_text.split('L')[1].split()[0]) if 'L' in st_text else 0
            player_data['ST'] = float(st_text.split()[-1]) if len(st_text.split()) > 0 and '.' in st_text.split()[-1] else 0.15 # fallback
            
            # 5: 全国勝率 (Win rate)
            # Text inside looks like:  5.40 37.10 54.83
            national_parts = tds[4].text.split()
            player_data['national_win_rate'] = float(national_parts[0]) if len(national_parts) > 0 else 0.0
            player_data['national_2ren'] = float(national_parts[1]) if len(national_parts) > 1 else 0.0
            
            # 6: 当地勝率
            local_parts = tds[5].text.split()
            player_data['local_win_rate'] = float(local_parts[0]) if len(local_parts) > 0 else 0.0
            player_data['local_2ren'] = float(local_parts[1]) if len(local_parts) > 1 else 0.0
            
            # 7: モーター
            motor_parts = tds[6].text.split()
            player_data['motor_no'] = int(motor_parts[0]) if len(motor_parts) > 0 and motor_parts[0].isdigit() else 0
            player_data['motor_2ren'] = float(motor_parts[1]) if len(motor_parts) > 1 else 0.0
            
            # 8: ボート
            boat_parts = tds[7].text.split()
            player_data['boat_2ren'] = float(boat_parts[1]) if len(boat_parts) > 1 else 0.0

    results.append(player_data)

import pprint
pprint.pprint(results)
