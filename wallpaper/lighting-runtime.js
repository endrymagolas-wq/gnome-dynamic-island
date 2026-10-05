import {lightingAt} from './lighting-model.js';
// Only the two-minute transition needs two decoders. The inactive slot is
// unloaded after promotion; neither Blender nor a 3D renderer runs here.
export function createLighting({settings,assets,image,atlas,smoke,ambient,clock,onChange,playback}){
 const stage=document.querySelector('#stage'),actor=document.querySelector('canvas');
 function group(poster,video,land){const box=document.createElement('div');box.style.cssText='position:absolute;inset:0';for(const e of [poster,video,land])box.append(e);stage.insertBefore(box,actor);return {box,poster,video,land,phase:null};}
 let active=group(document.querySelector('#poster'),document.querySelector('#water'),document.querySelector('#land'));
 const v=document.createElement('video');v.muted=true;v.loop=true;v.playsInline=true;v.preload='auto';
 let other=group(document.createElement('img'),v,document.createElement('img'));other.box.style.display='none';
 const cache=new Map([['day',Promise.resolve({atlas,smoke,ambient})]]);
 active.phase='day';active.data={atlas,smoke,ambient};let mode='auto',mix=0,revision=0,quality='high',busy=false,lastInfo=null;
 function base(phase){return assets+settings.phases[phase];}
 async function data(phase){if(!cache.has(phase))cache.set(phase,Promise.all([image(base(phase)+'character.png'),smoke?image(base(phase)+'smoke.png'):null,ambient?image(base(phase)+'ambient.png'):null]).then(([atlas,smoke,ambient])=>({atlas,smoke,ambient})));return cache.get(phase);}
 function settle(slot,error){for(const pending of slot.pending||[])error?pending.reject(error):pending.resolve();slot.pending=[];}
 function stop(slot){settle(slot);slot.video.onloadedmetadata=null;slot.video.onerror=null;slot.video.pause();slot.video.removeAttribute('src');slot.video.load();slot.box.style.display='none';slot.phase=null;slot.data=null;}
 function media(slot,syncTime){
  slot.video.hidden=!playback().waterEnabled||quality==='off';
  if(quality==='off'){slot.video.pause();return Promise.resolve();}
  const src=base(slot.phase)+`water-${quality==='low'?'720':'1080'}.mp4`;
  if(slot.video.getAttribute('src')!==src){
   return new Promise((resolve,reject)=>{
    (slot.pending||=[]).push({resolve,reject});
    slot.video.onerror=()=>settle(slot,Error('Lighting video could not be decoded'));
    slot.video.onloadedmetadata=()=>{slot.video.currentTime=(slot===active?syncTime:active.video.currentTime)%12;updatePlayback();settle(slot);};slot.video.src=src;
   });
  }
  if(slot.pending?.length)return new Promise((resolve,reject)=>slot.pending.push({resolve,reject}));
  return Promise.resolve();
 }
 async function assign(slot,phase,syncTime){
  const d=await data(phase);slot.phase=phase;slot.data=d;slot.poster.src=base(phase)+'poster.png';slot.land.src=base(phase)+'static.png';slot.video.poster=slot.poster.src;slot.box.style.display='block';await media(slot,syncTime);
 }
 function drift(){const d=Math.abs(active.video.currentTime-other.video.currentTime)%12;return Math.min(d,12-d);}
 function notify(){lastInfo={mode,a:active.phase,b:other.phase,mix,decoderCount:[active,other].filter(s=>s.phase&&!s.video.paused).length,clockDelta:other.phase?drift():0};onChange({atlas:active.data.atlas,smoke:active.data.smoke,ambient:active.data.ambient,video:active.video,blendAtlas:other.phase?other.data.atlas:null,blendSmoke:other.phase?other.data.smoke:null,blendAmbient:other.phase?other.data.ambient:null,mix,lighting:lastInfo});}
 function updatePlayback(){
  const p=playback();for(const slot of [active,other])if(slot.phase){slot.video.hidden=!p.waterEnabled||quality==='off';if(p.paused||!p.waterEnabled||quality==='off')slot.video.pause();else slot.video.play().catch(()=>{});}
  if(lastInfo)lastInfo.decoderCount=[active,other].filter(s=>s.phase&&!s.video.paused).length;
 }
 async function update(){
  if(busy||playback().paused)return;busy=true;const token=revision,want=lightingAt(clock(),settings,mode),time=active.video.currentTime||0;
  try{
   if(!want.b&&other.phase===want.a){stop(active);[active,other]=[other,active];mix=0;}
   if(active.phase!==want.a){const d=await data(want.a);if(token!==revision)return;stop(other);await assign(active,want.a,time);}
   if(want.b&&other.phase!==want.b){await data(want.b);if(token!==revision)return;await assign(other,want.b,time);}
   if(!want.b&&other.phase)stop(other);
   if(want.b&&other.video.readyState>=1&&drift()>.08)other.video.currentTime=active.video.currentTime;
   mix=want.b?want.mix:0;active.box.style.zIndex='0';active.box.style.opacity='1';other.box.style.zIndex='1';other.box.style.opacity=String(mix);actor.style.zIndex='2';
   for(const phase of cache.keys())if(phase!==active.phase&&phase!==other.phase)cache.delete(phase);
   updatePlayback();notify();
  }catch(error){document.querySelector('#status').textContent='Не вдалося завантажити освітлення';console.error(error);}
  finally{busy=false;}
 }
 function sample(){const want=lightingAt(clock(),settings,mode);if(want.a===active.phase&&want.b===other.phase){mix=want.b?want.mix:0;other.box.style.opacity=String(mix);}if(lastInfo){lastInfo.decoderCount=[active,other].filter(s=>s.phase&&!s.video.paused).length;lastInfo.clockDelta=other.phase?drift():0;}return mix;}
 return {update,updatePlayback,sample,setMode(value){mode=value;revision++;update();},setQuality(value){quality=value;for(const slot of [active,other])if(slot.phase)media(slot,slot.video.currentTime||0).catch(console.error);updatePlayback();notify();}};
}
