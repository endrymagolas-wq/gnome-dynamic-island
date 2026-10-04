// Red bass, amber low mids, pearl upper mids, blue highs.
export class Motion {
    constructor(){
        this.bands=[0,0,0,0];this.velocity=[0,0,0,0];
        this.phase=[.7,2.1,4.0,5.6];this.reference=.16;this.level=0;
        this.weights=[1,1,1,1];this.softness=1.8;this.mode='auto';this.drive=0;this.bpm=85;this.palette=0;this.intensity=.7;
    }
    step(input,dt){
        dt=Math.max(0,Math.min(.05,dt));
        const fresh=Number.isFinite(input.time)&&Date.now()/1000-input.time<1;
        const audible=fresh&&input.level>.006;
        if(audible)this.reference+=(input.level-this.reference)*(1-Math.exp(-dt/12));
        const scene=input.scene||{};
        const measured=Number.isFinite(scene.drive)?Math.max(0,Math.min(1,scene.drive)):.15;
        const recommended={calm:.05,flow:.45,drive:.9}[scene.profile];
        let drive=scene.source==='laya' && recommended!==undefined?measured*.3+recommended*.7:measured;
        if(this.mode==='calm')drive=0;else if(this.mode==='drive')drive=1;
        if(!audible)drive=0;
        this.drive+=(drive-this.drive)*(1-Math.exp(-dt/4));
        this.softness=1.8-this.drive*1.1;
        this.intensity=.7+this.drive*.85;
        const colorTarget=Math.max(0,Math.min(1,(this.drive-.32)/.48));
        this.palette+=(colorTarget-this.palette)*(1-Math.exp(-dt/5));
        let bpm=Number.isFinite(scene.bpm)&&scene.confidence>.2?scene.bpm:(scene.texture==='warm_harmonic'?75:90);
        if(this.mode==='calm')bpm=Math.min(95,bpm);
        this.bpm+=(Math.max(50,Math.min(190,bpm))-this.bpm)*(1-Math.exp(-dt/8));
        const gain=Math.min(7,.55/Math.max(.08,this.reference));
        const raw=Array.isArray(input.bands)?input.bands:[0,0,0,0];
        const attack=[.55,.85,1.2,1.8],release=[1.8,2.8,3.5,4.5];
        const slowCycles=[24,32,48,64],fastCycles=[10,16,24,40],balance=[1.15,1.1,1.3,1.45];
        for(let i=0;i<4;i++){
            const value=Number.isFinite(raw[i])?Math.max(0,raw[i]):0;
            const target=audible?(1-Math.exp(-value*gain*balance[i]))*this.weights[i]:0;
            const tau=(target>this.bands[i]?attack[i]:release[i])*this.softness;
            // Critically damped spring: position and velocity remain continuous.
            const omega=2/tau,e=Math.exp(-omega*dt),d=this.bands[i]-target;
            const t=(this.velocity[i]+omega*d)*dt;
            this.bands[i]=target+(d+t)*e;
            this.velocity[i]=(this.velocity[i]-omega*t)*e;
            const cycle=slowCycles[i]+(fastCycles[i]-slowCycles[i])*this.drive;
            this.phase[i]+=dt*(this.bpm/60)*2*Math.PI/cycle;
        }
        this.level=Math.max(...this.bands);
    }
}
