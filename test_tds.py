import requests
from bs4 import BeautifulSoup

url = "https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=10&jcd=18&hd=20260305"
headers = {'User-Agent': 'Mozilla/5.0'}
res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.content, 'html.parser')

tbodies = soup.find_all('tbody', class_='is-fs12')
for tbody in tbodies[:6]:
    all_tds = tbody.find_all('td')
    t_num = all_tds[0].get_text(strip=True)
    if len(all_tds) >= 6:
        print(f"--- 艇番 {t_num} ---")
        for i, td in enumerate(all_tds):
            print(f"td[{i}]: {td.get_text(strip=True)}")
