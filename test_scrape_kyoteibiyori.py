import requests
from bs4 import BeautifulSoup
import json

def test_kyotei_biyori(place_no, race_no, date_str):
    urls = [
        f"https://kyoteibiyori.com/race_shussou.php?place_no={place_no}&race_no={race_no}&date={date_str}"
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    for url in urls:
        print(f"Fetching: {url}")
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Look for 逃げ率 etc.
            # Kyotei biyori puts these in specific tables.
            tables = soup.find_all('table')
            for i, tbl in enumerate(tables):
                text = tbl.get_text()
                if "逃げ" in text and "捲り" in text:
                    print(f"--- Table {i} ---")
                    rows = tbl.find_all('tr')
                    for r in rows[:5]: # Print first few rows
                        print([td.get_text(strip=True) for td in r.find_all(['th', 'td'])])
            
test_kyotei_biyori("18", "1", "20240304")
