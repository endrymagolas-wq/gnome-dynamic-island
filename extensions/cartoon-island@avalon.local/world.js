/** Shared 3D island model. Coordinates are ground-plane x/z; y comes from terrain. */
export const STATES=['starting','editing','testing','failed','permission','done','working','browsing','idle'];
export const CAMERA={yaw:.48,pitch:.72};
export function terrainHeight(x,z){
    const r=Math.hypot(x/3.1,z/2.25);
    if(r>=1)return 0;
    if(r>.85)return .06+(1-r)*.8;
    return .32+.18*Math.sin(x*.9+1)*Math.cos(z*.8)+.3*Math.exp(-((x+1.1)**2+(z+1.1)**2)*1.3);
}
const TARGETS={permission:{x:2.52,z:.35},testing:{x:1.58,z:.7},browsing:{x:-1,z:-1.15},done:{x:-1.4,z:1.06},idle:{x:-1.4,z:1.06},desk:{x:-.68,z:.4}};
export class IslandWorld {
    constructor(){this.state='idle';this.source='desktop';this.floors=0;this.x=-1.4;this.z=1.06;this.t=0;this.changed=0;this.until=0;this.path=[];this.motion=true;this.heading=0;}
    target(){return TARGETS[this.state]??TARGETS.desk;}
    present(state,now,source='claude'){
        if(!STATES.includes(state)||!Number.isFinite(now))return false;
        if(state==='starting'){this.floors=0;this.x=-1.4;this.z=1.06;}
        if(state==='editing')this.floors=Math.min(4,this.floors+1);
        const old=this.target();this.state=state;this.source=source;this.changed=now;
        this.until=source==='claude'?now+(state==='done'?20:180):0;
        const target=this.target();
        // Keep the worker on clear paths, away from the desk and house footprint.
        if(old!==target||state==='starting'){
            if(this.z<-.5)this.path=[{x:-1.9,z:-.6},{x:-1.75,z:.7}];else this.path=[];
            if(state==='browsing')this.path.push({x:-1.75,z:.7},{x:-1.9,z:-.6});
            else if(this.x>.4||target.x>.4)this.path.push({x:.12,z:.94});
            this.path.push({...target});
        }
        return true;
    }
    step(now,dt,motion=true){
        if(this.until&&now>=this.until){this.present('idle',now,'desktop');}
        this.motion=motion;this.t=motion?now:0;
        if(!motion){Object.assign(this,this.target());this.path=[];return;}
        let budget=Math.max(0,Math.min(dt,.2))*.85;
        while(this.path.length&&budget>0){const p=this.path[0],dx=p.x-this.x,dz=p.z-this.z,d=Math.hypot(dx,dz);
            if(d<.001){this.path.shift();continue;}
            this.heading=Math.atan2(dx,dz);
            const step=Math.min(d,budget);this.x+=dx/d*step;this.z+=dz/d*step;budget-=step;
            if(step===d)this.path.shift();
        }
    }
}
export function applicationState(id){
    if(/code|codium|claude|codex|gedit|text.?editor|jetbrains|idea|pycharm|builder|sublime|emacs|antigravity|terminal|kitty|alacritty|wezterm|konsole|tilix|ghostty/i.test(id))return 'working';
    if(/firefox|chrom|brave|browser|vivaldi|epiphany/i.test(id))return 'browsing';
    return 'idle';
}
