import requests
from bs4 import BeautifulSoup

url = 'https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=8&jcd=16&hd=20260305'
res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(res.content, 'html.parser')

tbodies = soup.find_all('tbody', class_='is-fs12')
for i, tb in enumerate(tbodies[:6]):
    tds = tb.find_all('td')
    if len(tds) > 12:
        print(f"Teiban {tds[0].get_text(strip=True)[:2]} | TD4(ShowTime): {tds[4].get_text(strip=True)} | TD5(Tilt): {tds[5].get_text(strip=True)} | TD12(AdjWt): {tds[12].get_text(strip=True)}")
