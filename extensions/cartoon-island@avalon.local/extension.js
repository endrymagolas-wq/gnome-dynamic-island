import St from 'gi://St';
import Shell from 'gi://Shell';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {IslandWorld, applicationState, drawWorld} from './world.js';
import {CairoCanvas} from './cairo-canvas.js';

const API='<node><interface name="org.avalon.CartoonIsland"><method name="ClaudeState"><arg type="s" direction="in"/><arg type="b" direction="out"/></method></interface></node>';
export default class CartoonIsland extends Extension {
    enable(){
        this.world=new IslandWorld();this.actors=[];
        this.settings=new Gio.Settings({schema_id:'org.gnome.desktop.interface'});
        this.tracker=Shell.WindowTracker.get_default();
        this.focusId=global.display.connect('notify::focus-window',()=>this.focus());
        this.monitorsId=Main.layoutManager.connect('monitors-changed',()=>this.build());
        this.sessionId=Main.sessionMode.connect('updated',()=>this.visibility());
        this.bridge=Gio.DBusExportedObject.wrapJSObject(API,{
            ClaudeState:state=>{
                // Desktop states cannot be injected as Claude events.
                if(!['starting','editing','testing','failed','permission','done','working'].includes(state))return false;
                const accepted=this.world.present(state,GLib.get_monotonic_time()/1000000);
                this.repaint();return accepted;
            },
        });
        this.bridge.export(Gio.DBus.session,'/org/avalon/CartoonIsland');
        this.build();this.focus();this.last=GLib.get_monotonic_time()/1000000;
        this.timer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,83,()=>{
            const now=GLib.get_monotonic_time()/1000000;
            if(!Main.sessionMode.isLocked && !Main.sessionMode.isGreeter){
                const previous=this.world.source;
                this.world.step(now,now-this.last,this.settings.get_boolean('enable-animations'));
                if(previous==='claude'&&this.world.source==='desktop')this.focus();
                this.repaint();
            }
            this.last=now;return GLib.SOURCE_CONTINUE;
        });
    }
    focus(){
        if(this.world.source==='claude')return;
        const window=global.display.focus_window;
        const app=window?this.tracker.get_window_app(window):null;
        this.world.present(applicationState(app?.get_id()??''),GLib.get_monotonic_time()/1000000,'desktop');
        this.repaint();
    }
    build(){
        for(const actor of this.actors)actor.destroy();this.actors=[];
        for(const monitor of Main.layoutManager.monitors){
            const actor=new St.DrawingArea({reactive:false,can_focus:false,x:monitor.x,y:monitor.y,width:monitor.width,height:monitor.height});
            actor.connect('repaint',area=>{
                const cr=area.get_context();const [w,h]=area.get_surface_size();
                // Cover without stretching; wide displays crop sky/ocean, not the worker.
                const scale=Math.max(w/1000,h/650);
                cr.translate((w-1000*scale)/2,(h-650*scale)/2);cr.scale(scale,scale);
                try{drawWorld(new CairoCanvas(cr),this.world,1000,650);}finally{cr.$dispose();}
            });
            // This is a background actor: windows, desktop icons and panels stay above it.
            Main.layoutManager._backgroundGroup.add_child(actor);
            this.actors.push(actor);
        }
        this.visibility();this.repaint();
    }
    visibility(){for(const actor of this.actors)actor.visible=!Main.sessionMode.isLocked&&!Main.sessionMode.isGreeter;}
    repaint(){for(const actor of this.actors)if(actor.mapped)actor.queue_repaint();}
    disable(){
        if(this.timer)GLib.Source.remove(this.timer);this.timer=0;
        if(this.focusId)global.display.disconnect(this.focusId);
        if(this.monitorsId)Main.layoutManager.disconnect(this.monitorsId);
        if(this.sessionId)Main.sessionMode.disconnect(this.sessionId);
        this.bridge?.unexport();this.bridge=null;
        for(const actor of this.actors??[])actor.destroy();this.actors=[];
        this.world=null;this.settings=null;this.tracker=null;
    }
}
