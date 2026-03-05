import requests
from bs4 import BeautifulSoup

url = 'https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=8&jcd=16&hd=20260305'
res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(res.content, 'html.parser')

tbodies = soup.find_all('tbody', class_='is-fs12')
for i, tb in enumerate(tbodies[:6]):
    tds = tb.find_all('td')
    texts = [td.get_text(strip=True)[:10] for td in tds]
    print(f"Tbody {i} TD count: {len(tds)} | URLs: {texts}")
