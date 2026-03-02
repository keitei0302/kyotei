import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import sqlite3
import os
import re

def init_db(db_path="data/boatrace.db"):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS race_results (
            date TEXT,
            place_no TEXT,
            race_no INTEGER,
            rank1_teiban INTEGER,
            rank2_teiban INTEGER,
            rank3_teiban INTEGER,
            sanrentan_money INTEGER,
            UNIQUE(date, place_no, race_no)
        )
    ''')
    conn.commit()
    return conn

def scrape_race_result_bs4(date_str, place_no, race_no, conn):
    url = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return False
            
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # 着順の取得 (tbodyの中のtrを探す)
        ranks = []
        for tbody in soup.find_all('tbody'):
            for tr in tbody.find_all('tr'):
                # クラス名がわからなくても、tdの中身のテキスト構造で判定する
                tds = [td.text.strip().replace('\n', '').replace('\u3000', '') for td in tr.find_all('td')]
                
                # 着順表は [1着, 1号艇, 選手名, ...] のような構造になっている
                if len(tds) >= 3:
                    rank_text = tds[0].replace('着', '')
                    if rank_text in ['1', '2', '3'] and tds[1] in ['1', '2', '3', '4', '5', '6']:
                        ranks.append((int(rank_text), int(tds[1])))
                        
        if len(ranks) < 3:
            return False
            
        # 1着,2着,3着をソートして確保
        # 同着がある場合は最初のものを優先
        r1 = next((r[1] for r in ranks if r[0] == 1), None)
        r2 = next((r[1] for r in ranks if r[0] == 2), None)
        r3 = next((r[1] for r in ranks if r[0] == 3), None)
        
        if not r1 or not r2 or not r3:
            return False
            
        # 3連単の取得
        sanrentan_money = 0
        for tbody in soup.find_all('tbody'):
            for tr in tbody.find_all('tr'):
                text_content = tr.text.replace('\n', '').replace(' ', '').replace('\u3000', '')
                if '3連単' in text_content and '¥' in text_content:
                    # ¥1,230 のような表記を探す
                    match = re.search(r'¥([0-9,]+)', text_content)
                    if match:
                        try:
                            sanrentan_money = int(match.group(1).replace(',', ''))
                        except:
                            pass
                    break
            if sanrentan_money > 0:
                break
                
        if sanrentan_money > 0:
            cur = conn.cursor()
            cur.execute('''
                INSERT OR IGNORE INTO race_results 
                (date, place_no, race_no, rank1_teiban, rank2_teiban, rank3_teiban, sanrentan_money)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (date_str, place_no, race_no, r1, r2, r3, sanrentan_money))
            conn.commit()
            return True
            
        return False

    except Exception as e:
        print(f"[{place_no}R{race_no}] Error: {e}")
        return False

def collect_historical_data(start_date, end_date):
    conn = init_db()
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        print(f"--- Collecting data for {date_str} ---")
        
        for place_no in range(1, 25):
            place_str = str(place_no).zfill(2)
            success_count = 0
            for race_no in range(1, 13):
                if scrape_race_result_bs4(date_str, place_str, race_no, conn):
                    success_count += 1
                time.sleep(0.3)
                
            if success_count > 0:
                print(f"  Saved {success_count} races for place {place_str}")
                
        current_date += timedelta(days=1)
        
    conn.close()

if __name__ == "__main__":
    today = datetime.now()
    start = today - timedelta(days=2)
    end = today - timedelta(days=1)
    collect_historical_data(start, end)
