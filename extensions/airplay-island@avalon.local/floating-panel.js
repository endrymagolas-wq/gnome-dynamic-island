import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Shell from 'gi://Shell';
import St from 'gi://St';
import Meta from 'gi://Meta';
import {EdgeIntent,edgeSegments,hoverIntent} from './panel-intent.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export class FloatingPanel {
    constructor(indicator) {
        this.indicator=indicator;
        this.searchBin=Main.overview._overview.controls._searchEntryBin;
        this.searchStyle=this.searchBin.get_style();
        this.searchBin.set_style((this.searchStyle ? this.searchStyle+'; ' : '')+'padding-top: 34px;');
        this.settings=new Gio.Settings({schema_id:'org.gnome.desktop.interface'});
        this.actor=indicator.container;
        this.parent=this.actor.get_parent();
        this.index=this.parent.get_children().indexOf(this.actor);
        this.parent.remove_child(this.actor);
        Main.layoutManager.addChrome(this.actor,{affectsStruts:false,trackFullscreen:false});
        this.actor.set_size(128,26);
        this.panel=Main.layoutManager.panelBox;
        this.original={x:this.panel.x,y:this.panel.y,width:this.panel.width,translation:this.panel.translation_y,style:Main.panel.get_style(),clip:Main.panel.clip_to_allocation};
        Main.panel.clip_to_allocation=true;
        this.originalTrack={...Main.layoutManager._trackedActors.find(entry=>entry.actor===this.panel)};
        Main.layoutManager.untrackChrome(this.panel);
        Main.layoutManager.trackChrome(this.panel,{affectsStruts:false,trackFullscreen:false});
        Main.panel.add_style_class_name('ai-floating-panel');
        Main.panel.set_style('background-color: rgba(5,6,9,0.98); color: #f5f5f7; border-radius: 15px; height: 28px; padding: 0 10px; border: 1px solid rgba(255,255,255,0.14); box-shadow: none;');
        this.activities=Main.panel.statusArea.activities;
        this.activitiesVisible=this.activities?.visible;
        this.activities?.hide();
        // Bundle the owl emblem so the desktop icon theme cannot replace it.
        const owlFile=Gio.File.new_for_uri(import.meta.url).get_parent().get_child('assets').get_child('owl.png');
        this.logo=new St.Button({reactive:true,can_focus:true,accessible_name:'Dynamic Island · Програми',style_class:'ai-owl-button',
            child:new St.Icon({gicon:new Gio.FileIcon({file:owlFile}),icon_size:24,
                x_align:Clutter.ActorAlign.CENTER,y_align:Clutter.ActorAlign.CENTER})});
        this.logo.connect('clicked',()=>Main.overview.toggle());
        this.appLabel=new St.Label({text:'Робочий стіл',style_class:'ai-panel-app',y_align:Clutter.ActorAlign.CENTER});
        Main.panel._leftBox.insert_child_at_index(this.logo,0);
        Main.panel._leftBox.insert_child_at_index(this.appLabel,1);
        this.tracker=Shell.WindowTracker.get_default();
        this.focusId=global.display.connect('notify::focus-window',()=>this.updateApp());
        this.grabbing=false;this.hoverRevealMode='smart-edge';
        this.edgeIntent=new EdgeIntent();this.barriers=[];this.edgeRequestedUntil=0;
        this.grabBegin=global.display.connect('grab-op-begin',()=>{
            this.grabbing=true;this.edgeSince=0;this.edgeRequestedUntil=0;this.lastHover=0;
            this.clearBarriers();
            if(this.shown){
                for(const item of Object.values(Main.panel.statusArea))if(item!==this.indicator)item.menu?.close();
                this.morph(false);this.panel.hide();
            }
        });
        this.grabEnd=global.display.connect('grab-op-end',()=>{this.grabbing=false;this.edgeSince=0;this.edgeIntent.reset();});
        this.edgeSince=0; this.lastHover=0; this.shown=null;
        this.panel.set_pivot_point(.5,.5);
        this.panel.translation_y=0;
        this.panel.scale_x=1;
        this.panel.opacity=0;
        this.panel.hide();
        this.updateApp();
        this.timer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,40,()=>{this.update();return GLib.SOURCE_CONTINUE;});
        this.update();
    }
    updateApp() {
        const window=global.display.focus_window;
        if (window) this.appLabel.text=this.tracker.get_window_app(window)?.get_name() ?? window.get_title() ?? 'Програма';
    }
    clearBarriers() {
        for(const barrier of this.barriers)barrier.destroy();
        this.barriers=[];this.barrierKey=null;this.edgeIntent.reset();
    }
    syncBarriers(m,blocked) {
        const spans=edgeSegments(m,Main.layoutManager.monitors);
        const supported=Boolean(global.backend.capabilities&Meta.BackendCapabilities.BARRIERS);
        const key=JSON.stringify([m.y,spans,supported,blocked]);
        if(key===this.barrierKey)return;
        this.clearBarriers();this.barrierKey=key;
        if(blocked||!supported)return;
        for(const [left,right] of spans){
            try {
                const barrier=new Meta.Barrier({backend:global.backend,x1:left,x2:right,y1:m.y,y2:m.y,
                    directions:Meta.BarrierDirection.POSITIVE_Y});
                barrier.connect('left',()=>this.edgeIntent.reset());
                barrier.connect('hit',(_barrier,event)=>{
                    const [,y,modifiers]=global.get_pointer();
                    const blockedNow=this.grabbing||Boolean(modifiers&this.buttonMask)||Main.sessionMode.isLocked||
                        Main.sessionMode.isGreeter||this.fullscreen||global.display.get_monitor_in_fullscreen(m.index)||this.indicator.menu.isOpen||y>m.y+2||
                        !(Main.actionMode&(Shell.ActionMode.NORMAL|Shell.ActionMode.OVERVIEW));
                    if(this.edgeIntent.push({now:GLib.get_monotonic_time()/1000,dx:event.dx,dy:event.dy,blocked:blockedNow})){
                        const now=GLib.get_monotonic_time();
                        this.edgeRequestedUntil=now+600000;this.lastHover=now;this.update();
                    }
                });
                this.barriers.push(barrier);
            } catch(error){logError(error,'Island top-edge gesture');}
        }
    }
    titlebarAt(x,y) {
        // Geometry only, no application title/content capture. Topmost window wins.
        const actors=global.get_window_actors();
        for(let i=actors.length-1,seen=0;i>=0&&seen++<80;i--){
            const actor=actors[i],window=actor.meta_window;
            if(!actor.visible||!actor.mapped||window.minimized||!window.showing_on_its_workspace())continue;
            const r=window.get_frame_rect();
            if(x<r.x||x>=r.x+r.width||y<r.y||y>=r.y+r.height)continue;
            const type=window.get_window_type();
            return (type===Meta.WindowType.NORMAL||type===Meta.WindowType.DIALOG||type===Meta.WindowType.MODAL_DIALOG)&&y<r.y+Math.min(40,r.height);
        }
        return false;
    }
    update() {
        const m=Main.layoutManager.primaryMonitor;
        if (!m) return;
        const locked=Main.sessionMode.isLocked || Main.sessionMode.isGreeter;
        this.fullscreen=global.display.get_monitor_in_fullscreen(m.index) || Boolean(global.display.focus_window?.is_fullscreen() && global.display.focus_window.get_monitor()===m.index);
        this.actor.visible=!locked && !this.fullscreen;
        if (this.fullscreen && this.indicator.menu.isOpen) this.indicator.menu.close();
        this.actor.set_position(Math.round(m.x+(m.width-this.actor.width)/2),m.y+6);
        const inset=locked ? 0 : 16;
        this.expandedX=m.x+inset;
        this.expandedWidth=m.width-inset*2;
        const layoutKey=`${m.x}:${m.y}:${m.width}:${locked}`;
        if(layoutKey!==this.layoutKey) {
            this.layoutKey=layoutKey;
            this.panel.remove_all_transitions();
            this.panel.y=m.y+(locked ? 0 : 5);
            this.panel.set_width(this.shown?this.expandedWidth:this.actor.width);
            this.panel.x=this.shown?this.expandedX:Math.round(m.x+(m.width-this.actor.width)/2);
        }
        const [x,y,modifiers]=global.get_pointer();
        const now=GLib.get_monotonic_time();
        const buttons=Clutter.ModifierType.BUTTON1_MASK|Clutter.ModifierType.BUTTON2_MASK|Clutter.ModifierType.BUTTON3_MASK|Clutter.ModifierType.BUTTON4_MASK|Clutter.ModifierType.BUTTON5_MASK;
        this.buttonMask=buttons;
        const dragging=this.grabbing || Boolean(modifiers&buttons);
        this.syncBarriers(m,locked||this.fullscreen||dragging||this.indicator.menu.isOpen);
        if(dragging){this.edgeRequestedUntil=0;this.edgeIntent.reset();}
        const onIsland=x>=this.actor.x-8 && x<=this.actor.x+this.actor.width+8;
        const edge=x>=m.x+inset && x<=m.x+m.width-inset && y>=m.y && y<=m.y+2;
        const insidePanel=this.shown && x>=this.panel.x && x<=this.panel.x+this.panel.width && y>=m.y && y<=m.y+5+Main.panel.height;
        const menuOpen=Object.values(Main.panel.statusArea).some(item=>item!==this.indicator && item.menu?.isOpen);
        const hoverAllowed=hoverIntent({edge,onIsland,titlebar:edge&&!onIsland?this.titlebarAt(x,y):false,
            dragging,blocked:locked||this.fullscreen||this.indicator.menu.isOpen||
                !(Main.actionMode&(Shell.ActionMode.NORMAL|Shell.ActionMode.OVERVIEW)),
            shift:Boolean(modifiers&Clutter.ModifierType.SHIFT_MASK)});
        if (hoverAllowed) {
            if (!this.edgeSince) this.edgeSince=now;
        } else this.edgeSince=0;
        const dwell=this.edgeSince && now-this.edgeSince>=300000;
        const requested=now<this.edgeRequestedUntil || Boolean(dwell);
        if (requested || insidePanel || menuOpen) this.lastHover=now;
        const show=locked || (!this.fullscreen && !this.grabbing && !this.indicator.menu.isOpen && (menuOpen || requested || Boolean(this.shown && now-this.lastHover<600000)));
        if (show!==this.shown) this.morph(show);
    }
    morph(show) {
        const first=this.shown===null;
        this.shown=show;
        this.panel.remove_all_transitions();
        const duration=!first && this.settings.get_boolean('enable-animations') ? (show ? 400 : 260) : 0;
        const m=Main.layoutManager.primaryMonitor;
        if(!m)return;
        const collapsedWidth=this.actor.width;
        const collapsedX=Math.round(m.x+(m.width-collapsedWidth)/2);
        const boxes=[Main.panel._leftBox,Main.panel._rightBox];
        for (const box of boxes) box.remove_all_transitions();
        if (show) {
            if (!this.panel.visible) {
                this.panel.width=collapsedWidth;this.panel.x=collapsedX;this.panel.opacity=0;
            }
            this.panel.show();
            for (const box of boxes) {
                box.opacity=0;
                box.ease({opacity:255,delay:duration ? 190 : 0,duration:duration ? 180 : 0});
            }
            this.panel.ease({width:this.expandedWidth,x:this.expandedX,scale_x:1,scale_y:1,opacity:255,duration,
                mode:Clutter.AnimationMode.EASE_OUT_CUBIC});
        } else {
            for (const box of boxes) box.ease({opacity:0,duration:duration ? 60 : 0});
            this.panel.ease({width:collapsedWidth,x:collapsedX,scale_x:1,scale_y:1,opacity:0,duration,
                mode:Clutter.AnimationMode.EASE_OUT_CUBIC,onComplete:()=>{
                    if (!this.shown) {this.panel.hide();this.panel.opacity=0;}
                }});
        }
    }
    destroy() {
        this.clearBarriers();
        this.searchBin.set_style(this.searchStyle);
        if (this.timer) GLib.Source.remove(this.timer);
        for (const id of [this.focusId,this.grabBegin,this.grabEnd]) if (id) global.display.disconnect(id);
        this.logo.destroy();this.appLabel.destroy();
        if (this.activitiesVisible) this.activities?.show();
        this.panel.remove_all_transitions();
        this.panel.show();this.panel.opacity=255;this.panel.scale_x=1;this.panel.scale_y=1;
        this.panel.set_pivot_point(0,0);
        for (const box of [Main.panel._leftBox,Main.panel._rightBox]) {
            box.remove_all_transitions();box.opacity=255;
        }
        this.panel.translation_y=this.original.translation;
        this.panel.set_position(this.original.x,this.original.y);this.panel.set_width(this.original.width);
        Main.panel.remove_style_class_name('ai-floating-panel');
        Main.panel.set_style(this.original.style);
        Main.panel.clip_to_allocation=this.original.clip;
        Main.layoutManager.untrackChrome(this.panel);
        Main.layoutManager.trackChrome(this.panel,{affectsStruts:this.originalTrack.affectsStruts ?? true,trackFullscreen:this.originalTrack.trackFullscreen ?? true});
        Main.layoutManager.removeChrome(this.actor);
        this.parent.insert_child_at_index(this.actor,this.index);
    }
}
