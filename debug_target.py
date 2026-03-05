import requests
from bs4 import BeautifulSoup
import re

def dump_target_table():
    url = 'https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=10&jcd=16&hd=20260305'
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # is-fs12 を持つ tbody を含む table を探す
    tbodies = soup.find_all('tbody', class_='is-fs12')
    if not tbodies:
        print("No is-fs12 tbodies found")
        return
        
    for i, tbody in enumerate(tbodies[:6]):
        print(f"\n--- Tbody {i+1} ---")
        rows = tbody.find_all('tr')
        for j, tr in enumerate(rows):
            tds = tr.find_all('td')
            # 各 td のクラス名も出力して、どの列が何であるか正確に把握する
            td_info = []
            for k, td in enumerate(tds):
                class_name = " ".join(td.get('class', []))
                text = td.get_text(strip=True)
                td_info.append(f"td[{k}]({class_name}): {text}")
            print(f"  Row {j}: {td_info}")

dump_target_table()
