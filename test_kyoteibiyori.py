import requests
from bs4 import BeautifulSoup
import sys

def check_kyoteibiyori(place_no, race_no, date_str):
    urls = [
        f"https://kyoteibiyori.com/race_shussou.php?place_no={place_no}&race_no={race_no}&date={date_str}",
        f"https://kyoteibiyori.com/index.php?place_no={place_no}&race_no={race_no}&date={date_str}"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for url in urls:
        print(f"Testing {url}")
        res = requests.get(url, headers=headers)
        print("Status Code:", res.status_code)
        
        if res.status_code == 200:
            content_text = res.text
            if "まくり" in content_text or "差され" in content_text:
                print("SUCCESS: Found keywords 'まくり' or '差され'")
                
                # Check for what tables or divs contain these variables
                soup = BeautifulSoup(content_text, 'html.parser')
                # Try finding text containing 'まくり'
                elements = soup.find_all(lambda tag: tag.name == "td" and "まくり" in tag.text)
                print(f"Found {len(elements)} elements containing 'まくり'")
                if elements:
                    print("Sample:", elements[0].text.strip())
                return
    print("Keywords not found.")

if __name__ == "__main__":
    check_kyoteibiyori("21", "3", "2026-02-26")
    check_kyoteibiyori("21", "3", "20260226")
