import assert from 'node:assert/strict';
import fs from 'node:fs';
import {SceneModel,STATES,groundHeight} from '../wallpaper/scene-model.js';
const folder=process.env.RESORT_TEST_ASSETS||'wallpaper/assets';
const meta=JSON.parse(fs.readFileSync(`${folder}/scene.json`));
function inside(p,o){const [x0,y0,x1,y1]=o.bounds,c=meta.navigation.clearance;return p[0]>x0-c+1e-6&&p[0]<x1+c-1e-6&&p[1]>y0-c+1e-6&&p[1]<y1+c-1e-6;}
let samples=0,seq=0;
for(const first of STATES)for(const next of STATES){
 const m=new SceneModel(meta);
 for(const state of [first,next]){
  m.event({state,seq:++seq});
  for(let i=0;i<1600;i++){
   m.step(.05);
   if(m.path.length&&!m.transition){
    for(const obstacle of meta.navigation.obstacles)assert.ok(!inside(m.position,obstacle),`${first} → ${next}: walks inside ${obstacle.name}: ${m.position}`);
    assert.ok(Math.abs(m.position[2]-groundHeight(...m.position.slice(0,2),meta))<1e-8);
    samples++;
   }
  }
  assert.equal(m.path.length,0);assert.equal(m.transition,null);
  assert.deepEqual(m.position,meta.targets[state]||meta.targets.desk);
  assert.equal(m.seated,meta.seating.states.includes(state));
 }
}
// A new task can arrive while sitting down or standing up.
for(const time of [.05,.3,.7]){
 const m=new SceneModel(meta);m.event({state:'editing',seq:++seq});m.step(time);
 m.event({state:'permission',seq:++seq});
 for(let i=0;i<1600;i++)m.step(.05);
 assert.deepEqual(m.position,meta.targets.permission);assert.equal(m.seated,false);
}
console.log(`PASS 81 state pairs, ${samples} ground samples outside measured furniture, seat/stand and interrupted transitions`);
