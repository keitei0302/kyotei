import requests
import json

url = 'https://kyoteibiyori.com/request/request_race_shusso.php'
payload = {'place_no': '18', 'race_no': '1', 'hiduke': '20260305'}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': f'https://kyoteibiyori.com/race_shusso.php?place_no=18&race_no=1&hiduke=20260305',
    'X-Requested-With': 'XMLHttpRequest'
}
res = requests.post(url, data=payload, headers=headers)
print(res.status_code)
if res.status_code == 200:
    try:
        data = res.json()
        with open('biyori_api.json','w',encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        print('Keys:', data.keys())
    except:
        print('Not json:', res.text[:200])
