import requests
from bs4 import BeautifulSoup

def test_scrape_racelist(place_no="04", race_no="12", date_str="20260226"):
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    print(f"Fetching {url}")
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(f"HTTP Error: {res.status_code}")
        return
        
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # tbody を探して解析 (出走表は tbody.is-fs12 などの中にあると予想)
    # または tbody クラスなし
    for i, tbody in enumerate(soup.find_all('tbody')):
        trs = tbody.find_all('tr')
        if len(trs) > 0:
            print(f"--- Tbody {i} (contains {len(trs)} rows) ---")
            for j, tr in enumerate(trs[:4]):  # 最初の4行だけ表示
                print(f"Row {j}: {tr.text.replace(chr(10), ' ').replace('  ', ' ')[:150]}")
                
if __name__ == "__main__":
    test_scrape_racelist()
