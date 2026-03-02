import sys
import os
sys.path.append(os.getcwd())
from keitei_app import get_beforeinfo
from datetime import datetime

place_no = "04" # 平和島
race_no = 4
date_str = datetime.now().strftime("%Y%m%d")

print(f"Testing scraper for Place: {place_no}, Race: {race_no}, Date: {date_str}")
data = get_beforeinfo(place_no, race_no, date_str)
print("Scraped Data:")
for t, info in data.items():
    print(f"Boat {t}: ShowTime={info['show_time']}, Tilt={info['tilt']}")
