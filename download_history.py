import urllib.request
import re
import os
import lhafile
from datetime import datetime, timedelta

def download_and_extract(date_str, save_dir="data/raw"):
    # date_str format: YYYYMMDD
    os.makedirs(save_dir, exist_ok=True)
    
    # 公式サイトのアーカイブURL例: k260225.lzh (YYMMDD)
    yy = date_str[2:4]
    mm = date_str[4:6]
    dd = date_str[6:8]
    filename = f"k{yy}{mm}{dd}.lzh"
    url = f"https://www.boatrace.jp/yoso/archive/pc/{filename}"
    
    lzh_path = os.path.join(save_dir, filename)
    
    try:
        print(f"Downloading {url} ...")
        urllib.request.urlretrieve(url, lzh_path)
        print("Download complete. Extracting...")
        
        # lhafileを使って解凍
        f = lhafile.Lhafile(lzh_path)
        for info in f.infolist():
            content = f.read(info.filename)
            out_path = os.path.join(save_dir, info.filename)
            with open(out_path, "wb") as out_f:
                out_f.write(content)
            print(f"Extracted: {info.filename}")
            
    except Exception as e:
        print(f"Failed to process {date_str}: {e}")

if __name__ == "__main__":
    # テストとして昨日と今日のデータを取得してみる
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    download_and_extract(yesterday.strftime("%Y%m%d"))
    download_and_extract(today.strftime("%Y%m%d"))
