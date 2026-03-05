import requests
from bs4 import BeautifulSoup

def test_tilt():
    # 徳山 10R 等、昨日か今日のレースの beforeinfo を取得
    url = "https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=10&jcd=18&hd=20260305"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.content, 'html.parser')
    
    tbodies = soup.find_all('tbody', class_='is-fs12')
    for tbody in tbodies[:6]:
        # 1行目は選手名等、2行目以降に展示情報
        t_num_el = tbody.find('td', class_=lambda c: c and 'is-boatColor' in c)
        t_num = t_num_el.get_text(strip=True) if t_num_el else "?"
        
        # tbody内のtdをすべてダンプ
        print(f"--- 艇番 {t_num} ---")
        tds = tbody.find_all('td')
        for i, td in enumerate(tds):
            print(f"[{i}]: {td.get_text(strip=True)}")

test_tilt()
