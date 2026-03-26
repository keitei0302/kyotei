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
from datetime import datetime, timedelta

app = FastAPI()

# 静的ファイルとテンプレートの設定
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

@app.get("/")
async def read_root(request: Request):
    # 最新のStarlette/FastAPI仕様に対応するため、キーワード引数で明確に指定する
    return templates.TemplateResponse(request=request, name="index.html", context={})

from concurrent.futures import ThreadPoolExecutor

@app.get("/api/predict")
async def predict(place: str, race: int):
    # 1. 日付計算（午前5時以前は前日分を取得）
    # 日本時間 (JST) を取得 (UTC+9)
    now_jst = datetime.utcnow() + timedelta(hours=9)
    today_str = (now_jst - (timedelta(days=1) if now_jst.hour < 5 else timedelta(0))).strftime("%Y%m%d")
    
    print(f"\n[API] Processing Race: {place}#{race} (Date: {today_str})")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        # 基本情報の並列取得
        f_players = executor.submit(get_today_players, place, race, today_str)
        f_before = executor.submit(get_beforeinfo, place, race, today_str)
        f_odds = executor.submit(get_odds3t, place, race, today_str)
        f_result = executor.submit(get_race_result, place, race, today_str)
        
        players = f_players.result()
        beforeinfo = f_before.result()
        odds3t = f_odds.result()
        results = f_result.result()

    if not players:
        return {"error": "No players found"}

    players_list = players.get("players", []) if isinstance(players, dict) else players

    # 2. 予測ロジックの実行 (keitei_app.py と同期)
    from keitei_app import predict_race, apply_user_intuition
    df = pd.DataFrame(players_list)
    # predict_race 内で beforeinfo も加味される
    df = predict_race(place, race, today_str, df)
    df = apply_user_intuition(df)
    df['final_score'] = df['custom_prob']

    # 3. 買い目データの整理（オッズがある場合とない場合）
    # フロントエンド側で的中判定しやすいようにデータを送る
    
    print(f"[API] Process Complete. Odds Count: {len(odds3t) if odds3t else 0}")
    return {
        "players": players_list,
        "beforeinfo": beforeinfo,
        "odds": odds3t,
        "results": results,
        "ai_results": df.to_dict(orient="records"),
        "debug": {"date": today_str}
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
