/** Layout registration for the baked resort plate (1536 × 1024). */
export const VIEW={width:1000,height:2000/3};
const CY=Math.cos(.48),SY=Math.sin(.48);
export function groundPoint(px,py){
    const a=(px-500)/100,b=(py-300)/65;
    return {x:CY*a+SY*b,z:-SY*a+CY*b};
}
export function projectGround(x,z){return {x:500+(CY*x-SY*z)*100,y:300+(SY*x+CY*z)*65};}
export const TARGETS={permission:groundPoint(744,434),testing:groundPoint(628,337),browsing:groundPoint(429,254),done:groundPoint(371,366),idle:groundPoint(371,366),desk:groundPoint(458,319)};
export const ATLAS={width:1280,height:2084,cellWidth:80,cellHeight:100,anchorX:40,anchorY:88,effectsY:1700,effectWidth:160,effectHeight:128};
export const POSES=['idle','starting','editing','testing','failed','permission','done','browsing','working'];
export function characterFrame(world,now){
    const moving=world.path.length>0,animate=world.motion;
    const frame=animate?Math.floor(now*12)%8:0;
    const direction=((Math.round(world.heading/(Math.PI*2)*8)%8)+8)%8;
    const row=moving?direction:8+Math.max(0,POSES.indexOf(world.state));
    return {x:frame*80,y:row*100,width:80,height:100};
}
export function needsFrames(world,water=false){return world.motion&&(water||world.path.length>0||(world.source==='claude'&&['editing','failed','permission'].includes(world.state)));}
export function fitPlate(width,height){const scale=Math.min(width/VIEW.width,height/VIEW.height);return {scale,x:(width-VIEW.width*scale)/2,y:(height-VIEW.height*scale)/2};}
export function animationBounds(){return {x:280,y:210,width:530,height:290};}
/** Rectangle subtraction supports coverage by more than one opaque window. */
export function coveredByWindows(region,windows){
    let uncovered=[region];
    for(const w of windows){const next=[];
        for(const r of uncovered){const x=Math.max(r.x,w.x),y=Math.max(r.y,w.y),right=Math.min(r.x+r.width,w.x+w.width),bottom=Math.min(r.y+r.height,w.y+w.height);
            if(right<=x||bottom<=y){next.push(r);continue;}
            if(y>r.y)next.push({x:r.x,y:r.y,width:r.width,height:y-r.y});
            if(bottom<r.y+r.height)next.push({x:r.x,y:bottom,width:r.width,height:r.y+r.height-bottom});
            if(x>r.x)next.push({x:r.x,y,width:x-r.x,height:bottom-y});
            if(right<r.x+r.width)next.push({x:right,y,width:r.x+r.width-right,height:bottom-y});
        }
        uncovered=next;if(!uncovered.length)return true;
    }
    return false;
}
