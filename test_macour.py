import requests
from bs4 import BeautifulSoup

def fetch_macour():
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = 'https://macour.jp/s/race/syusso/1812026030501/'
    r = requests.get(url, headers=headers)
    with open('tmp_macour.html', 'w', encoding='utf-8') as f:
        f.write(r.text)
fetch_macour()
