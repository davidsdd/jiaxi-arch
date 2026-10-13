import pathlib,json,base64,csv
root=pathlib.Path(__file__).resolve().parents[1]
out=root/'output'
records=[]
for r in csv.DictReader((out/'建筑尺寸与来源.csv').open(encoding='utf-8-sig')):
 code=r['编号'];category=code[0] if len(code)==3 and code[0] in 'ABC' else 'public'
 records.append({'code':code,'name':r['建筑名称'],'layer':r['图层'],'height':float(r['高度_m']),'area':float(r['平面占地_m2']),'width':float(r['地图轴向宽_m']),'depth':float(r['地图轴向深_m']),'estimated':'估算' in r['高度说明'],'basis':r['尺寸来源'],'partition':r['体块说明'],'category':category})
data={'modelByteLength':(out/'XJTU_InnovationHarbour.3ds').stat().st_size,'model':base64.b64encode((out/'XJTU_InnovationHarbour.3ds').read_bytes()).decode(),'layers':json.loads((out/'layer_map.json').read_text()),'records':records,'preview':'data:image/png;base64,'+base64.b64encode((out/'模型鸟瞰预览.png').read_bytes()).decode()}
template=(root/'scripts/viewer.template.html').read_text()
bundle=(root/'tmp/viewer.bundle.js').read_text()
html=template.replace('__CAMPUS_DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</',r'<\/')).replace('__VIEWER_BUNDLE__',bundle.replace('</script',r'<\/script'))
assert '__CAMPUS_DATA__' not in html and '__VIEWER_BUNDLE__' not in html
path=root/'index.html';path.write_text(html,encoding='utf-8')
print(path,'bytes:',path.stat().st_size,'buildings:',len(records))
