import requests
from bs4 import BeautifulSoup

def test_scrape(url):
    print(f"Testing {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, 'html.parser')
        title = soup.title.string if soup.title else "No title found"
        print(f"Success! Title: {title}")
        print(f"Content Length: {len(res.content)}")
    except Exception as e:
        print(f"Error: {e}")

test_scrape("https://kyoteibiyori.com/")
print("---")
test_scrape("https://boatrace-db.net/")
