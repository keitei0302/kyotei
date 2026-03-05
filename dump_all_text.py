import requests
from bs4 import BeautifulSoup

def dump_all(place_no, race_no):
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={race_no}&jcd={place_no}&hd=20260305"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # "枠" というテキストがあるテーブルを探す
    for table in soup.find_all('table'):
        if '枠' in table.get_text():
            print(f"Table found with text length {len(table.get_text())}")
            tbodies = table.find_all('tbody')
            if tbodies:
                tbody = tbodies[0]
                tds = tbody.find_all('td')
                for i, td in enumerate(tds):
                    print(f"  td[{i}]: {td.get_text(strip=True)}")
            break

print("--- Kojima 8R ---")
dump_all('16', '8')
