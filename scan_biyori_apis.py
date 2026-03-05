import requests
import re
import time

url = "https://kyoteibiyori.com/js/race_shusso.js"
headers = {"User-Agent": "Mozilla/5.0"}

# GET API LIST
res = requests.get(url, headers=headers)
text = res.text
urls = set(re.findall(r"\'(.*?\.php.*?)\'", text) + re.findall(r"\"(.*?\.php.*?)\"", text))
apis = [u for u in urls if 'request' in u or 'ajax' in u or 'php' in u]
apis = list(set([u.split('?')[0] for u in apis])) # remove query params for base testing

payload = {
    "place_no": "16",
    "race_no": "8",
    "hiduke": "20260304"
}
req_headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://kyoteibiyori.com/race_shusso.php?place_no=16&race_no=8&hiduke=20260304",
    "X-Requested-With": "XMLHttpRequest"
}

print(f"Testing {len(apis)} endpoints...")
for api in apis:
    if not api.startswith("/"):
        api = "/" + api
    target = f"https://kyoteibiyori.com{api}"
    try:
        # Try POST
        r = requests.post(target, data=payload, headers=req_headers, timeout=5)
        if r.status_code == 200 and len(r.text) > 10:
            if "一周" in r.text or "オリジナル" in r.text or "展示" in r.text or "lap" in r.text.lower():
                print(f"[FOUND POST] {api} => MATCHED KEYWORDS!")
                print(r.text[:200].replace('\n', ' '))
                continue
    except:
        pass

    time.sleep(0.1)

    try:
        # Try GET
        r = requests.get(target, params=payload, headers=req_headers, timeout=5)
        if r.status_code == 200 and len(r.text) > 10:
            if "一周" in r.text or "オリジナル" in r.text or "展示" in r.text or "lap" in r.text.lower():
                print(f"[FOUND GET] {api} => MATCHED KEYWORDS!")
                print(r.text[:200].replace('\n', ' '))
    except:
        pass
    
print("Done.")
