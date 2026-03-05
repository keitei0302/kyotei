import requests
from bs4 import BeautifulSoup

def dump_html():
    url = 'https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=10&jcd=16&hd=20260305'
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # ページ内のすべての table タグを調査
    tables = soup.find_all('table')
    print(f"Total tables found: {len(tables)}")
    
    for i, table in enumerate(tables):
        print(f"--- Table {i} (Header sample) ---")
        thead = table.find('thead')
        if thead:
            print(f"  Head text: {thead.get_text(strip=True)[:100]}")
        tbody = table.find('tbody')
        if tbody:
            print(f"  Body text sample: {tbody.get_text(strip=True)[:100]}")
            
    # 特定のテキスト（菅、チルト等）で場所を特定
    target = soup.find(string=lambda t: '菅' in str(t))
    if target:
        parent = target.find_parent('table')
        if parent:
            print("\n--- Table containing '菅' ---")
            print(parent.encode('shift-jis', errors='ignore').decode('shift-jis')) # 構造を把握するために出力

dump_html()
