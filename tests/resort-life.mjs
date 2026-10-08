import assert from 'node:assert/strict';
import {ResortLife} from '../wallpaper/resort-life.js';
import {STATES,groundHeight,route} from '../wallpaper/scene-model.js';

// These are deliberately independent, roomy test props. The integration gate
// additionally accepts the measured Blender layout through RESORT_LIFE_ASSETS.
const keys=['claude','codex','apps'];
const testMeta={ground:{ellipse:[8,7],plateauRadius:.92,height:.43,slope:2.35},
  character:{walkSpeed:.5952},navigation:{clearance:.3,obstacles:[
    ...[-2,0,2].map((x,i)=>({name:`seat-${keys[i]}`,bounds:[x-.6,-2.5,x+.6,-1.5]})),
    {name:'bed',bounds:[3.35,-2.65,4.65,-.7]},
    {name:'tea counter',bounds:[-4.7,-1.6,-3.3,-.5]},
  ]},activities:{transitionSeconds:1.1,initialIdleSeconds:1,seatSeconds:2,
    seats:Object.fromEntries(keys.map((key,i)=>[key,{id:`seat-${key}`,position:[(i-1)*2,-2,.64],
      approach:[(i-1)*2,-3.1,.43],surfaceHeight:.95,rootOffset:.31}])),
    bed:{id:'bed',position:[4,-2.1,.94],approach:[4,-3.1,.43],seconds:3},
    tea:{id:'tea',position:[-4,-2.1,.43],approach:[-4,-2.1,.43],seconds:3},
    targets:Object.fromEntries(keys.map((key,i)=>[key,{desk:[(1-i)*2,.2,.43],testing:[(1-i)*2,.8,.43],
      failed:[(1-i)*2,.8,.43],permission:[(i-1)*2,-4.3,.43],browsing:[(i-1)*2,2,.43]}]))}};

let meta=testMeta;
if(process.env.RESORT_LIFE_ASSETS){
  const fs=await import('node:fs');
  meta=JSON.parse(fs.readFileSync(`${process.env.RESORT_LIFE_ASSETS}/scene.json`));
}
let assertions=0,samples=0,seq=0;
const check=(value,message)=>{assert.ok(value,message);assertions++;};
const distance=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
function bodyGate(life){
  for(let i=0;i<life.actors.length;i++)for(let j=i+1;j<life.actors.length;j++){
    const a=life.actors[i],b=life.actors[j];
    check(distance(a.position,b.position)>=a.radius+b.radius-1e-7,
      `${a.key}/${b.key} footprints overlap at ${life.clock}: ${a.position}, ${b.position}`);
  }
  for(const a of life.actors){
    if(a.path.length&&!a.transition){
      check(Math.abs(a.position[2]-groundHeight(a.position[0],a.position[1],meta))<1e-7,`${a.key} walks above/below beach`);
      for(const o of meta.navigation.obstacles){
        const c=Math.max(a.radius,meta.navigation.clearance),[x0,y0,x1,y1]=o.bounds;
        check(!(a.position[0]>x0-c+1e-7&&a.position[0]<x1+c-1e-7&&a.position[1]>y0-c+1e-7&&a.position[1]<y1+c-1e-7),
          `${a.key} walks through ${o.name}`);
      }
    }
  }
  const occupied=new Map();
  for(const a of life.actors){
    const place=a.place?.id;
    if(place){check(!occupied.has(place),`${place} has two bodies`);occupied.set(place,a.key);}
  }
  samples++;
}
function tick(life,seconds,onTick){
  for(let i=0;i<seconds/.05;i++){life.step(.05);bodyGate(life);onTick?.();}
}

const initial=new ResortLife(meta);
for(const a of initial.actors){
  assert.equal(a.seated,true);assert.equal(a.activityClip,'drink');assert.equal(initial.reservations.get(a.seat.id),a.key);
  if(Number.isFinite(a.seat.surfaceHeight))assert.equal(a.position[2],a.seat.surfaceHeight-(a.seat.rootOffset??.31)*a.scale);
}
assert.equal(initial.event('claude',{state:'unknown',seq:1}),false);
assert.equal(initial.event('claude',{state:'editing',seq:1}),true);
assert.equal(initial.event('claude',{state:'editing',seq:1}),false);
assert.equal(initial.actor('claude').stage,1);
initial.event('claude',{state:'starting',seq:2});assert.equal(initial.actor('claude').stage,0);

// All three must physically reach all three leisure activities. A second actor
// waits for the shared prop, and the reservation survives its leaving gesture.
const idle=new ResortLife(meta),seen=new Map(keys.map(key=>[key,new Set()]));
tick(idle,240,()=>{for(const a of idle.actors)seen.get(a.key).add(a.activityClip);});
for(const key of keys)for(const clip of ['drink','scratch','brew'])check(seen.get(key).has(clip),`${key} never reached ${clip}: ${[...seen.get(key)]}`);
check(idle.actors.every(a=>!a.routeError),JSON.stringify(idle.diagnostics()));

// Synchronized app events force intersecting routes and opposite travel. This
// reproduces the old implementation's 5cm body overlap without weakening the
// physical radius. Every actor must also arrive, so waiting forever is no PASS.
for(const state of STATES.filter(state=>!['idle','done'].includes(state))){
  const life=new ResortLife(meta);
  for(const key of keys)life.event(key,{state,seq:++seq});
  tick(life,120);
  for(const a of life.actors){
    check(a.path.length===0&&!a.transition&&a.activity==='work',`${state}: ${a.key} never arrived: ${JSON.stringify(life.diagnostics())}`);
    assert.deepEqual(a.position,life.workTarget(a));
    assert.equal(a.state,state);
    assert.equal(a.pose,meta.activities.poseOverrides?.[a.key]?.[state]??state);
  }
  for(const key of keys)life.event(key,{state:'idle',seq:++seq});
  let reached=new Set();
  tick(life,120,()=>{for(const a of life.actors)if(a.seated)reached.add(a.key);});
  check(reached.size===3,`${state}: an actor never returned to its seat`);
}

// Interrupt each physical transition at several phases. The first step must
// keep the current gesture, then safely leave the prop before approaching work.
for(const kind of ['sit','stand','lie','rise'])for(const progress of [.1,.5,.85]){
  const life=new ResortLife(meta),a=life.actor('claude');
  const place=kind==='sit'||kind==='stand'?a.seat:life.places.bed;
  a.place=place;a.position=kind==='sit'||kind==='lie'?[...place.approach]:life.origin(place,a.scale);
  a.seated=kind==='stand';life.reserve(place,a);
  life.transition(a,kind,kind==='sit'||kind==='lie'?life.origin(place,a.scale):place.approach);
  tick(life,a.transition.seconds*progress);
  const elapsed=a.transition.elapsed;
  life.event('claude',{state:'editing',seq:++seq});
  assert.equal(a.transition.kind,kind);assert.equal(a.transition.elapsed,elapsed);
  tick(life,100);
  check(!a.transition&&!a.path.length&&a.activity==='work',`${kind} interruption did not finish`);
  assert.deepEqual(a.position,life.workTarget(a));
  check(life.reservations.get(place.id)!==a.key,`${kind} left a stale reservation`);
}

// A malformed endpoint must hold the actor rather than fall back to walking
// straight through a chair, as the old Companion catch branch did.
const invalid=structuredClone(meta);
invalid.activities.targets.claude.desk=[...invalid.activities.seats.claude.position];
const blocked=new ResortLife(invalid),a=blocked.actor('claude');
blocked.event('claude',{state:'editing',seq:++seq});tick(blocked,10);
check(!!a.routeError,'An inside-furniture endpoint was accepted');
check(!a.path.length&&!a.transition,'Blocked actor kept walking');
assert.deepEqual(a.position,a.seat.approach);

// A reserved future prop must be released when a task interrupts standing up
// from the previous seat. Otherwise every later actor waits for a phantom body.
const interrupted=new ResortLife(meta),i=interrupted.actor('claude');
interrupted.reserve(interrupted.places.bed,i);i.goal='bed';interrupted.respond(i);
assert.equal(i.transition.kind,'stand');
interrupted.event('claude',{state:'editing',seq:++seq});
check(!interrupted.reservations.has(interrupted.places.bed.id),'Interrupted future bed reservation leaked');
assert.equal(interrupted.reservations.get(i.seat.id),'claude');
tick(interrupted,100);
check(i.activity==='work'&&!i.path.length&&!i.transition,'Interrupted reserved journey did not reach work');

// Without a physical keyboard in a personal nook, an active companion thinks
// or inspects. Its actual app event state still drives UI and future events.
const thoughtfulMeta=structuredClone(meta);
thoughtfulMeta.activities.poseOverrides=Object.fromEntries(['codex','apps'].map(key=>[key,{starting:'testing',editing:'testing',working:'testing'}]));
const thoughtful=new ResortLife(thoughtfulMeta);
for(const key of keys)thoughtful.event(key,{state:'working',seq:++seq});
tick(thoughtful,120);
for(const key of ['codex','apps']){
  assert.equal(thoughtful.actor(key).state,'working');assert.equal(thoughtful.actor(key).pose,'testing');
  thoughtful.event(key,{state:'editing',seq:++seq});assert.equal(thoughtful.actor(key).state,'editing');assert.equal(thoughtful.actor(key).pose,'testing');
}
assert.equal(thoughtful.actor('claude').pose,'working');

// A late actor needs the far console after the two near consoles are already
// occupied. They temporarily park, then resume their unchanged app states.
// Repeated edits at an occupied console must not evacuate the whole row.
if(meta.navigation.obstacles.some(o=>o.name==='work-claude')){
  const late=new ResortLife(meta);
  for(const key of keys)late.event(key,{state:'working',seq:++seq});
  tick(late,120);
  const beforePositions=late.actors.map(a=>[...a.position]);
  late.event('claude',{state:'editing',seq:++seq});late.step(.05);
  assert.deepEqual(late.actors.map(a=>a.position),beforePositions);
  check(!late.traffic.parking,'Repeated console edit needlessly evacuated the lane');
  late.event('claude',{state:'idle',seq:++seq});
  let returned=false;
  tick(late,120,()=>{if(late.actor('claude').seated)returned=true;});
  check(returned,'Far console actor never returned through the occupied lane');
  late.event('claude',{state:'editing',seq:++seq});
  tick(late,140);
  for(const actor of late.actors){
    check(actor.activity==='work'&&!actor.path.length&&!actor.transition,`${actor.key} did not resume after late lane entry: ${JSON.stringify(late.diagnostics())}`);
    assert.deepEqual(actor.position,late.workTarget(actor));
  }
  assert.equal(late.actor('codex').state,'working');assert.equal(late.actor('apps').state,'working');
  check(!late.traffic.parking,'Lane evacuation did not settle');
}

const paused=new ResortLife(meta),before=paused.diagnostics();paused.step(0);paused.step(-1);paused.step(NaN);
assert.deepEqual(paused.diagnostics(),before);paused.step(9);assert.equal(paused.clock,.1);

// The shortest furniture-clear route can leave the shoreline even when a
// longer dry route exists. Keep the real coastal shape and physical clearance.
const coastMeta={ground:{ellipse:[7.2,5.5],plateauRadius:.72,height:.43,slope:2.35,coastPerturb:[.045,.035,.4]},
  navigation:{clearance:.32,obstacles:[{name:'coastal tea table',bounds:[1.825,-3.775,2.91,-3.125]}]},
  activities:{minimumGroundHeight:.1}};
const coastal=Object.create(ResortLife.prototype);coastal.meta=coastMeta;coastal.layout=coastMeta.activities;
const from=[3.3,-2.66,groundHeight(3.3,-2.66,coastMeta)],to=[2.35,-4.27,groundHeight(2.35,-4.27,coastMeta)];
const originalRoute=route(from,to,coastMeta);
let previous=from,wet=false;
for(const next of originalRoute){wet||=!coastal.drySegment(previous,next);previous=next;}
check(wet,'Coastal regression no longer reproduces the original wet shortest route');
const dry=coastal.checkedRoute(from,to,{radius:.32});previous=from;
for(const next of dry){check(coastal.drySegment(previous,next),'Alternate route is wet');previous=next;}
assert.deepEqual(dry.at(-1),to);
assert.throws(()=>coastal.checkedRoute(from,[7,-5,0],{radius:.32}),/usable beach/);

// A body is a circle, so a free diagonal AABB corner must not trap a walker.
const bodyNav={...coastMeta,navigation:{clearance:.32,obstacles:[
  {name:'other body',bounds:[-.64,-.64,.64,.64],circle:{center:[0,0],radius:.64}}]}};
const diagonal=[.5,.5,.43],beyond=[-1,.8,.43];
assert.throws(()=>route(diagonal,beyond,bodyNav),/inside furniture/);
const around=coastal.checkedRoute(diagonal,beyond,{radius:.32},bodyNav);previous=diagonal;
for(const next of around){
  const dx=next[0]-previous[0],dy=next[1]-previous[1],d=dx*dx+dy*dy;
  const t=d?Math.max(0,Math.min(1,(-previous[0]*dx-previous[1]*dy)/d)):0;
  check(Math.hypot(previous[0]+dx*t,previous[1]+dy*t)>=.64,'Circular detour reduced body clearance');previous=next;
}
assert.deepEqual(around.at(-1),beyond);
console.log(`PASS ${assertions} physical checks across ${samples} frames: all3 sit/scratch/brew, shared-prop reservations, crossing routes, interruptions, blocked endpoint and pause`);
