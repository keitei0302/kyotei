"""
train_model_v2.py
本物の過去レース成績（boatrace_real.db）を使用して、
LightGBMモデルを学習・再構築するスクリプト。
"""

import sqlite3
import pandas as pd
import lightgbm as lgb
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def load_data(db_path='data/boatrace_real.db'):
    if not os.path.exists(db_path):
        print(f"エラー: {db_path} が見つかりません。先に download_history_txt.py を実行してください。")
        return None

    conn = sqlite3.connect(db_path)
    # 全データをロード
    # 枠番(teiban)ごとの1着(target=1/0)を予測するバイナリ分類
    query = "SELECT date, place_no, race_no, teiban, target FROM race_results"
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"データロード完了: {len(df)} レコード")
    return df

def train():
    df = load_data()
    if df is None: return

    # 特徴量エンジニアリング
    # 学習時点では「場」「レース番号」「枠番」のみ
    # （※勝率や展示タイムなどは、学習データ側に持たせるには別途スクレイピングが必要なため、
    #  一旦基本項目のみで精度を上げます。将来的にはここにも展示タイム等を追加します）
    
    X = df[['place_no', 'race_no', 'teiban']]
    y = df['target']

    # カテゴリカル変数の設定
    for col in ['place_no', 'race_no', 'teiban']:
        X[col] = X[col].astype('category')

    # 学習・検証データ分割
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("学習を開始します (LightGBM)...")
    model = lgb.LGBMClassifier(
        objective='binary',
        metric='binary_logloss',
        boosting_type='gbdt',
        num_leaves=31,
        learning_rate=0.05,
        n_estimators=1000
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(stopping_rounds=50)]
    )

    # 評価
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nモデル精度 (Accuracy): {acc:.4f}")

    # 保存
    os.makedirs('models', exist_ok=True)
    with open('models/lgb_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    print("\nモデルを保存しました: models/lgb_model.pkl")

if __name__ == '__main__':
    train()
