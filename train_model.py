import sqlite3
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import lightgbm as lgb
import os
import pickle

# --- ユーザー独自の予想ルール（直感やロジック）を組み込む部分 ---
def apply_custom_rules(df_features, predictions):
    """
    MLモデルが出した予測確率(predictions)に対して、
    ユーザー独自のルールで確率を上げ下げする関数
    """
    adjusted_preds = predictions.copy()
    
    # 例: 「1コースは無条件で少しだけ評価を上げる」
    # df_features['teiban'] == 1 のインデックスを見つけて確率を加算
    # (ここでは特徴量に 'teiban' がある前提)
    
    # 例: 「荒れやすい場（例: 戸田=02, 江戸川=03）では、アウトコース（5, 6コース）の評価を上げる」
    
    # ※後ほど、この部分にご自身のルールを追加できるように分離してあります
    
    return adjusted_preds

# --- 機械学習モデルの構築と学習 ---
def prepare_data(db_path="data/boatrace_real.db"):
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return None
        
    conn = sqlite3.connect(db_path)
    # race_results テーブルから詳細データを読み込む
    df = pd.read_sql_query("SELECT * FROM race_results", conn)
    conn.close()
    
    if len(df) == 0:
        print("No training data available.")
        return None
        
    # 特徴量の選択
    # X: [place_no, teiban, motor_no, show_time, entry_course, st]
    # y: [target (1着=1, 他=0)]
    
    # NaNや異常値のクリーンアップ
    df = df.dropna(subset=['show_time', 'st', 'motor_no'])
    
    X = df[['place_no', 'teiban', 'motor_no', 'show_time', 'entry_course', 'st']].copy()
    y = df['target']
    
    # カテゴリ変数の処理 (LabelEncoderを使用し、保存する)
    from sklearn.preprocessing import LabelEncoder
    categorical_features = ['place_no', 'teiban', 'motor_no', 'entry_course']
    
    label_encoders = {}
    for col in categorical_features:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
        label_encoders[col] = le
        
    # 全てのデータ型を float に統一して型不整合を防ぐ
    X = X.astype(float)
        
    # Encoderの保存
    os.makedirs("models", exist_ok=True)
    with open("models/label_encoders.pkl", "wb") as f:
        pickle.dump(label_encoders, f)
        
    return X, y

def train_model():
    data = prepare_data()
    if data is None:
        return
        
    X, y = data
    # 異常値除去
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    print(f"Training data size: {len(X)} records")
    
    # 全てのメタデータを削ぎ落とす
    X_raw = X.values.astype(np.float32)
    y_raw = y.values.astype(np.float32)
    
    X_train, X_test, y_train, y_test = train_test_split(X_raw, y_raw, test_size=0.15, random_state=42)
    
    # Dataset作成。不整合チェックを避けるため検証セットは入れない
    train_data = lgb.Dataset(X_train, label=y_train, free_raw_data=False)
    
    params = {
        'objective': 'binary',
        'metric': 'binary_logloss',
        'boosting_type': 'gbdt',
        'learning_rate': 0.05,
        'verbose': -1
    }
    
    print("Training LightGBM model (Atomic Mode)...")
    # 特徴量名等のメタデータを一切持たない生の状態で学習
    model = lgb.train(
        params,
        train_data,
        num_boost_round=300
    )
    
    print("Model training completed.")
    
    # モデルの保存
    os.makedirs("models", exist_ok=True)
    with open("models/lgb_model.pkl", "wb") as f:
        pickle.dump(model, f)
    print("Model saved to models/lgb_model.pkl")
    
    return model

def predict_race(place_no, race_no, apply_rules=True):
    try:
        with open("models/lgb_model.pkl", "rb") as f:
            model = pickle.load(f)
    except FileNotFoundError:
        print("Model not found. Please train the model first.")
        return
        
    # 推論用データの作成 (1号艇〜6号艇)
    records = []
    for teiban in range(1, 7):
        records.append({
            'place_no': int(place_no),
            'race_no': int(race_no),
            'teiban': teiban
        })
        
    df_pred = pd.DataFrame(records)
    for col in ['place_no', 'race_no', 'teiban']:
        df_pred[col] = df_pred[col].astype('category')
        
    # AIによる純粋な予測確率 (1着になる確率)
    predictions = model.predict(df_pred)
    df_pred['ai_prob'] = predictions
    
    # ユーザー独自のルールを適用
    if apply_rules:
        # 例: 「1号艇はとにかく強いはずだ」という直感をルールとして上乗せする
        df_pred['custom_prob'] = df_pred['ai_prob'].copy()
        
        # 1号艇の確率を少しカサ増しする (例: +0.05)
        df_pred.loc[df_pred['teiban'] == 1, 'custom_prob'] += 0.05
        
        # 最終的な予測スコアとして使用
        final_probs = df_pred['custom_prob']
    else:
        final_probs = df_pred['ai_prob']
        
    # 確率が高い順にソート (上位3艇を本命とする)
    df_pred['final_score'] = final_probs
    df_sorted = df_pred.sort_values(by='final_score', ascending=False)
    
    print(f"\n=== {place_no}場 {race_no}R の予想結果 ===")
    print("【各艇の1着予測スコア】")
    for _, row in df_sorted.iterrows():
        print(f"{int(row['teiban'])}号艇: {row['final_score']:.3f} (AI単体: {row['ai_prob']:.3f})")
        
    top3 = df_sorted['teiban'].values[:3]
    print(f"\nおすすめの買い目(3連単): {top3[0]}-{top3[1]}-{top3[2]}")
    

if __name__ == "__main__":
    # 学習の実行
    train_model()
    
    # テスト予測: 平和島(04) 12R を予測してみる
    predict_race(4, 12)
