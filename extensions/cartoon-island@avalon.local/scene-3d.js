import {CAMERA,terrainHeight} from './world.js';
const TAU=Math.PI*2;
const sub=(a,b)=>a.map((v,i)=>v-b[i]);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
function triangle(list,a,b,c,color,unlit=false){list.push({v:[a,b,c],color,unlit});}
function quad(list,a,b,c,d,color,unlit=false){triangle(list,a,b,c,color,unlit);triangle(list,a,c,d,color,unlit);}
function box(list,x,y,z,w,h,d,color){
    const a=[x-w/2,y,z-d/2],b=[x+w/2,y,z-d/2],c=[x+w/2,y,z+d/2],e=[x-w/2,y,z+d/2];
    const A=[a[0],y+h,a[2]],B=[b[0],y+h,b[2]],C=[c[0],y+h,c[2]],E=[e[0],y+h,e[2]];
    quad(list,e,c,C,E,color);quad(list,b,a,A,B,color);quad(list,a,e,E,A,color);quad(list,c,b,B,C,color);quad(list,A,E,C,B,color);
}
function sphere(list,x,y,z,rx,ry,rz,color,segments=9,rings=5){
    const p=(i,j)=>{const a=i/segments*TAU,b=j/rings*Math.PI;return [x+Math.cos(a)*Math.sin(b)*rx,y+Math.cos(b)*ry,z+Math.sin(a)*Math.sin(b)*rz];};
    for(let j=0;j<rings;j++)for(let i=0;i<segments;i++)quad(list,p(i,j),p(i+1,j),p(i+1,j+1),p(i,j+1),color);
}
function cylinder(list,a,b,r,color,n=7){
    const axis=sub(b,a),len=Math.hypot(...axis);if(len<.0001)return;
    const unit=axis.map(v=>v/len),ref=Math.abs(unit[1])>.9?[1,0,0]:[0,1,0];let u=cross(unit,ref);const ul=Math.hypot(...u);u=u.map(v=>v/ul);const v=cross(unit,u);
    const p=(at,i)=>at.map((x,j)=>x+r*(u[j]*Math.cos(i/n*TAU)+v[j]*Math.sin(i/n*TAU)));
    for(let i=0;i<n;i++){quad(list,p(a,i),p(a,i+1),p(b,i+1),p(b,i),color);triangle(list,b,p(b,i),p(b,i+1),color);}
}
const island=[];
const segments=44,rings=[0,.24,.48,.69,.85,.94,1];
function radial(r,a){const wobble=1+.035*Math.sin(a*5)+.025*Math.cos(a*7);const x=Math.cos(a)*3.1*r*wobble,z=Math.sin(a)*2.25*r*wobble;return [x,terrainHeight(x,z),z];}
for(let ring=1;ring<rings.length;ring++)for(let i=0;i<segments;i++){
    const a=i/segments*TAU,b=(i+1)/segments*TAU,r=rings[ring],p=radial(rings[ring-1],a),q=radial(rings[ring-1],b),s=radial(r,b),t=radial(r,a);
    const sand=r>.85;const color=sand?[.91,.80,.56]:[.42+(i%3)*.025,.65+(ring%2)*.02,.34];
    quad(island,p,q,s,t,color);
}
// Submerged shoreline rock skirt, with shaded facets.
for(let i=0;i<segments;i++){const a=radial(1,i/segments*TAU),b=radial(1,(i+1)/segments*TAU);quad(island,a,b,[b[0]*.96,-.35,b[2]*.96],[a[0]*.96,-.35,a[2]*.96],[.66,.55,.40]);}
function staticProps(){
    const list=[...island];
    // Palms have curved 3D trunks and broad low-poly leaf blades.
    for(const [x,z,k] of [[-2,-.5,1.05],[2,-.65,.9],[-.1,-1.65,.8]]){
        const y=terrainHeight(x,z);
        cylinder(list,[x,y,z],[x+.07,y+.65*k,z-.04],.07*k,[.56,.39,.25]);
        cylinder(list,[x+.07,y+.65*k,z-.04],[x+.2,y+1.4*k,z],.055*k,[.62,.44,.28]);
        const top=[x+.2,y+1.4*k,z];
        for(let i=0;i<7;i++){const a=i/7*TAU,tip=[top[0]+Math.cos(a)*.72*k,top[1]-.25*k,top[2]+Math.sin(a)*.72*k];
            const mid=[top[0]+Math.cos(a)*.38*k,top[1]+.09*k,top[2]+Math.sin(a)*.38*k];
            const side=[Math.sin(a)*.15*k,0,-Math.cos(a)*.15*k];
            quad(list,top,mid.map((v,j)=>v+side[j]),tip,mid.map((v,j)=>v-side[j]),[.22,.49+(i%2)*.06,.30],true);
        }
        sphere(list,x+.21,y+1.34*k,z+.06,.085,.085,.085,[.46,.32,.2],7,4);
    }
    for(const [x,z,s] of [[-2.4,.4,.22],[1.8,1.1,.20],[-1.5,-1.3,.19],[.2,-.9,.16]])sphere(list,x,terrainHeight(x,z)+.06,z,s,s*.65,s,[.49,.56,.48],7,4);
    // Desk on the front terrace, feet reaching the terrain.
    const x=-.55,z=-.1,y=terrainHeight(x,z);
    box(list,x,y+.48,z,.95,.08,.46,[.67,.43,.26]);
    for(const dx of [-.39,.39])for(const dz of [-.16,.16])box(list,x+dx,y,z+dz,.055,.5,.055,[.47,.30,.21]);
    box(list,x+.17,y+.57,z-.1,.33,.25,.025,[.22,.31,.39]);box(list,x+.17,y+.6,z-.081,.28,.18,.01,[.54,.86,.91]);
    box(list,x+.17,y+.56,z+.04,.36,.02,.20,[.35,.43,.47]);
    // Bench facing the ocean; footprints remain clear for navigation.
    const bx=-1.55,bz=1.08,by=terrainHeight(bx,bz);
    box(list,bx,by+.18,bz,.58,.07,.24,[.63,.44,.28]);
    box(list,bx,by+.25,bz-.1,.58,.25,.045,[.71,.50,.31]);
    for(const dx of [-.23,.23])box(list,bx+dx,by,bz,.04,.2,.16,[.43,.3,.23]);
    // A small plank lookout at the permission edge.
    const py=terrainHeight(2.48,.35);
    for(let i=0;i<5;i++)box(list,2.51+i*.10,py,.35,.085,.04,.43,[.70,.52,.34]);
    return list;
}
const props=staticProps();
export function project(point,camera=CAMERA){
    const [x,y,z]=point,cy=Math.cos(camera.yaw),sy=Math.sin(camera.yaw),sp=Math.sin(camera.pitch),cp=Math.cos(camera.pitch);
    return {x:500+(cy*x-sy*z)*105,y:360-(-sy*sp*x+cp*y-cy*sp*z)*105,depth:sy*cp*x+sp*y+cy*cp*z};
}
function worker(list,w){
    const firstFace=list.length;
    const x=w.x,z=w.z,y=terrainHeight(x,z),walking=w.path.length>0,t=w.t;
    const seated=['done','idle','browsing'].includes(w.state)&&!walking;
    const bob=walking?Math.sin(t*10)*.014:0;
    const hip=y+(seated?.25:.32),skin=[1,.79,.58],dark=[.19,.28,.36];
    sphere(list,x,y+.012,z,.13,.015,.1,[.28,.40,.26],9,3);
    const stride=walking?Math.sin(t*10)*.08:0;
    for(const side of [-1,1]){
        const knee=[x+side*.045,hip-.11,z+(seated?.13:side*stride)];
        cylinder(list,[x+side*.045,hip,z],knee,.034,dark);
        cylinder(list,knee,[knee[0],y+.035,knee[2]+.035],.03,dark);
        box(list,knee[0],y+.02,knee[2]+.055,.08,.04,.13,[.22,.27,.28]);
    }
    box(list,x,hip,z,.17,.23,.14,[.93,.58,.29]);
    sphere(list,x,hip+.36+bob,z,.112,.125,.105,skin,10,6);
    sphere(list,x-.014,hip+.42+bob,z-.024,.11,.085,.1,[.32,.24,.20],9,4);
    sphere(list,x+.055,hip+.36,z+.09,.012,.012,.014,[.17,.19,.2],6,3);
    const shoulder=[x+.10,hip+.19,z],left=[x-.10,hip+.19,z];
    let elbow=[x+.13,hip+.06,z+.04],hand=[x+.14,hip,z+.08];
    if(w.state==='permission'&&!walking){elbow=[x+.2,hip+.3,z];hand=[x+.19+Math.sin(t*8)*.045,hip+.5,z];}
    if(w.state==='editing'&&!walking){elbow=[x+.14,hip+.12,z-.06];hand=[x+.18,hip+.12+Math.sin(t*17)*.015,z-.20];}
    if(w.state==='testing'&&!walking){elbow=[x+.16,hip+.13,z];hand=[x+.2,hip+.21,z];}
    if(seated){elbow=[x+.13,hip+.13,z+.1];hand=[x+.12,hip+.21,z+.18];}
    cylinder(list,shoulder,elbow,.035,skin);cylinder(list,elbow,hand,.028,skin);
    cylinder(list,left,[x-.12,hip+.02,z+stride],.032,skin);
    if(w.state==='testing'&&!walking){cylinder(list,hand,[hand[0],hand[1]+.09,hand[2]],.022,[.38,.33,.26]);sphere(list,hand[0],hand[1]+.13,hand[2],.065,.07,.015,[.58,.83,.84],9,4);}
    if(seated){
        if(w.state==='browsing')box(list,x+.1,hip+.21,z+.22,.22,.015,.18,[.94,.87,.68]);
        else{cylinder(list,hand,[hand[0],hand[1]+.09,hand[2]],.045,[.96,.89,.74]);sphere(list,hand[0],hand[1]+.105,hand[2],.037,.006,.037,[.35,.23,.16],8,3);}
    }
    if(walking){const cs=Math.cos(w.heading),sn=Math.sin(w.heading);
        for(let i=firstFace;i<list.length;i++)list[i].v=list[i].v.map(p=>{const dx=p[0]-x,dz=p[2]-z;return [x+cs*dx+sn*dz,p[1],z-sn*dx+cs*dz];});
    }
}
function building(list,w){
    const x=1.05,z=-.12,y=terrainHeight(x,z),growth=w.state==='editing'&&w.motion?Math.min(1,Math.max(0,(w.t-w.changed)/.8)):1;
    const floors=w.floors?Math.max(0,w.floors-1)+growth:0,h=.48+floors*.22;
    box(list,x,y,z,.74,h,.70,[.91,.83,.67]);box(list,x,y-.035,z,.85,.055,.80,[.63,.58,.47]);
    const a=[x-.43,y+h,z-.42],b=[x+.43,y+h,z-.42],c=[x+.43,y+h,z+.42],d=[x-.43,y+h,z+.42],e=[x,y+h+.3,z-.42],f=[x,y+h+.3,z+.42];
    quad(list,a,d,f,e,[.68,.34,.27]);quad(list,e,f,c,b,[.78,.40,.29]);triangle(list,d,c,f,[.88,.76,.58]);triangle(list,b,a,e,[.88,.76,.58]);
    box(list,x,y,z+.355,.17,.3,.012,[.45,.33,.24]);
    for(let i=0;i<Math.floor(floors)+1;i++)for(const dx of [-.23,.23])box(list,x+dx,y+.18+i*.22,z+.36,.11,.11,.012,[.40,.69,.74]);
    for(let i=0;i<Math.floor(floors)+1;i++)box(list,x+.376,y+.18+i*.22,z,.012,.11,.18,[.37,.62,.65]);
    if(w.state==='failed')for(let i=0;i<6;i++){const rise=(w.t*.3+i*.13)%1;sphere(list,x+Math.sin(w.t+i)*.07,y+h+.2+rise,z,.09+rise*.10,.12+rise*.09,.10,[.49+rise*.1,.54+rise*.1,.56+rise*.1],7,4);}
}
function drawShadow(c,point,rx,rz,camera){
    const points=[];for(let i=0;i<20;i++){const a=i/20*TAU;points.push(project([point[0]+Math.cos(a)*rx,point[1],point[2]+Math.sin(a)*rz],camera));}
    c.beginPath();c.moveTo(points[0].x,points[0].y);for(const p of points.slice(1))c.lineTo(p.x,p.y);c.closePath();c.fillStyle='#274b3235';c.fill();
}
export function drawWorld(c,w,width,height,camera=CAMERA){
    c.save();c.scale(width/1000,height/650);
    const list=[...props];building(list,w);worker(list,w);
    const light=[-.38,.82,.43];
    const triangles=list.map(face=>{
        const p=face.v.map(v=>project(v,camera));let n=cross(sub(face.v[1],face.v[0]),sub(face.v[2],face.v[0]));const len=Math.hypot(...n);if(len<.000001)return null;
        // Both sides of low-poly foliage are lit; geometry controls face brightness.
        n=n.map(v=>v/len);
        const view=[Math.sin(camera.yaw)*Math.cos(camera.pitch),Math.sin(camera.pitch),Math.cos(camera.yaw)*Math.cos(camera.pitch)];
        if(!face.unlit && dot(n,view)<=0)return null;
        const illumination=face.unlit?Math.abs(dot(n,light)):Math.max(0,dot(n,light));
        const brightness=.57+.43*illumination;
        const color=face.color.map(v=>Math.round(Math.min(1,v*brightness)*255));
        return {p,depth:p.reduce((s,v)=>s+v.depth,0)/3,color:`rgb(${color.join(',')})`};
    }).filter(Boolean).sort((a,b)=>a.depth-b.depth);
    for(const face of triangles){c.beginPath();c.moveTo(face.p[0].x,face.p[0].y);for(const p of face.p.slice(1))c.lineTo(p.x,p.y);c.closePath();c.fillStyle=face.color;c.fill();c.strokeStyle=face.color;c.lineWidth=.35;c.stroke();}
    // Ground-contact shadow and a small caption; no screen-space walking shortcuts.
    drawShadow(c,[w.x,terrainHeight(w.x,w.z)+.008,w.z],.14,.09,camera);
    if(w.state==='failed'||w.state==='permission'){
        const p=project([w.x,terrainHeight(w.x,w.z)+1.15,w.z],camera);
        c.beginPath();c.roundRect(p.x-48,p.y-23,110,30,10);c.fillStyle='#fff2dc';c.fill();c.fillStyle='#67503f';c.font='13px Sans';c.fillText(w.state==='failed'?'блять…':'Гей! Дозвіл?',p.x-36,p.y-3);
    }
    const labels={starting:'До роботи',editing:'Будуємо потроху',testing:'Перевіряю будинок',failed:'Щось пішло не так…',permission:'Потрібна твоя відповідь',done:'Готово. Час на каву',working:'Працюємо',browsing:'Досліджую острів',idle:'Спокійний день на острові'};
    c.fillStyle='#e1f8f2';c.font='16px Sans';c.fillText(labels[w.state],35,613);
    c.restore();
}

/** Build-time only: bake poses into a transparent sprite atlas. */
export function drawAtlasCharacter(c,state,frame,direction=null){
    const speed=state==='permission'?8:state==='editing'?17:10;
    const w={state,x:0,z:0,path:direction===null?[]:[{}],heading:direction??0,t:frame/8*Math.PI*2/speed,motion:true};
    const list=[];worker(list,w);
    const ground=project([0,terrainHeight(0,0),0]);
    c.save();c.translate(40-ground.x,88-ground.y);
    const camera=CAMERA,view=[Math.sin(camera.yaw)*Math.cos(camera.pitch),Math.sin(camera.pitch),Math.cos(camera.yaw)*Math.cos(camera.pitch)],light=[-.38,.82,.43];
    const faces=list.map(face=>{let n=cross(sub(face.v[1],face.v[0]),sub(face.v[2],face.v[0]));const len=Math.hypot(...n);if(len<.000001)return null;n=n.map(v=>v/len);if(dot(n,view)<=0)return null;const shade=.57+.43*Math.max(0,dot(n,light));const p=face.v.map(v=>project(v));return {p,depth:p.reduce((s,v)=>s+v.depth,0)/3,color:`rgb(${face.color.map(v=>Math.round(v*shade*255)).join(',')})`};}).filter(Boolean).sort((a,b)=>a.depth-b.depth);
    for(const f of faces){c.beginPath();c.moveTo(f.p[0].x,f.p[0].y);for(const p of f.p.slice(1))c.lineTo(p.x,p.y);c.closePath();c.fillStyle=f.color;c.fill();c.strokeStyle=f.color;c.lineWidth=.3;c.stroke();}
    c.restore();
}

export function drawAtlasCabana(c,stage){
    const list=[],y=terrainHeight(0,0),color=[.93,.87,.72];
    box(list,0,y,0,.95,.04,.82,[.72,.64,.48]);
    if(stage>0)for(const x of [-.35,.35])for(const z of [-.3,.3])box(list,x,y,z,.045,.62,.045,[.64,.47,.29]);
    if(stage>1){
        box(list,0,y+.04,0,.74,.61,.63,color);
        box(list,-.13,y+.04,.321,.17,.36,.012,[.49,.35,.22]);box(list,.20,y+.31,.323,.16,.17,.012,[.38,.66,.70]);
        box(list,.378,y+.28,.03,.013,.19,.20,[.35,.63,.66]);
    }
    if(stage>2){
        const top=y+.67,a=[-.46,top,-.40],b=[.46,top,-.40],d=[-.46,top,.4],e=[0,top+.26,-.4],f=[0,top+.26,.4],right=[.46,top,.4];
        quad(list,a,d,f,e,[.69,.35,.23]);quad(list,e,f,right,b,[.77,.41,.26]);triangle(list,d,right,f,color);triangle(list,b,a,e,color);
        // Individual terracotta tile strips are baked once, never animated meshes.
        for(let side of [-1,1])for(let i=0;i<5;i++)for(let j=0;j<8;j++){
            const x1=side*(i*.09),x2=side*((i+1)*.09),z1=-.395+j*.10,z2=z1+.095,yy1=top+.26-Math.abs(x1)/.46*.26+.006,yy2=top+.26-Math.abs(x2)/.46*.26+.006;
            const points=[[x1,yy1,z1],[x1,yy1,z2],[x2,yy2,z2],[x2,yy2,z1]];
            if(side<0)points.reverse();quad(list,...points,[.71+(j%3)*.025,.36+(i%2)*.02,.23]);
        }
    }
    if(stage>3){
        box(list,0,y+.03,.49,.82,.045,.24,[.68,.49,.31]);
        for(const x of [-.29,.29]){cylinder(list,[x,y+.04,.50],[x,y+.14,.50],.075,[.69,.43,.29]);sphere(list,x,y+.19,.50,.09,.13,.09,[.32,.53,.26],8,5);}
    }
    const ground=project([0,y,0]),view=[Math.sin(CAMERA.yaw)*Math.cos(CAMERA.pitch),Math.sin(CAMERA.pitch),Math.cos(CAMERA.yaw)*Math.cos(CAMERA.pitch)],light=[-.38,.82,.43];
    c.save();c.translate(80-ground.x,116-ground.y);
    const faces=list.map(face=>{let n=cross(sub(face.v[1],face.v[0]),sub(face.v[2],face.v[0]));const len=Math.hypot(...n);if(len<.000001)return null;n=n.map(v=>v/len);if(dot(n,view)<=0)return null;const shade=.62+.38*Math.max(0,dot(n,light)),p=face.v.map(v=>project(v));return {p,depth:p.reduce((s,v)=>s+v.depth,0)/3,color:`rgb(${face.color.map(v=>Math.round(v*shade*255)).join(',')})`};}).filter(Boolean).sort((a,b)=>a.depth-b.depth);
    for(const f of faces){c.beginPath();c.moveTo(f.p[0].x,f.p[0].y);for(const p of f.p.slice(1))c.lineTo(p.x,p.y);c.closePath();c.fillStyle=f.color;c.fill();c.strokeStyle=f.color;c.lineWidth=.3;c.stroke();}
    c.restore();
}
