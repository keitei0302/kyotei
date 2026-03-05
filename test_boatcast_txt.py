import requests

def test_boatcast_txt():
    place_no = "16"
    race_no = "08" # 2 digits
    date_str = "20260304"
    
    url = f"https://race.boatcast.jp/txt/{place_no}/bc_oriten_{date_str}_{place_no}_{race_no}.txt"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        # Shift-JIS or UTF-8? Let's try to decode
        try:
            text = res.content.decode('utf-8')
        except:
            text = res.content.decode('shift_jis')
            
        print(f"URL: {url}")
        print("--- Content ---")
        print(text)
        print("---------------")
        
        # Parse logic
        lines = text.strip().split('\\n')
        times = {i: {'lap': 0.0, 'turn': 0.0, 'straight': 0.0} for i in range(1, 7)}
        
        for line in lines:
            parts = line.split() # split by any whitespace
            if len(parts) >= 4:
                try:
                    t_num = int(parts[0])
                    # Format: 1 Rock  Hiroaki 36.30  6.03  6.43
                    # so the last 3 elements are the times
                    val_strt = float(parts[-1])
                    val_turn = float(parts[-2])
                    val_lap = float(parts[-3])
                    times[t_num]['lap'] = val_lap
                    times[t_num]['turn'] = val_turn
                    times[t_num]['straight'] = val_strt
                except ValueError:
                    pass
                    
        import json
        print(json.dumps(times, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_boatcast_txt()
