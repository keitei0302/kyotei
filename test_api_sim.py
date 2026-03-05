import json
from keitei_app import get_today_players, get_beforeinfo, get_odds3t, get_race_result, predict_race, apply_user_intuition
import pandas as pd
from datetime import datetime, timedelta

def test_api_full():
    place = '16'
    race = '8'
    today_str = '20260305'
    
    players = get_today_players(place, race, today_str)
    beforeinfo = get_beforeinfo(place, race, today_str)
    
    if not players:
        print("No players")
        return

    players_list = players.get("players", [])
    df = pd.DataFrame(players_list)
    df = predict_race(place, race, today_str, df)
    df = apply_user_intuition(df)
    
    res = {
        "players": players_list,
        "beforeinfo": beforeinfo,
        "ai_results": df.to_dict(orient='records')
    }
    
    print(json.dumps(res, indent=2, ensure_ascii=False))

test_api_full()
