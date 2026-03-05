import requests
from bs4 import BeautifulSoup
import re
import json

def test_final():
    place_no = '16'
    race_no = '8'
    date_str = '20260305'
    
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={race_no}&jcd={place_no}&hd={date_str}"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    
    table = soup.find('div', class_='contentsFrame').find('table')
    headers = [th.get_text(strip=True) for th in table.find('thead').find_all('th')]
    print("Headers:", headers)
    
    # 実際に出力される JSON 構造を再現
    res_info = {}
    tbodies = soup.find_all('tbody', class_='is-fs12')
    for tbody in tbodies[:6]:
        tds = tbody.find_all('td')
        t_num = tds[0].get_text(strip=True)
        # ヘッダーから位置を探す
        tilt_idx = -1
        show_idx = -1
        adj_idx = -1
        
        # ヘッダー行が複数ある場合があるので結合して探す
        header_text = " ".join(headers)
        # ... 実際は th の index を使う
        ths = table.find('thead').find_all('tr')[0].find_all('th')
        for i, th in enumerate(ths):
            txt = th.get_text(strip=True)
            if 'チルト' in txt: tilt_idx = i
            if 'タイム' in txt: show_idx = i
            if '調整' in txt: adj_idx = i

        # td は tr が分かれている場合、index がズレる
        # 1行目の td 数を数える
        tr1_tds = tbody.find_all('tr')[0].find_all('td')
        print(f"Boat {t_num} Row1 TDs:", [td.get_text(strip=True) for td in tr1_tds])
        
        tr2_tds = tbody.find_all('tr')[1].find_all('td') if len(tbody.find_all('tr')) > 1 else []
        print(f"Boat {t_num} Row2 TDs:", [td.get_text(strip=True) for td in tr2_tds])

test_final()
