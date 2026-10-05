import assert from 'node:assert/strict';import fs from 'node:fs';
import {SceneModel,project,STATES,groundHeight} from '../wallpaper/scene-model.js';
const meta=JSON.parse(fs.readFileSync(process.env.RESORT_TEST_ASSETS?`${process.env.RESORT_TEST_ASSETS}/scene.json`:new URL(`../wallpaper/assets/${process.argv.includes('--v3')?'scene-v2':'scene'}.json`,import.meta.url)));
for(const [key,p] of Object.entries(meta.projections)){
 const actual=project(meta.targets[key],meta);assert.ok(Math.abs(actual.x-p.x)<.01);assert.ok(Math.abs(actual.y-p.y)<.01);
}
const m=new SceneModel(meta);let seq=0;
for(const state of STATES){assert.ok(m.event({state,seq:++seq}));for(let i=0;i<1000;i++)m.step(.05);assert.equal(m.path.length,0);assert.deepEqual(m.position,(meta.targets[state]||meta.targets.desk));}
m.event({state:'starting',seq:++seq});for(let i=0;i<8;i++)m.event({state:'editing',seq:++seq});assert.equal(m.stage,4);assert.equal(m.event({state:'failed',seq}),false);assert.equal(m.event({state:'bad',seq:++seq}),false);
console.log('PASS Blender camera registration, all state routes, construction cap and event deduplication');
if(meta.ground.coastPerturb){const p=project([2.8,.3,.43],meta),b=meta.construction;for(const key of ['x','y','depth'])assert.ok(Math.abs(p[key]-b[key])<.01,`Construction ${key} is from a stale camera`);assert.ok(Number.isFinite(meta.smoke.anchorY));console.log('PASS construction and smoke registration after the camera change');}

const slope=new SceneModel(meta);slope.event({state:'permission',seq:999});for(let i=0;i<50;i++){slope.step(.05);if(slope.path.length)assert.ok(Math.abs(slope.position[2]-groundHeight(...slope.position.slice(0,2),meta))<1e-9);}
if(meta.ground.coastPerturb){
 const evidence=JSON.parse(fs.readFileSync(new URL('../docs/evidence/resort/ground-v3-probes.json',import.meta.url)));
 for(const probe of evidence.probes)assert.ok(Math.abs(groundHeight(...probe.point,meta)-probe.meshZ)<.015,JSON.stringify(probe));
 console.log(`PASS ${evidence.probes.length} walk-surface samples against the actual Blender mesh`);
}
