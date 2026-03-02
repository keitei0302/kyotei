import pandas as pd
import sqlite3
import os
import time
from datetime import datetime, timedelta
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

def scrape_race_result(date_str, place_no, race_no, conn):
    url = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={race_no}&jcd={place_no}&hd={date_str}"
    
    try:
        tables = pd.read_html(url, encoding='utf-8')
        
        # 着順の取得
        # Table 0が通常着順
        df_rank = tables[0]
        ranks = []
        for _, row in df_rank.iterrows():
            try:
                # 1着, 2着などの数字とし、枠番を抽出
                r = str(row[0]).replace('着', '').strip()
                waku = int(row[1])
                if r.isdigit():
                    ranks.append((int(r), waku))
            except:
                pass
                
        if len(ranks) < 3:
            print(f"[{place_no}R{race_no}] Error: len(ranks) < 3. Found: {ranks}")
            return False
            
        ranks.sort(key=lambda x: x[0])
        r1, r2, r3 = ranks[0][1], ranks[1][1], ranks[2][1]
        
        # 3連単の取得
        sanrentan_money = 0
        for df in tables:
            for _, row in df.iterrows():
                row_str = " ".join([str(x) for x in row.values])
                if '3連単' in row_str and '¥' in row_str:
                    match = re.search(r'¥([0-9,]+)', row_str)
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
        else:
            print(f"[{place_no}R{race_no}] Error: sanrentan_money not found.")
            
        return False

    except Exception as e:
        print(f"[{place_no}R{race_no}] Exception: {e}")
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

if __name__ == "__main__":
    today = datetime.now()
    start = today - timedelta(days=3)
    end = today - timedelta(days=1)
    collect_historical_data(start, end)
