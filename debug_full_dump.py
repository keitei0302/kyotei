import requests
from bs4 import BeautifulSoup

def dump_everything():
    url = 'https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=10&jcd=16&hd=20260305'
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # 全ての tbody を調べる
    tbodies = soup.find_all('tbody')
    print(f"Total tbodies: {len(tbodies)}")
    
    for i, tbody in enumerate(tbodies):
        txt = tbody.get_text(strip=True)
        if '菅' in txt or 'チルト' in txt or '展示タイム' in txt:
            print(f"\n--- Tbody {i} (contains target text) ---")
            class_str = " ".join(tbody.get('class', []))
            print(f"Class: {class_str}")
            rows = tbody.find_all('tr')
            for j, tr in enumerate(rows):
                tds = tr.find_all(['td', 'th'])
                row_info = []
                for k, td in enumerate(tds):
                    t = td.get_text(strip=True)
                    c = " ".join(td.get('class', []))
                    rs = td.get('rowspan', '1')
                    cs = td.get('colspan', '1')
                    row_info.append(f"[{k}](c:{c}, rs:{rs}, cs:{cs})='{t}'")
                print(f"  Row {j}: {row_info}")

dump_everything()
