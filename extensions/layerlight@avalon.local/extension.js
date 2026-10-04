import St from 'gi://St';
import Shell from 'gi://Shell';
import GObject from 'gi://GObject';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Motion} from './motion.js';

const moduleDir=Gio.File.new_for_uri(import.meta.url).get_parent();
const [,shaderBytes]=moduleDir.get_child('wave.glsl').load_contents(null);
const [,boundaryBytes]=moduleDir.get_child('boundaries.glsl').load_contents(null);
const wave=new TextDecoder().decode(boundaryBytes)+new TextDecoder().decode(shaderBytes);
const WaveEffect=GObject.registerClass(class LayerlightWaveEffect extends Shell.GLSLEffect {
    vfunc_build_pipeline(){
        this.add_glsl_snippet(Shell.SnippetHook.FRAGMENT,`uniform vec4 bands;uniform vec4 phases;uniform vec2 crop;uniform float strength;uniform float palette;${wave}`,
            'vec2 uv=(cogl_tex_coord_in[0].st-.5)*crop+.5;cogl_color_out=layeredColor(cogl_sampler0,uv,crop,phases,bands,strength,palette)*cogl_color_in;',true);
    }
    update(motion,strength,actor){
        if(this._bands===undefined){for(const name of ['bands','phases','strength','palette','crop'])this['_'+name]=this.get_uniform_location(name);}
        this.set_uniform_float(this._bands,4,motion.bands);
        this.set_uniform_float(this._phases,4,motion.phase);
        this.set_uniform_float(this._strength,1,[strength*motion.intensity]);this.set_uniform_float(this._palette,1,[motion.palette]);
        const w=actor.get_width(),h=actor.get_height();if(w<=0||h<=0)return;const scale=Math.max(w/3840,h/2160);
        this.set_uniform_float(this._crop,2,[w/(3840*scale),h/(2160*scale)]);
    }
});

export default class Layerlight extends Extension {
    enable(){
        console.log('Layerlight waves enabled');
        this._enabled=true;this._strength=1.1;this._motion=new Motion();this._state={level:0,bands:[0,0,0,0]};this._actors=new Map();this._managers=new Map();
        const uid=Gio.Credentials.new().get_unix_user();this._file=Gio.File.new_for_path(`${GLib.get_user_runtime_dir()}/layerlight-${uid}.json`);
        this._startAudio();
        // The producer atomically replaces the state file. Read its current path
        // on a fixed cadence instead of following a replaced inode.
        this._readState=()=>{try{const [ok,bytes]=this._file.load_contents(null);const state=ok?JSON.parse(new TextDecoder().decode(bytes)):null;const fresh=state&&Math.abs(Date.now()/1000-state.time)<.7;const valid=fresh&&Number.isFinite(state.level)&&Array.isArray(state.bands)&&state.bands.length===4&&state.bands.every(Number.isFinite);this._state=valid?{...state,level:Math.max(0,Math.min(2,state.level)),bands:state.bands.map(v=>Math.max(0,Math.min(2,v)))}:{level:0,bands:[0,0,0,0]};}catch(_) {this._state={level:0,bands:[0,0,0,0]};}};
        this._readState();
        this._reader=GLib.timeout_add(GLib.PRIORITY_DEFAULT,50,()=>{this._readState();return GLib.SOURCE_CONTINUE;});
        this._diagnostic=Gio.File.new_for_path(`${GLib.get_user_runtime_dir()}/layerlight-render-${uid}.json`);
        this._lastDiagnostic=0;
        this._button=new PanelMenu.Button(0,'Живі хвилі');this._button.add_child(new St.Icon({icon_name:'weather-clear-night-symbolic',style_class:'system-status-icon'}));
        const toggle=new PopupMenu.PopupSwitchMenuItem('Хвилі під музику',true);toggle.connect('toggled',(_,value)=>{this._enabled=value;if(value)this._startAudio();else this._stopAudio();});this._button.menu.addMenuItem(toggle);
        for(const [label,mode] of [['Авто · музика','auto'],['Лоуфай','calm'],['Енергійно','drive']]){const item=new PopupMenu.PopupMenuItem(label);item.connect('activate',()=>{this._motion.mode=mode;});this._button.menu.addMenuItem(item);}
        for(const [label,index] of [['Червоний · 35–180 Гц',0],['Жовтий · 180–700 Гц',1],['Світлий · 700–2400 Гц',2],['Синій · 2400–5500 Гц',3]]){const item=new PopupMenu.PopupSwitchMenuItem(label,true);item.connect('toggled',(_,value)=>{this._motion.weights[index]=value?1:0;});this._button.menu.addMenuItem(item);}
        for(const [label,value] of [['М’який рух',.7],['Виразний рух',1.1],['Сильний рух',1.6]]){const item=new PopupMenu.PopupMenuItem(label);item.connect('activate',()=>{this._strength=value;});this._button.menu.addMenuItem(item);}
        Main.panel.addToStatusArea(this.uuid,this._button);
        this._background=new Gio.Settings({schema_id:'org.gnome.desktop.background'});
        this._backgroundSignal=this._background.connect('changed',()=>this._build());
        this._monitors=Main.layoutManager.connect('monitors-changed',()=>this._build());this._build();
        this._lastTime=GLib.get_monotonic_time();
        this._timer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,16,()=>{
            const now=GLib.get_monotonic_time();this._motion.step(this._enabled?this._state:{level:0,bands:[0,0,0,0]},(now-this._lastTime)/1000000,false);this._lastTime=now;
            const active=this._motion.level>.00001;
            for(const [actor,effect] of this._actors){effect.set_enabled(active);if(active){effect.update(this._motion,this._strength,actor);actor.queue_redraw();}}
            if(now-this._lastDiagnostic>2000000){
                this._lastDiagnostic=now;
                try{this._diagnostic.replace_contents(JSON.stringify({time:Date.now()/1000,audioTime:this._state.time??0,level:this._motion.level,bands:this._motion.bands,phase:this._motion.phase,actors:this._actors.size,enabled:this._enabled}),null,false,Gio.FileCreateFlags.PRIVATE,null);}catch(_) {}
            }
            return GLib.SOURCE_CONTINUE;
        });
    }
    _startAudio(){
        if(this._process)return;
        try{const process=Gio.Subprocess.new(['/usr/bin/python3',`${this.path}/audio.py`],Gio.SubprocessFlags.STDOUT_SILENCE|Gio.SubprocessFlags.STDERR_SILENCE);this._process=process;process.wait_async(null,()=>{if(this._process===process)this._process=null;});}catch(error){console.warn(`Layerlight audio unavailable: ${error.message}`);}
    }
    _stopAudio(){
        // SIGTERM lets the producer stop its owned PipeWire monitor as well.
        try{this._process?.send_signal(15);}catch(_){}this._process=null;this._state={level:0,bands:[0,0,0,0]};
    }
    _attach(actor){
        if(!actor||this._actors.has(actor))return;
        const effect=new WaveEffect();actor.add_effect_with_name('layerlight-waves',effect);this._actors.set(actor,effect);console.log('Layerlight wave shader attached');
        actor.connect('destroy',()=>{this._actors.delete(actor);});
    }
    _build(){
        for(const [actor] of this._actors)actor.remove_effect_by_name('layerlight-waves');this._actors.clear();
        for(const [manager,id] of this._managers)manager.disconnect(id);this._managers.clear();
        if(!this._background.get_string('picture-uri').endsWith('WhiteSur-light.jpg'))return;
        for(const manager of Main.layoutManager._bgManagers){
            this._attach(manager.backgroundActor);
            this._managers.set(manager,manager.connect('changed',()=>this._attach(manager.backgroundActor)));
        }
    }
    disable(){
        if(this._timer)GLib.source_remove(this._timer);
        if(this._reader)GLib.source_remove(this._reader);
        try{this._diagnostic?.delete(null);}catch(_) {}
        if(this._monitors)Main.layoutManager.disconnect(this._monitors);
        if(this._backgroundSignal)this._background.disconnect(this._backgroundSignal);
        for(const [manager,id] of this._managers??[])manager.disconnect(id);
        for(const [actor] of this._actors??[])actor.remove_effect_by_name('layerlight-waves');
        this._actors?.clear();this._managers?.clear();this._monitor?.cancel();this._stopAudio();this._button?.destroy();
    }
}
