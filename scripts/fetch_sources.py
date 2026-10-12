import urllib.request, urllib.parse, re, json, pathlib
from urllib.parse import urljoin

root = pathlib.Path(__file__).resolve().parents[1] / 'sources'
root.mkdir(exist_ok=True)
def fetch(url, filename, data=None):
    req = urllib.request.Request(url, data=data, headers={'User-Agent':'CampusMassingModel/1.0 (public research)'})
    raw = urllib.request.urlopen(req, timeout=150).read()
    (root / filename).write_bytes(raw)
    print(filename, len(raw), url, flush=True)
    return raw

page='https://vi.xjtu.edu.cn/cxg/cxgdt.htm'
s=fetch(page,'map_page.html').decode('utf-8')
imgs=re.findall(r'<img[^>]+src="([^"]+)"',s)
for i,u in enumerate(imgs):
    if '__local' in u or 'b77f' in u:
        try: fetch(urljoin(page,u),f'official_{i}.png')
        except Exception as e: print('Image error',str(e),flush=True)

q='[out:json][timeout:110];(nwr(34.244,108.632,34.273,108.678););out body geom;'
for endpoint in ['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']:
    try:
        fetch(endpoint,'osm_raw.json',urllib.parse.urlencode({'data':q}).encode())
        break
    except Exception as e: print('Overpass error', str(e),flush=True)
