import requests
from bs4 import BeautifulSoup

def save_kojima10r_table():
    url = 'https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=10&jcd=16&hd=20260305'
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    
    with open('kojima10r_table.txt', 'w', encoding='utf-8') as f:
        tbodies = soup.find_all('tbody', class_='is-fs12')
        for i, tbody in enumerate(tbodies[:6]):
            f.write(f"\n--- Tbody {i+1} ---\n")
            for j, tr in enumerate(tbody.find_all('tr')):
                tds = tr.find_all(['td', 'th'])
                row_items = []
                for k, td in enumerate(tds):
                    txt = td.get_text(strip=True)
                    rs = td.get('rowspan', '1')
                    cs = td.get('colspan', '1')
                    row_items.append(f"[{k}](rs:{rs}, cs:{cs})='{txt}'")
                f.write(f"  Row {j}: {' | '.join(row_items)}\n")
    print("Saved to kojima10r_table.txt")

save_kojima10r_table()
