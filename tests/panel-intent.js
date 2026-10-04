import {EdgeIntent,edgeSegments,hoverIntent} from '../extensions/airplay-island@avalon.local/panel-intent.js';
function check(value,name){if(!value)throw new Error(name);console.log('PASS '+name);}
const e=new EdgeIntent();
check(!e.push({now:0,dx:0,dy:-500}),'single fast impact ignored');
check(!e.push({now:50,dx:0,dy:-500}),'initial guard');
for(let t=150;t<=470;t+=80)check(!e.push({now:t,dx:0,dy:-15}),'pressure below threshold '+t);
check(e.push({now:550,dx:0,dy:-15}),'continued push opens');
check(!e.push({now:700,dx:0,dy:-100}),'one reveal until leave');
e.reset();check(!e.push({now:0,dx:0,dy:0}),'stationary hover never opens');
for(let t=0;t<800;t+=80)check(!e.push({now:t,dx:80,dy:-10}),'sideways travel ignored '+t);
for(const name of ['mouse pressed','window drag','fullscreen','lock','island menu']){
 e.reset();for(let t=0;t<800;t+=80)check(!e.push({now:t,dx:0,dy:-100,blocked:true}),name+' '+t);
}
e.reset();e.push({now:0,dx:0,dy:-10});e.push({now:200,dx:0,dy:-15});check(!e.push({now:1400,dx:0,dy:-500}),'old pressure expires');
const m={x:0,y:0,width:1920,height:1080};
check(JSON.stringify(edgeSegments(m,[m]))==='[[32,800],[1120,1888]]','corners and island excluded');
check(JSON.stringify(edgeSegments(m,[m,{x:0,y:-1080,width:700,height:1080}]))==='[[700,800],[1120,1888]]','adjacent monitor passage kept');
check(edgeSegments({x:0,y:0,width:320,height:600},[]).length===0,'narrow screen safe fallback');

const state={edge:true,onIsland:false,titlebar:false,dragging:false,blocked:false,shift:false};
check(hoverIntent(state),'empty desktop ceiling hover opens');
check(!hoverIntent({...state,titlebar:true}),'top-aligned titlebar hover does not open');
check(hoverIntent({...state,titlebar:true,onIsland:true}),'ceiling above island opens over titlebar');
check(hoverIntent({...state,titlebar:true,shift:true}),'explicit Shift opens over titlebar');
check(!hoverIntent({...state,edge:false,onIsland:true}),'island body is not top-edge trigger');
check(!hoverIntent({...state,onIsland:true,dragging:true}),'pressed mouse never opens');
check(!hoverIntent({...state,onIsland:true,blocked:true}),'fullscreen lock menu context never opens');
