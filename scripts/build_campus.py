"""Public-source outdoor campus massing. All coordinates and heights are in meters.
Requires rhino3dm, shapely, pyproj, trimesh, mapbox-earcut, numpy and matplotlib.
"""
import sys, os, json, math, csv, struct, pathlib, xml.etree.ElementTree as ET
import numpy as np
import trimesh
import rhino3dm as rh
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box, shape, mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely import affinity
from shapely import set_precision
from pyproj import Transformer

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)
HEIGHT_SOURCE = 'https://24959527.s21i.faiusr.com/61/ABUIABA9GAAgn5zYpQYowILN7gI.pdf'
MAP_SOURCE = 'https://vi.xjtu.edu.cn/cxg/cxgdt.htm'
tf = Transformer.from_crs(4326, 32649, always_xy=True)
ORIGIN_LON, ORIGIN_LAT = 108.646, 34.251
OX, OY = tf.transform(ORIGIN_LON, ORIGIN_LAT)
xml = ET.parse(ROOT / 'sources/osm_map.osm').getroot()
nodes = {}
node_tags = {}
for n in xml.findall('node'):
    i = int(n.attrib['id'])
    x, y = tf.transform(float(n.attrib['lon']), float(n.attrib['lat']))
    nodes[i] = (x-OX, y-OY)
    node_tags[i] = {t.attrib['k']: t.attrib['v'] for t in n.findall('tag')}
ways = {}
for w in xml.findall('way'):
    i = int(w.attrib['id'])
    ways[i] = {'id': i, 'tags': {t.attrib['k']: t.attrib['v'] for t in w.findall('tag')},
               'coords': [nodes[int(n.attrib['ref'])] for n in w.findall('nd') if int(n.attrib['ref']) in nodes]}
features = json.loads((ROOT / 'sources/site_features.geojson').read_text())['features']
features = [{'id': f['properties']['osm_id'], 'tags': f['properties'], 'poly': shape(f['geometry'])} for f in features]
site = next(f['poly'] for f in features if f['id'] == 492791467)
buildings = [f for f in features if 'building' in f['tags'] and site.buffer(15).contains(f['poly'].representative_point())]

# Published building numbers are matched to the university map and OSM location.
META = {
    13689263: ('B001', '敏行楼', 31.9, 7, '工程资料第7页：1号楼'),
    13689264: ('B002', '力行楼', 31.67, 7, '工程资料第7页：2号楼'),
    13689265: ('B003', '躬行楼', 31.92, 7, '工程资料第7页：3号楼'),
    14001685: ('B004', '泓理楼', 42.5, 9, '工程资料第7页：4号楼，主体7层，局部9层'),
    760895829: ('B005', '涵英楼', 88.8, 15, '工程资料第7页：5号楼，局部2层'),
    1038790001: ('B006', '米兰楼', 27.9, 6, '工程资料第7页：6号楼；按学校地图对应米兰楼'),
    1047701474: ('B007', '居源楼', 20.0, None, '缺少已核实标高；体块估算'),
    1017709116: ('B008', '高等工程教育博物馆', 23.95, 4, '工程资料第7页：8号楼'),
    870325661: ('B009', '阅览中心', 21.35, 3, '工程资料第7页：9号楼'),
    870325679: ('B015', '和鸣苑', 15.9, 3, '工程资料第7页：15号楼'),
    870325678: ('B016', '惠风苑', 17.7, 3, '工程资料第7页：16号楼'),
    870325677: ('B017', '朗清苑', 21.0, 3, '工程资料第7页：17号楼'),
    1017709048: ('B018', '泓生楼', 23.7, 5, '工程资料第7页：18号楼；按学校地图对应'),
    1017533272: ('B019', '泓德楼', 23.7, 5, '工程资料第7页：19号楼；按学校地图对应'),
    1017709046: ('B020', '泓仁楼', 23.7, 5, '工程资料第7页：20/21号楼，单栋对应关系待复核'),
    760895826: ('B021', '泓润楼', 23.7, 5, '工程资料第7页：20/21号楼；OSM标6层，采用工程资料高度'),
    962000803: ('B022', '动物实验中心', 21.9, 4, '工程资料第7页：22号楼'),
    1038790005: ('B023', '同和苑', 18.0, None, '缺少已核实标高；体块估算'),
    1038790002: ('S001', '校车候车处', 3.6, None, '缺少已核实标高；体块估算'),
    1047701466: ('S002', '保安亭', 3.3, None, '缺少已核实标高；体块估算'),
    1047701473: ('S003', '鸽舍', 3.0, None, '缺少已核实标高；体块估算'),
}
for prefix, ids in [
    ('A', [1017723397,1017723400,1017723401,1017723402,1017723403,1017723404,1017723405,1017723406,1017723407,1017723398]),
    ('B', [1017723379,1017723378,1017723377,1017723385,1017723376,1017723382,1017723374,1017723380,1017723381,1017723384,1017723375,1017723383]),
    ('C', [1017709107,1017709106,1017709104,1017709105,1017709108,1017709111,1017709109,1017709103,1017709102,1017709113,1017709110,1017709112]),
]:
    garden = {'A':'和园','B':'惠园','C':'朗园'}[prefix]
    for j, i in enumerate(ids, 1):
        h = 23.65 if prefix=='A' and j==1 else (31.98 if prefix=='B' and j<=5 else 31.8)
        levels = 8 if prefix=='A' and j==1 else 11
        META[i] = (prefix+f'{j:02d}', garden+f'{prefix}{j:02d}宿舍', h, levels, '工程资料第7页；宿舍编号按学校地图位置对应')
assert len(buildings) == 55
assert all(f['id'] in META for f in buildings)
buildings.sort(key=lambda f: META[f['id']][0])

def polygons(g):
    if g.is_empty: return []
    if g.geom_type in ['Polygon','MultiPolygon']:
        g=set_precision(g.buffer(0),.001).buffer(0)
    if isinstance(g, Polygon): return [orient(g, sign=1)] if g.area > 0.05 else []
    if hasattr(g, 'geoms'): return [p for q in g.geoms for p in polygons(q)]
    return []

COLORS = {
    'Wall': (224,220,201), 'Roof': (161,76,60), 'DormRoof': (184,153,101),
    'MedicalRoof': (133,151,159), 'Ground': (219,220,207), 'Road': (89,101,109),
    'Paving': (195,186,162), 'Grass': (112,156,112), 'Water': (80,153,174),
    'Track': (166,96,77), 'Court': (104,132,143), 'Marking': (230,227,209),
    'Leaves': (72,123,81), 'Trunk': (129,106,78),
}
model = rh.File3dm()
model.ApplicationName = 'XJTU Innovation Harbour Public-source Campus Model'
model.ApplicationDetails = 'Generated outdoor massing; measured coordinates in meters; editable Rhino extrusions.'
model.Settings.ModelUnitSystem = rh.UnitSystem.Meters
model.Settings.ModelAbsoluteTolerance = 0.01
model.Settings.ModelAngleToleranceDegrees = 1
model.Settings.ModelRelativeTolerance = 0.001
anchor = model.Settings.EarthAnchorPoint
anchor.Name = 'Innovation Harbour local origin / WGS84'
anchor.EarthBasepointLatitude = ORIGIN_LAT
anchor.EarthBasepointLongitude = ORIGIN_LON
anchor.EarthBasepointElevation = 0
anchor.ModelBasePoint = rh.Point3d(0,0,0)
anchor.ModelNorth = rh.Vector3d(0,1,0)
anchor.ModelEast = rh.Vector3d(1,0,0)
model.Settings.EarthAnchorPoint = anchor
material_ids = {}
for name, color in COLORS.items():
    mat = rh.Material()
    mat.Name = name
    mat.DiffuseColor = (*color,255)
    mat.AmbientColor = (*[int(c*.5) for c in color],255)
    mat.Shine = 0
    material_ids[name] = model.Materials.Add(mat)
layers = {}
def add_layer(name, color):
    layer=rh.Layer();layer.Name=name;layer.Color=(*color,255)
    idx=model.Layers.Add(layer);layers[name]=idx;return idx
env_layer = add_layer('环境', COLORS['Grass'])
objects_3ds = []
layer_map = {}
records = []
model_meshes = []
native_solids = []
feature_records = []

def attrs(name, layer, mat, info=None):
    a=rh.ObjectAttributes();a.Name=name;a.LayerIndex=layer;a.MaterialIndex=material_ids[mat]
    a.MaterialSource=rh.ObjectMaterialSource.MaterialFromObject
    a.ColorSource=rh.ObjectColorSource.ColorFromObject;a.ObjectColor=(*COLORS[mat],255)
    if info:
        for k,v in info.items():a.SetUserString(k,str(v))
    return a

def mesh_rh(m):
    r=rh.Mesh()
    for v in m.vertices:r.Vertices.Add(*map(float,v))
    for f in m.faces:r.Faces.AddFace(*map(int,f))
    r.Normals.ComputeNormals();r.Compact()
    assert r.IsValid
    return r

def extrusion_rh(p, z, h):
    c=rh.PolylineCurve([rh.Point3d(float(x),float(y),float(z)) for x,y in p.exterior.coords])
    e=rh.Extrusion.Create(c,float(h),True)
    assert e is not None
    for ring in p.interiors:
        c=rh.PolylineCurve([rh.Point3d(float(x),float(y),float(z)) for x,y in ring.coords])
        assert e.AddInnerProfile(c)
    assert e.IsValid and e.IsSolid
    return e

def extrude(p, z, h):
    p=orient(p.simplify(.001,preserve_topology=True),sign=1)
    m=trimesh.creation.extrude_polygon(p,float(h),engine='earcut')
    m.apply_translation((0,0,z))
    m.merge_vertices(digits_vertex=7)
    m.update_faces(m.nondegenerate_faces())
    m.update_faces(m.unique_faces())
    m.remove_unreferenced_vertices()
    trimesh.repair.fix_normals(m,multibody=True)
    if m.volume < 0:m.invert()
    if not m.is_watertight:
        (ROOT/'tmp/problem_polygon.wkt').write_text(p.wkt)
        np.savez(ROOT/'tmp/problem_mesh.npz',v=m.vertices,f=m.faces)
    assert m.is_watertight and m.is_winding_consistent, (p.bounds,p.area,len(m.vertices),len(m.faces),m.is_watertight,m.is_winding_consistent)
    return m

def push_mesh(name, m, mat, layer_name, face_mats=None, native=True, info=None):
    assert len(m.vertices)<65536 and len(m.faces)<65536
    fm=list(face_mats) if face_mats is not None else [mat]*len(m.faces)
    objects_3ds.append({'name':name,'mesh':m,'materials':fm})
    layer_map[name] = {'layer': layer_name, 'color': COLORS[mat], 'category': 'environment' if layer_name=='环境' else 'building'}
    model_meshes.append((m,fm))
    if native:model.Objects.AddMesh(mesh_rh(m),attrs(name,layers[layer_name],mat,info))

def uv(g):return affinity.rotate(g,-30,origin=(0,0))
def xy(g):return affinity.rotate(g,30,origin=(0,0))

for f in buildings:
    i,p=f['id'],f['poly']
    code,name,height,levels,basis=META[i]
    layer_name=code+'_'+name
    add_layer(layer_name,COLORS['Wall'])
    local=uv(p);u0,v0,u1,v1=local.bounds
    # Preserve the footprint. Local height partitions are illustrative, not surveyed roof plans.
    parts=[(p,height)]
    partition='统一采用资料建筑高度的简化范围体块'
    if code=='B005':
        north = local.intersection(box(u0-1,v1-43,u1+1,v1+1))
        tower = north.intersection(box((u0+u1)/2-17,v0-1,(u0+u1)/2+17,v1+1))
        rest=local.difference(north)
        parts=[(xy(rest),14.0),(xy(north.difference(tower)),56.0),(xy(tower),height)]
        partition='最高88.8m有来源；14m/56m辅楼及塔身分区位置依据公开鸟瞰图推定'
    elif code=='B004':
        tower=local.intersection(box((u0+u1)/2-28,v1-37,(u0+u1)/2+28,v1+1))
        parts=[(xy(local.difference(tower)),32.0),(xy(tower),height)]
        partition='最高42.5m有来源；32m主体及局部高区范围为体块推定'
    elif code in ['B001','B002','B003']:
        lab=local.intersection(unary_union([box(u0-1,v0-1,u0+31,v1+1),box(u1-31,v0-1,u1+1,v1+1)]))
        parts=[(xy(lab),14.0),(xy(local.difference(lab)),height)]
        partition='最高标高有来源；两侧14m实验大厅分区按公开鸟瞰图简化推定'
    roof='DormRoof' if code[0] in ['A','B','C'] and len(code)==3 else ('MedicalRoof' if code in ['B018','B019','B020','B021','B022','B009'] else 'Roof')
    meshes=[]
    confidence='公开工程资料高度，非逐点实测' if levels else '高度估算，未核实'
    info={'建筑名称':name,'编号':code,'OSM来源':f'https://www.openstreetmap.org/{"relation" if f["tags"].get("relation") else "way"}/{i}',
          '高度米':height,'高度依据':basis,'高度置信度':confidence,'体块分区':partition,'平面依据':'OSM WGS84轮廓投影至UTM49N，非竣工测量',
          '地面标高':'局部相对标高0m；地形平整化'}
    n=0
    for pg,h in parts:
        for q in polygons(pg):
            e=extrusion_rh(q,0,h)
            a=attrs(code+f'_{n:02d}',layers[layer_name],'Wall',info)
            model.Objects.AddExtrusion(e,a);native_solids.append(e)
            m=extrude(q,0,h);meshes.append(m)
            face_mat=np.array(['Wall']*len(m.faces),dtype=object)
            face_mat[m.face_normals[:,2]>.9]=roof
            push_mesh(code+f'_{n:02d}',m,'Wall',layer_name,face_mat,native=False)
            n+=1
    # Editable map footprint, on the same building layer.
    for q in polygons(p):
        curve=rh.PolylineCurve([rh.Point3d(float(x),float(y),0) for x,y in q.exterior.coords])
        a=attrs(code+'_PLAN',layers[layer_name],'Wall',info);a.WireDensity=-1
        model.Objects.AddCurve(curve,a)
    record={'编号':code,'建筑名称':name,'图层':layer_name,'OSM_ID':i,'高度_m':height,'楼层资料':levels or '',
            '平面占地_m2':round(p.area,2),'地图轴向宽_m':round(u1-u0,2),'地图轴向深_m':round(v1-v0,2),
            '中心X_m':round(p.centroid.x,2),'中心Y_m':round(p.centroid.y,2),'高度说明':confidence,
            '尺寸来源':basis,'体块说明':partition,'高度来源链接':HEIGHT_SOURCE if levels else '',
            '平面来源链接':info['OSM来源'],'平面精度说明':'公开地图近似轮廓，未取得实测误差值'}
    records.append(record)
    feature_records.append({'type':'Feature','properties':record,'geometry':mapping(p)})

# Outdoor elements are kept together in one layer; roads, paving and grass stay separate objects.
footprints=unary_union([f['poly'] for f in buildings])
adjacent_greens=[]
for f in features:
    t,p=f['tags'],f['poly']
    if (t.get('leisure')=='park' or t.get('landuse')=='grass') and p.intersects(site.buffer(45)):
        adjacent_greens.append(p.intersection(site.buffer(90)))
scope=unary_union([site.buffer(18,join_style=2)]+adjacent_greens).buffer(0)
env_groups={k:[] for k in COLORS}
def env_shape(g,z,h,mat):
    for p in polygons(g):
        p=p.simplify(.05,preserve_topology=True)
        if p.area>.05:env_groups[mat].append(extrude(p,z,h))

env_shape(scope,-1.2,1.2,'Ground')
roads=[];paths=[];road_records=[]
width_default={'tertiary':8.0,'residential':6.0,'unclassified':6.0,'service':4.5,'footway':2.5,'pedestrian':5.0,'path':2.0,'cycleway':2.5}
for w in ways.values():
    t=w['tags'];cs=w['coords'];hw=t.get('highway')
    if hw not in width_default or len(cs)<2:continue
    line=LineString(cs)
    if not line.intersects(scope):continue
    if t.get('area')=='yes' and len(cs)>3 and cs[0]==cs[-1]:
        paths.append(Polygon(cs).intersection(scope));continue
    try:width=float(t.get('width',''))
    except ValueError:width=width_default[hw]
    surf=line.buffer(width/2,cap_style=2,join_style=2).intersection(scope).difference(footprints)
    (paths if hw in ['footway','pedestrian','path','cycleway'] else roads).append(surf)
    road_records.append({'OSM_ID':w['id'],'名称':t.get('name',hw),'宽度_m':width,'依据':'OSM width' if 'width' in t else '示意宽度，未实测','地理来源':'OSM中心线'})
road_area=unary_union(roads).buffer(0)
path_area=unary_union(paths).difference(road_area).buffer(0)
env_shape(road_area,0.035,.055,'Road')
env_shape(path_area,0.045,.07,'Paving')

green_polys=[];water_polys=[];sport_polys=[];plazas=[];tracks=[]
for f in features:
    p,t=f['poly'],f['tags']
    if not p.intersects(scope):continue
    p=p.intersection(scope).difference(footprints).difference(road_area).difference(path_area)
    if t.get('leisure')=='park' or t.get('landuse')=='grass' or t.get('name')=='中心绿地':green_polys.append(p)
    elif t.get('natural')=='water':water_polys.append(p)
    elif t.get('leisure')=='pitch':sport_polys.append((p,t))
    elif t.get('leisure')=='track':tracks.append(p)
    elif t.get('highway')=='pedestrian' and t.get('area')=='yes':plazas.append(p)
water=unary_union(water_polys)
sports=unary_union([p for p,t in sport_polys])
track=unary_union(tracks).difference(sports)
plaza=unary_union(plazas).difference(water).difference(sports)
greens=unary_union(green_polys).difference(water).difference(sports).difference(track).difference(plaza).buffer(0)
# Courtyard lawns retain the actual mapped voids; planting is schematic.
courtyard_lawns=[]
for f in buildings:
    for q in polygons(f['poly']):
        for ring in q.interiors:
            lawn=Polygon(ring).buffer(-3)
            if not lawn.is_empty:courtyard_lawns.append(lawn)
greens=unary_union([greens]+courtyard_lawns).difference(footprints).buffer(0)
env_shape(greens,0.06,.12,'Grass')
env_shape(water,0.10,.08,'Water')
env_shape(plaza,0.045,.085,'Paving')
env_shape(track,0.08,.06,'Track')
for p,t in sport_polys:
    env_shape(p,0.10,.055,'Grass' if t.get('sport')=='soccer' else 'Court')
    for q in polygons(p):
        marking=q.boundary.buffer(.08,cap_style=2,join_style=2).intersection(q)
        env_shape(marking,0.157,.01,'Marking')

# Low-poly trees: OSM tree-row alignment when available, plus illustrative park planting.
tree_points=[]
for w in ways.values():
    if w['tags'].get('natural')!='tree_row' or len(w['coords'])<2:continue
    line=LineString(w['coords'])
    for d in np.arange(3,line.length,13):
        p=line.interpolate(float(d))
        if scope.contains(p) and greens.buffer(2).contains(p) and not footprints.buffer(4).contains(p):tree_points.append((p.x,p.y))
rng=np.random.default_rng(20261012)
gx0,gy0,gx1,gy1=scope.bounds
for x in np.arange(gx0,gx1,20):
    for y in np.arange(gy0,gy1,20):
        xx,yy=x+rng.uniform(-5,5),y+rng.uniform(-5,5)
        p=Point(xx,yy)
        if greens.buffer(-5).contains(p) and not footprints.buffer(5).contains(p) and all((xx-a)**2+(yy-b)**2>100 for a,b in tree_points):
            tree_points.append((xx,yy))
for x,y in tree_points:
    h=float(rng.uniform(5.0,7.5));rad=float(rng.uniform(2.6,3.5))
    trunk=trimesh.creation.cylinder(radius=.23,height=h*.58,sections=6)
    trunk.apply_translation((x,y,.18+h*.29));env_groups['Trunk'].append(trunk)
    leaf=trimesh.creation.icosphere(subdivisions=0,radius=1)
    leaf.apply_scale((rad,rad,h*.43));leaf.apply_translation((x,y,.18+h*.67));env_groups['Leaves'].append(leaf)

# Road-side paving strip distinguishes carriageways without inventing detailed sidewalks.
kerb=road_area.buffer(1.2,join_style=2).difference(road_area).difference(footprints).difference(greens).difference(water).intersection(scope)
env_shape(kerb,0.05,.09,'Paving')
env_index=1
for mat,meshes in env_groups.items():
    chunk=[];nv=0;nf=0
    def flush():
        global env_index
        if not chunk:return
        m=trimesh.util.concatenate(chunk)
        push_mesh('E'+f'{env_index:05d}',m,mat,'环境',info={'环境分类':mat,'尺度':'1单位=1米','细节说明':'道路宽度、树位、地表高差为示意；详见说明'})
        env_index+=1
    for m in meshes:
        if nv+len(m.vertices)>60000 or nf+len(m.faces)>60000:
            flush();chunk=[];nv=0;nf=0
        chunk.append(m);nv+=len(m.vertices);nf+=len(m.faces)
    flush()

# Native Rhino named views.
cx,cy=scope.centroid.x,scope.centroid.y
view=rh.ViewInfo();view.Name='鸟瞰_Aerial'
view.Viewport.SetCameraLocation(rh.Point3d(cx+1300,cy-1700,1900))
view.Viewport.SetCameraDirection(rh.Vector3d(-1300,1700,-1880))
view.Viewport.SetCameraUp(rh.Vector3d(0,0,1))
view.Viewport.TargetPoint=rh.Point3d(cx,cy,20)
view.Viewport.ChangeToParallelProjection(True)
view.Viewport.SetFrustum(-1000,1000,-900,900,1,6000)
model.NamedViews.Add(view)
top=rh.ViewInfo();top.Name='总平面_Plan'
top.Viewport.SetCameraLocation(rh.Point3d(cx,cy,2500))
top.Viewport.SetCameraDirection(rh.Vector3d(0,0,-1))
top.Viewport.SetCameraUp(rh.Vector3d(0,1,0))
top.Viewport.TargetPoint=rh.Point3d(cx,cy,0)
top.Viewport.ChangeToParallelProjection(True)
top.Viewport.SetFrustum(-800,800,-800,800,1,5000)
model.NamedViews.Add(top)
notes='创新港校区公开资料体块模型；单位米。55栋建筑分别建层；环境单独一层。建筑平面为OSM近似轮廓，主要建筑最大高度来自陕西建工公开资料第7页。道路宽度、树位、地形和局部屋顶高度分区为示意。不能认证为实测模型。'
model.Strings['ModelNotes']=notes
assert model.Write(str(OUT/'XJTU_InnovationHarbour_Layered.3dm'),7)

# 3DS binary writer: separate named objects, per-face materials, 16-bit mesh limits.
def chunk(tag,data=b''):return struct.pack('<HI',tag,len(data)+6)+data
def zstr(s):return s.encode('ascii')+b'\0'
def rgb(c):return chunk(0x0011,bytes(c))
materials=b''
for name,c in COLORS.items():
    materials+=chunk(0xAFFF,chunk(0xA000,zstr(name))+chunk(0xA010,rgb(tuple(int(v*.45) for v in c)))+chunk(0xA020,rgb(c))+chunk(0xA030,rgb((30,30,30)))+chunk(0xA040,chunk(0x0030,struct.pack('<H',0))))
objdata=b''
for o in objects_3ds:
    m=o['mesh'];v=np.asarray(m.vertices,dtype='<f4');faces=np.asarray(m.faces,dtype='<u2')
    vertices=chunk(0x4110,struct.pack('<H',len(v))+v.tobytes())
    ff=np.column_stack((faces,np.full(len(faces),7,dtype='<u2'))).astype('<u2')
    fdata=struct.pack('<H',len(faces))+ff.tobytes()
    for mat in sorted(set(o['materials'])):
        inds=np.array([i for i,x in enumerate(o['materials']) if x==mat],dtype='<u2')
        fdata+=chunk(0x4130,zstr(mat)+struct.pack('<H',len(inds))+inds.tobytes())
    # Zero smoothing groups preserves crisp building edges and faceted tree crowns.
    fdata+=chunk(0x4150,np.zeros(len(faces),dtype='<u4').tobytes())
    tri=chunk(0x4100,vertices+chunk(0x4120,fdata))
    objdata+=chunk(0x4000,zstr(o['name'])+tri)
edit=chunk(0x3D3D,chunk(0x3D3E,struct.pack('<I',3))+chunk(0x0100,struct.pack('<f',1.0))+materials+objdata)
(OUT/'XJTU_InnovationHarbour.3ds').write_bytes(chunk(0x4D4D,chunk(0x0002,struct.pack('<I',3))+edit))
(OUT/'layer_map.json').write_text(json.dumps(layer_map,ensure_ascii=False,indent=2))
with (OUT/'建筑尺寸与来源.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
with (OUT/'道路宽度与来源.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(road_records[0]));writer.writeheader();writer.writerows(road_records)
(OUT/'建筑轮廓_本地米坐标.geojson').write_text(json.dumps({'type':'FeatureCollection','name':'XJTU_local_meters','coordinate_system':{'crs':'EPSG:32649','origin_easting':OX,'origin_northing':OY,'unit':'m','note':'Subtract origin from projected coordinates; not longitude/latitude'},'features':feature_records},ensure_ascii=False))

# Save the exact exported meshes for rendering/QA rather than regenerate a separate preview model.
all_vertices=[];all_faces=[];face_colors=[];offset=0
for m,fm in model_meshes:
    all_vertices.append(m.vertices);all_faces.append(m.faces+offset)
    face_colors.extend([COLORS[k] for k in fm]);offset+=len(m.vertices)
np.savez_compressed(OUT/'preview_mesh_data.npz',vertices=np.vstack(all_vertices),faces=np.vstack(all_faces),colors=np.array(face_colors,dtype=np.uint8))
summary={'building_count':len(buildings),'layer_count':len(model.Layers),'environment_layer':'环境','native_closed_extrusions':len(native_solids),
         '3ds_object_count':len(objects_3ds),'vertices':offset,'triangles':sum(len(m.faces) for m,fm in model_meshes),'tree_count':len(tree_points),
         'units':'meters','origin_wgs84':[ORIGIN_LON,ORIGIN_LAT],'origin_utm49n':[OX,OY],
         'scope_area_m2':scope.area,'campus_osm_area_m2':site.area,'scope_bounds_m':scope.bounds,'max_height_m':max(r['高度_m'] for r in records),
         'height_estimated_building_count':sum(not META[f['id']][3] for f in buildings),'height_source':HEIGHT_SOURCE,
         'precision':'Metric projection of public map footprints; no survey accuracy certification',
         'ground':'Flat relative Z=0; no surveyed elevation or terrain surface',
         'environment':'Mapped road centerlines, green/water/plaza boundaries; road widths and tree locations are approximate'}
(OUT/'模型统计.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
