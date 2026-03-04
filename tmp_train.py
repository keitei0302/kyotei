import sqlite3
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import pickle
import os

# 1. データの読み込み
conn = sqlite3.connect('data/boatrace_real.db')
df = pd.read_sql_query('SELECT * FROM race_results', conn)
conn.close()

# 2. 前処理
df = df.dropna(subset=['motor_no', 'show_time', 'st'])
X = df[['place_no', 'teiban', 'motor_no', 'show_time', 'entry_course', 'st']].copy()
y = df['target']

# 3. エンコーディング
label_encoders = {}
for col in ['place_no', 'teiban', 'motor_no', 'entry_course']:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col].astype(str))
    label_encoders[col] = le

# モデル/エンコーダー保存ディレクトリ
os.makedirs('models', exist_ok=True)
with open('models/label_encoders.pkl', 'wb') as f:
    pickle.dump(label_encoders, f)

# 4. 学習 (100% 数値 Numpy 配列として扱う)
X_values = X.values.astype(np.float32)
y_values = y.values.astype(np.float32)

X_train, X_test, y_train, y_test = train_test_split(X_values, y_values, test_size=0.15, random_state=42)

# Dataset作成 (単純化)
train_data = lgb.Dataset(X_train, label=y_train)

params = {
    'objective': 'binary',
    'metric': 'binary_logloss',
    'boosting_type': 'gbdt',
    'learning_rate': 0.05,
    'num_leaves': 31,
    'verbose': -1
}

print(f"Training on {len(X_train)} samples...")
model = lgb.train(params, train_data, num_boost_round=200)

# 5. 保存
with open('models/lgb_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Training Success!")
