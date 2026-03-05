import requests
from bs4 import BeautifulSoup
import json
import re

def test_boatcast():
    url = "https://race.boatcast.jp/?jo=16"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 取得できたHTMLのテキストを一部出力して確認
        text_content = soup.get_text()
        print("HTML内に '周回' や '展示' などの文字が含まれているか確認します:")
        
        keywords = ["タイム", "周回", "回り足", "直線", "オリジナル展示", "展示"]
        for kw in keywords:
            if kw in text_content:
                print(f"✅ キーワード '{kw}' を発見しました")
            else:
                print(f"❌ '{kw}' は見つかりません")
        
        # iframeやscriptなどで非同期読み込みされていないかチェック
        frames = soup.find_all('iframe')
        print(f"\\nIframe: {len(frames)}個")
        for f in frames:
            print("  - src:", f.get('src'))
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_boatcast()
