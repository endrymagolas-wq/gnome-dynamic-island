// Deliberate outward pressure, never stationary hover or a single fast impact.
export class EdgeIntent {
    constructor() { this.reset(); }
    reset() { this.started=null;this.last=null;this.events=[];this.triggered=false; }
    push({now,dx,dy,blocked=false}) {
        if(blocked){this.reset();return false;}
        if(this.triggered)return false;
        const across=Math.abs(dy),along=Math.abs(dx);
        if(!Number.isFinite(now)||!Number.isFinite(across)||!Number.isFinite(along))return false;
        if(across<=0||along>across){this.reset();return false;}
        if(this.started===null||this.last===null||now-this.last>1000||now<this.last){
            this.started=now;this.last=now;this.events=[];return false;
        }
        this.last=now;
        if(now-this.started<120)return false;
        this.events=this.events.filter(([time])=>now-time<=1000);
        this.events.push([now,Math.min(15,across)]);
        if(this.events.reduce((sum,[,distance])=>sum+distance,0)<80)return false;
        this.triggered=true;return true;
    }
}

// Leave the corners, island and passages to an adjacent monitor unobstructed.
export function edgeSegments(primary,monitors) {
    const center=primary.x+primary.width/2;
    let spans=[[primary.x+32,center-160],[center+160,primary.x+primary.width-32]];
    for(const monitor of monitors){
        if(monitor===primary||monitor.y+monitor.height!==primary.y)continue;
        const left=monitor.x,right=monitor.x+monitor.width;
        spans=spans.flatMap(([a,b])=>right<=a||left>=b?[[a,b]]:[[a,Math.min(b,left)],[Math.max(a,right),b]]);
    }
    return spans.map(([a,b])=>[Math.ceil(a),Math.floor(b)]).filter(([a,b])=>b-a>=16);
}

// The dedicated island strip is explicit navigation intent. Elsewhere preserve
// a window's draggable titlebar; empty desktop does not need extra pressure.
export function hoverIntent({edge,onIsland,titlebar,dragging,blocked,shift}) {
    return Boolean(edge&&!dragging&&!blocked&&(onIsland||!titlebar||shift));
}
