import requests
from bs4 import BeautifulSoup

def fetch():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    url = 'https://kyoteibiyori.com/race_shussou.php?place_no=18&race_no=1&date=20260305'
    r = requests.get(url, headers=headers)
    with open('tmp.html', 'w', encoding='utf-8') as f:
        f.write(r.text)
    soup = BeautifulSoup(r.text, 'html.parser')
    print([t.text.strip() for t in soup.find_all(['th', 'td']) if '逃げ' in t.text or '率' in t.text][:20])
fetch()
