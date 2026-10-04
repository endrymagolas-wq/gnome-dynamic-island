import assert from 'node:assert/strict';
import {IslandWorld,applicationState,drawWorld} from '../extensions/cartoon-island@avalon.local/world.js';
const w=new IslandWorld();
assert.equal(w.present('invalid',0),false);
assert.equal(w.present('editing',NaN),false);
w.present('starting',0);assert.equal(w.x,350);assert.equal(w.floors,0);
w.present('editing',1);assert.equal(w.floors,1);
for(let i=0;i<10;i++)w.present('editing',2+i);
assert.equal(w.floors,4);
w.present('permission',20);w.step(21,.1);assert(w.x>350&&w.x<760);
w.step(22,1,false);assert.equal(w.x,760);
w.step(201,.1);assert.equal(w.source,'desktop');assert.equal(w.state,'idle');
w.present('done',210);w.step(231,.1);assert.equal(w.state,'idle');
assert.equal(applicationState('org.mozilla.firefox.desktop'),'browsing');
assert.equal(applicationState('com.visualstudio.code.desktop'),'working');
assert.equal(applicationState('org.gnome.Terminal.desktop'),'working');
assert.equal(applicationState('org.gnome.Nautilus.desktop'),'idle');
// Every state renders using finite coordinates, including initial empty building.
for(const state of ['starting','editing','testing','failed','permission','done','working','browsing','idle']){
 w.present(state,0);w.step(1,.1);
 const calls=[];
 const ctx=new Proxy({}, {get:(_,key)=>(...args)=>{assert(args.filter(x=>typeof x==='number').every(Number.isFinite),key);calls.push(key);},set:()=>true});
 drawWorld(ctx,w,1920,1080);
 assert.equal(calls[0],'save');assert.equal(calls.at(-1),'restore');assert(calls.includes('fillText'));
}
console.log('PASS wallpaper states, floor cap, motion, expiry, application mapping and all-state rendering');
