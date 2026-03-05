import re

with open('keitei_app.py', 'r', encoding='utf-8') as f:
    code = f.read()

new_intuition = """
def apply_user_intuition(df_pred):
    # 新しい強力な補正ロジック
    df_pred['custom_prob'] = df_pred['ai_prob'].copy()
    
    # 各種スコア計算
    for i, row in df_pred.iterrows():
        score = row['ai_prob']
        
        # --- 1. 勝率アドバンテージ ---
        # 全国勝率と当地勝率の平均を重視
        win_rate = row.get('win_rate', 0.0)
        local_win = row.get('local_win_rate', win_rate)
        avg_win_rate = (win_rate + local_win) / 2
        if avg_win_rate >= 7.0:
            score += 0.15
        elif avg_win_rate >= 6.0:
            score += 0.08
        elif avg_win_rate < 4.0:
            score -= 0.05
            
        # 当地が極端に高い（当地巧者）
        if local_win - win_rate >= 1.0 and local_win >= 6.0:
            score += 0.05
            
        # --- 2. 展示タイムと節間タイム ---
        if row.get('show_time', 0) > 0:
            avg_st = df_pred[df_pred['show_time'] > 0]['show_time'].mean()
            diff = avg_st - row['show_time']
            # 展示が良いと最大+10%
            score += diff * 2.5
            
        if row.get('lap_time', 0) > 0:
            avg_lap = df_pred[df_pred['lap_time'] > 0]['lap_time'].mean()
            score += (avg_lap - row['lap_time']) * 0.5
            
        # --- 3. コース別・決まり手（逃げ・捲り）適性 ---
        course = int(row['teiban'])
        if course == 1:
            # イン逃げ評価
            if avg_win_rate >= 6.0 and row.get('ST', 0.20) < 0.15:
                score += 0.20 # 逃げ鉄板
            if row.get('motor_2ren', 0) >= 40.0:
                score += 0.05
        else:
            # ダッシュ・センターの捲り/差し評価
            if course in [3, 4] and row.get('ST', 0.20) < 0.14 and avg_win_rate >= 6.0:
                score += 0.10 # 捲り警戒
            if course in [2, 5] and avg_win_rate >= 6.5:
                score += 0.05 # 差し/捲り差し警戒
                
        # --- 4. 部品交換情報 ---
        parts = str(row.get('parts_exchange', 'なし'))
        if parts != 'なし':
            if 'リング' in parts:
                # リング交換は良化の兆しがある場合加点。基本はマイナス要素だが直前で変わる可能性
                score += 0.02
            elif 'ピストン' in parts or 'シリンダ' in parts:
                score -= 0.05 # 大掛かりな整備は機力難の証明
            elif 'キャブレタ' in parts or 'キャリアボデ' in parts:
                score -= 0.02
                
        if row.get('propeller', False):
            score -= 0.03 # 新ペラは調整が間に合ってないリスク
            
        df_pred.at[i, 'custom_prob'] = max(0.01, score)
        
    # 正規化
    total = df_pred['custom_prob'].sum()
    if total > 0:
        df_pred['custom_prob'] = df_pred['custom_prob'] / total
    
    return df_pred
"""

# 正規表現で元の apply_user_intuition を置換
# 非常に長いので、分割して置換するか、文字列で見つける
start_idx = code.find('def apply_user_intuition(df_pred):')
if start_idx != -1:
    end_idx = code.find('# ──────────────────────────────────────────', start_idx)
    if end_idx != -1:
        code = code[:start_idx] + new_intuition + code[end_idx:]

with open('keitei_app.py', 'w', encoding='utf-8') as f:
    f.write(code)
