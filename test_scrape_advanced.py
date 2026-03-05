import requests
from bs4 import BeautifulSoup
import json
import re

hd = '20260305'
jcd = '18'
rno = '10'

def scrape_beforeinfo():
    url = f'https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={jcd}&hd={hd}'
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    res = {}
    parts_table = soup.find('th', string=re.compile(r'部品交換'))
    if parts_table:
        ptb = parts_table.find_parent('table')
        if ptb:
            trs = ptb.find_all('tbody')
            for i, tbody in enumerate(trs):
                if i >= 6: break
                s = tbody.get_text(strip=True)
                res[i+1] = 'なし' if not s else s
    print('Parts:', res)

def scrape_racelist():
    url = f'https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd}&hd={hd}'
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    tbodies = soup.find_all('tbody', class_='is-fs12')
    res = []
    for tb in tbodies[:6]:
        tds = tb.find_all('td', rowspan='4')
        if len(tds) >= 4:
            zenkoku = tds[0].get_text(separator=' ', strip=True)
            touchi = tds[1].get_text(separator=' ', strip=True)
            res.append({'zenkoku': zenkoku, 'touchi': touchi})
    print('WinRates:', res)

scrape_beforeinfo()
scrape_racelist()
