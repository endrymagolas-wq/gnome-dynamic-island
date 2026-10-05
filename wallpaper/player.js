import {SceneModel,project} from './scene-model.js';
function srgb(v){return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}
const meta=await fetch('assets/scene.json').then(r=>r.json()),model=new SceneModel(meta);
const video=document.querySelector('video'),canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d'),control=document.querySelector('#controls');
const debug=new URLSearchParams(location.search).has('preview');if(debug)control.classList.add('show');
const image=src=>new Promise((resolve,reject)=>{let i=new Image();i.onload=()=>resolve(i);i.onerror=reject;i.src=src;});
const atlas=await image('assets/character.png'),depthImage=await image('assets/depth.png');
const smoke=meta.smoke?await image('assets/smoke.png'):null;
const depthCanvas=document.createElement('canvas');depthCanvas.width=meta.width;depthCanvas.height=meta.height;
const dc=depthCanvas.getContext('2d',{willReadFrequently:true});dc.drawImage(depthImage,0,0,meta.width,meta.height);
const depthPixels=dc.getImageData(0,0,meta.width,meta.height).data;
const depth=Float32Array.from({length:meta.width*meta.height},(_,i)=>srgb(depthPixels[i*4]/255)*50);
let cabanaDepth=null;
if(meta.construction?.depthAtlas){const imageDepth=await image('assets/'+meta.construction.depthAtlas),c=document.createElement('canvas');c.width=imageDepth.width;c.height=imageDepth.height;const d=c.getContext('2d',{willReadFrequently:true});d.drawImage(imageDepth,0,0);const p=d.getImageData(0,0,c.width,c.height).data;cabanaDepth={width:c.width,data:Float32Array.from({length:c.width*c.height},(_,i)=>srgb(p[i*4]/255)*meta.construction.depthScale-meta.construction.depthBias)};}
const scratch=document.createElement('canvas');scratch.width=384;scratch.height=384;const sc=scratch.getContext('2d',{willReadFrequently:true});
let paused=false,hostPause=false,observerPause=false,waterEnabled=true,quality='high',raf=0,last=0,nextDraw=0,seq=0,smokeVisiblePixels=0;
function updatePause(){const next=hostPause||observerPause||document.hidden||matchMedia('(prefers-reduced-motion: reduce)').matches;
  paused=next;if(paused){cancelAnimationFrame(raf);raf=0;video.pause();last=0;nextDraw=0;}else{if(waterEnabled&&quality!=='off')video.play().catch(()=>{});else video.pause();if(!raf)raf=requestAnimationFrame(tick);}}
function setQuality(value){quality=value;video.src=`assets/water-${value==='low'?'720':'1080'}.mp4`;video.hidden=!waterEnabled||value==='off';updatePause();}
function masked(source,rect,x,y,w,h,footDepth,footY,ppm,depthStage=null){
  x=Math.round(x);y=Math.round(y);sc.clearRect(0,0,384,384);sc.drawImage(source,...rect,0,0,w,h);
  const pixels=sc.getImageData(0,0,w,h);
  let visible=0;
  for(let j=0;j<h;j++)for(let i=0;i<w;i++){
    if(!pixels.data[(j*w+i)*4+3])continue;
    const xx=x+i,yy=y+j;if(xx<0||xx>=meta.width||yy<0||yy>=meta.height)continue;
    const d=depth[yy*meta.width+xx];
    const spriteDepth=depthStage!==null&&cabanaDepth?footDepth+cabanaDepth.data[Math.floor(j*meta.construction.height/h)*cabanaDepth.width+depthStage*meta.construction.width+Math.floor(i*meta.construction.width/w)]:footDepth-(footY-yy)*meta.camera.matrixWorld[2][2]/(ppm*meta.camera.matrixWorld[2][1]);
    if(d>0&&d<spriteDepth-.18)pixels.data[(j*w+i)*4+3]=0;else visible++;
  }
  sc.putImageData(pixels,0,0);ctx.drawImage(scratch,0,0,w,h,x,y,w,h);return visible;
}
function draw(){
  ctx.clearRect(0,0,meta.width,meta.height);
  smokeVisiblePixels=0;
  const p=project(model.position,meta),a=meta.character;
  if(!a)return;
  const moving=model.path.length>0,dir=((Math.round(model.heading/Math.PI*4)%8)+8)%8;
  const row=moving?dir:8+Math.max(0,a.poses.indexOf(model.state));
  const frame=Math.floor(model.time*(!moving&&['idle','done'].includes(model.state)?a.fps/4:a.fps))%a.frames;
  const w=Math.max(1,Math.round(a.width*p.ppm/a.ppm)),h=Math.max(1,Math.round(a.height*p.ppm/a.ppm));
  const x=Math.round(p.x-w*a.anchorX/a.width),y=Math.round(p.y-h*a.anchorY/a.height);
  // Draw the growing cabana before the actor; both obey the static depth matte.
  if(model.stage&&meta.construction){const b=meta.construction,ppm=meta.width*meta.camera.lens/meta.camera.sensor/b.depth,scale=ppm/b.ppm;masked(atlas,[model.stage*b.width,b.atlasY,b.width,b.height],b.x-b.anchorX*scale,b.y-b.anchorY*scale,Math.round(b.width*scale),Math.round(b.height*scale),b.depth,b.y,ppm,model.stage);}
  ctx.save();ctx.fillStyle='#514c3029';ctx.beginPath();ctx.ellipse(p.x,p.y+1,p.ppm*.22,p.ppm*.075,0,0,Math.PI*2);ctx.fill();ctx.restore();
  masked(atlas,[frame*a.width,row*a.height,a.width,a.height],x,y,w,h,p.depth,p.y,p.ppm);
  if(!moving&&model.state==='failed'){
    const b=project(meta.smoke?.worldOrigin||[2.8,.3,1.72],meta),a=meta.smoke;
    if(smoke&&a){const frame=Math.floor(model.time*a.fps)%a.frames,scale=b.ppm/a.ppm;smokeVisiblePixels=masked(smoke,[frame%a.columns*a.width,Math.floor(frame/a.columns)*a.height,a.width,a.height],b.x-(a.anchorX??a.width/2)*scale,b.y-(a.anchorY??a.height*.712)*scale,Math.round(a.width*scale),Math.round(a.height*scale),b.depth,b.y,b.ppm);}
  }
  if(!moving&&['failed','permission'].includes(model.state)){ctx.font='22px system-ui';const text=model.state==='failed'?'блять…':'Гей! Дозвіл?',width=Math.ceil(ctx.measureText(text).width)+24;ctx.fillStyle='#fff7e7';ctx.beginPath();ctx.roundRect(p.x-width/2,y-38,width,32,12);ctx.fill();ctx.fillStyle='#4d4435';ctx.fillText(text,p.x-width/2+12,y-15);}
  canvas.dataset.diagnostics=JSON.stringify({state:model.state,stage:model.stage,position:model.position,paused,waterEnabled,quality,time:model.time,moving,videoTime:video.currentTime,videoPaused:video.paused,totalVideoFrames:video.getVideoPlaybackQuality?.().totalVideoFrames,droppedVideoFrames:video.getVideoPlaybackQuality?.().droppedVideoFrames});
}
function tick(t){raf=0;if(paused)return;if(nextDraw&&t+.1<nextDraw){raf=requestAnimationFrame(tick);return;}if(!nextDraw||t-nextDraw>1000/30)nextDraw=t;nextDraw+=1000/30;const dt=last?(t-last)/1000:0;last=t;model.step(dt);draw();if(model.path.length||['editing','permission','failed','testing','browsing','working','starting','done'].includes(model.state))raf=requestAnimationFrame(tick);else last=0;}
window.livelyWallpaperPlaybackChanged=data=>{try{hostPause=JSON.parse(data).IsPaused;updatePause();}catch{}};
window.livelyPropertyListener=(name,value)=>{if(name==='water'){waterEnabled=!!value;video.hidden=!waterEnabled||quality==='off';updatePause();if(!waterEnabled)video.pause();}if(name==='quality')setQuality(value===1?'low':value===2?'off':'high');};
document.addEventListener('visibilitychange',updatePause);matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change',updatePause);
document.querySelector('#waterToggle').onchange=e=>window.livelyPropertyListener('water',e.target.checked);
document.querySelector('#quality').onchange=e=>setQuality(e.target.value);
document.querySelector('#send').onclick=()=>{model.event({state:document.querySelector('#event').value,seq:++seq});draw();};
async function poll(){try{const e=await fetch('/events').then(r=>r.json());if(!debug)model.event(e);observerPause=!debug&&e.paused;updatePause();}catch{}setTimeout(poll,1000);}
setQuality('high');poll();
// Public diagnostics contain scene state only, never application text.
window.resortDiagnostics=()=>({state:model.state,stage:model.stage,position:[...model.position],paused,waterEnabled,quality,videoFrames:video.getVideoPlaybackQuality?.(),time:model.time});

// Opt-in native benchmark telemetry: media counters only, local and ephemeral.
if(new URLSearchParams(location.search).has('metrics')){
 const started=performance.now();setInterval(()=>{const q=video.getVideoPlaybackQuality();fetch('/bench-metrics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({format:waterEnabled&&quality!=='off'?'video':'still',clock:(performance.now()-started)/1000,totalVideoFrames:q.totalVideoFrames,droppedVideoFrames:q.droppedVideoFrames,paused,videoPaused:video.paused,videoWidth:video.videoWidth,videoHeight:video.videoHeight,state:model.state,stage:model.stage,position:model.position,smokeVisiblePixels})}).catch(()=>{});},1000);
}
