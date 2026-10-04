import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import {PhoneVolume} from './phone-volume.js';
import {ConnectionNotice} from './connection-notice.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {getMixerControl} from 'resource:///org/gnome/shell/ui/status/volume.js';

export class LiveStates {
    constructor(owner) {
        this.owner=owner;this.alive=true;this.active='';this.timeout=0;this.events=[];
        this.notice=new ConnectionNotice(owner);
        this.phoneMeter=new PhoneVolume(owner);
        this.systemMeter=new PhoneVolume(owner,true);
        this.systemMeter.onChange=level=>{
            const sink=this.control.get_default_sink();if(!sink)return;
            sink.volume=Math.round(level*this.control.get_vol_max_norm());sink.push_volume();
            if(level>0&&sink.is_muted)sink.change_is_muted(false);
        };
        this.osdOriginal=Main.osdWindowManager.show;
        this.osdHook=(monitor,icon,label,level,maxLevel)=>{
            const names=icon?.get_names?.()??[];
            if(names.some(name=>name.startsWith('audio-volume-'))&&typeof level==='number'){
                Main.osdWindowManager.hideAll();this.systemMeter.show(level);return;
            }
            this.osdOriginal.call(Main.osdWindowManager,monitor,icon,label,level,maxLevel);
        };
        Main.osdWindowManager.show=this.osdHook;
        this.label=new St.Label({style_class:'ai-live-label',visible:false,y_align:Clutter.ActorAlign.CENTER});
        owner._pill.insert_child_at_index(this.label,1);
        this.control=getMixerControl();
        this.sinkId=this.control.connect('default-sink-changed',()=>this.bindSink());
        this.readyId=this.control.connect('state-changed',()=>this.bindSink());
        this.bindSink();
        this.cancel=new Gio.Cancellable();
        Gio.DBusProxy.new_for_bus(Gio.BusType.SESSION,Gio.DBusProxyFlags.DO_NOT_AUTO_START,null,
            'org.gnome.ShairportSync','/org/gnome/ShairportSync','org.gnome.ShairportSync.RemoteControl',
            this.cancel,(_s,result)=>{
                if (!this.alive) return;
                try {
                    this.airplay=Gio.DBusProxy.new_for_bus_finish(result);
                    this.connection();
                    this.airVolume=this.airplay.get_cached_property('AirplayVolume')?.deepUnpack();
                    this.airId=this.airplay.connect('g-properties-changed',(_proxy,changed)=>{
                        this.connection();
                        const properties=changed.deepUnpack();
                        if(properties.AirplayVolume!==undefined) {
                            const value=properties.AirplayVolume instanceof GLib.Variant ? properties.AirplayVolume.deepUnpack() : properties.AirplayVolume;
                            if(value!==this.airVolume) {
                                this.airVolume=value;
                                if(this.active==='volume') this.reset();
                                this.phoneMeter.show(value);
                            }
                        }
                    });
                } catch (error) {console.warn(`Island connection: ${error.message}`);}
            });
        this.connectionTimer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,250,()=>{this.connection();return GLib.SOURCE_CONTINUE;});
        this.sessionId=Main.sessionMode.connect('updated',()=>{
            if (Main.sessionMode.isLocked) {this.phoneMeter.hide(true);this.systemMeter.hide(true);this.reset();owner._indicator.menu.close();}
        });
    }
    bindSink() {
        for (const id of this.streamIds ?? []) this.stream?.disconnect(id);
        this.stream=this.control.get_default_sink();this.streamIds=[];
        if (!this.stream) return;
        this.lastVolume=this.stream.volume;this.lastMute=this.stream.is_muted;
        const changed=()=>{
            if (this.stream.volume===this.lastVolume && this.stream.is_muted===this.lastMute) return;
            this.lastVolume=this.stream.volume;this.lastMute=this.stream.is_muted;
            if(this.systemMeter.active&&!this.systemMeter.dragging)
                this.systemMeter.show(this.stream.is_muted?0:this.stream.volume/this.control.get_vol_max_norm());
        };
        this.streamIds=[this.stream.connect('notify::volume',changed),this.stream.connect('notify::is-muted',changed)];
    }
    connection() {
        if(!this.airplay) return;
        const client=this.airplay.get_cached_property('Client')?.deepUnpack() ?? '';
        const parts=String(client).split('.');
        const remote=parts.length===4 ? parts.reverse().map(x=>Number(x).toString(16).padStart(2,'0')).join('').toUpperCase() : '';
        const sessions=[];
        if(remote) for(const path of ['/proc/net/tcp','/proc/net/tcp6']) {
            try {
                const [ok,data]=GLib.file_get_contents(path);
                if(!ok) continue;
                for(const line of new TextDecoder().decode(data).split('\n').slice(1)) {
                    const fields=line.trim().split(/\s+/);
                    if(fields[3]==='01' && fields[1]?.endsWith(':1388') && fields[2]?.split(':')[0].endsWith(remote))
                        sessions.push(fields[2]);
                }
            } catch { /* Retain native playback without connection telemetry. */ }
        }
        const key=sessions.sort().join(',');
        if(key && key!==this.socketKey)
            this.show('connection','AirPlay підключено',2600);
        this.socketKey=key;
    }
    show(kind,text,milliseconds) {
        if (Main.sessionMode.isLocked || Main.sessionMode.isGreeter) return;
        if(kind==='connection'){
            this.events.push({kind,text,at:GLib.get_real_time()});this.events=this.events.slice(-12);
            if(!this.owner._modelStatus())this.notice.showConnection(milliseconds);return;
        }
        if (this.timeout) GLib.Source.remove(this.timeout);
        this.events.push({kind,text,at:GLib.get_real_time()});this.events=this.events.slice(-12);
        this.active=kind;this.label.text=text;this.label.show();
        this.owner._focusLabel.hide();this.owner._wave.hide();
        this.owner._floating.actor.ease({width:248,duration:this.owner._settings.get_boolean('enable-animations') ? 260 : 0,
            mode:Clutter.AnimationMode.EASE_OUT_CUBIC});
        this.owner._liquid.pulse();
        this.timeout=GLib.timeout_add(GLib.PRIORITY_DEFAULT,milliseconds,()=>{
            this.timeout=0;this.reset();return GLib.SOURCE_REMOVE;
        });
    }
    focusFinished() {
        this.show('focus','Фокус завершено · час на паузу',5000);
        const m=Main.layoutManager.primaryMonitor;
        if (!Main.sessionMode.isLocked && !global.display.get_monitor_in_fullscreen(m.index) && !global.display.focus_window?.is_fullscreen()) {
            this.owner._indicator.menu.open();this.owner._autoClose();
        }
    }
    reset() {
        if (this.timeout) GLib.Source.remove(this.timeout);
        this.timeout=0;this.active='';this.label.hide();
        this.owner._focusLabel.show();this.owner._wave.visible=this.owner._playing;
        this.owner._floating.actor.ease({width:this.owner._status==='Playing' || this.owner._status==='Paused' ? 156 : 128,
            duration:this.owner._settings.get_boolean('enable-animations') ? 260 : 0,mode:Clutter.AnimationMode.EASE_OUT_CUBIC});
    }
    destroy() {
        this.alive=false;this.notice.destroy();
        if(Main.osdWindowManager.show===this.osdHook)Main.osdWindowManager.show=this.osdOriginal;
        this.systemMeter.destroy();this.phoneMeter.destroy();if(this.volumeTimer) GLib.Source.remove(this.volumeTimer);this.cancel.cancel();if(this.connectionTimer) GLib.Source.remove(this.connectionTimer);if(this.timeout) GLib.Source.remove(this.timeout);
        for(const id of this.streamIds ?? []) this.stream?.disconnect(id);
        this.control.disconnect(this.sinkId);this.control.disconnect(this.readyId);
        if(this.airId) this.airplay.disconnect(this.airId);
        Main.sessionMode.disconnect(this.sessionId);this.label.destroy();
    }
}
