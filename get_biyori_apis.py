import requests
import re

url = "https://kyoteibiyori.com/js/race_shusso.js"
headers = {"User-Agent": "Mozilla/5.0"}
try:
    res = requests.get(url, headers=headers)
    text = res.text
    urls = set(re.findall(r"\'(.*?\.php.*?)\'", text) + re.findall(r"\"(.*?\.php.*?)\"", text))
    apis = [u for u in urls if 'request' in u or 'ajax' in u or 'php' in u]
    for u in sorted(apis):
        print(u)
except Exception as e:
    print(e)
