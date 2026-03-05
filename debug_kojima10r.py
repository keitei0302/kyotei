import requests
from bs4 import BeautifulSoup
import re

def dump_kojima10r():
    url = 'https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=10&jcd=16&hd=20260305'
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # contentsFrame 内の table を探す
    frame = soup.find('div', class_='contentsFrame')
    if not frame:
        print("contentsFrame not found")
        return
        
    table = frame.find('table')
    if not table:
        print("Table not found in contentsFrame")
        return
        
    # Headers
    thead = table.find('thead')
    if thead:
        for i, tr in enumerate(thead.find_all('tr')):
            print(f"Header Row {i}: {[th.get_text(strip=True) for th in tr.find_all(['th', 'td'])]}")
            
    # Body
    tbodies = table.find_all('tbody', class_='is-fs12')
    for i, tbody in enumerate(tbodies[:6]):
        print(f"--- Tbody {i+1} ---")
        for j, tr in enumerate(tbody.find_all('tr')):
            print(f"  Row {j}: {[td.get_text(strip=True) for td in tr.find_all('td')]}")

dump_kojima10r()
