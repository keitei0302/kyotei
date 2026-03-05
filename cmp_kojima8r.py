import requests
import json

def compare_race_data():
    place = "16" # 児島
    race = 8
    date = "20260304"
    
    print(f"--- Comparing Data for {place}#{race} ({date}) ---")
    
    url = f"http://localhost:8000/api/predict?place={place}&race={race}"
    try:
        res = requests.get(url, timeout=15)
        data = res.json()
        
        # 5号艇と6号艇を抽出
        p5 = next((p for p in data['players'] if p['teiban'] == 5), None)
        p6 = next((p for p in data['players'] if p['teiban'] == 6), None)
        
        b5 = data['beforeinfo'].get('5', data['beforeinfo'].get(5, {}))
        b6 = data['beforeinfo'].get('6', data['beforeinfo'].get(6, {}))
        
        a5 = next((r for r in data['ai_results'] if r['teiban'] == 5), None)
        a6 = next((r for r in data['ai_results'] if r['teiban'] == 6), None)
        
        print(f"\n[5号艇: {p5['name'] if p5 else 'N/A'}]")
        print(f"  勝率: {p5['win_rate'] if p5 else 'N/A'}")
        print(f"  ST: {p5['ST'] if p5 else 'N/A'}")
        print(f"  モーター2連率: {p5['motor_2ren'] if p5 else 'N/A'}%")
        print(f"  展示タイム: {b5.get('show_time', 'N/A')}")
        print(f"  チルト: {b5.get('tilt', 'N/A')}")
        print(f"  AI最終スコア: {a5['final_score'] * 100 if a5 else 'N/A'}pt")

        print(f"\n[6号艇: {p6['name'] if p6 else 'N/A'}]")
        print(f"  勝率: {p6['win_rate'] if p6 else 'N/A'}")
        print(f"  ST: {p6['ST'] if p6 else 'N/A'}")
        print(f"  モーター2連率: {p6['motor_2ren'] if p6 else 'N/A'}%")
        print(f"  展示タイム: {b6.get('show_time', 'N/A')}")
        print(f"  チルト: {b6.get('tilt', 'N/A')}")
        print(f"  AI最終スコア: {a6['final_score'] * 100 if a6 else 'N/A'}pt")
        
        # 展示平均の確認
        sts = [float(b.get('show_time', 0)) for b in data['beforeinfo'].values() if float(b.get('show_time', 0)) > 0]
        if sts:
            avg = sum(sts) / len(sts)
            print(f"\n[展示平均]: {avg:.2f}")

    except Exception as e:
        print(f"Error during comparison: {e}")

if __name__ == "__main__":
    compare_race_data()
