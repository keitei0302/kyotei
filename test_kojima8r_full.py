import requests
import re
from bs4 import BeautifulSoup

url = 'https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=8&jcd=16&hd=20260305'
soup = BeautifulSoup(requests.get(url).content, 'html.parser')
for i, tb in enumerate(soup.find_all('tbody', class_='is-fs12')):
    if tb.find('td', class_=re.compile(r'is-boatColor')):
        print(f"Tbody {i} TD count: {len(tb.find_all('td'))}")
        tds = tb.find_all('td')
        print(f"TD4: {tds[4].get_text(strip=True)[:10]}")
        print(f"TD5: {tds[5].get_text(strip=True)[:10]}")
