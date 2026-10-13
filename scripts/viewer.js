import {prepareLandscape,stabilizeBuildingMaterial,updateCampusDepthRange} from './surface_rendering.js';
import {groundHeight} from './ground_height.js';
import {installMapSelection} from './map_selection.js';
import {CampusMapControls,setRotationMode,frameCampusBox} from './campus_controls.js';
import {parseCampusModel,nextPaint} from './model_parser.js';
import {loadingIndicator} from './loading.js';
import {loadModelBytes} from './model_data.js';
import {updateCampusZoomLimit} from './camera_limits.js';
import * as THREE from 'three';

const data=JSON.parse(document.getElementById('campus-data').textContent);
const $=id=>document.getElementById(id);
let bytes=null;
const records=data.records;
const byLayer=new Map(records.map(r=>[r.layer,r]));
const buildingGroups=new Map();
let selected=null,category='all',renderer,scene,camera,controls,campus,envMeshes=[],pickMeshes=[],edgeLines=[],campusDiagonal=1,modelReady=false,pendingFocus=null,renderBounds=null,frameHeight=1750,viewMode='aerial';
const sidebar=$('sidebar');
const compact=window.matchMedia('(max-width:720px)');
function syncSidebar(){sidebar.classList.toggle('closed',compact.matches);$('toggle-sidebar').setAttribute('aria-expanded',String(!sidebar.classList.contains('closed')));}
syncSidebar();compact.addEventListener('change',syncSidebar);
$('toggle-sidebar').addEventListener('click',()=>{sidebar.classList.toggle('closed');$('toggle-sidebar').setAttribute('aria-expanded',String(!sidebar.classList.contains('closed')));});
$('close-sidebar').addEventListener('click',()=>{sidebar.classList.add('closed');$('toggle-sidebar').setAttribute('aria-expanded','false');});
$('open-help').addEventListener('click',()=>$('help-dialog').showModal());
$('close-help').addEventListener('click',()=>$('help-dialog').close());
$('help-dialog').addEventListener('click',e=>{if(e.target===$('help-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
function download(blob,name){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('download-3ds').addEventListener('click',()=>download(new Blob([bytes],{type:'application/octet-stream'}),'XJTU_InnovationHarbour.3ds'));
$('download-image').addEventListener('click',()=>{if(!renderer||!modelReady)return;drawScene();renderer.domElement.toBlob(blob=>{if(blob)download(blob,'创新港_当前视角.png');},'image/png');});

const loadLabels={local:'读取本地模型',read:'下载模型数据',decode:'解码模型数据',unpack:'解压模型数据',parse:'解析建筑几何',scene:'准备建筑与景观',render:'绘制首个视图',ready:'加载完成',total:'总体'};
const loadingView=loadingIndicator($('load-progress'),$('load-status'),key=>loadLabels[key.slice(5)]);
const reportLoad=event=>loadingView.update(event);
$('download-image').disabled=true;$('download-3ds').disabled=true;
function listRecords(){const q=$('search').value.trim().toLowerCase();return records.filter(r=>(category==='all'||r.category===category)&&(!q||r.name.toLowerCase().includes(q)||r.code.toLowerCase().includes(q)));}
function refreshList(){
 const list=$('building-list');list.replaceChildren();
 const filtered=listRecords();
 if(!filtered.length){const p=document.createElement('div');p.className='empty-list';p.textContent='没有匹配的建筑';list.append(p);}
 for(const r of filtered){
  const row=document.createElement('div');row.className='building-row'+(selected===r.code?' selected':'');row.dataset.code=r.code;
  const toggle=document.createElement('input');toggle.type='checkbox';toggle.disabled=!modelReady;toggle.checked=buildingGroups.get(r.code)?.visible??true;toggle.setAttribute('aria-label','显示'+r.name);
  toggle.addEventListener('change',()=>setVisible(r.code,toggle.checked));
  const btn=document.createElement('button');btn.type='button';btn.className='building-button';btn.title=r.name;
  const name=document.createElement('span');name.className='building-name';name.textContent=r.name;
  const code=document.createElement('span');code.className='building-code';code.textContent=r.code;
  btn.append(name,code);btn.addEventListener('click',()=>selectBuilding(r.code,true));
  row.append(toggle,btn);list.append(row);
 }
 updateCount();
}
function updateCount(){const n=[...buildingGroups.values()].filter(g=>g.visible).length;$('visible-count').innerHTML=(buildingGroups.size?n:55)+'<small>/ 55</small>';$('status-text').textContent=`${buildingGroups.size?n:55} 栋建筑显示 · 米制模型 · 公开资料近似体块`;}
function setVisible(code,value){const g=buildingGroups.get(code);if(g)g.visible=value;if(!value&&selected===code)selectBuilding(null);updateCount();render();}
$('search').addEventListener('input',refreshList);
document.querySelectorAll('[data-category]').forEach(b=>b.addEventListener('click',()=>{category=b.dataset.category;document.querySelectorAll('[data-category]').forEach(x=>{const active=x===b;x.classList.toggle('active',active);x.setAttribute('aria-pressed',String(active));});refreshList();}));
$('show-all').addEventListener('click',()=>{for(const g of buildingGroups.values())g.visible=true;$('environment').checked=true;envMeshes.forEach(m=>m.visible=true);refreshList();render();});
$('environment').addEventListener('change',e=>{envMeshes.forEach(m=>m.visible=e.target.checked);render();});
$('edges').addEventListener('change',e=>{edgeLines.forEach(l=>l.visible=e.target.checked);render();});
function emptyDetail(){$('detail').innerHTML='<div class="detail-title">探索校区空间</div><div class="detail-sub">点击模型或列表中的建筑，查看高度、宽深和来源说明。</div><div class="detail-note">55 栋建筑逐栋分层。环境包含道路、广场、绿地、水景和运动场。尺寸依据公开资料，部分内容为估算。</div>';}
function selectBuilding(code,focus=false){
 selected=code;
 for(const [c,g] of buildingGroups)g.children.forEach(m=>{if(m.isMesh)(Array.isArray(m.material)?m.material:[m.material]).forEach(mat=>{mat.emissive.set(c===code?0x284e3d:0);mat.emissiveIntensity=c===code?.32:0;});});
 if(!code){emptyDetail();refreshList();render();return;}
 const r=records.find(x=>x.code===code);if(!r)return;
 const g=buildingGroups.get(code);if(g)g.visible=true;
 const panel=$('detail');panel.replaceChildren();
 const title=document.createElement('div');title.className='detail-title';title.textContent=r.name;
 const sub=document.createElement('div');sub.className='detail-sub';sub.textContent=r.code+' · '+(r.estimated?'高度估算':'采用公开工程高度');
 const dl=document.createElement('dl');dl.className='dimensions';
 for(const [label,value] of [['最高高度',`${r.height.toFixed(2)} m`],['平面占地',`${Math.round(r.area).toLocaleString()} m²`],['地图轴向宽度',`${r.width.toFixed(2)} m`],['地图轴向深度',`${r.depth.toFixed(2)} m`]]){const cell=document.createElement('div');const dt=document.createElement('dt');dt.textContent=label;const dd=document.createElement('dd');dd.textContent=value;cell.append(dt,dd);dl.append(cell);}
 const actions=document.createElement('div');actions.className='detail-actions';
 const locate=document.createElement('button');locate.textContent='定位此建筑';locate.disabled=!modelReady;locate.addEventListener('click',()=>focusBuilding(code));
 const only=document.createElement('button');only.textContent='单独查看';only.disabled=!modelReady;only.addEventListener('click',()=>{for(const[c,x]of buildingGroups)x.visible=c===code;refreshList();focusBuilding(code);});
 const clear=document.createElement('button');clear.textContent='取消选择';clear.addEventListener('click',()=>selectBuilding(null));actions.append(locate,only,clear);
 const note=document.createElement('p');note.className='detail-note';note.textContent=r.partition+'。平面尺寸来自公开地图近似轮廓，未取得实测误差值。';
 const basis=document.createElement('p');basis.className='detail-note';basis.textContent='高度依据：'+r.basis;
 panel.append(title,sub,dl,actions,note,basis);
 refreshList();if(focus)focusBuilding(code);render();
}
function aspect(){const r=$('viewport').getBoundingClientRect();return Math.max(1,r.width)/Math.max(1,r.height);}
function updateFrustum(){if(!camera)return;const a=aspect();camera.left=-frameHeight*a/2;camera.right=frameHeight*a/2;camera.top=frameHeight/2;camera.bottom=-frameHeight/2;camera.updateProjectionMatrix();if(controls)updateCampusZoomLimit(camera,controls,campusDiagonal);}
function fitBox(box,mode=viewMode,focus=false){
 frameHeight=frameCampusBox(camera,controls,box,{aspect:aspect(),mode,pad:1.2,distance:3000,direction:new THREE.Vector3(1.3,-.7,1.15),minimumHeight:80,pivotHeight:focus?undefined:groundHeight(data,(box.min.x+box.max.x)/2,(box.min.y+box.max.y)/2)});updateFrustum();render();
}
function focusBuilding(code){if(!modelReady){pendingFocus=code;return;}const g=buildingGroups.get(code);if(!g||!camera)return;g.visible=true;g.updateWorldMatrix(true,true);fitBox(new THREE.Box3().setFromObject(g),'aerial',true);viewMode='aerial';setViewButtons();}
function setViewButtons(){for(const name of ['aerial','plan']){$(name).classList.toggle('active',viewMode===name);$(name).setAttribute('aria-pressed',String(viewMode===name));}}
function syncRotationButton(){const b=$('rotation-mode');b.classList.toggle('active',Boolean(controls?.rotationMode));b.setAttribute('aria-pressed',String(Boolean(controls?.rotationMode)));}
function resetInteraction(){if(controls)setRotationMode(controls,false);syncRotationButton();}
$('rotation-mode').onclick=()=>{if(controls)setRotationMode(controls,!controls.rotationMode);syncRotationButton();};
function fullView(mode){if(mode==='plan')resetInteraction();viewMode=mode;setViewButtons();if(campus)fitBox(new THREE.Box3().setFromObject(campus),mode);}
$('aerial').addEventListener('click',()=>fullView('aerial'));
$('plan').addEventListener('click',()=>fullView('plan'));
$('reset-view').addEventListener('click',()=>{resetInteraction();fullView('aerial');});
let renderQueued=false;
function render(updateShadows=true){if(renderer&&updateShadows!==false)renderer.shadowMap.needsUpdate=true;if(!renderer||!modelReady||renderQueued)return;renderQueued=true;requestAnimationFrame(()=>{renderQueued=false;drawScene();});}
function drawScene(){
 if(!renderer||!modelReady)return;
 updateCampusDepthRange(camera,renderBounds);renderer.render(scene,camera);
 const north=new THREE.Vector3(0,1,0).transformDirection(camera.matrixWorldInverse);
 $('north-arrow').style.transform=`rotate(${Math.atan2(north.x,north.y)}rad)`;
}
refreshList();
async function initializeModel(){
try{
 bytes=await loadModelBytes(data,{},reportLoad);
 $('download-3ds').disabled=false;
 THREE.Object3D.DEFAULT_UP.set(0,0,1);
 renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,preserveDrawingBuffer:true});
 renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));renderer.setClearColor(0xedf1e9);
 renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.NoToneMapping;
 renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
 renderer.domElement.setAttribute('aria-label','可旋转与缩放的创新港三维模型');renderer.domElement.setAttribute('tabindex','0');
 renderer.domElement.tabIndex=0;$('canvas-host').append(renderer.domElement);
 scene=new THREE.Scene();
 camera=new THREE.OrthographicCamera(-1000,1000,1000,-1000,.1,12000);camera.up.set(0,0,1);
 scene.add(new THREE.HemisphereLight(0xffffff,0x738068,2.0));
 const sun=new THREE.DirectionalLight(0xffffff,2.4);sun.position.set(-300,-650,1800);sun.target.position.set(550,700,0);scene.add(sun,sun.target);
 sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);sun.shadow.camera.left=-1300;sun.shadow.camera.right=1300;sun.shadow.camera.top=1300;sun.shadow.camera.bottom=-1300;sun.shadow.camera.near=1;sun.shadow.camera.far=4000;sun.shadow.bias=-.0003;sun.shadow.normalBias=1.0;
 campus=await parseCampusModel(bytes,reportLoad);
 const meshes=[];campus.traverse(o=>{if(o.isMesh)meshes.push(o);});
 const materialOverrides={Wall:0xe0dcc9,Roof:0xa14c3c,DormRoof:0xb89965,MedicalRoof:0x85979f,Ground:0xdbdccf,Road:0x59656d,Paving:0xc3baa2,Grass:0x709c70,Water:0x5099ae,Track:0xa6604d,Court:0x68848f,Marking:0xe6e3d1,Leaves:0x487b51,Trunk:0x816a4e};
 let prepared=0;
 for(const m of meshes){
  const old=Array.isArray(m.material)?m.material:[m.material];
  const mats=old.map(mat=>{const x=mat.clone();if(materialOverrides[x.name])x.color.setHex(materialOverrides[x.name]);x.flatShading=true;x.shininess=0;x.specular.set(0);x.emissiveIntensity=0;stabilizeBuildingMaterial(x);return x;});
  m.material=Array.isArray(m.material)?mats:mats[0];m.receiveShadow=true;
  const layer=data.layers[m.name];const r=layer?byLayer.get(layer.layer):null;
  if(r){
   let group=buildingGroups.get(r.code);if(!group){group=new THREE.Group();group.name=r.code;group.userData.record=r;buildingGroups.set(r.code,group);campus.add(group);}
   group.attach(m);m.castShadow=true;m.userData.code=r.code;pickMeshes.push(m);
   const edge=new THREE.LineSegments(new THREE.EdgesGeometry(m.geometry,35),new THREE.LineBasicMaterial({color:0x616b5a,transparent:true,opacity:.26}));edge.material.depthWrite=false;edge.renderOrder=1;m.add(edge);edgeLines.push(edge);
  }else{m.castShadow=mats.some(x=>x.name==='Leaves'||x.name==='Trunk');envMeshes.push(...prepareLandscape(m));}
  if(++prepared%32===0){reportLoad({phase:'scene',loaded:meshes.length+prepared,total:meshes.length*2});await nextPaint();}
 }
 reportLoad({phase:'scene',loaded:1,total:1});
 envMeshes.forEach(m=>m.visible=$('environment').checked);edgeLines.forEach(e=>e.visible=$('edges').checked);
 scene.add(campus);renderBounds=new THREE.Box3().setFromObject(campus);renderer.shadowMap.autoUpdate=false;renderer.shadowMap.needsUpdate=true;campusDiagonal=new THREE.Box3().setFromObject(campus).getSize(new THREE.Vector3()).length();
 controls=new CampusMapControls(camera,renderer.domElement);controls.groundHeight=(x,y)=>groundHeight(data,x,y);controls.addEventListener('change',()=>render(false));controls.listenToKeyEvents(renderer.domElement);syncRotationButton();
 renderer.domElement.addEventListener('keydown',e=>{if(e.ctrlKey||e.metaKey||e.altKey)return;if(['+','=','-','_'].includes(e.key)){e.preventDefault();if(e.key==='+'||e.key==='=')controls.dollyIn(.9);else controls.dollyOut(.9);}if(!e.repeat&&e.key.toLowerCase()==='r'){$('rotation-mode').click();}});
 const host=$('viewport');let lastHeight=host.clientHeight;const observer=new ResizeObserver(()=>{const h=host.clientHeight;if(h<1||host.clientWidth<1)return;if(lastHeight>0)frameHeight*=h/lastHeight;lastHeight=h;renderer.setSize(host.clientWidth,h);updateFrustum();render();});observer.observe(host);
 reportLoad({phase:'render',loaded:0,total:1});await nextPaint();modelReady=true;
 renderer.setSize(host.clientWidth,host.clientHeight);fullView('aerial');if(selected)selectBuilding(selected,Boolean(pendingFocus));pendingFocus=null;refreshList();
 const ray=new THREE.Raycaster();const pointer=new THREE.Vector2();
 function pick(e){const r=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(pointer,camera);const hits=ray.intersectObjects(pickMeshes.filter(m=>m.parent.visible),false);return hits[0]?.object.userData.code??null;}
 installMapSelection(renderer.domElement,e=>selectBuilding(pick(e)));
 renderer.domElement.addEventListener('pointermove',e=>{if(e.buttons||e.pointerType==='touch'){$('hover-tip').style.display='none';return;}const code=pick(e);const tip=$('hover-tip');if(code){const r=records.find(x=>x.code===code);tip.textContent=r.name+' · '+r.height.toFixed(2)+' m';tip.style.display='block';const box=host.getBoundingClientRect();tip.style.left=Math.min(e.clientX-box.left+15,host.clientWidth-tip.offsetWidth-12)+'px';tip.style.top=Math.min(e.clientY-box.top+15,host.clientHeight-tip.offsetHeight-45)+'px';renderer.domElement.style.cursor='pointer';}else{tip.style.display='none';renderer.domElement.style.cursor='grab';}});
 renderer.domElement.addEventListener('pointerleave',()=>$('hover-tip').style.display='none');
 renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();$('status-text').textContent='三维显示暂时中断，请重新打开本文件';});

 reportLoad({phase:'ready',loaded:1,total:1});await nextPaint();$('download-image').disabled=false;$('loading').remove();
}catch(err){
 console.error(err);modelReady=false;if(controls)controls.dispose();if(renderer)renderer.dispose();renderer=null;$('canvas-host').replaceChildren();
 const img=$('fallback');img.src=data.preview;img.style.display='block';$('loading').remove();
 const note=document.createElement('div');note.className='error-message';note.textContent='当前浏览器无法启动三维显示，已显示静态鸟瞰预览。可使用支持 WebGL 2 的 Chrome、Edge 或 Safari，并启用图形加速后重新打开。建筑尺寸查询与 3DS 下载仍可使用。';$('viewport').append(note);
 $('download-image').disabled=true;$('status-text').textContent='静态预览模式 · 三维显示未启用';
}
}
initializeModel();
