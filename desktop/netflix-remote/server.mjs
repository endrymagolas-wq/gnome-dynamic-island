import http from 'node:http';
import {readFile,writeFile,mkdir,chmod} from 'node:fs/promises';
import {randomBytes,timingSafeEqual} from 'node:crypto';
import {homedir,networkInterfaces} from 'node:os';
import {join,dirname} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
const ROOT=dirname(fileURLToPath(import.meta.url));
const DATA=process.env.REMOTE_DATA || join(homedir(),'.local/share/netflix-remote');
const PORT=Number(process.env.REMOTE_PORT || 8765), CDP_PORT=Number(process.env.REMOTE_CDP_PORT || 9327);
const LAN=process.env.REMOTE_LAN==='1';
const BIND=LAN?'0.0.0.0':'127.0.0.1';
const DEBUG=`http://127.0.0.1:${CDP_PORT}`;
let key, browserStarting, commandQueue=Promise.resolve(), lastState=null;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
export function normalizeNetflixUrl(input){
 let text=String(input||'').trim();
 const found=text.match(/https:\/\/(?:www\.)?netflix\.com\/[^\s<>]+/i); if(found)text=found[0];
 let u;try{u=new URL(text)}catch{throw Error('Встав посилання на фільм або серіал Netflix.')}
 if(u.protocol!=='https:' || !['netflix.com','www.netflix.com'].includes(u.hostname) || u.port || u.username || u.password)throw Error('Потрібне посилання саме з netflix.com.');
 const m=u.pathname.match(/^\/(?:[a-z]{2}(?:-[A-Z]{2})?\/)?(?:title|watch)\/(\d{3,14})\/?$/);
 if(!m)throw Error('Відкрий фільм у Netflix → Поділитися → Копіювати посилання.');
 return `https://www.netflix.com/watch/${m[1]}`;
}
export function ipv4(ip){
 ip=String(ip||'').replace(/^::ffff:/,'');const parts=ip.split('.');
 if(parts.length!==4||parts.some(x=>!/^\d{1,3}$/.test(x)||Number(x)>255))return null;
 return parts.reduce((value,x)=>((value<<8)|Number(x))>>>0,0);
}
export function isPrivate(ip){const n=ipv4(ip);return n!==null&&((n>>>24)===10||(n>>>20)===0xac1||(n>>>16)===0xc0a8)}
export function isLocal(ip,interfaces=networkInterfaces(),lan=LAN){
 ip=String(ip||'').replace(/^::ffff:/,'');if(ip==='127.0.0.1'||ip==='::1')return true;
 if(!lan||!isPrivate(ip))return false;
 const n=ipv4(ip);
 return Object.values(interfaces).flat().some(x=>{
  if(x?.family!=='IPv4'||x.internal||!isPrivate(x.address))return false;
  const address=ipv4(x.address),mask=ipv4(x.netmask);
  return mask!==null&&mask!==0&&((n&mask)>>>0)===((address&mask)>>>0);
 });
}
function hosts(){return new Set(['localhost','127.0.0.1',...Object.values(networkInterfaces()).flat().filter(x=>x?.family==='IPv4'&&isLocal(x.address)).map(x=>x.address)])}
export function allowedTarget(t){try{const u=new URL(t.url);return t.type==='page'&&u.protocol==='https:'&&u.hostname==='www.netflix.com'&&!u.port&&!u.username&&!u.password}catch{return false}}
async function targets(){return await (await fetch(DEBUG+'/json/list',{signal:AbortSignal.timeout(1200)})).json()}
async function ensureBrowser(){
 try{await targets();return}catch{}
 if(browserStarting)return browserStarting;
 browserStarting=(async()=>{
  const child=spawn('/usr/bin/python3',[join(homedir(),'.local/share/island-desktop/mediactl.py'),'netflix'],{stdio:'ignore',detached:true});child.on('error',()=>{});child.unref();
  for(let i=0;i<60;i++){await sleep(200);try{await targets();return}catch{}}
  throw Error('Не вдалося відкрити Chrome. Перевір, чи виконаний вхід у робочий стіл Ubuntu.');
 })().finally(()=>browserStarting=null);return browserStarting;
}
async function target(create=false){
 if(create)await ensureBrowser();
 let all;try{all=await targets()}catch{throw Error('Натисни «Відкрити Netflix», щоб запустити вікно на ПК.')}
 let t=all.find(allowedTarget);
 if(!t&&create)t=await(await fetch(DEBUG+'/json/new?'+encodeURIComponent('https://www.netflix.com/browse'),{method:'PUT'})).json();
 if(!t||!allowedTarget(t))throw Error('Вікно Netflix закрите. Відкрий його з пульта.');return t;
}
export async function cdp(t,method,params={}){
 return new Promise((resolve,reject)=>{
  const ws=new WebSocket(t.webSocketDebuggerUrl);const timer=setTimeout(()=>{ws.close();reject(Error('Netflix довго відповідає. Спробуй ще раз.'))},7000);
  function finish(e,v){clearTimeout(timer);ws.close();e?reject(e):resolve(v)}
  ws.addEventListener('open',()=>ws.send(JSON.stringify({id:1,method,params})));
  ws.addEventListener('error',()=>finish(Error('Втрачено зв’язок із вікном Netflix.')));
  ws.addEventListener('message',e=>{const r=JSON.parse(e.data);if(r.id===1)finish(r.error?Error(r.error.message):null,r.result)});
 });
}
async function evaluate(t,expression){const r=await cdp(t,'Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw Error('Netflix ще не готовий до цієї дії.');return r.result?.value}
async function revealPlayerControls(t){
 const size=await evaluate(t,'({width:innerWidth,height:innerHeight})');
 await cdp(t,'Input.dispatchMouseEvent',{type:'mouseMoved',x:Math.round(size.width*.55),y:Math.round(size.height*.68)});
 await sleep(220);
}
const STATE_SCRIPT=`(()=>{
 const video=[...document.querySelectorAll('video')].find(v=>v.duration>0)||null;
 const profiles=[...document.querySelectorAll('.profile-link')].map((e,index)=>({index,name:e.querySelector('.profile-name')?.textContent?.trim()||''})).filter(p=>p.name);
 const titleParts=[...document.querySelector('[data-uia="video-title"]')?.children||[]].map(e=>e.textContent?.trim()).filter(Boolean);
 const label=(titleParts.length>=3?titleParts[0]+' · '+titleParts[1]+': '+titleParts.slice(2).join(' '):titleParts.join(' '))||document.title.replace(/\\s*[|–-]\\s*Netflix.*$/,'').trim();
 const panel=document.querySelector('[data-uia="selector-episode"]');
 const episodePanelOpen=!!panel&&panel.getAttribute('aria-hidden')!=='true'&&!!panel.getClientRects().length;
 const seasons=episodePanelOpen?[...panel.querySelectorAll('[data-uia^="season-pane-item-"]')].slice(0,100).map((e,index)=>({index,name:(e.getAttribute('aria-label')||e.textContent||'').trim().slice(0,80)})):[];
 const episodes=episodePanelOpen?[...panel.querySelectorAll('[data-uia="episode-pane-item"]')].slice(0,100).map((e,index)=>({index,number:e.querySelector('[data-uia="episode-pane-item-number"]')?.textContent?.trim().slice(0,8)||String(index+1),title:(e.getAttribute('aria-label')||'Серія '+(index+1)).trim().slice(0,120),current:!!e.querySelector('[data-uia="episode-pane-item-now-playing"]')})):[];
 return {open:true,title:label,needsLogin:!!document.querySelector('input[type=password]')||location.pathname.includes('/login'),profiles,hasVideo:!!video,paused:video?.paused??true,position:video?.currentTime||0,duration:Number.isFinite(video?.duration)?video.duration:0,volume:video?Math.round(video.volume*100):50,muted:video?.muted??false,fullscreen:!!document.fullscreenElement,buffering:!!video&&!video.paused&&video.readyState<3,isWatchPage:/^\\/watch\\/\\d+/.test(location.pathname),episodePanelOpen,seasons,season:episodePanelOpen?(panel.querySelector('[data-uia="selector-episode-header"]')?.textContent?.trim().slice(0,80)||''):null,episodes};})()`;
async function state(){try{const t=await target();return {...await evaluate(t,STATE_SCRIPT),connected:true}}catch(e){return {open:false,connected:true,title:'Готовий до вечора кіно',hasVideo:false,paused:true,error:e.message}}}
async function command(body){
 const action=body.action;
 if(!['open','play','pause','toggle','seek','volume','mute','fullscreen','profile','back','home','episodes','season','episode','next'].includes(action))throw Error('Невідома команда.');
 if(action==='open'||action==='home'){
  const url=action==='home'||!body.url?'https://www.netflix.com/browse':normalizeNetflixUrl(body.url);
  const t=await target(true);await cdp(t,'Page.navigate',{url});await cdp(t,'Page.bringToFront');return;
 }
 const t=await target();
 if(action==='episodes'||action==='next'){
  const onPlayer=await evaluate(t,'/^\\/watch\\/\\d+/.test(location.pathname)');
  if(!onPlayer)throw Error('Спочатку відкрий серіал у Netflix.');
  const selector=action==='episodes'?'control-episodes':'control-next';
  let ok=false,playerReady=false;
  const deadline=Date.now()+7800;
  await cdp(t,'Page.bringToFront');
  while(!ok&&Date.now()<deadline){
   playerReady=await evaluate(t,'!!document.querySelector("[data-uia=player]")');
   if(!playerReady){await sleep(350);continue}
   await revealPlayerControls(t);
   ok=await evaluate(t,`(()=>{const b=document.querySelector('button[data-uia="${selector}"]');if(!b||b.disabled)return false;b.click();return true})()`);
   if(!ok)await sleep(260);
  }
  if(!ok)throw Error(!playerReady?'Netflix ще завантажує відео. Спробуй трохи пізніше.':action==='episodes'?'Для цього відео немає списку серій.':'Наступна серія зараз недоступна.');
  return;
 }
 if(action==='season'||action==='episode'){
  if(!Number.isInteger(body.index)||body.index<0||body.index>99)throw Error('Онови список і вибери серію ще раз.');
  const selector=action==='season'?'[data-uia^="season-pane-item-"]':'[data-uia="episode-pane-item"]';
  const ok=await evaluate(t,`(async()=>{const panel=document.querySelector('[data-uia="selector-episode"]');let item=panel?.querySelectorAll('${selector}')[${body.index}];if(!item)return false;const press=e=>e.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:1,pointerType:'mouse',isPrimary:true}));if(${action==='episode'}&&!item.querySelector('[data-uia="episode-pane-item-preview-open"]')){press(item);await new Promise(r=>setTimeout(r,100));item=panel?.querySelectorAll('${selector}')[${body.index}];if(!item)return false}press(item);return true})()`);
  if(!ok)throw Error('Список серій змінився. Відкрий його ще раз.');
  return;
 }
 if(action==='profile'){
  if(!Number.isInteger(body.index)||body.index<0||body.index>9)throw Error('Вибери профіль.');
  const ok=await evaluate(t,`(()=>{const e=document.querySelectorAll('.profile-link')[${body.index}];if(!e)return false;e.click();return true})()`);if(!ok)throw Error('Онови пульт і вибери профіль ще раз.');return;
 }
 if(action==='back'){const h=await cdp(t,'Page.getNavigationHistory');if(h.currentIndex>0)await cdp(t,'Page.navigateToHistoryEntry',{entryId:h.entries[h.currentIndex-1].id});return;}
 if(action==='fullscreen'){
  await cdp(t,'Page.bringToFront');
  // Use Chrome's window fullscreen state; works even before a player is available.
  const w=await cdp(t,'Browser.getWindowForTarget',{targetId:t.id});
  await cdp(t,'Browser.setWindowBounds',{windowId:w.windowId,bounds:{windowState:w.bounds.windowState==='fullscreen'?'normal':'fullscreen'}});return;
 }
 let script;
 if(action==='seek'){
  if(!Number.isFinite(body.seconds)||![-10,10].includes(body.seconds))throw Error('Недопустиме перемотування.');
  script=`v.currentTime=Math.max(0,Math.min(v.duration-0.1,v.currentTime+${body.seconds}));`;
 }else if(action==='volume'){
  if(!Number.isFinite(body.value)||body.value<0||body.value>100)throw Error('Гучність має бути від 0 до 100.');
  script=`v.volume=${body.value/100};v.muted=false;`;
 }else if(action==='mute')script='v.muted=!v.muted;';
 else if(action==='pause')script='v.pause();';
 else if(action==='play')script='await v.play();';
 else script='if(v.paused)await v.play();else v.pause();';
 const r=await evaluate(t,`(async()=>{const v=[...document.querySelectorAll('video')].find(v=>v.duration>0);if(!v)return {error:'Спочатку відкрий фільм і вибери профіль Netflix.'};${script}return {ok:true}})()`);
 if(r?.error)throw Error(r.error);
}
function json(res,status,obj){res.writeHead(status,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(obj))}
async function readBody(req){let data='';for await(const c of req){data+=c;if(data.length>4096)throw Error('Запит завеликий.')}return JSON.parse(data||'{}')}
const failed=new Map();
function authenticated(req){
 const bearer=(req.headers.authorization||'').replace(/^Bearer /,'');
 const cookie=(req.headers.cookie||'').split(';').map(s=>s.trim()).find(s=>s.startsWith('cinema-session='))?.slice('cinema-session='.length)||'';
 const expected=Buffer.from(key);
 return [bearer,cookie].some(candidate=>{const value=Buffer.from(candidate);return value.length===expected.length&&timingSafeEqual(value,expected)});
}
export async function start(){
 await mkdir(DATA,{recursive:true,mode:0o700});await chmod(DATA,0o700);
 const keyfile=join(DATA,'remote-key');try{key=(await readFile(keyfile,'utf8')).trim()}catch(error){if(error.code!=='ENOENT')throw error;key=randomBytes(24).toString('base64url');await writeFile(keyfile,key,{mode:0o600,flag:'wx'})}
 if(!/^[A-Za-z0-9_-]{32}$/.test(key))throw Error('Invalid pairing key; preserve the old key and generate a fresh one.');await chmod(keyfile,0o600);
 const server=http.createServer(async(req,res)=>{
  const ip=req.socket.remoteAddress;
  res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','no-referrer');res.setHeader('X-Frame-Options','DENY');
  res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; media-src 'self'; frame-ancestors 'none'; base-uri 'none'");
  if(!isLocal(ip)){json(res,403,{error:'Доступ лише з домашньої мережі.'});return}
  let url;try{url=new URL(req.url,`http://${req.headers.host}`)}catch{json(res,400,{error:'Bad request'});return}
  if(!hosts().has(url.hostname)||url.port!==String(PORT)){json(res,403,{error:'Невідома адреса пульта.'});return}
  if(req.headers.origin && req.headers.origin!==`http://${req.headers.host}`){json(res,403,{error:'Origin denied'});return}
  if(url.pathname.startsWith('/api/')){
   const attempts=failed.get(ip);if(attempts&&attempts.count>=20&&Date.now()-attempts.time<60000){json(res,429,{error:'Зачекай хвилину перед наступною спробою.'});return}
   if(!authenticated(req)){failed.set(ip,{count:(attempts&&Date.now()-attempts.time<60000?attempts.count:0)+1,time:Date.now()});json(res,401,{error:'Відскануй QR-код із ПК, щоб підключити пульт.'});return}
   failed.delete(ip);
   res.setHeader('Set-Cookie',`cinema-session=${key}; Path=/api; Max-Age=31536000; HttpOnly; SameSite=Strict`);
   try{
    if(req.method==='GET'&&url.pathname==='/api/state'){lastState={...await state(),paired:true};json(res,200,lastState);return}
    if(req.method==='POST'&&url.pathname==='/api/command'){
     if(req.headers['content-type']!=='application/json'){json(res,415,{error:'JSON required'});return}
     const body=await readBody(req);const result=commandQueue.then(()=>command(body));commandQueue=result.catch(()=>{});await result;json(res,200,{ok:true});return;
    }
    json(res,404,{error:'Not found'});
   }catch(e){json(res,400,{error:e.message})}return;
  }
  if(req.method!=='GET'){json(res,405,{error:'Method not allowed'});return}
  const routes={'/':['index.html','text/html; charset=utf-8'],'/app.js':['app.js','text/javascript; charset=utf-8'],'/style.css':['style.css','text/css; charset=utf-8'],'/icon.svg':['icon.svg','image/svg+xml'],'/manifest.webmanifest':['manifest.webmanifest','application/manifest+json']};
  
  const route=routes[url.pathname];if(!route){json(res,404,{error:'Not found'});return}
  try{const data=await readFile(join(ROOT,'public',route[0]));
   res.writeHead(200,{'Content-Type':route[1],'Content-Length':data.length,'Accept-Ranges':'bytes'});res.end(data)
  }catch{json(res,404,{error:'Not found'})}
 });
 server.requestTimeout=12000;server.headersTimeout=10000;
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(PORT,BIND,resolve)});console.log(`Cinema remote ready on port ${PORT}`);return server;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)await start();
