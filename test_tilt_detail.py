import requests
from bs4 import BeautifulSoup

def test_tilt_detail():
    url = "https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=10&jcd=18&hd=20260305"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.content, 'html.parser')
    
    tbodies = soup.find_all('tbody', class_='is-fs12')
    for tbody in tbodies[:6]:
        t_num_el = tbody.find('td', class_=lambda c: c and 'is-boatColor' in c)
        t_num = t_num_el.get_text(strip=True) if t_num_el else "?"
        
        all_tds = tbody.find_all('td')
        print(f"--- 艇番 {t_num} ---")
        if len(all_tds) >= 6:
            show_time_str = all_tds[4].get_text(strip=True)
            tilt_str = all_tds[5].get_text(strip=True)
            print(f"HTML直接取得 -> td[4](展示): '{show_time_str}', td[5](チルト): '{tilt_str}'")
        else:
            print("tdが足りない")

test_tilt_detail()
