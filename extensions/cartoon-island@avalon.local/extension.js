import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Cogl from 'gi://Cogl';
import GdkPixbuf from 'gi://GdkPixbuf';
import Shell from 'gi://Shell';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {IslandWorld,applicationState} from './world.js';
import {VIEW,ATLAS,WATER,waterFrame,fitPlate,projectGround,characterFrame,needsFrames,animationBounds,coveredByWindows,intersectRegion} from './resort-layout.js';

const API='<node><interface name="org.avalon.CartoonIsland"><method name="ClaudeState"><arg type="s" direction="in"/><arg type="b" direction="out"/></method><method name="WaterAnimation"><arg type="b" direction="in"/></method></interface></node>';
function texture(path){
    const pixbuf=GdkPixbuf.Pixbuf.new_from_file(path),image=new Clutter.Image();
    image.set_data(pixbuf.get_pixels(),pixbuf.get_has_alpha()?Cogl.PixelFormat.RGBA_8888:Cogl.PixelFormat.RGB_888,pixbuf.get_width(),pixbuf.get_height(),pixbuf.get_rowstride());
    return image;
}
function sprite(parent,image,width,height,scale){
    const clip=new St.Widget({reactive:false,clip_to_allocation:true,width:width*scale,height:height*scale});
    const sheet=new St.Widget({reactive:false,width:ATLAS.width*scale,height:ATLAS.height*scale,content:image,content_gravity:Clutter.ContentGravity.RESIZE_FILL});
    clip.add_child(sheet);parent.add_child(clip);
    return {clip,sheet,scale,frame(x,y){sheet.set_position(-x*scale,-y*scale);}};
}
export default class CartoonIsland extends Extension {
    enable(){
        this.world=new IslandWorld();this.actors=[];this.connections=[];this.windows=new Map();this.water=true;
        this.settings=new Gio.Settings({schema_id:'org.gnome.desktop.interface'});
        this.tracker=Shell.WindowTracker.get_default();
        this.plate=texture(`${this.path}/assets/resort.jpg`);this.atlas=texture(`${this.path}/assets/sprites.png`);
        this.waterBanks=[0,1].map(i=>texture(`${this.path}/assets/water-${i}.png`));
        this.connect(global.display,'notify::focus-window',()=>{this.focus();this.wake();});
        this.connect(global.display,'restacked',()=>this.wake());
        this.connect(global.display,'window-created',(_display,window)=>{this.watch(window);this.wake();});
        this.connect(global.workspace_manager,'active-workspace-changed',()=>this.wake());
        this.connect(Main.layoutManager,'monitors-changed',()=>{this.build();this.wake();});
        this.connect(Main.sessionMode,'updated',()=>{this.visibility();this.wake();});
        this.connect(Main.overview,'showing',()=>this.wake());this.connect(Main.overview,'hidden',()=>this.wake());
        this.connect(this.settings,'changed::enable-animations',()=>this.wake());
        for(const actor of global.get_window_actors())this.watch(actor.meta_window);
        this.bridge=Gio.DBusExportedObject.wrapJSObject(API,{
            ClaudeState:state=>{
                if(!['starting','editing','testing','failed','permission','done','working'].includes(state))return false;
                const ok=this.world.present(state,this.now());this.expiration();this.wake();return ok;
            },
            WaterAnimation:enabled=>{this.water=enabled;this.wake();},
        });
        this.bridge.export(Gio.DBus.session,'/org/avalon/CartoonIsland');
        this.build();this.focus();this.wake();
    }
    now(){return GLib.get_monotonic_time()/1000000;}
    connect(object,signal,callback){this.connections.push([object,object.connect(signal,callback)]);}
    watch(window){
        if(this.windows.has(window))return;
        const ids=['position-changed','size-changed','notify::fullscreen','notify::minimized'].map(name=>window.connect(name,()=>this.wake()));
        ids.push(window.connect('unmanaged',()=>{for(const id of this.windows.get(window)??[])window.disconnect(id);this.windows.delete(window);this.wake();}));
        this.windows.set(window,ids);
    }
    focus(){
        if(this.world.source==='claude')return;
        const window=global.display.focus_window,app=window?this.tracker.get_window_app(window):null;
        this.world.present(applicationState(app?.get_id()??''),this.now(),'desktop');
    }
    expiration(){
        if(this.expireTimer)GLib.Source.remove(this.expireTimer);this.expireTimer=0;
        if(!this.world.until)return;
        this.expireTimer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,Math.max(1,Math.ceil((this.world.until-this.now())*1000)),()=>{
            this.expireTimer=0;this.world.step(this.now(),0,this.settings.get_boolean('enable-animations'));this.focus();this.wake();return GLib.SOURCE_REMOVE;
        });
    }
    build(){
        for(const item of this.actors)item.group.destroy();this.actors=[];
        for(const monitor of Main.layoutManager.monitors){
            const fit=fitPlate(monitor.width,monitor.height),group=new St.Widget({reactive:false,x:monitor.x,y:monitor.y,width:monitor.width,height:monitor.height,style:'background-color: #126174;'});
            const plate=new St.Widget({reactive:false,x:fit.x,y:fit.y,width:VIEW.width*fit.scale,height:VIEW.height*fit.scale,content:this.plate,content_gravity:Clutter.ContentGravity.RESIZE_FILL});
            group.add_child(plate);
            const waterClip=new St.Widget({reactive:false,clip_to_allocation:true,x:fit.x,y:fit.y,width:VIEW.width*fit.scale,height:VIEW.height*fit.scale});
            group.add_child(waterClip);const waterScale=VIEW.width/WATER.width*fit.scale;
            const waterSheets=this.waterBanks.map(content=>{const sheet=new St.Widget({reactive:false,visible:false,width:WATER.bankWidth*waterScale,height:WATER.bankHeight*waterScale,content,content_gravity:Clutter.ContentGravity.RESIZE_FILL});waterClip.add_child(sheet);return sheet;});
            const worker=sprite(group,this.atlas,80,100,.65*fit.scale);
            const building=sprite(group,this.atlas,160,128,.85*fit.scale);
            building.clip.set_position(fit.x+(552-80*.85)*fit.scale,fit.y+(430-120*.85)*fit.scale);
            const smoke=sprite(group,this.atlas,160,128,.65*fit.scale);
            smoke.clip.set_position(fit.x+560*fit.scale,fit.y+150*fit.scale);
            const bubble=new St.Label({visible:false,style:'background-color: #fff2dc; color: #67503f; border-radius: 12px; padding: 5px 9px; font-size: 12px;'});group.add_child(bubble);
            Main.layoutManager._backgroundGroup.add_child(group);
            this.actors.push({group,monitor,fit,worker,building,smoke,bubble,waterClip,waterSheets,waterScale,waterIndex:-1,buildingStage:-1});
        }
        this.visibility();
    }
    visibility(){for(const item of this.actors)item.group.visible=!Main.sessionMode.isLocked&&!Main.sessionMode.isGreeter;}
    visibleItems(){
        if(Main.sessionMode.isLocked||Main.sessionMode.isGreeter)return [];
        if(Main.overview.visible)return this.actors;
        // Conservative: only opaque maximized/fullscreen windows are blockers.
        const rectangles=global.workspace_manager.get_active_workspace().list_windows().filter(w=>!w.minimized&&w.showing_on_its_workspace()&&(w.is_fullscreen()||w.get_maximized()===Meta.MaximizeFlags.BOTH)&&(w.get_compositor_private()?.opacity??255)===255).map(w=>w.get_frame_rect());
        return this.actors.filter(item=>{
            const r=animationBounds();if(this.water){r.x=0;r.y=0;r.width=VIEW.width;r.height=VIEW.height;}
            const region={x:item.monitor.x+item.fit.x+r.x*item.fit.scale,y:item.monitor.y+item.fit.y+r.y*item.fit.scale,width:r.width*item.fit.scale,height:r.height*item.fit.scale};
            const workArea=global.workspace_manager.get_active_workspace().get_work_area_for_monitor(item.monitor.index);
            const exposed=intersectRegion(region,workArea);
            return exposed.width>0&&exposed.height>0&&!coveredByWindows(exposed,rectangles);
        });
    }
    paint(items,now){
        const p=projectGround(this.world.x,this.world.z),frame=characterFrame(this.world,now),effectFrame=this.world.motion?Math.floor(now*8)%8:0;
        for(const item of items){const {fit,worker,building,smoke,bubble,waterClip,waterSheets,waterScale}=item;
            worker.clip.set_position(fit.x+(p.x-ATLAS.anchorX*.65)*fit.scale,fit.y+(p.y-ATLAS.anchorY*.65)*fit.scale);worker.frame(frame.x,frame.y);
            if(item.buildingStage!==this.world.floors){building.frame(this.world.floors*160,1956);building.clip.visible=this.world.floors>0;item.buildingStage=this.world.floors;}
            // Painter order at the new cabana, while the main resort is baked.
            if(p.y<430)item.group.set_child_above_sibling(building.clip,worker.clip);else item.group.set_child_above_sibling(worker.clip,building.clip);
            smoke.clip.visible=this.world.state==='failed';if(smoke.clip.visible)smoke.frame(effectFrame*160,1828);
            bubble.visible=['permission','failed'].includes(this.world.state)&&this.world.path.length===0;
            if(bubble.visible){const text=this.world.state==='failed'?'блять…':'Гей! Дозвіл?';if(bubble.text!==text)bubble.text=text;bubble.set_position(fit.x+(p.x-28)*fit.scale,fit.y+(p.y-90)*fit.scale);}
            waterClip.visible=this.water&&this.world.motion;
            if(waterClip.visible){const f=waterFrame(now);if(item.waterIndex!==f.index){
                for(let i=0;i<waterSheets.length;i++)waterSheets[i].visible=i===f.bank;
                waterSheets[f.bank].set_position(-f.x*waterScale,-f.y*waterScale);item.waterIndex=f.index;
            }}
        }
    }
    wake(){
        if(!this.world)return;
        if(this.timer)GLib.Source.remove(this.timer);this.timer=0;
        const now=this.now(),motion=this.settings.get_boolean('enable-animations');this.world.step(now,0,motion);
        const items=this.visibleItems();this.paint(items,now);this.last=now;
        if(!items.length||!needsFrames(this.world,this.water))return;
        this.timer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,83,()=>{
            const now=this.now();
            if(!items.length){this.timer=0;return GLib.SOURCE_REMOVE;}
            this.world.step(now,now-this.last,this.settings.get_boolean('enable-animations'));this.last=now;this.paint(items,now);
            if(!needsFrames(this.world,this.water)){this.timer=0;return GLib.SOURCE_REMOVE;}
            return GLib.SOURCE_CONTINUE;
        });
    }
    disable(){
        for(const id of [this.timer,this.expireTimer])if(id)GLib.Source.remove(id);this.timer=this.expireTimer=0;
        for(const [object,id] of this.connections??[])object.disconnect(id);this.connections=[];
        for(const [window,ids] of this.windows??[])for(const id of ids)window.disconnect(id);this.windows?.clear();
        this.bridge?.unexport();this.bridge=null;
        for(const item of this.actors??[])item.group.destroy();this.actors=[];this.world=null;this.plate=null;this.atlas=null;this.waterBanks=null;
    }
}
