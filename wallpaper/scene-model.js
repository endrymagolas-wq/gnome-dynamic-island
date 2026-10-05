export const STATES=['starting','editing','testing','failed','permission','done','working','browsing','idle'];
export function project(point,meta){
  const c=meta.camera,m=c.matrixWorld,d=point.map((v,i)=>v-c.location[i]);
  const x=d.reduce((s,v,i)=>s+v*m[i][0],0),y=d.reduce((s,v,i)=>s+v*m[i][1],0),depth=-d.reduce((s,v,i)=>s+v*m[i][2],0);
  const f=meta.width*c.lens/c.sensor;
  return {x:meta.width/2+f*x/depth,y:meta.height/2-f*y/depth,depth,ppm:f/depth};
}
export function groundHeight(x,y,meta){
  const g=meta.ground||{ellipse:[5.5,4.3],plateauRadius:.72,height:.43,slope:2.35};
  let r=Math.hypot(x/g.ellipse[0],y/g.ellipse[1]);
  if(g.coastPerturb&&r>g.plateauRadius){
    const a=Math.atan2(y/g.ellipse[1],x/g.ellipse[0]);
    const dr=g.coastPerturb[0]*Math.sin(3*a)+g.coastPerturb[1]*Math.cos(5*a+g.coastPerturb[2]);
    const band=.18;
    r=r>=g.plateauRadius+band+dr?r-dr:(r+dr*g.plateauRadius/band)/(1+dr/band);
  }
  return g.height-Math.max(0,r-g.plateauRadius)*g.slope;
}
// Visibility graph around measured furniture footprints, expanded by actor radius.
function route(start,end,meta){
  const c=meta.navigation.clearance;
  const boxes=meta.navigation.obstacles.map(o=>[o.bounds[0]-c,o.bounds[1]-c,o.bounds[2]+c,o.bounds[3]+c]);
  const inside=(p,b)=>p[0]>b[0]+1e-7&&p[0]<b[2]-1e-7&&p[1]>b[1]+1e-7&&p[1]<b[3]-1e-7;
  const blocked=(a,b)=>boxes.some(r=>{
    let lo=0,hi=1;
    for(let axis=0;axis<2;axis++){
      const d=b[axis]-a[axis];
      if(Math.abs(d)<1e-9){if(a[axis]<=r[axis]+1e-7||a[axis]>=r[axis+2]-1e-7)return false;}
      else{const p=(r[axis]-a[axis])/d,q=(r[axis+2]-a[axis])/d;lo=Math.max(lo,Math.min(p,q));hi=Math.min(hi,Math.max(p,q));}
    }
    if(hi-lo<1e-7)return false;
    const t=(lo+hi)/2;return inside([a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t],r);
  });
  if(boxes.some(b=>inside(start,b)||inside(end,b)))throw Error('Walking endpoint is inside furniture');
  const nodes=[start,end];
  for(const b of boxes)for(const x of [b[0]-.01,b[2]+.01])for(const y of [b[1]-.01,b[3]+.01]){
    if(!boxes.some(r=>inside([x,y],r)))nodes.push([x,y,groundHeight(x,y,meta)]);
  }
  const dist=nodes.map(()=>Infinity),prev=nodes.map(()=>-1),visited=new Set();dist[0]=0;
  for(let i=0;i<nodes.length;i++){
    let u=-1;for(let n=0;n<nodes.length;n++)if(!visited.has(n)&&(u<0||dist[n]<dist[u]))u=n;
    if(u<0||!Number.isFinite(dist[u]))break;if(u===1)break;visited.add(u);
    for(let v=0;v<nodes.length;v++)if(!visited.has(v)&&!blocked(nodes[u],nodes[v])){
      const d=dist[u]+Math.hypot(nodes[v][0]-nodes[u][0],nodes[v][1]-nodes[u][1]);
      if(d<dist[v]){dist[v]=d;prev[v]=u;}
    }
  }
  if(!Number.isFinite(dist[1]))throw Error('No clear beach route');
  const path=[];for(let n=1;n>0;n=prev[n])path.unshift([...nodes[n]]);return path;
}
export class SceneModel{
  constructor(meta){this.meta=meta;this.state='idle';this.position=[...meta.targets.idle];this.path=[];this.stage=0;this.heading=0;this.seq=-1;this.time=0;this.seated=!!meta.seating;this.transition=null;}
  event(e){
    if(e.seq===this.seq||!STATES.includes(e.state))return false;
    this.seq=e.seq;if(e.state==='starting')this.stage=0;
    if(e.state==='editing')this.stage=Math.min(4,this.stage+1);
    this.state=e.state;
    if(this.meta.seating){
      if(this.transition)return true;
      if(this.seated){if(!this.meta.seating.states.includes(this.state))this.transition={kind:'stand',elapsed:0};}
      else this.plan();
      return true;
    }
    const t=this.meta.targets[e.state]||this.meta.targets.desk;
    // Route via the clear front beach. No shortcut through cottage/terrace.
    this.path=[];
    if(this.position[1]>.1){const side=this.position[0]<0?-3.3:3.6;this.path.push([side,1.2,.43],[side,-1.2,.43]);}
    if(t[1]>.1)this.path.push([-3.3,-1.2,.43],[-3.3,1.2,.43]);
    this.path.push([...t]);return true;
  }
  plan(){
    const t=this.meta.seating.states.includes(this.state)?this.meta.seating.approach:(this.meta.targets[this.state]||this.meta.targets.desk);
    this.path=route(this.position,t,this.meta);
  }
  step(dt){
    // Each offline rig supplies its measured stride; preserve legacy Snow speed.
    const speed=this.meta.character?.walkSpeed??.468;
    this.time+=Math.min(.1,dt);let budget=Math.max(0,Math.min(.1,dt))*speed;
    if(this.transition){
      const seat=this.meta.seating,t=this.transition;t.elapsed+=Math.max(0,Math.min(.1,dt));
      const phase=Math.min(1,t.elapsed/seat.seconds),u=t.kind==='sit'?phase:1-phase,e=u*u*(3-2*u);
      this.position=seat.approach.map((v,i)=>v+(seat.position[i]-v)*e);
      this.position[2]+=seat.hopHeight*Math.sin(u*Math.PI);
      if(phase===1){
        this.seated=t.kind==='sit';if(this.seated)this.seatedSince=this.time;this.position=[...(this.seated?seat.position:seat.approach)];this.transition=null;
        if(this.seated){if(!seat.states.includes(this.state))this.transition={kind:'stand',elapsed:0};}
        else this.plan();
      }
      return;
    }
    while(this.path.length&&budget>0){const t=this.path[0],dx=t[0]-this.position[0],dy=t[1]-this.position[1],d=Math.hypot(dx,dy);
      if(d<.001){this.position=[...t];this.path.shift();continue;}this.heading=Math.atan2(dy,dx);
      const v=Math.min(budget,d);this.position[0]+=dx/d*v;this.position[1]+=dy/d*v;this.position[2]=groundHeight(this.position[0],this.position[1],this.meta);budget-=v;if(v===d){this.position=[...t];this.path.shift();}
    }
    if(this.meta.seating&&!this.path.length&&!this.seated&&this.meta.seating.states.includes(this.state))this.transition={kind:'sit',elapsed:0};
  }
}
