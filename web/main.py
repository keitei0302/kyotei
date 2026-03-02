from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import sys

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keitei_app import get_today_players, get_beforeinfo, get_odds3t, get_race_result
import pickle
import pandas as pd
from datetime import datetime

app = FastAPI()

# 静的ファイルとテンプレートの設定
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

from concurrent.futures import ThreadPoolExecutor

@app.get("/api/predict")
async def predict(place: str, race: int):
    today_str = datetime.now().strftime("%Y%m%d")
    print(f"\n[API] Processing Race: {place}#{race} at {datetime.now().time()}")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        # 1. 基本情報の並列取得
        f_players = executor.submit(get_today_players, place, race, today_str)
        f_before = executor.submit(get_beforeinfo, place, race, today_str)
        f_odds = executor.submit(get_odds3t, place, race, today_str)
        f_result = executor.submit(get_race_result, place, race, today_str)
        
        players = f_players.result()
        beforeinfo = f_before.result()
        odds3t = f_odds.result()
        results = f_result.result()
        
        # 2. 選手ごとの戦術データの並列取得
        from keitei_app import get_kimari_te, analyze_race_tactics
        kimari_te_data = {}
        if players:
            futures_kimari = {
                p['teiban']: executor.submit(get_kimari_te, p['toban']) 
                for p in players if 'toban' in p and p['toban'] != "0"
            }
            for teiban, f in futures_kimari.items():
                kimari_te_data[teiban] = f.result()
            
    # モデルの読み込み
    with open("models/lgb_model.pkl", "rb") as f:
        model = pickle.load(f)
        
    records = []
    for p in (players or []):
        bi = beforeinfo.get(p['teiban'], {'show_time': 0.0, 'tilt': 0.0})
        records.append({
            'place_no': place, 'race_no': race, 'teiban': p['teiban'],
            'ST': p['ST'], 'F': p['F'], 'L': p['L'], 'win_rate': p['win_rate'],
            'motor_2ren': p['motor_2ren'], 'show_time': bi['show_time'], 'tilt': bi['tilt'],
        })
        
    df_pred = pd.DataFrame(records)
    if not df_pred.empty:
        for col in ['place_no', 'race_no', 'teiban']:
            df_pred[col] = df_pred[col].astype('category')
        predictions = model.predict(df_pred[['place_no', 'race_no', 'teiban']])
        df_pred['ai_prob'] = predictions
        df_pred = analyze_race_tactics(df_pred, kimari_te_data)
        
    print(f"[API] Process Complete. Odds Count: {len(odds3t)}")
    return {
        "players": players,
        "beforeinfo": beforeinfo,
        "odds": odds3t,
        "results": results,
        "ai_results": df_pred.to_dict(orient="records"),
        "kimari_te": kimari_te_data
    }

if __name__ == "__main__":
    import uvicorn
    import argparse
    import os
    
    # Renderなどの環境では $PORT が指定されるため、それを優先的に使用する
    port = int(os.environ.get("PORT", 8000))
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=port)
    args = parser.parse_args()
    
    print(f"--- Starting Server on http://0.0.0.0:{args.port} ---")
    # 外部(Render)からアクセスできるように host を 0.0.0.0 に設定
    uvicorn.run(app, host="0.0.0.0", port=args.port)
