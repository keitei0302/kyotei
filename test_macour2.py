import requests
from bs4 import BeautifulSoup
import re

def test_macour():
    url = 'https://sp.macour.jp/s/race/syusso/1812026030501/'
    headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15'}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    text = soup.get_text()
    print('Length:', len(text))
    print('Contains 逃げ:', '逃げ' in text)
    if '逃がし率' in text:
        print('Contains 逃がし率')
    # check tables
    for t in soup.find_all('table'):
        if '逃げ' in t.get_text():
            print('Find table with 逃げ:', t.get_text(strip=True)[:50])
test_macour()
