/** Shared wallpaper model and renderer; also used by the browser preview. */
export const STATES = ['starting','editing','testing','failed','permission','done','working','browsing','idle'];
export class IslandWorld {
    constructor() {this.state='idle';this.source='desktop';this.floors=0;this.x=350;this.t=0;this.changed=0;this.until=0;}
    target() {return this.state==='permission'?760:this.state==='testing'?620:this.state==='browsing'?370:this.state==='done'||this.state==='idle'?350:465;}
    present(state, now, source='claude') {
        if (!STATES.includes(state) || !Number.isFinite(now)) return false;
        if(state==='starting'){this.floors=0;this.x=350;}
        if(state==='editing')this.floors=Math.min(4,this.floors+1);
        this.state=state;this.source=source;this.changed=now;
        this.until=source==='claude'?now+(state==='done'?20:180):0;
        return true;
    }
    step(now, dt, motion=true) {
        if(this.until && now>=this.until){this.state='idle';this.source='desktop';this.until=0;}
        this.motion=motion;this.t=motion?now:0;
        const target=this.target();
        if(motion)this.x+=Math.sign(target-this.x)*Math.min(Math.abs(target-this.x),Math.max(0,Math.min(dt,.2))*100);
        else this.x=target;
    }
}
export function applicationState(id) {
    if(/code|codium|claude|codex|gedit|text.?editor|jetbrains|idea|pycharm|builder|sublime|emacs|antigravity/i.test(id))return 'working';
    if(/firefox|chrom|brave|browser|vivaldi|epiphany/i.test(id))return 'browsing';
    if(/terminal|kitty|alacritty|wezterm|konsole|tilix|ghostty/i.test(id))return 'working';
    return 'idle';
}

// Canvas-style drawing interface, supported by Cairo in GNOME and HTML canvas.
export function drawWorld(c, world, width, height) {
    c.save();c.scale(width/1000,height/650);
    const t=world.t;
    const ellipse=(x,y,rx,ry,color)=>{c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fillStyle=color;c.fill();};
    const line=(points,color,w=3)=>{c.beginPath();c.moveTo(...points[0]);for(const p of points.slice(1))c.lineTo(...p);c.strokeStyle=color;c.lineWidth=w;c.stroke();};
    const poly=(points,color)=>{c.beginPath();c.moveTo(...points[0]);for(const p of points.slice(1))c.lineTo(...p);c.closePath();c.fillStyle=color;c.fill();};
    const box=(x,y,w,h,color,r=0)=>{c.beginPath();c.roundRect(x,y,w,h,r);c.fillStyle=color;c.fill();};
    const text=(s,x,y,size,color)=>{c.fillStyle=color;c.font=`${size}px Sans`;c.fillText(s,x,y);};
    // Warm storybook sky and a turquoise ocean, drawn without external assets.
    box(0,0,1000,650,'#aee3ef');box(0,260,1000,390,'#66bfcb');box(0,440,1000,210,'#4eabbf');
    ellipse(816,106,47,47,'#fff2b8');ellipse(800,100,56,56,'#fff2b830');
    const cloud=(x,y)=>{ellipse(x,y,45,17,'#f7fbeb');ellipse(x-20,y-6,20,18,'#f7fbeb');ellipse(x+9,y-13,24,23,'#f7fbeb');};
    cloud(172+Math.sin(t*.04)*12,112);cloud(587+Math.sin(t*.06)*18,156);cloud(925,198);
    for(let i=0;i<15;i++){const x=35+(i*137)%930;const y=286+(i*53)%320;const shift=Math.sin(t*.8+i)*10;
        line([[x+shift,y],[x+25+shift,y]],'#a5dfdf',2);}
    // Waterline, chunky earth cliffs and the island's grassy top.
    ellipse(508,524,350,56,'#389bb0');ellipse(508,517,327,43,'#a5e1dc');
    poly([[197,394],[250,476],[380,528],[599,532],[750,490],[818,398]],'#b88058');
    poly([[250,419],[280,488],[380,528],[386,444]],'#966749');
    poly([[591,448],[599,532],[750,490],[774,418]],'#a56d4c');
    line([[310,459],[319,488]],'#c69868',5);line([[688,459],[681,494]],'#c69868',5);
    ellipse(506,397,310,99,'#efd39b');ellipse(506,382,285,84,'#83b967');ellipse(507,369,261,67,'#9bcc79');
    // Winding sandy path joining the desk, house and lookout.
    line([[338,407],[425,416],[518,407],[625,404],[761,410]],'#dfc992',21);
    line([[338,405],[425,414],[518,405],[625,402],[761,408]],'#eedbb0',14);
    // Small palms with rounded cartoon leaves.
    for(const [x,y,k] of [[266,352,1],[713,328,.8],[795,388,.7]]){
        line([[x,y+40*k],[x+8*k,y-31*k],[x+3*k,y-63*k]],'#b58454',11*k);
        for(const a of [-2.7,-2,-1.2,-.5,.2]){
            const ex=x+Math.cos(a)*51*k,ey=y-63*k+Math.sin(a)*20*k;
            line([[x+3*k,y-63*k],[ex,ey]],'#4c975a',15*k);
        }
    }
    // Little shrubs, flowers and shoreline pebbles.
    for(const [x,y] of [[306,375],[652,354],[456,333]]){ellipse(x,y,18,11,'#64a55e');ellipse(x+12,y-4,12,13,'#73b66a');}
    for(const [x,y] of [[295,400],[673,383],[419,365],[732,433]]){line([[x,y],[x,y-10]],'#59985a',2);ellipse(x,y-12,4,4,'#ffe3a1');}
    ellipse(225,433,12,6,'#d4bb8e');ellipse(791,443,18,8,'#d4bb8e');
    // Desk, laptop, chair and a plant.
    box(429,372,103,10,'#bc8050',4);line([[438,382],[435,413]],'#8e6145',7);line([[522,382],[526,410]],'#8e6145',7);
    box(483,338,38,30,'#405978',4);box(487,342,30,22,'#b3eafa',2);box(478,368,49,4,'#57728e',2);
    line([[408,382],[411,416]],'#9a6b50',5);box(403,364,22,23,'#d5a971',4);box(402,385,33,6,'#b78152',3);
    box(440,358,13,14,'#e2ac86',3);ellipse(446,352,9,11,'#64a569');
    // The building grows by one floor per actual edit hook.
    let floors=world.floors;
    if(world.state==='editing' && floors && world.motion!==false)floors=floors-1+Math.min(1,Math.max(0,(world.t-world.changed)/.8));
    const bh=26+floors*22,top=407-bh;
    box(568,top,70,bh,'#f6e0ba',5);poly([[563,top+3],[603,top-23],[643,top+3]],'#dd886d');
    line([[562,409],[644,409]],'#af916e',5);box(593,386,16,21,'#b18a67',3);
    for(let i=0;i<Math.floor(floors);i++){box(579,top+10+i*22,12,13,'#74b8c8',2);box(614,top+10+i*22,12,13,'#74b8c8',2);}
    if(world.state==='editing'){
        line([[653,409],[653,top-15]],'#b7a079',4);line([[650,top-15],[664,top-15]],'#b7a079',4);
        text('+',657,top-23,22,'#fff6d4');
    }
    // A tiny seated reader/coffee corner.
    box(323,410,57,8,'#b68b65',3);line([[329,418],[326,433]],'#9b7456',5);line([[374,418],[377,433]],'#9b7456',5);
    // Worker: rounded face, hair, little shirt and shorts, articulated arms.
    const x=world.x,y=world.state==='idle'||world.state==='done'||world.state==='browsing'?407:403;
    const walking=Math.abs(x-world.target())>2;
    const bob=walking?Math.sin(t*10)*2:0;
    const seated=['done','idle','browsing'].includes(world.state)&&!walking;
    ellipse(x,y+13,15,4,'#729958');
    line([[x-4,y-3],[x-8+(walking?Math.sin(t*10)*5:0),y+12]],'#4a5b70',6);
    line([[x+4,y-3],[x+(seated?15:9)-(walking?Math.sin(t*10)*5:0),y+(seated?3:12)]],'#4a5b70',6);
    box(x-10,y-29+bob,20,29,'#eeae64',7);box(x-9,y-5,18,7,'#5e7892',3);
    ellipse(x,y-42+bob,13,15,'#ffe0b5');ellipse(x-4,y-51+bob,11,7,'#695444');
    ellipse(x+4,y-42+bob,1.7,2,'#4f4c49');line([[x+2,y-34+bob],[x+7,y-35+bob]],'#b68063',1.5);
    let arm=[[x+8,y-22],[x+18,y-13]];
    if(world.state==='permission')arm=[[x+8,y-22],[x+17,y-35],[x+16+Math.sin(t*9)*5,y-56]];
    if(world.state==='editing')arm=[[x+8,y-22],[x+18,y-18+Math.sin(t*15)*3]];
    if(world.state==='testing')arm=[[x-8,y-22],[x-21,y-27]];
    if(seated)arm=[[x+8,y-22],[x+21,y-27]];
    line(arm,'#ffe0b5',6);line([[x-8,y-23],[x-13,y-9]],'#ffe0b5',6);
    if(world.state==='testing'){ellipse(x-26,y-31,9,9,'#c6f0ea');line([[x-21,y-24],[x-14,y-17]],'#7d6e57',4);}
    if(seated && world.state!=='browsing'){
        box(x+18,y-35,11,13,'#fff5db',3);line([[x+29,y-32],[x+33,y-32],[x+33,y-26],[x+29,y-26]],'#fff5db',2);
        line([[x+20,y-39],[x+23+Math.sin(t*3)*2,y-47]],'#f8efda',2);
    }
    if(seated && world.state==='browsing')poly([[x+13,y-31],[x+26,y-34],[x+39,y-29],[x+37,y-14],[x+24,y-18],[x+12,y-15]],'#fff4d5');
    // Soft smoke and a speech bubble for failure / attention.
    if(world.state==='failed')for(let i=0;i<5;i++){
        const rise=(t*18+i*12)%65;ellipse(603+Math.sin(t+i)*11,top-15-rise,8+i*2,10+i*2,'#87949e');}
    if(world.state==='failed'||world.state==='permission'){
        const bx=world.state==='permission'?690:422,by=world.state==='permission'?300:279;
        box(bx,by,120,42,'#fff7df',15);poly([[bx+28,by+40],[bx+34,by+53],[bx+48,by+40]],'#fff7df');
        text(world.state==='failed'?'блять…':'Гей! Дозвіл?',bx+13,by+27,world.state==='failed'?19:15,'#685e52');
    }
    // Birds and quiet storytelling captions.
    for(const [x,y] of [[372,177],[400,189]]){const wing=Math.sin(t*3)*3;line([[x-7,y-wing],[x,y],[x+7,y-wing]],'#5b8995',2);}
    const labels={starting:'До роботи!',editing:'Будуємо потроху',testing:'Перевіряю, чи все тримається',failed:'Щось пішло не так…',permission:'Потрібна твоя відповідь',done:'Готово. Час на каву',working:'Працюємо',browsing:'Трохи досліджень',idle:'Спокійний день на острові'};
    text(labels[world.state],42,602,18,'#e3f5ec');
    c.restore();
}
