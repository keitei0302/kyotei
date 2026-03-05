import requests

url = 'https://race.boatcast.jp/txt/16/bc_oriten_20260305_16_08.txt'
res = requests.get(url)
res.encoding = res.apparent_encoding
lines = res.text.strip().split('\n')

for line in lines:
    print(repr(line))
