import {STATES, route, groundHeight} from './scene-model.js';

// The app event remains the source of truth. A separate, shared coordinator
// assigns physical places and quiet leisure activity to the three mascots.
const KEYS=['claude','codex','apps'];
const REST_STATES=new Set(['idle','done']);
const CYCLE=['tea','seat','bed','seat'];
const EPS=1e-7;
const distance=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
const point=p=>Array.isArray(p)&&p.length===3&&p.every(Number.isFinite);
const copy=p=>[...p];

function checkedPlace(value, fallbackId){
  if(!value||!point(value.position)||!point(value.approach))throw Error(`Invalid resort place: ${fallbackId}`);
  return {...value,id:value.id||fallbackId,position:copy(value.position),approach:copy(value.approach)};
}

export class ResortLife{
  constructor(meta, definitions=[{key:'claude',scale:1},{key:'codex',scale:.86},{key:'apps',scale:.8}]){
    if(!meta.activities?.seats)throw Error('The resort activity layout must define three seats');
    this.meta=meta;this.layout=meta.activities;this.reservations=new Map();this.clock=0;
    this.places={bed:checkedPlace(this.layout.bed,'bed'),tea:checkedPlace(this.layout.tea,'tea')};
    this.actors=definitions.map((definition,index)=>{
      const key=definition.key;
      if(!KEYS.includes(key))throw Error(`Unknown resort actor: ${key}`);
      const scale=definition.scale??1;
      if(!(scale>0))throw Error('Actor scale must be positive');
      const seat=checkedPlace(this.layout.seats[key],`seat-${key}`);
      const a={key,scale,radius:definition.radius??.32*scale,priority:index,seat,
        state:'idle',seq:-1,time:0,stage:0,position:this.origin(seat,scale),path:[],heading:seat.heading??0,
        seated:true,seatedSince:0,transition:null,activity:'sit',activityClip:'drink',activityTime:0,
        pose:'idle',place:seat,goal:null,destination:null,routeError:null,waitTime:0,replanAt:0,
        routineIndex:index%4,nextIdleAt:(this.layout.initialIdleSeconds??10)+index*5};
      if(this.reservations.has(seat.id))throw Error(`Duplicate assigned seat: ${seat.id}`);
      this.reservations.set(seat.id,key);
      return a;
    });
    // A rear console row with only an east-side entrance is a single lane.
    // Enter far-to-near and leave near-to-far; body avoidance alone cannot
    // pass an occupied near console in the measured narrow corridor.
    const consoles=this.actors.every(a=>meta.navigation.obstacles.some(o=>o.name===`work-${a.key}`));
    this.traffic=consoles?{ticket:null,parking:false,parked:[],saved:new Map(),
      y:this.layout.targets[this.actors[0].key].desk[1],
      left:Math.min(...this.actors.map(a=>this.layout.targets[a.key].desk[0]))-.4,
      right:Math.max(...this.actors.map(a=>a.seat.approach[0]))+1.2}:null;
    if(new Set(this.actors.map(a=>a.key)).size!==this.actors.length)throw Error('Duplicate resort actor');
    for(const a of this.actors)this.checkedRoute(a.seat.approach,a.seat.approach,a);
    for(const kind of ['bed','tea'])this.checkedRoute(this.places[kind].approach,this.places[kind].approach,this.actors[0]);
    for(let i=0;i<this.actors.length;i++)for(let j=i+1;j<this.actors.length;j++){
      if(distance(this.actors[i].position,this.actors[j].position)<this.actors[i].radius+this.actors[j].radius-EPS)
        throw Error('Assigned resort seats overlap actor footprints');
    }
  }

  actor(key){return this.actors.find(a=>a.key===key);}

  origin(place,scale){
    const p=copy(place.position);
    if(Number.isFinite(place.surfaceHeight))p[2]=place.surfaceHeight-(place.rootOffset??.31)*scale;
    return p;
  }

  nav(a){
    return {...this.meta,navigation:{...this.meta.navigation,
      clearance:Math.max(this.meta.navigation.clearance??0,a.radius)}};
  }

  checkedRoute(from,to,a,nav=this.nav(a)){
    let path=nav.navigation.obstacles.some(o=>o.circle)?this.dryRoute(from,to,nav):route(from,to,nav);
    // A visibility graph can go around a prop through the water when its
    // bounds are near the coast. Treat that as unavailable, never a shortcut.
    const minimum=this.layout.minimumGroundHeight??.1;
    let previous=from;
    for(const next of path){if(!this.drySegment(previous,next,minimum))return this.dryRoute(from,to,nav);previous=next;}
    return path;
  }

  drySegment(from,to,minimum=this.layout.minimumGroundHeight??.1){
    const samples=Math.max(1,Math.ceil(distance(from,to)/.1));
    for(let i=0;i<=samples;i++){
      const t=i/samples,x=from[0]+(to[0]-from[0])*t,y=from[1]+(to[1]-from[1])*t;
      if(groundHeight(x,y,this.meta)<minimum)return false;
    }
    return true;
  }

  dryRoute(from,to,nav){
    // The legacy graph chooses the shortest prop-clear route before checking
    // the shore. On the enlarged island, a coastal chair may have a short wet
    // route and a perfectly usable dry route on its other side. Filter edges
    // before Dijkstra instead of rejecting the complete route afterwards.
    const c=nav.navigation.clearance;
    const boxes=nav.navigation.obstacles.filter(o=>!o.circle).map(o=>[o.bounds[0]-c,o.bounds[1]-c,o.bounds[2]+c,o.bounds[3]+c]);
    const circles=nav.navigation.obstacles.filter(o=>o.circle).map(o=>o.circle);
    const insideBox=(p,b)=>p[0]>b[0]+EPS&&p[0]<b[2]-EPS&&p[1]>b[1]+EPS&&p[1]<b[3]-EPS;
    const inside=p=>boxes.some(b=>insideBox(p,b))||circles.some(b=>distance(p,b.center)<b.radius-EPS);
    const blocked=(a,b)=>{
      if(boxes.some(r=>{
        let lo=0,hi=1;
        for(let axis=0;axis<2;axis++){
          const d=b[axis]-a[axis];
          if(Math.abs(d)<1e-9){if(a[axis]<=r[axis]+EPS||a[axis]>=r[axis+2]-EPS)return false;}
          else{const p=(r[axis]-a[axis])/d,q=(r[axis+2]-a[axis])/d;lo=Math.max(lo,Math.min(p,q));hi=Math.min(hi,Math.max(p,q));}
        }
        if(hi-lo<EPS)return false;
        const t=(lo+hi)/2;return insideBox([a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t],r);
      }))return true;
      return circles.some(r=>{
        const dx=b[0]-a[0],dy=b[1]-a[1],length=dx*dx+dy*dy;
        const t=length?Math.max(0,Math.min(1,((r.center[0]-a[0])*dx+(r.center[1]-a[1])*dy)/length)):0;
        return Math.hypot(a[0]+dx*t-r.center[0],a[1]+dy*t-r.center[1])<r.radius;
      });
    };
    if(inside(from)||inside(to))throw Error('Walking endpoint is inside furniture or another body');
    if(!this.drySegment(from,from)||!this.drySegment(to,to))throw Error('Walking endpoint leaves the usable beach');
    const nodes=[from,to];
    const add=p=>{if(!inside(p)&&this.drySegment(p,p))nodes.push([p[0],p[1],groundHeight(p[0],p[1],this.meta)]);};
    for(const b of boxes)for(const x of [b[0]-.01,b[2]+.01])for(const y of [b[1]-.01,b[3]+.01])add([x,y]);
    // Twelve tangent-safe vertices approximate the free route around a body;
    // collision tests use its exact circle. This avoids false AABB corner
    // blockage while preserving the same measured physical radius.
    for(const b of circles)for(let i=0;i<12;i++){
      const angle=i*Math.PI/6,r=b.radius/Math.cos(Math.PI/12)+.01;
      add([b.center[0]+Math.cos(angle)*r,b.center[1]+Math.sin(angle)*r]);
    }
    const dist=nodes.map(()=>Infinity),prev=nodes.map(()=>-1),visited=new Set();dist[0]=0;
    for(let i=0;i<nodes.length;i++){
      let u=-1;for(let n=0;n<nodes.length;n++)if(!visited.has(n)&&(u<0||dist[n]<dist[u]))u=n;
      if(u<0||!Number.isFinite(dist[u]))break;if(u===1)break;visited.add(u);
      for(let v=0;v<nodes.length;v++)if(!visited.has(v)&&!blocked(nodes[u],nodes[v])&&this.drySegment(nodes[u],nodes[v])){
        const d=dist[u]+distance(nodes[u],nodes[v]);if(d<dist[v]){dist[v]=d;prev[v]=u;}
      }
    }
    if(!Number.isFinite(dist[1]))throw Error('No clear dry beach route');
    const path=[];for(let n=1;n>0;n=prev[n])path.unshift(copy(nodes[n]));return path;
  }

  event(key,event){
    const a=this.actor(key);
    if(!a||!event||event.seq===a.seq||!STATES.includes(event.state))return false;
    a.seq=event.seq;a.state=event.state;
    // A leisure destination may already be reserved while its actor is still
    // standing up from the previous prop. A new task cancels that reservation
    // but retains the currently occupied prop until its exit gesture finishes.
    for(const [id,owner] of this.reservations)if(owner===key&&id!==a.place?.id)this.reservations.delete(id);
    if(a.state==='starting')a.stage=0;
    if(a.state==='editing')a.stage=Math.min(4,a.stage+1);
    const goal=REST_STATES.has(a.state)?'seat':'work';
    if(a.trafficPark){this.traffic.saved.set(key,goal);a.goal='seat';}
    else a.goal=goal;
    // An interrupted lowering/rising gesture completes before changing course.
    // That prevents snapping from a cushion into the sand mid animation.
    if(!a.transition)this.respond(a);
    return true;
  }

  workTarget(a){
    const targets=this.layout.targets?.[a.key]||this.meta.targets;
    const state=['starting','editing','working'].includes(a.state)?'desk':a.state;
    const p=targets[state]||targets.desk;
    if(!point(p))throw Error(`Missing ${a.key} ${state} activity target`);
    return copy(p);
  }

  workPose(a){
    const pose=this.layout.poseOverrides?.[a.key]?.[a.state];
    return STATES.includes(pose)?pose:a.state;
  }

  reserve(place,a){
    const owner=this.reservations.get(place.id);
    if(owner&&owner!==a.key)return false;
    this.reservations.set(place.id,a.key);return true;
  }

  release(place,a){
    if(place&&this.reservations.get(place.id)===a.key)this.reservations.delete(place.id);
  }

  go(a,kind){
    const place=kind==='seat'?a.seat:this.places[kind];
    if(place&&!this.reserve(place,a))return false;
    let destination;
    try{destination=place?copy(place.approach):this.workTarget(a);a.path=this.checkedRoute(a.position,destination,a);}
    catch(error){
      if(place&&place!==a.place)this.release(place,a);
      a.path=[];a.routeError=error.message;a.activity='wait';a.activityClip='stand';a.pose='browsing';return false;
    }
    if(a.destination?.place&&a.destination.place!==a.place&&a.destination.place!==place)this.release(a.destination.place,a);
    a.destination={kind,place,target:destination};a.activity='walk';a.activityClip=null;a.pose='walk';a.routeError=null;a.waitTime=0;
    if(!a.path.length||distance(a.position,destination)<.001){a.position=destination;a.path=[];this.arrive(a);}
    return true;
  }

  transition(a,kind,to){
    const seconds=a.place?.transitionSeconds??this.layout.transitionSeconds??1.1;
    a.transition={kind,elapsed:0,seconds,from:copy(a.position),to:copy(to),place:a.place?.id};
    a.activity=kind;a.activityClip=kind;a.pose=kind;a.path=[];
  }

  inLane(a){
    return !!this.traffic&&a.position[0]>=this.traffic.left&&a.position[0]<=this.traffic.right&&Math.abs(a.position[1]-this.traffic.y)<.25;
  }

  laneTarget(a,goal=a.goal){
    if(!this.traffic||goal!=='work')return null;
    const target=this.workTarget(a),desk=this.layout.targets[a.key].desk;
    return distance(target,desk)<.01?target:null;
  }

  parkLane(){
    const t=this.traffic;if(t.parking)return;
    t.parking=true;t.ticket=null;
    t.parked=this.actors.filter(a=>this.inLane(a)).sort((a,b)=>b.position[0]-a.position[0]);
    for(const a of t.parked){
      t.saved.set(a.key,a.goal??(REST_STATES.has(a.state)?'seat':'work'));
      a.trafficPark=true;a.goal='seat';a.path=[];a.destination=null;
    }
  }

  trafficAllows(a,goal){
    const t=this.traffic;if(!t)return true;
    if(t.parking){
      const next=t.parked.find(other=>!(other.place===other.seat&&other.seated&&!other.transition));
      if(!next)return false;
      if(next!==a)return false;
      t.ticket=a.key;return true;
    }
    const target=this.laneTarget(a,goal),inside=this.inLane(a);
    if(!target&&!inside){if(t.ticket===a.key)t.ticket=null;return true;}
    const eastOf=this.actors.some(other=>other!==a&&this.inLane(other)&&other.position[0]>
      (target?.[0]??a.position[0])+a.radius+other.radius&&other.activity==='work');
    if(eastOf){this.parkLane();return false;}
    if(t.ticket&&t.ticket!==a.key)return false;
    if(target){
      const earlier=this.actors.some(other=>other!==a&&this.laneTarget(other)&&
        this.workTarget(other)[0]<target[0]&&other.goal&&other.activity!=='work'&&!other.trafficPark);
      if(earlier)return false;
    }else{
      const nearer=this.actors.some(other=>other!==a&&this.inLane(other)&&other.goal&&other.position[0]>a.position[0]);
      if(nearer)return false;
    }
    t.ticket=a.key;return true;
  }

  updateTraffic(){
    const t=this.traffic;if(!t)return;
    if(t.ticket){
      const holder=this.actor(t.ticket);
      if(!holder.transition&&!holder.path.length&&!holder.goal)t.ticket=null;
    }
    if(t.parking&&t.parked.every(a=>a.place===a.seat&&a.seated&&!a.transition)){
      t.parking=false;t.ticket=null;
      for(const a of t.parked){a.trafficPark=false;a.goal=t.saved.get(a.key)??(REST_STATES.has(a.state)?'seat':'work');}
      t.parked=[];t.saved.clear();
    }
  }

  leave(a){
    if(a.transition)return;
    if(a.place===a.seat&&a.seated){this.transition(a,'stand',a.seat.approach);return;}
    if(a.place===this.places.bed){this.transition(a,'rise',a.place.approach);return;}
    this.release(a.place,a);a.place=null;a.seated=false;this.respond(a);
  }

  respond(a){
    if(a.transition)return;
    const goal=a.goal??(REST_STATES.has(a.state)?'seat':'work');
    if(a.place&&((goal==='seat'&&a.place===a.seat)||(goal==='bed'&&a.place===this.places.bed)||(goal==='tea'&&a.place===this.places.tea))){
      a.goal=null;return;
    }
    if(goal==='work'&&a.activity==='work'&&distance(a.position,this.workTarget(a))<.001){
      a.pose=this.workPose(a);a.goal=null;return;
    }
    if(!this.trafficAllows(a,goal))return;
    if(a.place){this.leave(a);return;}
    if(a.destination){
      this.release(a.destination.place,a);a.destination=null;a.path=[];
    }
    this.go(a,goal);
  }

  arrive(a){
    const destination=a.destination;if(!destination)return;
    a.path=[];a.destination=null;a.place=destination.place||null;a.waitTime=0;
    if(destination.kind==='seat'){
      this.transition(a,'sit',this.origin(a.seat,a.scale));
    }else if(destination.kind==='bed'){
      this.transition(a,'lie',this.origin(a.place,a.scale));
    }else if(destination.kind==='tea'){
      a.position=this.origin(a.place,a.scale);a.heading=a.place.heading??0;
      a.activity='tea';a.activityClip='brew';a.pose='brew';a.activityTime=0;
      a.goal=null;a.nextIdleAt=a.time+(a.place.seconds??10);
    }else{
      a.activity='work';a.activityClip=null;a.pose=this.workPose(a);a.activityTime=0;a.goal=null;
      if(this.traffic?.ticket===a.key)this.traffic.ticket=null;
    }
  }

  clear(a,candidate){
    return this.actors.every(other=>other===a||distance(candidate,other.position)>=a.radius+other.radius+EPS);
  }

  segmentClear(a,from,to){
    try{
      const path=this.checkedRoute(from,to,a);
      return path.length<=1;
    }catch{return false;}
  }

  detour(a){
    if(!a.destination||a.time<a.replanAt)return false;
    a.replanAt=a.time+.5;
    const nav=this.nav(a);
    // The same visibility graph now treats the present body positions as
    // temporary furniture. It finds a route around a crossing walker rather
    // than endlessly shuffling at the next real chair corner.
    nav.navigation.obstacles=[...nav.navigation.obstacles,...this.actors.filter(other=>other!==a).map(other=>({
      name:`actor-${other.key}`,bounds:[other.position[0]-other.radius,other.position[1]-other.radius,
        other.position[0]+other.radius,other.position[1]+other.radius],
      circle:{center:other.position,radius:a.radius+other.radius+EPS}}))];
    try{a.path=this.checkedRoute(a.position,a.destination.target,a,nav);return true;}catch{return false;}
  }

  move(a,budget){
    if(!a.path.length)return;
    const target=a.path[0],d=distance(a.position,target);
    if(d<.001){a.position=copy(target);a.path.shift();if(!a.path.length)this.arrive(a);return;}
    const dx=(target[0]-a.position[0])/d,dy=(target[1]-a.position[1])/d,step=Math.min(budget,d);
    let next=[a.position[0]+dx*step,a.position[1]+dy*step,0];next[2]=groundHeight(next[0],next[1],this.meta);
    if(this.clear(a,next)){
      a.heading=Math.atan2(dy,dx);a.position=next;a.waitTime=0;
      if(step===d){a.position=copy(target);a.path.shift();if(!a.path.length)this.arrive(a);}
      return;
    }
    a.waitTime+=budget/((this.meta.character?.walkSpeed??.5952)*a.scale);
    if(this.detour(a))return;
    // A walker yields into the free side of its route, rather than occupying
    // a narrow approach forever. Each sidestep is tested against real props
    // and every other body. Only one actor moves at a time in this frame.
    for(const [sx,sy] of [[-dy,dx],[dy,-dx],[-dx,-dy]]){
      next=[a.position[0]+sx*step,a.position[1]+sy*step,0];next[2]=groundHeight(next[0],next[1],this.meta);
      if(this.clear(a,next)&&this.segmentClear(a,a.position,next)){
        a.position=next;a.heading=Math.atan2(sy,sx);
        try{a.path=this.checkedRoute(a.position,a.destination.target,a);}catch(error){a.routeError=error.message;}
        return;
      }
    }
  }

  advanceTransition(a,dt){
    const t=a.transition;if(!t)return;
    const elapsed=Math.min(t.seconds,t.elapsed+dt),phase=elapsed/t.seconds,e=phase*phase*(3-2*phase);
    const next=t.from.map((v,i)=>v+(t.to[i]-v)*e);
    if(t.kind==='sit'||t.kind==='stand')next[2]+=(a.place?.hopHeight??.12)*Math.sin(phase*Math.PI);
    if(!this.clear(a,next)){a.waitTime+=dt;return;}
    a.position=next;t.elapsed=elapsed;
    if(phase<1)return;
    a.transition=null;a.activityTime=0;a.waitTime=0;
    if(t.kind==='stand'||t.kind==='rise'){
      this.release(a.place,a);a.place=null;a.seated=false;this.respond(a);return;
    }
    a.heading=a.place?.heading??0;
    if(t.kind==='sit'){
      a.seated=true;a.seatedSince=a.time;a.activity='sit';a.activityClip='drink';a.pose='idle';
      a.nextIdleAt=a.time+(this.layout.seatSeconds??12)+a.priority*1.2;
    }else{
      a.seated=false;a.activity='scratch';a.activityClip='scratch';a.pose='scratch';
      a.nextIdleAt=a.time+(a.place.seconds??14);
    }
    const wanted=a.goal;
    a.goal=null;
    if(wanted&&wanted!==(t.kind==='sit'?'seat':'bed')){a.goal=wanted;this.respond(a);}
    else if(!REST_STATES.has(a.state)&&!a.trafficPark){a.goal='work';this.respond(a);}
  }

  leisure(a){
    if(a.trafficPark||!REST_STATES.has(a.state)||a.goal||a.transition||a.path.length||a.activity==='walk'||a.time<a.nextIdleAt)return;
    if(a.activity==='tea'||a.activity==='scratch'){
      a.goal='seat';this.respond(a);return;
    }
    const kind=CYCLE[a.routineIndex%4],place=kind==='seat'?a.seat:this.places[kind];
    if(!this.reserve(place,a)){a.nextIdleAt=a.time+1.5;return;}
    a.routineIndex++;
    if(kind==='seat'){a.nextIdleAt=a.time+(this.layout.seatSeconds??12);return;}
    a.goal=kind;this.respond(a);
  }

  step(dt){
    dt=Math.max(0,Math.min(.1,Number.isFinite(dt)?dt:0));if(!dt)return;
    this.clock+=dt;
    this.updateTraffic();
    for(const a of this.actors){a.time+=dt;a.activityTime+=dt;}
    const order=[...this.actors].sort((a,b)=>b.waitTime-a.waitTime||a.priority-b.priority);
    for(const a of order){
      if(a.transition)this.advanceTransition(a,dt);
      else if(a.path.length)this.move(a,dt*(this.meta.character?.walkSpeed??.5952)*a.scale);
      else if(a.activity==='walk'&&a.destination)this.arrive(a);
      else if(a.goal)this.respond(a);
      this.leisure(a);
    }
  }

  diagnostics(){
    return {time:this.clock,reservations:Object.fromEntries(this.reservations),actors:this.actors.map(a=>({
      key:a.key,state:a.state,activity:a.activity,clip:a.activityClip,position:copy(a.position),moving:!!a.path.length,
      transition:a.transition?.kind??null,place:a.place?.id??null,routeError:a.routeError,waitTime:a.waitTime}))};
  }
}
