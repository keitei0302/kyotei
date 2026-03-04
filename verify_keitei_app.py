from keitei_app import get_beforeinfo
import json

def test_before_info():
    # 多摩川 (05) の第1レース、本日の日付でテスト (適宜変更してください)
    # ライブ中の場がない場合はエラーになりますが、コードの構造的な動作チェックとして実行します
    place = "05"
    race = 1
    date = "20260304" 
    
    print(f"--- Testing get_beforeinfo for {place}#{race} ({date}) ---")
    info = get_beforeinfo(place, race, date)
    
    print(json.dumps(info, indent=2))
    
    # 成功判定（データが空でないか）
    if any(v['show_time'] > 0 for v in info.values()):
        print("\n[SUCCESS] 展示タイムを取得できました。")
    else:
        print("\n[INFO] 展示タイムは取得できませんでした（開催時間外の可能性があります）。")

    if any(v['propeller'] for v in info.values()):
        print("[SUCCESS] プロペラ交換情報を検知しました。")
    else:
        print("[INFO] プロペラ交換情報は False です（全員交換なし、または取得失敗）。")

if __name__ == "__main__":
    test_before_info()
