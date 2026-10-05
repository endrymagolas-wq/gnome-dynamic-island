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
export class SceneModel{
  constructor(meta){this.meta=meta;this.state='idle';this.position=[...meta.targets.idle];this.path=[];this.stage=0;this.heading=0;this.seq=-1;this.time=0;}
  event(e){
    if(e.seq===this.seq||!STATES.includes(e.state))return false;
    this.seq=e.seq;if(e.state==='starting')this.stage=0;
    if(e.state==='editing')this.stage=Math.min(4,this.stage+1);
    this.state=e.state;
    const t=this.meta.targets[e.state]||this.meta.targets.desk;
    // Route via the clear front beach. No shortcut through cottage/terrace.
    this.path=[];
    if(this.position[1]>.1){const side=this.position[0]<0?-3.3:3.6;this.path.push([side,1.2,.43],[side,-1.2,.43]);}
    if(t[1]>.1)this.path.push([-3.3,-1.2,.43],[-3.3,1.2,.43]);
    this.path.push([...t]);return true;
  }
  step(dt){
    // Each offline rig supplies its measured stride; preserve legacy Snow speed.
    const speed=this.meta.character?.walkSpeed??.468;
    this.time+=Math.min(.1,dt);let budget=Math.max(0,Math.min(.1,dt))*speed;
    while(this.path.length&&budget>0){const t=this.path[0],dx=t[0]-this.position[0],dy=t[1]-this.position[1],d=Math.hypot(dx,dy);
      if(d<.001){this.position=[...t];this.path.shift();continue;}this.heading=Math.atan2(dy,dx);
      const v=Math.min(budget,d);this.position[0]+=dx/d*v;this.position[1]+=dy/d*v;this.position[2]=groundHeight(this.position[0],this.position[1],this.meta);budget-=v;if(v===d){this.position=[...t];this.path.shift();}
    }
  }
}
