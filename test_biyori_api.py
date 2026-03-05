import requests

apis = [
    "/request/request_chokuzen_data.php",
    "/request/request_tenji_honban_start.php",
    "/request/request_race_shusso.php",
]

payload = {
    "place_no": "16",
    "race_no": "8",
    "hiduke": "20260304"
}
headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://kyoteibiyori.com/race_shusso.php?place_no=16&race_no=8&hiduke=20260304",
    "X-Requested-With": "XMLHttpRequest"
}

for api in apis:
    url = f"https://kyoteibiyori.com{api}"
    try:
        # POSTで試す
        res = requests.post(url, data=payload, headers=headers, timeout=10)
        print(f"--- {api} --- Status: {res.status_code}")
        if res.status_code == 200:
            if "一周" in res.text or "オリジナル" in res.text or "展示" in res.text or "lap" in res.text.lower():
                print("★ MATCH!")
            print(res.text[:300])
    except Exception as e:
        print(e)
