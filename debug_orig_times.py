import requests
from bs4 import BeautifulSoup
import re
import json

def test_original_times():
    place_no = "16" # 児島
    race_no = 8
    date_str = "20260304"
    
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    times = {i: {'lap': 0.0, 'turn': 0.0, 'straight': 0.0} for i in range(1, 7)}
    
    res = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.content, 'html.parser')
    
    try:
        # "オリジナル展示タイム"が見出しにあるテーブルを探す
        target_h3 = soup.find(lambda tag: tag.name in ["h3", "p", "div"] and "オリジナル展示タイム" in tag.get_text())
        if target_h3:
            # 近くの table を探す
            table = target_h3.find_next('table')
            if table:
                tbodies = table.find_all('tbody')
                for tbody in tbodies:
                    # class is-fs14 などの tbody? 枠番を探す
                    td_teiban = tbody.find('td', class_=re.compile(r'is-boatColor'))
                    if not td_teiban: continue
                    try:
                        t_num = int(td_teiban.get_text(strip=True))
                        tds = tbody.find_all('td')
                        # 0:枠番, 1:一周, 2:まわり足, 3:直線
                        if len(tds) >= 4:
                            val_lap = tds[1].get_text(strip=True)
                            val_turn = tds[2].get_text(strip=True)
                            val_straight = tds[3].get_text(strip=True)
                            
                            if re.match(r'^\d{1,2}\.\d{2}$', val_lap): times[t_num]['lap'] = float(val_lap)
                            if re.match(r'^\d\.\d{2}$', val_turn): times[t_num]['turn'] = float(val_turn)
                            if re.match(r'^\d\.\d{2}$', val_straight): times[t_num]['straight'] = float(val_straight)
                    except Exception as e:
                        print(e)
            else:
                print("Table not found")
        else:
            print("Headers not found. Let's try finding the specific table directly.")
            # 代替: th に 一周タイム などのテキストがあるテーブル
            th_lap = soup.find('th', string=re.compile(r'一周タイム'))
            if th_lap:
                table = th_lap.find_parent('table')
                tbodies = table.find_all('tbody')
                for tbody in tbodies:
                    td_teiban = tbody.find('td', class_=re.compile(r'is-boatColor'))
                    if not td_teiban: continue
                    try:
                        t_num = int(td_teiban.get_text(strip=True))
                        tds = tbody.find_all('td')
                        if len(tds) >= 4:
                            val_lap = tds[1].get_text(strip=True)
                            val_turn = tds[2].get_text(strip=True)
                            val_straight = tds[3].get_text(strip=True)
                            
                            if re.match(r'^\d{1,2}\.\d{2}$', val_lap): times[t_num]['lap'] = float(val_lap)
                            if re.match(r'^\d\.\d{2}$', val_turn): times[t_num]['turn'] = float(val_turn)
                            if re.match(r'^\d\.\d{2}$', val_straight): times[t_num]['straight'] = float(val_straight)
                    except Exception as e:
                        print(e)
        
        print(json.dumps(times, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_original_times()
