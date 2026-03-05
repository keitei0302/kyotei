import requests
from bs4 import BeautifulSoup
import re

def dump_headers(place_no, race_no):
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={race_no}&jcd={place_no}&hd=20260305"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # 複数の table があるかもしれないので、より広く探す
    tables = soup.find_all('table')
    for idx, table in enumerate(tables):
        thead = table.find('thead')
        if thead:
            print(f"Table {idx} Headers:")
            for i, tr in enumerate(thead.find_all('tr')):
                ths = tr.find_all(['th', 'td'])
                print(f"  Row {i}: {[th.get_text(strip=True) for th in ths]}")
        
        tbody = table.find('tbody')
        if tbody:
            print(f"Table {idx} Tbody Row 0 Sample:")
            tr = tbody.find('tr')
            if tr:
                tds = tr.find_all('td')
                print(f"  Row 0: {[td.get_text(strip=True) for td in tds]}")

print("--- Kojima 8R ---")
dump_headers('16', '8')
