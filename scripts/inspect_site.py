import sys,pathlib,xml.etree.ElementTree as ET,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
from pyproj import Transformer

root=pathlib.Path(__file__).resolve().parents[1]
(root/'tmp').mkdir(exist_ok=True)
xml=ET.parse(root/'sources/osm_map.osm').getroot()
tf=Transformer.from_crs(4326,32649,always_xy=True)
origin=tf.transform(108.646,34.251)
nodes={int(n.attrib['id']): (tf.transform(float(n.attrib['lon']),float(n.attrib['lat']))[0]-origin[0],tf.transform(float(n.attrib['lon']),float(n.attrib['lat']))[1]-origin[1]) for n in xml.findall('node')}
ways={int(w.attrib['id']):{'id':int(w.attrib['id']),'tags':{t.attrib['k']:t.attrib['v'] for t in w.findall('tag')},'coords':[nodes[int(a.attrib['ref'])] for a in w.findall('nd') if int(a.attrib['ref']) in nodes]} for w in xml.findall('way')}
def poly(w):
 c=w['coords'];return Polygon(c).buffer(0) if len(c)>3 and c[0]==c[-1] else None
site=poly(ways[492791467])
features=[]
for w in ways.values():
 p=poly(w)
 if p is not None and w['tags']:features.append(dict(w,geometry=p))
for r in xml.findall('relation'):
 tags={t.attrib['k']:t.attrib['v'] for t in r.findall('tag')}
 if tags.get('type')!='multipolygon':continue
 outer=[];inner=[]
 for m in r.findall('member'):
  w=ways.get(int(m.attrib['ref']))
  if m.attrib['type']=='way' and w:
   p=poly(w)
   if p is not None:(inner if m.attrib.get('role')=='inner' else outer).append(p)
 if outer: features.append({'id':int(r.attrib['id']),'tags':tags,'geometry':unary_union(outer).difference(unary_union(inner)),'relation':True})
bs=[f for f in features if 'building' in f['tags'] and site.buffer(15).contains(f['geometry'].representative_point())]
print('Site area',site.area,'bounds',site.bounds,'Buildings',len(bs))
fig,ax=plt.subplots(figsize=(13,14));ax.set_aspect('equal')
x,y=site.exterior.xy;ax.fill(x,y,facecolor='#eef3e9',edgecolor='#56685f')
for w in ways.values():
 if 'highway' in w['tags'] and len(w['coords'])>1:
  line=LineString(w['coords'])
  if line.intersects(site):
   x,y=line.xy;ax.plot(x,y,color='#c2c7c9',lw=1)
for i,f in enumerate(bs):
 p=f['geometry'];x,y=p.exterior.xy;ax.fill(x,y,color='#a5b8c9')
 for hole in p.interiors: x,y=hole.xy;ax.fill(x,y,color='#eef3e9')
 c=p.representative_point(); ax.text(c.x,c.y,str(i),fontsize=8,ha='center',va='center')
 print(i,f['id'],f['tags'].get('name',''),round(p.area),[round(c.x),round(c.y)],f['tags'])
ax.set_xlim(site.bounds[0]-80,site.bounds[2]+80);ax.set_ylim(site.bounds[1]-80,site.bounds[3]+80)
fig.savefig(root/'tmp/footprint_index.png',dpi=160,bbox_inches='tight')
from shapely.geometry import mapping
(root/'sources/site_features.geojson').write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{**f['tags'],'osm_id':f['id'],'relation':f.get('relation',False)},'geometry':mapping(f['geometry'])} for f in features]},ensure_ascii=False))
