import requests
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from keitei_app import get_today_players, get_beforeinfo, get_odds3t, get_race_result, predict_race, apply_user_intuition
import pandas as pd

place, race, today_str = '18', 1, '20260305'
players = get_today_players(place, race, today_str)
if players:
    df = pd.DataFrame(players['players'])
    print('Players:', df.columns)
    df = predict_race(place, race, today_str, df)
    print('After Predict:', df.columns)
    df = apply_user_intuition(df)
    print('Final:', df[['teiban', 'ai_prob', 'custom_prob']])
    # check parts
    if 'parts_exchange' in df.columns:
        print('Parts:', df[['teiban', 'parts_exchange']])
