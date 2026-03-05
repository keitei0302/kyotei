import requests
from bs4 import BeautifulSoup

def dump_detailed_table():
    url = 'https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=10&jcd=16&hd=20260305'
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    
    tbodies = soup.find_all('tbody', class_='is-fs12')
    if not tbodies:
        print("No is-fs12 tbodies found")
        return
        
    for i, tbody in enumerate(tbodies[:6]):
        print(f"\n--- Tbody {i+1} ---")
        rows = tbody.find_all('tr')
        for j, tr in enumerate(rows):
            tds = tr.find_all('td')
            row_data = []
            for k, td in enumerate(tds):
                class_str = " ".join(td.get('class', []))
                # rowspan, colspan もチェック
                rs = td.get('rowspan', '1')
                cs = td.get('colspan', '1')
                txt = td.get_text(strip=True)
                row_data.append(f"td[{k}](c:{class_str}, rs:{rs}, cs:{cs}): '{txt}'")
            print(f"  Row {j}: {row_data}")

dump_detailed_table()
