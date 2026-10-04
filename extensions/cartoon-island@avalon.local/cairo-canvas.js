import Cairo from 'cairo';
/** Small adapter so the very same scene renders in GNOME and in the preview. */
export class CairoCanvas {
    constructor(cr){this.cr=cr;this.fillStyle='#000000';this.strokeStyle='#000000';this.lineWidth=1;this.font='16px Sans';}
    color(value){if(value.startsWith('rgb(')){const rgb=value.slice(4,-1).split(',').map(Number);this.cr.setSourceRGBA(rgb[0]/255,rgb[1]/255,rgb[2]/255,1);return;}const s=value.replace('#','');const n=parseInt(s.slice(0,6),16);this.cr.setSourceRGBA((n>>16&255)/255,(n>>8&255)/255,(n&255)/255,s.length===8?parseInt(s.slice(6),16)/255:1);}
    save(){this.cr.save();} restore(){this.cr.restore();} scale(x,y){this.cr.scale(x,y);}
    beginPath(){this.cr.newPath();} moveTo(x,y){this.cr.moveTo(x,y);} lineTo(x,y){this.cr.lineTo(x,y);} closePath(){this.cr.closePath();}
    ellipse(x,y,rx,ry){this.cr.save();this.cr.translate(x,y);this.cr.scale(rx,ry);this.cr.arc(0,0,1,0,Math.PI*2);this.cr.restore();}
    roundRect(x,y,w,h,r){r=Math.min(r,w/2,h/2);if(!r){this.cr.rectangle(x,y,w,h);return;}for(const [cx,cy,a] of [[x+w-r,y+r,-Math.PI/2],[x+w-r,y+h-r,0],[x+r,y+h-r,Math.PI/2],[x+r,y+r,Math.PI]])this.cr.arc(cx,cy,r,a,a+Math.PI/2);this.cr.closePath();}
    fill(){this.color(this.fillStyle);this.cr.fill();}
    stroke(){this.color(this.strokeStyle);this.cr.setLineWidth(this.lineWidth);this.cr.setLineCap(Cairo.LineCap.ROUND);this.cr.setLineJoin(Cairo.LineJoin.ROUND);this.cr.stroke();}
    fillText(text,x,y){this.color(this.fillStyle);this.cr.selectFontFace('Sans',Cairo.FontSlant.NORMAL,Cairo.FontWeight.NORMAL);this.cr.setFontSize(parseFloat(this.font));this.cr.moveTo(x,y);this.cr.showText(text);}
}
