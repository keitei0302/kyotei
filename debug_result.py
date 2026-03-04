from keitei_app import get_race_result
import json
import requests
from bs4 import BeautifulSoup
import re

def debug_race_result():
    # 本日の平和島 1R (既に終了している可能性が高いレース) でテスト
    place = "04"
    race = 1
    date = "20260304"
    
    print(f"--- Debugging get_race_result for {place}#{race} ({date}) ---")
    
    # 1. 現在の関数の動作確認
    result = get_race_result(place, race, date)
    print("\n[Current Logic Result]:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 2. ページ構造の直接確認
    url = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={race}&jcd={place}&hd={date}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        print("\n[Checking Page Structure]:")
        # 3連単の配当テーブルを探す
        tables = soup.find_all('table')
        for i, table in enumerate(tables):
            text = table.get_text()
            if "3連単" in text:
                print(f"\nFound '3連単' in Table {i}:")
                # 該当テーブルの行を詳細に表示
                for tr in table.find_all('tr'):
                    print(f"  Row: {tr.get_text(separator=' ', strip=True)}")
        
        # 着順の確認
        print("\nChecking rank (is-isX class):")
        for k in range(1, 7):
            el = soup.find(class_=f'is-is{k}')
            if el:
                parent_tr = el.find_parent('tr')
                rank_raw = parent_tr.find('td').get_text(strip=True) if parent_tr else "N/A"
                print(f"  Boat {k}: Class is-is{k} found. Rank text in same row: {rank_raw}")

    except Exception as e:
        print(f"Error during debug: {e}")

if __name__ == "__main__":
    debug_race_result()
