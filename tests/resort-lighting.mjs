import assert from 'node:assert/strict';import {lightingAt} from '../wallpaper/lighting-model.js';
const settings={phases:{morning:'m',day:'d',evening:'e',night:'n'},schedule:[{phase:'morning',minute:360},{phase:'day',minute:540},{phase:'evening',minute:1080},{phase:'night',minute:1260}],fadeSeconds:120};
const at=(h,m=0,s=0)=>new Date(2026,9,5,h,m,s);
for(const [h,name] of [[0,'night'],[5,'night'],[7,'morning'],[10,'day'],[19,'evening'],[23,'night']])assert.equal(lightingAt(at(h),settings).a,name);
for(const [h,prev,next] of [[6,'night','morning'],[9,'morning','day'],[18,'day','evening'],[21,'evening','night']]){
 assert.deepEqual(lightingAt(at(h),settings),{a:prev,b:next,mix:0});
 assert.deepEqual(lightingAt(at(h,1),settings),{a:prev,b:next,mix:.5});
 assert.deepEqual(lightingAt(at(h,2),settings),{a:next,b:null,mix:0});
}
assert.equal(lightingAt(at(1),settings,'day').a,'day');assert.equal(lightingAt(at(12),null).a,'day');
console.log('PASS local clock, midnight, four phase boundaries, two-minute fades and fixed override');
