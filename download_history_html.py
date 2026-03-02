import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import sqlite3
import os

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

def scrape_race_result(date_str, place_no, race_no, conn):
    url = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return False
            
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # 着順の取得 (すべてから is-fs14 クラス等を持つ数字を探すなど、より柔軟に)
        # 今回はシンプルに 'is-fs14' を持つタグで 1, 2, 3 などのテキストを探す
        ranks = []
        # レース結果の着順行は <tbody> <tr> <td> の中にあります。
        # 着順テーブルを見つけるために "着" という文字を含んでいるか等で判断
        for tr in soup.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 3:
                r_text = tds[0].text.strip()
                t_text = tds[1].text.strip()
                if r_text in ['1', '2', '3', '4', '5', '6'] and t_text in ['1', '2', '3', '4', '5', '6']:
                    try:
                        ranks.append((int(r_text), int(t_text)))
                    except:
                        pass
        
        if len(ranks) < 3:
            return False
            
        ranks.sort(key=lambda x: x[0])
        r1, r2, r3 = ranks[0][1], ranks[1][1], ranks[2][1]
        
        # 3連単の取得
        sanrentan_money = 0
        for tr in soup.find_all('tr'):
            th = tr.find('th')
            if th and '3連単' in th.text:
                tds = tr.find_all('td')
                if len(tds) >= 2:
                    m_text = tds[1].text.replace(',', '').replace('¥', '').replace('円', '').strip()
                    try:
                        sanrentan_money = int(m_text)
                    except ValueError:
                        pass
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
        print(f"Error scraping {date_str} {place_no}R{race_no}: {e}")
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
                if scrape_race_result(date_str, place_str, race_no, conn):
                    success_count += 1
                time.sleep(0.3)
                
            if success_count > 0:
                print(f"  Saved {success_count} races for place {place_str}")
                
        current_date += timedelta(days=1)
        
    conn.close()
    print("Data collection completed.")

if __name__ == "__main__":
    # 2日前から1日前までのデータを取得テスト
    today = datetime.now()
    start = today - timedelta(days=2)
    end = today - timedelta(days=1)
    
    collect_historical_data(start, end)
