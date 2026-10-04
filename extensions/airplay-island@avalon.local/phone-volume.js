import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// One renderer, with separate phone and keyboard lifetimes and input behavior.
export class PhoneVolume {
    constructor(owner,system=false) {
        this.owner=owner;this.system=system;this.active=false;this.level=0;this.fill=0;
        this.actor=new St.DrawingArea({reactive:system,width:system?38:112,height:system?132:12,
            visible:false,style_class:'ai-phone-volume',accessible_name:system?'Системна гучність':'Гучність AirPlay'});
        this.actor.connect('repaint',area=>this.draw(area));
        this.actor.set_pivot_point(.5,system?1:.5);
        Main.layoutManager.addChrome(this.actor,{affectsStruts:false,affectsInputRegion:system,trackFullscreen:false});
        if(system) {
            this.actor.connect('button-press-event',(_a,e)=>{
                if(e.get_button()!==1)return Clutter.EVENT_PROPAGATE;
                this.dragging=true;this.grab=global.stage.grab(this.actor);
                this.changeAt(e);return Clutter.EVENT_STOP;
            });
            this.actor.connect('motion-event',(_a,e)=>{
                if(!this.dragging)return Clutter.EVENT_PROPAGATE;
                this.changeAt(e);return Clutter.EVENT_STOP;
            });
            this.actor.connect('button-release-event',()=>{
                if(!this.dragging)return Clutter.EVENT_PROPAGATE;
                this.release();this.show(this.level);return Clutter.EVENT_STOP;
            });
            this.actor.connect('scroll-event',(_a,e)=>{
                const dir=e.get_scroll_direction();let delta=0;
                if(dir===Clutter.ScrollDirection.UP)delta=.03;
                else if(dir===Clutter.ScrollDirection.DOWN)delta=-.03;
                else if(dir===Clutter.ScrollDirection.SMOOTH)delta=-e.get_scroll_delta()[1]*.03;
                this.writeLevel(Math.max(0,Math.min(1,this.level+delta)));return Clutter.EVENT_STOP;
            });
        }
    }
    get duration(){return this.owner._settings.get_boolean('enable-animations')?(this.system?280:160):0;}
    draw(area) {
        const cr=area.get_context();const [w,h]=area.get_surface_size();const r=Math.min(w,h)/2;
        const path=()=>{
            cr.newPath();cr.arc(w-r,r,r,-Math.PI/2,0);cr.arc(w-r,h-r,r,0,Math.PI/2);
            cr.arc(r,h-r,r,Math.PI/2,Math.PI);cr.arc(r,r,r,Math.PI,Math.PI*1.5);cr.closePath();
        };
        path();cr.setSourceRGBA(.45,.48,.52,.48);cr.fillPreserve();
        cr.setSourceRGBA(1,1,1,.24);cr.setLineWidth(.8);cr.stroke();
        cr.save();path();cr.clip();
        if(this.system)cr.rectangle(0,h*(1-this.fill),w,h*this.fill);
        else cr.rectangle(0,0,w*this.fill,h);
        cr.setSourceRGBA(1,1,1,.96);cr.fill();cr.restore();
        if(this.system){
            const blend=Math.max(0,Math.min(1,(this.fill-.16)/.12));
            cr.setSourceRGBA(.96-.76*blend,.96-.75*blend,.98-.75*blend,.95);
            cr.save();cr.translate(11,h-30);cr.scale(1.25,1.25);
            cr.newPath();cr.moveTo(0,3);cr.lineTo(3,3);cr.lineTo(7,0);cr.lineTo(7,12);
            cr.lineTo(3,9);cr.lineTo(0,9);cr.closePath();cr.fill();
            cr.setLineWidth(1.2);cr.setLineCap(1);cr.arc(7,6,4,-.8,.8);cr.stroke();cr.arc(7,6,6,-.75,.75);cr.stroke();
            cr.restore();
        }
        cr.$dispose();
    }
    position() {
        const m=Main.layoutManager.primaryMonitor;
        if(!m||Main.sessionMode.isLocked||(!this.system&&this.owner._floating.fullscreen)){this.hide(true);return;}
        if(this.system){this.actor.set_position(m.x+24,Math.round(m.y+m.height/2-66));return;}
        let y=m.y+36;const card=this.owner._indicator.menu.actor;
        if(this.owner._indicator.menu.isOpen){const [,top]=card.get_transformed_position();const [,height]=card.get_transformed_size();if(Number.isFinite(top+height))y=top+height+8;}
        this.actor.set_position(Math.round(m.x+m.width/2-56),Math.round(y));
    }
    changeAt(event) {
        const [,y]=event.get_coords();const top=this.actor.y;
        const raw=1-(y-top)/this.actor.height;this.writeLevel(Math.max(0,Math.min(1,raw)));
        const excess=Math.min(.07,Math.abs(raw-Math.max(0,Math.min(1,raw)))*.14);
        this.actor.ease({scale_x:1.025-excess*.6,scale_y:1+excess,duration:this.duration?180:0,
            mode:Clutter.AnimationMode.EASE_OUT_CUBIC});
    }
    writeLevel(level){this.onChange?.(level);this.show(level);}
    release(){this.dragging=false;this.grab?.dismiss();this.grab=null;}
    show(value) {
        if(!Number.isFinite(value)||Main.sessionMode.isLocked||(!this.system&&this.owner._floating.fullscreen))return;
        const increasing=value>this.lastValue;this.lastValue=value;
        this.level=this.system?Math.max(0,Math.min(1,value)):value<=-30?0:Math.max(0,Math.min(1,(value+30)/30));
        if(this.hideTimer)GLib.Source.remove(this.hideTimer);
        if(!this.system&&this.fillTimer){GLib.Source.remove(this.fillTimer);this.fillTimer=0;}
        if(!this.active)this.actor.remove_all_transitions();
        if(!this.actor.visible){this.actor.opacity=0;this.actor.scale_x=.92;this.actor.scale_y=.92;}
        this.recentUntil=GLib.get_monotonic_time()+3000000;this.active=true;this.position();this.actor.show();
        if(!this.dragging)this.actor.ease({opacity:255,scale_x:!this.system&&increasing?1.06:1,
            scale_y:this.system&&increasing?1.025:1,duration:this.duration,mode:Clutter.AnimationMode.EASE_OUT_CUBIC,
            onComplete:()=>{if(this.active&&!this.dragging)this.actor.ease({scale_x:1,scale_y:1,duration:this.duration?(this.system?380:this.duration+80):0,mode:Clutter.AnimationMode.EASE_OUT_CUBIC});}});
        else this.actor.opacity=255;
        if(this.system)this.animateFill();
        else {
            const start=this.fill,target=this.level,began=GLib.get_monotonic_time();
            if(!this.duration){this.fill=target;this.actor.queue_repaint();}
            else this.fillTimer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,16,()=>{
                const t=Math.min(1,(GLib.get_monotonic_time()-began)/(this.duration*1000));
                this.fill=start+(target-start)*(1-Math.pow(1-t,3));this.actor.queue_repaint();
                if(t===1){this.fillTimer=0;return GLib.SOURCE_REMOVE;}return GLib.SOURCE_CONTINUE;
            });
        }
        this.actor.accessible_name=`${this.system?'Системна гучність':'Гучність AirPlay'} · ${Math.round(this.level*100)}%`;
        if(!this.positionTimer)this.positionTimer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,80,()=>{this.position();return GLib.SOURCE_CONTINUE;});
        this.hideTimer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,this.system?1800:1400,()=>{
            if(this.dragging)return GLib.SOURCE_CONTINUE;
            this.hideTimer=0;this.hide();return GLib.SOURCE_REMOVE;
        });
    }
    animateFill() {
        if(!this.duration){
            if(this.fillTimer)GLib.Source.remove(this.fillTimer);this.fillTimer=0;
            this.fill=this.level;this.velocity=0;this.actor.queue_repaint();return;
        }
        // Retarget the existing spring without discarding its position or velocity.
        if(this.fillTimer)return;
        this.velocity??=0;let last=GLib.get_monotonic_time();
        this.fillTimer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,16,()=>{
            const now=GLib.get_monotonic_time(),dt=Math.min(.05,(now-last)/1000000);last=now;
            const omega=this.dragging?24:16,error=this.fill-this.level;
            const c=this.velocity+omega*error,decay=Math.exp(-omega*dt);
            this.fill=Math.max(0,Math.min(1,this.level+(error+c*dt)*decay));
            this.velocity=(this.velocity-omega*c*dt)*decay;this.actor.queue_repaint();
            if(Math.abs(this.fill-this.level)<.0003&&Math.abs(this.velocity)<.004){
                this.fill=this.level;this.velocity=0;this.fillTimer=0;this.actor.queue_repaint();return GLib.SOURCE_REMOVE;
            }
            return GLib.SOURCE_CONTINUE;
        });
    }
    hide(immediate=false) {
        if(this.hideTimer)GLib.Source.remove(this.hideTimer);this.hideTimer=0;
        if(this.positionTimer)GLib.Source.remove(this.positionTimer);this.positionTimer=0;
        this.release();this.active=false;this.actor.remove_all_transitions();
        this.actor.ease({opacity:0,scale_x:.92,scale_y:.92,duration:immediate?0:this.system?320:this.duration,
            mode:Clutter.AnimationMode.EASE_IN_OUT_CUBIC,onComplete:()=>this.actor.hide()});
    }
    destroy(){this.hide(true);if(this.fillTimer)GLib.Source.remove(this.fillTimer);this.actor.remove_all_transitions();Main.layoutManager.removeChrome(this.actor);this.actor.destroy();}
}
