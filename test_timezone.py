from datetime import datetime, timedelta

def test_date_calculation():
    # 日本時間 (JST) を取得 (UTC+9)
    # 実際のコードと同じロジック
    now_utc = datetime.utcnow()
    now_jst = now_utc + timedelta(hours=9)
    
    target_date = now_jst - (timedelta(days=1) if now_jst.hour < 5 else timedelta(0))
    d_str = target_date.strftime("%Y%m%d")
    
    print(f"UTC Now: {now_utc}")
    print(f"JST Now: {now_jst}")
    print(f"Target Date: {d_str}")
    
    # 検証: 現在の日本時間が 2026-03-04 13:16 (JST) ならば、
    # 5時を過ぎているので Target Date は 20260304 になるはず。
    
    # シミュレーション: 日本時間の午前4時 (JST) の場合
    sim_jst_early = datetime(2026, 3, 4, 4, 0, 0)
    target_early = sim_jst_early - (timedelta(days=1) if sim_jst_early.hour < 5 else timedelta(0))
    print(f"Sim JST 04:00 -> Target: {target_early.strftime('%Y%m%d')} (Expected: 20260303)")
    
    # シミュレーション: 日本時間の午前6時 (JST) の場合
    sim_jst_late = datetime(2026, 3, 4, 6, 0, 0)
    target_late = sim_jst_late - (timedelta(days=1) if sim_jst_late.hour < 5 else timedelta(0))
    print(f"Sim JST 06:00 -> Target: {target_late.strftime('%Y%m%d')} (Expected: 20260304)")

if __name__ == "__main__":
    test_date_calculation()
