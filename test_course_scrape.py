import requests
from bs4 import BeautifulSoup

toban = '4320'
url = f'https://www.boatrace.jp/owpc/pc/data/racersearch/course?toban={toban}'
res = requests.get(url)
print('Length:', len(res.text))
print('Status:', res.status_code)
if '1コース' in res.text:
    print('Found 1コース')
else:
    print('Not found 1コース')
soup = BeautifulSoup(res.text, 'html.parser')
for th in soup.find_all('th'):
    if 'コース' in th.get_text():
        print(th.get_text(strip=True))
# the actual course rows are typically in <tbody>
tbodies = soup.find_all('tbody')
for tb in tbodies:
    text = tb.get_text(strip=True)
    if '1コース' in text:
        print('Found tbody with 1コース', len(text))
