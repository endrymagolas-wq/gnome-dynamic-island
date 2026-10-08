import assert from 'node:assert/strict';
import {createLighting} from '../wallpaper/lighting-runtime.js';
let automaticMetadata=true;
class Element {
  constructor(tag){this.tag=tag;this.style={};this.paused=true;this.currentTime=3;this.readyState=1;this.attrs={};this.children=[];}
  append(e){this.children.push(e);}
  insertBefore(e){this.children.push(e);}
  set src(v){this.attrs.src=v;if(this.tag==='video'&&automaticMetadata)queueMicrotask(()=>this.onloadedmetadata?.());}
  get src(){return this.attrs.src;}
  getAttribute(k){return this.attrs[k];}
  removeAttribute(k){delete this.attrs[k];}
  load(){this.loads=(this.loads||0)+1;}
  play(){this.paused=false;return Promise.resolve();}
  pause(){this.paused=true;}
}
const elements={'#stage':new Element('div'),'canvas':new Element('canvas'),'#poster':new Element('img'),'#water':new Element('video'),'#land':new Element('img'),'#status':new Element('div')};
globalThis.document={querySelector:key=>elements[key],createElement:tag=>new Element(tag)};
const settings={phases:{day:'',morning:'phases/morning/',evening:'phases/evening/',night:'phases/night/'},schedule:[{phase:'morning',minute:360},{phase:'day',minute:540},{phase:'evening',minute:1080},{phase:'night',minute:1260}],fadeSeconds:120};
let date=new Date(2026,9,5,9,1),paused=false,waterEnabled=true,current;
const runtime=createLighting({settings,assets:'assets/',image:async src=>({src}),atlas:{src:'day'},smoke:{},ambient:{},clock:()=>date,onChange:data=>{current=data;},playback:()=>({paused,waterEnabled})});
await runtime.update();
assert.equal(current.lighting.a,'morning');assert.equal(current.lighting.b,'day');
assert.equal(current.lighting.mix,.5);assert.equal(current.lighting.decoderCount,2);
paused=true;runtime.updatePlayback();assert.equal(current.lighting.decoderCount,0);
const oldA=current.video;date=new Date(2026,9,5,22);await runtime.update();
assert.equal(current.video,oldA,'Paused clock change must not load another phase');
paused=false;date=new Date(2026,9,5,9,2);await runtime.update();
assert.equal(current.lighting.a,'day');assert.equal(current.lighting.b,null);assert.equal(current.lighting.decoderCount,1);
assert.equal(oldA.getAttribute('src'),undefined,'Finished fade must unload the retired decoder');
runtime.setQuality('off');assert.equal(current.lighting.decoderCount,0);
runtime.setQuality('low');await new Promise(resolve=>setImmediate(resolve));
assert.match(current.video.src,/water-720\.mp4$/);assert.equal(current.lighting.decoderCount,1);
waterEnabled=false;runtime.updatePlayback();assert.equal(current.lighting.decoderCount,0);
waterEnabled=true;runtime.updatePlayback();runtime.setMode('night');await new Promise(resolve=>setImmediate(resolve));
assert.equal(current.lighting.a,'night');assert.equal(current.lighting.b,null);assert.equal(current.lighting.decoderCount,1);
automaticMetadata=false;
runtime.setMode('day');await new Promise(resolve=>setImmediate(resolve));
runtime.setQuality('high');current.video.onloadedmetadata();
await new Promise(resolve=>setImmediate(resolve));
assert.equal(current.lighting.a,'day','Changing quality during phase load must release the pending phase update');
automaticMetadata=true;runtime.setMode('evening');await new Promise(resolve=>setImmediate(resolve));
assert.equal(current.lighting.a,'evening','Controller must remain usable after the loading race');
console.log('PASS lighting media lifecycle: aligned fade, pause, deferred clock changes, decoder unload, quality and water controls');
