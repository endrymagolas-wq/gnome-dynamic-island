import {SceneModel,Companion,project} from './scene-model.js';
import {ResortLife} from './resort-life.js';
import {createLighting} from './lighting-runtime.js';
function srgb(v){return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}
const params=new URLSearchParams(location.search),debug=params.has('preview');
const stage=debug&&['v4','v6','v7'].includes(params.get('assets'))?params.get('assets'):null;
const assets=stage?`assets/${stage}-stage/`:'assets/';
document.querySelector('#poster').src=assets+'poster.png';
document.querySelector('#land').src=assets+'static.png';
document.querySelector('video').poster=assets+'poster.png';
const meta=await fetch(assets+'scene.json').then(r=>r.json());let model=new SceneModel(meta);
// Pip follows Claude; two tinted companions on the same rig follow Codex and the other apps.
const actors=[{key:'claude',name:'Claude',filter:'none',scale:1,color:'#22a99c',model,shownAt:-9},
  {key:'codex',name:'Codex',filter:'hue-rotate(95deg) saturate(1.15)',scale:.86,color:'#8a63ee',model:new Companion(meta,'codex'),shownAt:-9},
  {key:'apps',name:'Програми',filter:'hue-rotate(205deg) saturate(1.3) brightness(1.04)',scale:.8,color:'#ef7f63',model:new Companion(meta,'apps'),shownAt:-9}];
const life=meta.activities&&meta.character.life?new ResortLife(meta,actors.map(({key,scale})=>({key,scale}))):null;
if(life){for(const actor of actors)actor.model=life.actor(actor.key);model=actors[0].model;}
let drawFilter='none';
let video=document.querySelector('video');
const canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d'),control=document.querySelector('#controls');
if(debug)control.classList.add('show');
if(debug&&life){document.querySelector('#life-controls').hidden=false;document.querySelector('#visit').onclick=()=>{const key=document.querySelector('#actor').value,m=life.actor(key);life.event(key,{state:'idle',seq:++seq});m.goal=document.querySelector('#activity').value;life.respond(m);draw();updatePause();};}
if(debug&&stage)video.addEventListener('loadedmetadata',()=>{
  document.querySelector('#quality option[value="high"]').textContent=`Пробна вода ${video.videoWidth} × ${video.videoHeight} / 30 fps`;
});
const image=src=>new Promise((resolve,reject)=>{let i=new Image();i.onload=()=>resolve(i);i.onerror=reject;i.src=src;});
let atlas=await image(assets+'character.png'),smoke=meta.smoke?await image(assets+'smoke.png'):null;
const depthImage=await image(assets+'depth.png');
let ambient=meta.character?.ambient?await image(assets+meta.character.ambient.atlas):null;
let lifeAtlas=meta.character?.life?await image(assets+meta.character.life.atlas):null,blendLife=null,lifeDepth=null;
if(meta.character?.life?.depthAtlas){const d=await image(assets+meta.character.life.depthAtlas),c=document.createElement('canvas');c.width=d.width;c.height=d.height;const dc=c.getContext('2d',{willReadFrequently:true});dc.drawImage(d,0,0);const p=dc.getImageData(0,0,c.width,c.height).data;lifeDepth={width:c.width,data:Float32Array.from({length:c.width*c.height},(_,i)=>srgb(p[i*4]/255)*meta.character.life.depthScale-meta.character.life.depthBias)};}
let blendAtlas=null,blendSmoke=null,blendAmbient=null,lightingMix=0,lightingInfo=null,lightingRuntime=null;
let actorDepth=null;
if(meta.character?.depthAtlas){const d=await image(assets+meta.character.depthAtlas),c=document.createElement('canvas');c.width=d.width;c.height=d.height;const dc=c.getContext('2d',{willReadFrequently:true});dc.drawImage(d,0,0);const p=dc.getImageData(0,0,c.width,c.height).data;actorDepth={width:c.width,data:Float32Array.from({length:c.width*c.height},(_,i)=>srgb(p[i*4]/255)*meta.character.depthScale-meta.character.depthBias)};}
let ambientDepth=null;
if(meta.character?.ambient?.depthAtlas){const d=await image(assets+meta.character.ambient.depthAtlas),c=document.createElement('canvas');c.width=d.width;c.height=d.height;const dc=c.getContext('2d',{willReadFrequently:true});dc.drawImage(d,0,0);const p=dc.getImageData(0,0,c.width,c.height).data;ambientDepth={width:c.width,data:Float32Array.from({length:c.width*c.height},(_,i)=>srgb(p[i*4]/255)*meta.character.depthScale-meta.character.depthBias)};}
const depthCanvas=document.createElement('canvas');depthCanvas.width=meta.width;depthCanvas.height=meta.height;
const dc=depthCanvas.getContext('2d',{willReadFrequently:true});dc.drawImage(depthImage,0,0,meta.width,meta.height);
const depthPixels=dc.getImageData(0,0,meta.width,meta.height).data;
const depth=Float32Array.from({length:meta.width*meta.height},(_,i)=>srgb(depthPixels[i*4]/255)*50);
let cabanaDepth=null;
if(meta.construction?.depthAtlas){const imageDepth=await image(assets+meta.construction.depthAtlas),c=document.createElement('canvas');c.width=imageDepth.width;c.height=imageDepth.height;const d=c.getContext('2d',{willReadFrequently:true});d.drawImage(imageDepth,0,0);const p=d.getImageData(0,0,c.width,c.height).data;cabanaDepth={width:c.width,data:Float32Array.from({length:c.width*c.height},(_,i)=>srgb(p[i*4]/255)*meta.construction.depthScale-meta.construction.depthBias)};}
const scratch=document.createElement('canvas');scratch.width=384;scratch.height=384;const sc=scratch.getContext('2d',{willReadFrequently:true});
let paused=false,hostPause=false,observerPause=false,waterEnabled=true,quality='high',raf=0,last=0,nextDraw=0,seq=0,smokeVisiblePixels=0;
function updatePause(){const next=hostPause||observerPause||document.hidden||matchMedia('(prefers-reduced-motion: reduce)').matches;
  paused=next;if(paused){cancelAnimationFrame(raf);raf=0;video.pause();last=0;nextDraw=0;}else{if(waterEnabled&&quality!=='off')video.play().catch(()=>{});else video.pause();if(!raf)raf=requestAnimationFrame(tick);}lightingRuntime?.updatePlayback();}
function setQuality(value){quality=value;if(lightingRuntime)lightingRuntime.setQuality(value);else video.src=`${assets}water-${value==='low'?'720':'1080'}.mp4`;video.hidden=!waterEnabled||value==='off';updatePause();}
function masked(source,rect,x,y,w,h,footDepth,footY,ppm,depthStage=null,useActorDepth=false,bodyScale=1){
  x=Math.round(x);y=Math.round(y);if(w>scratch.width)scratch.width=w;if(h>scratch.height)scratch.height=h;sc.clearRect(0,0,scratch.width,scratch.height);
  const alt=source===atlas?blendAtlas:source===smoke?blendSmoke:source===ambient?blendAmbient:source===lifeAtlas?blendLife:null;
  const animationDepth=source===ambient?ambientDepth:source===lifeAtlas?lifeDepth:actorDepth;
  sc.filter=drawFilter;
  if(alt&&lightingMix){sc.globalAlpha=1-lightingMix;sc.drawImage(source,...rect,0,0,w,h);sc.globalCompositeOperation='lighter';sc.globalAlpha=lightingMix;sc.drawImage(alt,...rect,0,0,w,h);sc.globalAlpha=1;sc.globalCompositeOperation='source-over';}
  else sc.drawImage(source,...rect,0,0,w,h);
  sc.filter='none';
  const pixels=sc.getImageData(0,0,w,h);
  let visible=0;
  for(let j=0;j<h;j++)for(let i=0;i<w;i++){
    if(!pixels.data[(j*w+i)*4+3])continue;
    const xx=x+i,yy=y+j;if(xx<0||xx>=meta.width||yy<0||yy>=meta.height)continue;
    const d=depth[yy*meta.width+xx];
    const spriteDepth=useActorDepth&&animationDepth?footDepth+bodyScale*animationDepth.data[(rect[1]+Math.floor(j*rect[3]/h))*animationDepth.width+rect[0]+Math.floor(i*rect[2]/w)]:depthStage!==null&&cabanaDepth?footDepth+cabanaDepth.data[Math.floor(j*meta.construction.height/h)*cabanaDepth.width+depthStage*meta.construction.width+Math.floor(i*meta.construction.width/w)]:footDepth-(footY-yy)*meta.camera.matrixWorld[2][2]/(ppm*meta.camera.matrixWorld[2][1]);
    if(d>0&&d<spriteDepth-.18)pixels.data[(j*w+i)*4+3]=0;else visible++;
  }
  sc.putImageData(pixels,0,0);ctx.drawImage(scratch,0,0,w,h,x,y,w,h);return visible;
}
function draw(){
  if(lightingRuntime){lightingMix=lightingRuntime.sample();if(lightingInfo)lightingInfo.mix=lightingMix;}
  ctx.clearRect(0,0,meta.width,meta.height);
  smokeVisiblePixels=0;
  const a=meta.character;
  if(!a)return;
  // Draw the growing cabana before the actors; it and every actor obey the static depth matte.
  if(model.stage&&meta.construction&&meta.effects?.construction!==false){drawFilter='none';const b=meta.construction,ppm=meta.width*meta.camera.lens/meta.camera.sensor/b.depth,scale=ppm/b.ppm;masked(atlas,[model.stage*b.width,b.atlasY,b.width,b.height],b.x-b.anchorX*scale,b.y-b.anchorY*scale,Math.round(b.width*scale),Math.round(b.height*scale),b.depth,b.y,ppm,model.stage);}
  let diagnostics=null;
  for(const {actor,p} of actors.map(actor=>({actor,p:project(actor.model.position,meta)})).sort((l,r)=>r.p.depth-l.p.depth)){
    const d=drawActor(actor,p,a);actor.diagnostics=d;if(actor.model===model)diagnostics=d;
  }
  canvas.dataset.diagnostics=JSON.stringify(diagnostics);
  canvas.dataset.sceneVersion=String(meta.version||6);
  canvas.dataset.actors=JSON.stringify(actors.map(({key,model:m,diagnostics:d})=>({key,state:m.state,position:[...m.position],activity:m.activity,activityTime:m.activityTime,clip:m.activityClip,visiblePixels:d?.actorVisiblePixels,moving:!!m.path.length,transition:m.transition?.kind||null,routeError:m.routeError||null})));
}
function bubble(text,cx,top,fill,ink){ctx.font='22px system-ui';const width=Math.ceil(ctx.measureText(text).width)+24;ctx.fillStyle=fill;ctx.beginPath();ctx.roundRect(cx-width/2,top,width,32,12);ctx.fill();ctx.fillStyle=ink;ctx.fillText(text,cx-width/2+12,top+23);}
function drawActor(actor,p,a){
  const m=actor.model,isPip=m===model;
  if(life&&lifeAtlas&&m.activityClip&&!(m.transition&&['sit','stand'].includes(m.transition.kind))&&meta.character.life.clips.includes(m.activityClip))return drawLifeActor(actor,p);
  const moving=m.path.length>0,dir=((Math.round(m.heading/Math.PI*4)%8)+8)%8;
  const row=m.transition?8+a.poses.length+a.transitions.indexOf(m.transition.kind):moving?dir:8+Math.max(0,a.poses.indexOf(m.pose||m.state));
  const frame=m.transition?Math.min(a.frames-1,Math.floor(m.transition.elapsed/(m.transition.seconds||meta.seating.seconds)*(a.frames-1))):Math.floor(m.time*(!moving&&['idle','done'].includes(m.state)?a.fps/4:a.fps))%a.frames;
  const w=Math.max(1,Math.round(a.width*p.ppm/a.ppm*actor.scale)),h=Math.max(1,Math.round(a.height*p.ppm/a.ppm*actor.scale));
  const x=Math.round(p.x-w*a.anchorX/a.width),y=Math.round(p.y-h*a.anchorY/a.height);
  if(!m.seated&&!m.transition){ctx.save();ctx.fillStyle='#514c3029';ctx.beginPath();ctx.ellipse(p.x,p.y+1,p.ppm*.22*actor.scale,p.ppm*.075*actor.scale,0,0,Math.PI*2);ctx.fill();ctx.restore();}
  let actorImage=atlas,actorRect=[frame*a.width,row*a.height,a.width,a.height],ambientState=null;
  if(isPip&&ambient&&m.seated&&!m.transition&&['idle','done'].includes(m.state)){
    const b=a.ambient,t=(m.time-(m.seatedSince||0))%b.cycleSeconds;
    ambientState=t>=12&&t<18?'nod':t>=30&&t<36?'yawn':'drink';
    const f=Math.floor((ambientState==='nod'?t-12:ambientState==='yawn'?t-30:t%6)*b.fps)%b.frames;
    actorImage=ambient;actorRect=[f%b.columns*a.width,(b.clips.indexOf(ambientState)*b.rowsPerClip+Math.floor(f/b.columns))*a.height,a.width,a.height];
  }
  drawFilter=actor.filter;
  const actorVisiblePixels=masked(actorImage,actorRect,x,y,w,h,p.depth,p.y,p.ppm,null,true,actor.scale);
  drawFilter='none';
  if(isPip&&!moving&&!m.transition&&m.state==='failed'&&meta.effects?.smoke!==false){
    const b=project(meta.smoke?.worldOrigin||[2.8,.3,1.72],meta),s=meta.smoke;
    if(smoke&&s){const frame=Math.floor(m.time*s.fps)%s.frames,scale=b.ppm/s.ppm;smokeVisiblePixels=masked(smoke,[frame%s.columns*s.width,Math.floor(frame/s.columns)*s.height,s.width,s.height],b.x-(s.anchorX??s.width/2)*scale,b.y-(s.anchorY??s.height*.712)*scale,Math.round(s.width*scale),Math.round(s.height*scale),b.depth,b.y,b.ppm);}
  }
  if(!moving&&!m.transition&&['failed','permission'].includes(m.state))bubble(m.state==='failed'?'блять…':'Гей! Дозвіл?',p.x,y-38,'#fff7e7','#4d4435');
  else if(m.time-actor.shownAt<3.5){ctx.save();ctx.globalAlpha=Math.min(1,(3.5-(m.time-actor.shownAt))/.6);ctx.font='600 17px system-ui';const label=actor.name,width=Math.ceil(ctx.measureText(label).width)+20;ctx.fillStyle=actor.color;ctx.beginPath();ctx.roundRect(p.x-width/2,y-30,width,26,13);ctx.fill();ctx.fillStyle='#fff';ctx.fillText(label,p.x-width/2+10,y-12);ctx.restore();}
  return {state:m.state,stage:m.stage,position:m.position,seated:m.seated,transition:m.transition,ambient:ambientState,actorRect,restTime:(m.time-(m.seatedSince||0))%(a.ambient?.cycleSeconds||42),actorVisiblePixels,lighting:lightingInfo,paused,waterEnabled,quality,time:m.time,moving,videoTime:video.currentTime,videoPaused:video.paused,totalVideoFrames:video.getVideoPlaybackQuality?.().totalVideoFrames,droppedVideoFrames:video.getVideoPlaybackQuality?.().droppedVideoFrames};
}
function drawLifeActor(actor,p){
  const m=actor.model,b=meta.character.life,name=m.transition?.kind==='lie'?'recline':m.activityClip,clip=b.clips.indexOf(name),count=b.frameCounts?.[name]||b.frames;
  const t=m.transition?Math.min(1,m.transition.elapsed/m.transition.seconds):m.activityTime;
  const frame=m.transition?Math.min(count-1,Math.floor(t*(count-1))):Math.floor(t*b.fps)%count;
  const rect=[frame%b.columns*b.width,(clip*b.rowsPerClip+Math.floor(frame/b.columns))*b.height,b.width,b.height];
  const w=Math.max(1,Math.round(b.width*p.ppm/b.ppm*actor.scale)),h=Math.max(1,Math.round(b.height*p.ppm/b.ppm*actor.scale));
  const x=Math.round(p.x-w*b.anchorX/b.width),y=Math.round(p.y-h*b.anchorY/b.height);
  drawFilter=actor.filter;const visible=masked(lifeAtlas,rect,x,y,w,h,p.depth,p.y,p.ppm,null,true,actor.scale);drawFilter='none';
  return {key:actor.key,state:m.state,activity:m.activity,clip:m.activityClip,activityTime:m.activityTime,position:[...m.position],seated:m.seated,transition:m.transition,actorRect:[x,y,w,h],actorVisiblePixels:visible,time:m.time,paused,lighting:lightingInfo,waterEnabled,quality,videoTime:video.currentTime,videoPaused:video.paused,totalVideoFrames:video.getVideoPlaybackQuality?.().totalVideoFrames};
}
function tick(t){raf=0;if(paused)return;if(nextDraw&&t+.1<nextDraw){raf=requestAnimationFrame(tick);return;}if(!nextDraw||t-nextDraw>1000/30)nextDraw=t;nextDraw+=1000/30;const dt=last?(t-last)/1000:0;last=t;if(life)life.step(dt);else for(const actor of actors)actor.model.step(dt);draw();if(life||(ambient&&model.seated)||actors.some(({model:m,shownAt})=>m.path.length||m.transition||m.time-shownAt<3.5||['editing','permission','failed','testing','browsing','working','starting','done'].includes(m.state)))raf=requestAnimationFrame(tick);else last=0;}
window.livelyWallpaperPlaybackChanged=data=>{try{hostPause=JSON.parse(data).IsPaused;updatePause();}catch{}};
window.livelyPropertyListener=(name,value)=>{if(name==='water'){waterEnabled=!!value;video.hidden=!waterEnabled||quality==='off';updatePause();if(!waterEnabled)video.pause();}if(name==='quality')setQuality(value===1?'low':value===2?'off':'high');if(name==='timeOfDay')lightingRuntime?.setMode(['auto','morning','day','evening','night'][Number(value)]||'auto');};
document.addEventListener('visibilitychange',updatePause);matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change',updatePause);
document.querySelector('#waterToggle').onchange=e=>window.livelyPropertyListener('water',e.target.checked);
document.querySelector('#quality').onchange=e=>setQuality(e.target.value);
document.querySelector('#timeOfDay').onchange=e=>lightingRuntime?.setMode(e.target.value);
document.querySelector('#send').onclick=()=>{const key=document.querySelector('#actor')?.value||'claude',e={state:document.querySelector('#event').value,seq:++seq};if(life)life.event(key,e);else actors.find(a=>a.key===key).model.event(e);draw();updatePause();};
async function poll(){try{const e=await fetch('/events').then(r=>r.json());if(!debug){const channels=e.actors||{claude:e};for(const actor of actors){const ev=channels[actor.key];if(ev&&(life?life.event(actor.key,ev):actor.model.event(ev)))actor.shownAt=actor.model.time;}}observerPause=!debug&&!params.has('live')&&e.paused;/* ?live=1: real events in a normal browser tab, ignoring desktop coverage */updatePause();}catch{}setTimeout(poll,1000);}
setQuality('high');poll();
if(meta.lighting){
 const clock=()=>{const date=new Date();if(debug&&params.has('lightingMinute'))date.setHours(0,Number(params.get('lightingMinute')),0,0);return date;};
 lightingRuntime=createLighting({settings:meta.lighting,assets,image,atlas,smoke,ambient,life:lifeAtlas,clock,playback:()=>({paused,waterEnabled}),onChange(data){atlas=data.atlas;smoke=data.smoke;ambient=data.ambient;lifeAtlas=data.life;video=data.video;blendAtlas=data.blendAtlas;blendSmoke=data.blendSmoke;blendAmbient=data.blendAmbient;blendLife=data.blendLife;lightingMix=data.mix;lightingInfo=data.lighting;updatePause();}});
 lightingRuntime.setQuality(quality);lightingRuntime.setMode(debug?document.querySelector('#timeOfDay').value:'auto');setInterval(()=>lightingRuntime.update(),1000);
}else document.querySelector('#timeOfDay').hidden=true;
// Public diagnostics contain scene state only, never application text.
window.resortDiagnostics=()=>({version:meta.version||6,state:model.state,stage:model.stage,position:[...model.position],paused,waterEnabled,quality,videoFrames:video.getVideoPlaybackQuality?.(),time:model.time,actors:actors.map(({key,model:m,diagnostics})=>({key,state:m.state,position:[...m.position],activity:m.activity,activityTime:m.activityTime,seated:m.seated,transition:m.transition,path:m.path,diagnostics}))});

// Opt-in native benchmark telemetry: media counters only, local and ephemeral.
if(new URLSearchParams(location.search).has('metrics')){
 const started=performance.now();setInterval(()=>{const q=video.getVideoPlaybackQuality(),d=JSON.parse(canvas.dataset.diagnostics||'{}');fetch('/bench-metrics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({format:waterEnabled&&quality!=='off'?'video':'still',clock:(performance.now()-started)/1000,totalVideoFrames:q.totalVideoFrames,droppedVideoFrames:q.droppedVideoFrames,paused,videoPaused:video.paused,videoWidth:video.videoWidth,videoHeight:video.videoHeight,state:model.state,stage:model.stage,position:model.position,seated:model.seated,transition:model.transition,ambient:d.ambient,actorRect:d.actorRect,restTime:d.restTime,actorVisiblePixels:d.actorVisiblePixels,lighting:lightingInfo,smokeVisiblePixels,...(life?{actors:actors.map(({key,model:m})=>({key,state:m.state,position:[...m.position],activity:m.activity}))}:{})})}).catch(()=>{});},1000);
}
