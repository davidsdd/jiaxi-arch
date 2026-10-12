"""Render the exact exported CAD mesh arrays into an orthographic bird's-eye preview."""
import sys,pathlib,json,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'output'
d=np.load(OUT/'preview_mesh_data.npz');v=d['vertices'];f=d['faces'];c=d['colors']
S=2;W,H=2400,1850
canvas=Image.new('RGB',(W*S,H*S),(245,246,241));draw=ImageDraw.Draw(canvas)
back=np.array([1.30,-.70,1.15]);back/=np.linalg.norm(back)
right=np.cross(np.array([0.,0.,1.]),back);right/=np.linalg.norm(right)
up=np.cross(back,right)
def project(v):return np.column_stack([v@right,v@up,v@back])
pv=project(v);xmin,ymin=pv[:,:2].min(axis=0);xmax,ymax=pv[:,:2].max(axis=0)
scale=min((W-220)/(xmax-xmin),(H-430)/(ymax-ymin))
xoff=(W-(xmax-xmin)*scale)/2-xmin*scale
yoff=260+(H-430-(ymax-ymin)*scale)/2+ymax*scale
screen=np.column_stack(((pv[:,0]*scale+xoff)*S,(-pv[:,1]*scale+yoff)*S))
tri=v[f];norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);length=np.linalg.norm(norm,axis=1);norm/=np.maximum(length[:,None],1e-10)
light=np.array([-.35,-.55,1.]);light/=np.linalg.norm(light)
shade=.67+.33*np.maximum(norm@light,0)
rgb=np.clip(c*shade[:,None],0,255).astype(np.uint8)
# Depth buffering is necessary: large ground triangles cross several buildings.
pixels=np.full((H*S,W*S,3),[245,246,241],dtype=np.uint8)
depth=np.full((H*S,W*S),-np.inf,dtype=np.float32)
visible=np.flatnonzero(norm@back>1e-7)
for i in visible:
    pp=screen[f[i]];zz=pv[f[i],2]
    bx0=max(0,int(np.floor(pp[:,0].min())));bx1=min(W*S-1,int(np.ceil(pp[:,0].max())))
    by0=max(0,int(np.floor(pp[:,1].min())));by1=min(H*S-1,int(np.ceil(pp[:,1].max())))
    if bx1<bx0 or by1<by0:continue
    x0,y0=pp[0];x1,y1=pp[1];x2,y2=pp[2]
    den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
    if abs(den)<1e-9:continue
    xx=np.arange(bx0,bx1+1,dtype=np.float32)[None,:]+.5
    yy=np.arange(by0,by1+1,dtype=np.float32)[:,None]+.5
    wa=((y1-y2)*(xx-x2)+(x2-x1)*(yy-y2))/den
    wb=((y2-y0)*(xx-x2)+(x0-x2)*(yy-y2))/den
    wc=1-wa-wb;z=wa*zz[0]+wb*zz[1]+wc*zz[2]
    sub=depth[by0:by1+1,bx0:bx1+1]
    mask=(wa>=-1e-6)&(wb>=-1e-6)&(wc>=-1e-6)&(z>sub)
    sub[mask]=z[mask];pixels[by0:by1+1,bx0:bx1+1][mask]=rgb[i]
canvas=Image.fromarray(pixels);draw=ImageDraw.Draw(canvas)
fonts=['/System/Library/Fonts/PingFang.ttc','/System/Library/Fonts/STHeiti Light.ttc']
fontpath=next((q for q in fonts if pathlib.Path(q).exists()),None)
def font(n):return ImageFont.truetype(fontpath,n*S) if fontpath else ImageFont.load_default()
draw.text((110*S,70*S),'西安交通大学 · 创新港校区',font=font(54),fill=(39,66,71))
draw.text((112*S,150*S),'室外空间三维体块  /  建筑逐栋分层  /  1 单位 = 1 米',font=font(24),fill=(87,111,110))
draw.line((110*S,210*S,(W-110)*S,210*S),fill=(204,215,207),width=2*S)
items=[('教学科研',(161,76,60)),('学生宿舍',(184,153,101)),('道路',(89,101,109)),('广场铺装',(195,186,162)),('绿地景观',(112,156,112)),('水景',(80,153,174))]
x=112;y=H-130
for text,color in items:
    draw.rounded_rectangle((x*S,y*S,(x+24)*S,(y+24)*S),radius=4*S,fill=color)
    draw.text(((x+36)*S,(y-5)*S),text,font=font(22),fill=(67,88,89));x+=215
draw.text((112*S,(H-75)*S),'公开地图近似轮廓 + 公开工程高度；局部体块分区、道路宽度、树位及地形为简化表达。',font=font(20),fill=(102,116,111))
# Scale is valid for the horizontal screen direction of this orthographic projection.
bar=100*scale
x=(W-110-bar);y=H-125
draw.line((x*S,y*S,(x+bar)*S,y*S),fill=(51,75,74),width=3*S)
draw.line((x*S,(y-8)*S,x*S,(y+8)*S),fill=(51,75,74),width=2*S)
draw.line(((x+bar)*S,(y-8)*S,(x+bar)*S,(y+8)*S),fill=(51,75,74),width=2*S)
draw.text(((x+bar/2-35)*S,(y+15)*S),'100 m',font=font(20),fill=(51,75,74))
canvas.resize((W,H),Image.Resampling.LANCZOS).save(OUT/'模型鸟瞰预览.png')

# North-up plan from the exact original georeferenced footprint collection.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import shape
from matplotlib.patches import Polygon as Patch
from matplotlib.collections import PatchCollection
plt.rcParams['font.family']='Heiti TC'
fig,ax=plt.subplots(figsize=(12,13),facecolor='#f5f6f1');ax.set_facecolor('#f5f6f1');ax.set_aspect('equal')
ground_ids=np.flatnonzero((np.mean(tri[:,:,2],axis=1)<.3)&(norm[:,2]>.9))
ground_ids=ground_ids[np.argsort(np.mean(tri[ground_ids,:,2],axis=1))]
patches=[Patch(tri[i,:,:2],closed=True) for i in ground_ids]
ax.add_collection(PatchCollection(patches,facecolors=c[ground_ids]/255,edgecolors='none',antialiaseds=False))
for a in json.load(open(OUT/'建筑轮廓_本地米坐标.geojson'))['features']:
    p=shape(a['geometry']);r=a['properties'];code=r['编号']
    color='#b89965' if len(code)==3 else '#a14c3c'
    ax.fill(*p.exterior.xy,color=color,alpha=.88)
    for ring in p.interiors:ax.fill(*ring.xy,color='#c8d9ba')
    q=p.representative_point();ax.text(q.x,q.y,code,ha='center',va='center',fontsize=6.8,color='#253c3a')
ax.set_xlim(v[:,0].min()-40,v[:,0].max()+50);ax.set_ylim(v[:,1].min()-40,v[:,1].max()+50)
ax.set_xlabel('X 东向 / m');ax.set_ylabel('Y 北向 / m')
ax.set_title('创新港校区 | 总平面与建筑编号',loc='left',fontsize=18,pad=22)
ax.annotate('N',xy=(.96,.94),xytext=(.96,.88),xycoords='axes fraction',ha='center',arrowprops=dict(arrowstyle='->',lw=2,color='#27463e'),fontsize=16)
fig.savefig(OUT/'总平面与建筑编号.png',dpi=180,bbox_inches='tight')
print('Previews written')
