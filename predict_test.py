import requests
from bs4 import BeautifulSoup
import argparse
import random

def get_race_data_official(place_no, race_no, date_str):
    # ボートレース公式サイトの出走表URL
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={race_no}&jcd={place_no}&hd={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    print(f"URL: {url}")
    print("データを取得中...")
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # 選手名の取得
        player_names = [div.text.strip().replace('\n', '').replace('\u3000', ' ').replace('\r', '') 
                       for div in soup.select('.is-fs18') if div.text]
        
        # 取得できた選手名を出力（通常6名）
        players = player_names[:6]
        if not players:
            print("本日のレースデータがまだ公開されていないか、終了しています。")
            return None
            
        print("\n【出走表】")
        for i, name in enumerate(players):
            print(f"{i+1}号艇: {name}")
            
        return players
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None

def dummy_predict(players):
    print("\n【AI予測中...】")
    # 今回は学習モデルがないため、簡易的なロジックでランダム予測結果を出力します
    
    # 基本的にインコース（1,2）が強いという競艇の性質を模擬
    weights = [40, 20, 15, 10, 10, 5] 
    
    print("\n=== AI 予想（デモ版） ===")
    
    # 3連単の買い目を3つ出す
    print("おすすめの買い目 (3連単):")
    for _ in range(3):
        # 雑な重み付け抽選
        seq = []
        while len(seq) < 3:
            choice = random.choices([1,2,3,4,5,6], weights=weights)[0]
            if choice not in seq:
                seq.append(choice)
        
        prob = random.randint(10, 35)
        print(f" {seq[0]}-{seq[1]}-{seq[2]} (予想的中率: {prob}%)")
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--place", type=str, default="05", help="場コード (多摩川は05)")
    parser.add_argument("--race", type=str, default="3", help="レース番号")
    parser.add_argument("--date", type=str, default="20260225", help="日付 yyyymmdd")
    
    args = parser.parse_args()
    place_no = args.place.zfill(2)
    
    place_names = {"04": "平和島", "05": "多摩川", "12": "尼崎"} # 一部抜粋
    p_name = place_names.get(place_no, f"場{place_no}")
    
    print(f"--- {p_name} 第{args.race}R ({args.date}) の予想 ---")
    
    players = get_race_data_official(place_no, args.race, args.date)
    if players:
        dummy_predict(players)
