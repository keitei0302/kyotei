import requests
from bs4 import BeautifulSoup

def find_parts():
    for r in range(1, 13):
        url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={r}&jcd=18&hd=20260305"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.content, 'html.parser')
        for tbody in soup.find_all('tbody', class_='is-fs12')[:6]:
            tds = tbody.find_all('td')
            if len(tds) >= 8:
                parts = tds[7].get_text(strip=True)
                if parts:
                    print(f"Race {r}, Tbody parts: {parts}")

find_parts()
