import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const canvas=document.querySelector('#stage'),status=document.querySelector('#status');
let renderer;
try{renderer=new THREE.WebGLRenderer({canvas,antialias:true});}
catch(error){status.textContent='WebGL unavailable. View the actual Blender render and download the GLB.';document.querySelectorAll('nav button').forEach(b=>b.disabled=true);throw error;}
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.35;
const scene=new THREE.Scene();scene.background=new THREE.Color('#cbd2c6');
scene.add(new THREE.HemisphereLight(0xffffff,0x4e5e4d,3));
for(const [x,y,z,power] of [[15,25,10,5],[-10,14,-15,3]]){const l=new THREE.DirectionalLight(0xfff3dc,power);l.position.set(x,y,z);scene.add(l);}
const camera=new THREE.PerspectiveCamera(40,1,.05,250),controls=new OrbitControls(camera,canvas);controls.enableDamping=false;controls.minDistance=5;controls.maxDistance=70;controls.maxPolarAngle=Math.PI*.49;
let current=null,wire=false,generation=0,home=null;
function render(){const {width,height}=canvas.getBoundingClientRect();renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();renderer.render(scene,camera);}
controls.addEventListener('change',render);new ResizeObserver(render).observe(canvas);
function reset(){if(home){camera.position.copy(home.position);controls.target.copy(home.target);controls.update();render();}}
function dispose(object){object.traverse(o=>{if(o.geometry)o.geometry.dispose();if(o.material){for(const m of Array.isArray(o.material)?o.material:[o.material])m.dispose();}});}
async function load(name){
  const ticket=++generation;status.textContent='Loading '+name+'...';
  try{
    const [model,response]=await Promise.all([new GLTFLoader().loadAsync(`assets/${name}/model.glb`),fetch(`assets/${name}/scene_telemetry.json`)]);
    if(!response.ok)throw Error('Missing model evidence');const data=await response.json();
    if(ticket!==generation){dispose(model.scene);return;}
    if(current){scene.remove(current);dispose(current);}current=model.scene;scene.add(current);
    current.traverse(o=>{if(o.isMesh)o.material.wireframe=wire;});
    const bounds=new THREE.Box3().setFromObject(current),size=bounds.getSize(new THREE.Vector3()),center=bounds.getCenter(new THREE.Vector3());
    const distance=Math.max(size.x,size.y,size.z)*1.8;
    home={target:center,position:center.clone().add(new THREE.Vector3(distance*.75,distance*.42,distance))};reset();
    document.querySelector('#render').src=`assets/${name}/iso.png`;document.querySelector('#render').alt=`Actual Cycles render of ${name}`;
    document.querySelector('#download').href=`assets/${name}/model.glb`;
    document.querySelector('#stats').textContent=`${data.objects.length} components · ${data.params.tiers} tier(s) · ${size.y.toFixed(2)} nominal metres tall`;
    document.querySelector('#evidence').textContent=`Generated with ${data.engine}. Three actual Cycles views and SHA-256-linked GLB evidence included.`;
    for(const id of ['pagoda','pavilion'])document.querySelector('#'+id).setAttribute('aria-pressed',String(id===name));
    status.textContent='WebGL ready · '+name;render();
  }catch(error){if(ticket===generation)status.textContent='3D unavailable. The actual Blender render and GLB download remain available.';console.error(error);}
}
for(const name of ['pagoda','pavilion'])document.querySelector('#'+name).onclick=()=>load(name);
document.querySelector('#wire').onclick=e=>{wire=!wire;e.target.setAttribute('aria-pressed',String(wire));current?.traverse(o=>{if(o.isMesh)o.material.wireframe=wire;});render();};
document.querySelector('#reset').onclick=reset;
canvas.onkeydown=e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();const delta=camera.position.clone().sub(controls.target);const spherical=new THREE.Spherical().setFromVector3(delta);spherical.theta+=e.key==='ArrowLeft'?.12:e.key==='ArrowRight'?-.12:0;spherical.phi=THREE.MathUtils.clamp(spherical.phi+(e.key==='ArrowUp'?-.1:e.key==='ArrowDown'?.1:0),.1,Math.PI*.49);camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical));controls.update();render();};
load('pagoda');
