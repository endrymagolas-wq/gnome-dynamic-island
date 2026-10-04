import assert from 'node:assert/strict';
import {IslandWorld,applicationState,terrainHeight} from '../extensions/cartoon-island@avalon.local/world.js';
import {drawAtlasCharacter} from '../extensions/cartoon-island@avalon.local/scene-3d.js';
import {TARGETS,ATLAS,groundPoint,projectGround,characterFrame,needsFrames,coveredByWindows,fitPlate,VIEW} from '../extensions/cartoon-island@avalon.local/resort-layout.js';
const w=new IslandWorld();
assert.equal(w.present('invalid',0),false);assert.equal(w.present('editing',NaN),false);
w.present('starting',0);assert.equal(w.x,TARGETS.idle.x);assert.equal(w.floors,0);
w.present('editing',1);assert.equal(w.floors,1);for(let i=0;i<10;i++)w.present('editing',2+i);assert.equal(w.floors,4);
w.present('permission',20);w.step(21,.1);assert(w.path.length>0);
w.step(22,1,false);assert.equal(w.x,w.target().x);assert.equal(w.z,w.target().z);assert.equal(needsFrames(w,true),false);
w.step(201,.1);assert.equal(w.source,'desktop');assert.equal(w.state,'idle');
w.present('done',210);w.step(231,.1);assert.equal(w.state,'idle');
assert.equal(applicationState('org.mozilla.firefox.desktop'),'browsing');assert.equal(applicationState('com.visualstudio.code.desktop'),'working');assert.equal(applicationState('org.gnome.Terminal.desktop'),'working');assert.equal(applicationState('org.gnome.Nautilus.desktop'),'idle');
for(const [x,y] of [[371,366],[458,319],[628,337],[744,434],[429,254]]){const ground=groundPoint(x,y),p=projectGround(ground.x,ground.z);assert(Math.abs(x-p.x)<.0001&&Math.abs(y-p.y)<.0001);}
let now=300;
for(const state of ['starting','editing','testing','permission','browsing','done','testing','browsing','editing','idle']){
 w.present(state,now);
 for(let i=0;i<220;i++){const old={x:w.x,z:w.z};now+=.1;w.step(now,.1);const p=projectGround(w.x,w.z);
  assert(Math.hypot(w.x-old.x,w.z-old.z)<=.085001);assert(terrainHeight(w.x,w.z)>0);
  assert(p.x>=370&&p.x<=745&&p.y>=253&&p.y<=435,'route stays on baked island');
  assert(!(p.x>426&&p.x<521&&p.y>265&&p.y<313),'worker enters desk');
  assert(!(p.x>530&&p.x<735&&p.y<312),'worker enters resort villa');
  const f=characterFrame(w,now);assert(f.x>=0&&f.y>=0&&f.x+f.width<=ATLAS.width&&f.y+f.height<=1700);
 }
 assert(Math.hypot(w.x-w.target().x,w.z-w.target().z)<.001);
}
w.present('idle',now,'desktop');w.step(now,0,false);assert.equal(needsFrames(w,false),false);
w.step(now,.1,true);assert.equal(needsFrames(w,false),false);assert.equal(needsFrames(w,true),true);
w.present('permission',now);assert.equal(needsFrames(w,false),true);
const rect={x:10,y:20,width:100,height:80};
assert(coveredByWindows(rect,[{x:0,y:0,width:200,height:200}]));
assert(coveredByWindows(rect,[{x:0,y:0,width:65,height:200},{x:65,y:0,width:135,height:200}]));
assert(!coveredByWindows(rect,[{x:0,y:0,width:64,height:200},{x:65,y:0,width:135,height:200}]));
assert(!coveredByWindows(rect,[]));assert(!coveredByWindows(rect,[{x:110,y:20,width:100,height:80}]));
for(const [width,height] of [[1920,1080],[3840,2160],[3440,1440],[1080,1920]]){const f=fitPlate(width,height);assert(VIEW.width*f.scale<=width+.001&&VIEW.height*f.scale<=height+.001);}
for(const state of ['idle','starting','editing','testing','failed','permission','done','browsing','working'])for(let frame=0;frame<8;frame++){
 const calls=[];const ctx=new Proxy({}, {get:(_,key)=>(...args)=>{assert(args.filter(x=>typeof x==='number').every(Number.isFinite),key);calls.push(key);},set:()=>true});drawAtlasCharacter(ctx,state,frame);
 assert.equal(calls[0],'save');assert.equal(calls.at(-1),'restore');assert(calls.includes('fill'));
}
console.log('PASS resort registration/routes, sprite bounds/baking, idle/covered/reduced-motion policy, floor cap, expiry and monitor fitting');
