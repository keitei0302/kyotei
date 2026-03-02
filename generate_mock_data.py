import sqlite3
import os
import random
from datetime import datetime, timedelta

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

def generate_mock_history(days=30):
    conn = init_db()
    cur = conn.cursor()
    
    today = datetime.now()
    count = 0
    
    print(f"--- Generating {days} days of mock data for ML processing ---")
    
    for i in range(days):
        target_date = today - timedelta(days=i+1)
        date_str = target_date.strftime("%Y%m%d")
        
        # 1日で5場開催されていると仮定
        places = random.sample(range(1, 25), 5)
        
        for place_no in places:
            place_str = str(place_no).zfill(2)
            
            # 各場12レース
            for race_no in range(1, 13):
                # 競艇っぽく、1号艇の勝率を高くするモックデータ
                weights1 = [50, 20, 15, 10, 3, 2] # 1着の確率イメージ
                r1 = random.choices([1,2,3,4,5,6], weights=weights1)[0]
                
                weights2 = [10, 30, 30, 15, 10, 5]
                r2 = random.choices([1,2,3,4,5,6], weights=weights2)[0]
                while r2 == r1: r2 = random.choices([1,2,3,4,5,6])[0]
                
                weights3 = [5, 15, 20, 30, 20, 10]
                r3 = random.choices([1,2,3,4,5,6], weights=weights3)[0]
                while r3 == r1 or r3 == r2: r3 = random.choices([1,2,3,4,5,6])[0]
                
                # 配当金のモック（ガチガチなら低く、荒れたら高く）
                if r1 == 1 and r2 == 2:
                    money = random.randint(500, 1500)
                elif r1 == 6:
                    money = random.randint(10000, 100000)
                else:
                    money = random.randint(1500, 10000)
                    
                cur.execute('''
                    INSERT OR IGNORE INTO race_results 
                    (date, place_no, race_no, rank1_teiban, rank2_teiban, rank3_teiban, sanrentan_money)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (date_str, place_str, race_no, r1, r2, r3, money))
                count += 1
                
    conn.commit()
    conn.close()
    print(f"Completed! Generated {count} historical race records.")

if __name__ == "__main__":
    generate_mock_history(365) # 1年分のモックデータを作成

