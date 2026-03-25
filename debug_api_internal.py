import json
from keitei_app import get_today_players, get_beforeinfo, get_odds3t, get_race_result, predict_race, apply_user_intuition
import pandas as pd

def debug_api_response():
    place = '16'
    race = '10'
    today_str = '20260326'
    
    players_data = get_today_players(place, race, today_str)
    beforeinfo = get_beforeinfo(place, race, today_str)
    
    if not players_data:
        print("No players data")
        return

    players_list = players_data.get("players", [])
    df = pd.DataFrame(players_list)
    df = predict_race(place, race, today_str, df)
    df = apply_user_intuition(df)
    
    # フロントエンドに送られる形式を模倣
    res = {
        "players": players_list,
        "beforeinfo": beforeinfo,
        "ai_results": df.to_dict(orient='records')
    }
    
    # 第1号艇（菅選手）のデータを抽出して確認
    print("--- BeforeInfo (Internal) for Boat 1 ---")
    print(json.dumps(beforeinfo.get(1), indent=2))
    print("\n--- AI Results (Internal) for Boat 1 ---")
    boat1_ai = next((r for r in res["ai_results"] if r['teiban'] == 1), None)
    print(json.dumps(boat1_ai, indent=2, ensure_ascii=False))

debug_api_response()
