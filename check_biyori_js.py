import requests
import re

url = "https://kyoteibiyori.com/js/race_shusso.js"
headers = {"User-Agent": "Mozilla/5.0"}
try:
    res = requests.get(url, headers=headers, timeout=10)
    text = res.text
    
    # URLっぽいやつを抽出してユニークに
    urls = set(re.findall(r"\'(.*?\.php.*?)\'", text) + re.findall(r"\"(.*?\.php.*?)\"", text))
    apis = [u for u in urls if 'request' in u or 'ajax' in u]
    for u in apis:
        print("Possible API Endpoint:", u)
        
    # '直前' や '展示' に関連する処理を探す
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if 'ajax' in line.lower() and ('chokuzen' in line.lower() or 'tenji' in line.lower() or 'request' in line.lower()):
            print(f"L{i}: {line.strip()[:100]}")
            
except Exception as e:
    print(e)
