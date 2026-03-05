from keitei_app import get_beforeinfo
import json

def test_new_logic():
    place_no = 16
    race_no = 8
    date_str = "20260304"
    
    print(f"Testing place_no={place_no}, race_no={race_no}, date={date_str}...")
    result = get_beforeinfo(place_no, race_no, date_str)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_new_logic()
