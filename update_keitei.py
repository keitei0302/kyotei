import re

with open('keitei_app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update result initialization in get_beforeinfo
code = re.sub(
    r"result = \{i: \{'show_time': 0\.0, 'tilt': 0\.0, 'propeller': False, 'lap_time': 0\.0, 'turn_time': 0\.0, 'straight_time': 0\.0\} for i in range\(1, 7\)\}",
    "result = {i: {'show_time': 0.0, 'tilt': 0.0, 'propeller': False, 'lap_time': 0.0, 'turn_time': 0.0, 'straight_time': 0.0, 'parts_exchange': 'なし'} for i in range(1, 7)}",
    code
)

# 2. Add parts extraction logic in get_beforeinfo
parts_logic = """
        # 1.5 部品交換情報の取得
        parts_table = soup.find('th', string=re.compile(r'部品交換'))
        if parts_table:
            ptb = parts_table.find_parent('table')
            if ptb:
                for i, tbody in enumerate(ptb.find_all('tbody')):
                    if i >= 6: break
                    t = tbody.get_text(separator=' ', strip=True)
                    # 艇番（1〜6）を除去
                    t = re.sub(r'^[1-6]\\s*', '', t)
                    result[i+1]['parts_exchange'] = t if t else 'なし'
"""
code = code.replace("        # 1. 展示タイムとチルトの取得", parts_logic + "        # 1. 展示タイムとチルトの取得")

# 3. Add get_player_course_data
course_data_func = """\
import urllib.request
def get_player_course_data(toban):
    # 選手のコース別成績（1〜6コースの1着率、2着率等）を取得
    # （逃げ率、差し率等として活用）
    url = f"https://www.boatrace.jp/owpc/pc/data/racersearch/course?toban={toban}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            soup = BeautifulSoup(res.read(), 'html.parser')
            
        course_stats = {}
        # 1着回数、出走回数などを探す
        tbodies = soup.find_all('tbody', class_='is-p10-0')
        for tbody in tbodies:
            tds = tbody.find_all('td')
            if len(tds) > 10:
                # コース番号は行の最初の方にあるか、表の構造から推定
                pass # 詳細パースは後続で
        return course_stats
    except Exception as e:
        print(f"[CourseData] Error: {e}")
        return {}
"""
# We will add it after get_today_players
if "def get_player_course_data" not in code:
    code = code.replace("# ──────────────────────────────────────────\n# AI予測", course_data_func + "\n# ──────────────────────────────────────────\n# AI予測")

with open('keitei_app.py', 'w', encoding='utf-8') as f:
    f.write(code)
