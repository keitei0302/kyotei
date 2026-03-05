import requests
from bs4 import BeautifulSoup
import re

url = "https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=8&jcd=16&hd=20260305"
headers = {'User-Agent': 'Mozilla/5.0'}
res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.content, 'html.parser')

# 「展示タイム」などが含まれる表を探す
tbodies = soup.find_all('tbody', class_='is-fs12')
for i, tbody in enumerate(tbodies[:6]):
    t_num_el = tbody.find('td', class_=re.compile(r'is-boatColor'))
    if t_num_el:
        t_num = t_num_el.get_text(strip=True)
        tds = tbody.find_all('td')
        print(f"--- Teiban {t_num} ---")
        for j, td in enumerate(tds):
            print(f"td[{j}]: {td.get_text(strip=True)[:10]}")
