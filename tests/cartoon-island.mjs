import assert from 'node:assert/strict';
import {IslandWorld,applicationState,terrainHeight,CAMERA} from '../extensions/cartoon-island@avalon.local/world.js';
import {drawWorld,project} from '../extensions/cartoon-island@avalon.local/scene-3d.js';
const w=new IslandWorld();
assert.equal(w.present('invalid',0),false);
assert.equal(w.present('editing',NaN),false);
w.present('starting',0);assert.equal(w.x,-1.4);assert.equal(w.floors,0);
w.present('editing',1);assert.equal(w.floors,1);
for(let i=0;i<10;i++)w.present('editing',2+i);
assert.equal(w.floors,4);
w.present('permission',20);const oldX=w.x;w.step(21,.1);assert(w.x>oldX);
w.step(22,1,false);assert.equal(w.x,w.target().x);assert.equal(w.z,w.target().z);
w.step(201,.1);assert.equal(w.source,'desktop');assert.equal(w.state,'idle');
w.present('done',210);w.step(231,.1);assert.equal(w.state,'idle');
assert.equal(applicationState('org.mozilla.firefox.desktop'),'browsing');
assert.equal(applicationState('com.visualstudio.code.desktop'),'working');
assert.equal(applicationState('org.gnome.Terminal.desktop'),'working');
assert.equal(applicationState('org.gnome.Nautilus.desktop'),'idle');
// All task/application transitions follow finite, bounded routes on land.
let now=300;
for(const state of ['starting','editing','testing','permission','browsing','done','testing','browsing','editing','idle']){
 w.present(state,now);
 for(let i=0;i<200;i++){
  const before={x:w.x,z:w.z};now+=.1;w.step(now,.1);
  assert(Math.hypot(w.x-before.x,w.z-before.z)<=.085001,'walking speed');
  assert(Math.hypot(w.x/3.1,w.z/2.25)<1,'worker left the island');
  assert(terrainHeight(w.x,w.z)>0,'worker walked into water');
  // Keep clear of building and desk, allowing the worker to reach the keyboard.
  assert(!(Math.abs(w.x-1.05)<.42&&Math.abs(w.z+.12)<.39),'route enters house');
  assert(!(Math.abs(w.x+.55)<.48&&Math.abs(w.z+.1)<.23),'route enters desk');
 }
 assert(Math.hypot(w.x-w.target().x,w.z-w.target().z)<.001,'arrival');
}
const back=project([-1,terrainHeight(-1,-1.15),-1.15]),front=project([-1,terrainHeight(-1,1),1]);
assert(back.y<front.y,'depth changes screen height');
assert.notEqual(terrainHeight(-1,-1.15),terrainHeight(-1,1),'terrain has elevation');
// Every state renders with finite coordinates at the default and rotated views.
for(const state of ['starting','editing','testing','failed','permission','done','working','browsing','idle'])for(const yaw of [CAMERA.yaw,-.7,2]){
 w.present(state,0);w.step(1,.1);
 const calls=[];
 const ctx=new Proxy({}, {get:(_,key)=>(...args)=>{assert(args.filter(x=>typeof x==='number').every(Number.isFinite),key);calls.push(key);},set:()=>true});
 drawWorld(ctx,w,1920,1080,{...CAMERA,yaw});
 assert.equal(calls[0],'save');assert.equal(calls.at(-1),'restore');assert(calls.includes('fillText'));assert(calls.length>500);
}
console.log('PASS 3D island states, ground-plane routes, collision clearance, terrain elevation, expiry, camera projection and all-state rendering');
