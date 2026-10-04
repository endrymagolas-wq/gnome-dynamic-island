import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import St from 'gi://St';
import Pango from 'gi://Pango';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// A passive notification surface; never takes a popup grab or consumes clicks.
export class ConnectionNotice {
    constructor(owner) {
        this.owner=owner;this.active=false;this.timeout=0;
        this.actor=new St.Widget({visible:false,reactive:false,clip_to_allocation:true,
            layout_manager:new Clutter.BinLayout(),style:'background-color:#050609;border-radius:28px;box-shadow:none;'});
        this.content=new St.BoxLayout({vertical:true,x_expand:true,x_align:Clutter.ActorAlign.FILL,y_align:Clutter.ActorAlign.START,
            style:'padding:20px 22px;spacing:7px;',reactive:false});
        const heading=new St.BoxLayout({x_expand:true,style:'spacing:10px;',reactive:false});
        this.icon=new St.Icon({icon_name:'audio-headphones-symbolic',icon_size:18,
            y_align:Clutter.ActorAlign.CENTER,style:'color:#f5f5f7;'});heading.add_child(this.icon);
        this.title=new St.Label({x_expand:true,text:'AirPlay під’єднано',style:'font-size:14px;font-weight:600;color:#f5f5f7;'});heading.add_child(this.title);
        this.content.add_child(heading);
        this.message=new St.Label({text:'Телефон готовий до музики',style:'font-size:12px;color:#f5f5f7;'});this.content.add_child(this.message);
        this.footer=new St.Label({text:'Ubuntu PC · аудіо',style:'font-size:10px;color:#a8abb2;'});this.content.add_child(this.footer);
        for(const label of [this.title,this.message,this.footer]) {
            label.clutter_text.set_ellipsize(Pango.EllipsizeMode.END);
            label.clutter_text.set_line_wrap(false);
            label.clutter_text.set_single_line_mode(true);
        }
        this.actor.add_child(this.content);
        Main.layoutManager.addChrome(this.actor,{affectsStruts:false,trackFullscreen:false});
        this.menuId=owner._indicator.menu.connect('open-state-changed',(_m,open)=>{if(open)this.hide(true);});
        this.timer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,40,()=>{
            if(this.active){
                if(this.blocked())this.hide(true);
                else {const m=Main.layoutManager.primaryMonitor;this.actor.set_position(Math.round(m.x+(m.width-this.actor.width)/2),m.y+6);}
            }
            return GLib.SOURCE_CONTINUE;
        });
    }
    blocked() {
        const m=Main.layoutManager.primaryMonitor;
        return !m || Main.sessionMode.isLocked || Main.sessionMode.isGreeter || Main.overview.visible ||
            this.owner._indicator.menu.isOpen || global.display.get_monitor_in_fullscreen(m.index) ||
            Boolean(global.display.focus_window?.is_fullscreen());
    }
    get motion(){return this.owner._settings.get_boolean('enable-animations');}
    showConnection(milliseconds=2700) {
        this.title.text='AirPlay під’єднано';this.message.text='Телефон готовий до музики';
        this.footer.text='Ubuntu PC · аудіо';this.icon.icon_name='audio-headphones-symbolic';
        return this.show(milliseconds);
    }
    present(data) {
        if(this.blocked()||this.active)return false;
        this.title.text=String(data.title).slice(0,48);this.message.text=String(data.message).slice(0,72);
        this.footer.text=typeof data.advice==='string' ? data.advice.slice(0,72) : 'Laya · локальна системна подія';
        this.icon.icon_name=['audio-headphones-symbolic','folder-download-symbolic','utilities-system-monitor-symbolic','media-playback-stop-symbolic','dialog-warning-symbolic','drive-harddisk-symbolic','network-wireless-symbolic'].includes(data.icon)?data.icon:'dialog-information-symbolic';
        return this.show(3200);
    }
    show(milliseconds=2700) {
        if(this.blocked())return false;
        if(this.timeout)GLib.Source.remove(this.timeout);
        const m=Main.layoutManager.primaryMonitor;
        const width=Math.min(346,m.width-24),restWidth=this.owner._floating.actor.width;
        this.actor.remove_all_transitions();this.content.remove_all_transitions();
        if(!this.active){this.actor.set_size(restWidth,26);this.content.opacity=0;}
        this.active=true;this.actor.opacity=255;this.actor.show();this.owner._pill.opacity=0;
        this.actor.set_position(Math.round(m.x+(m.width-this.actor.width)/2),m.y+6);
        this.actor.ease({width,height:126,duration:this.motion?480:0,mode:Clutter.AnimationMode.EASE_OUT_CUBIC});
        this.content.ease({opacity:255,delay:this.motion?140:0,duration:this.motion?180:0});
        this.timeout=GLib.timeout_add(GLib.PRIORITY_DEFAULT,milliseconds,()=>{this.timeout=0;this.hide();return GLib.SOURCE_REMOVE;});
        return true;
    }
    hide(immediate=false) {
        if(this.timeout)GLib.Source.remove(this.timeout);this.timeout=0;
        if(!this.active)return;
        this.actor.remove_all_transitions();this.content.remove_all_transitions();
        const finish=()=>{
            this.active=false;this.actor.hide();
            if(!this.owner._indicator.menu.isOpen)this.owner._pill.opacity=255;
        };
        if(immediate||!this.motion){finish();return;}
        this.content.ease({opacity:0,duration:100});
        this.actor.ease({width:this.owner._floating.actor.width,height:26,duration:320,
            mode:Clutter.AnimationMode.EASE_IN_OUT_CUBIC,onComplete:finish});
    }
    destroy() {
        this.hide(true);GLib.Source.remove(this.timer);
        this.owner._indicator.menu.disconnect(this.menuId);
        Main.layoutManager.removeChrome(this.actor);this.actor.destroy();
    }
}
