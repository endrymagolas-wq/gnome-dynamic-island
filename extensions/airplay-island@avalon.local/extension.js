import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import Pango from 'gi://Pango';
import Cairo from 'cairo';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {CastControls} from './cast-controls.js';
import {FloatingPanel} from './floating-panel.js';
import {LiquidIsland} from './liquid-island.js';
import {LiveStates} from './live-states.js';
import {DesktopTools} from './desktop-tools.js';
import {AlbumArt} from './album-art.js';
import {roundArtwork} from './rounded-art.js';
import {MediaPlayers} from './media-players.js';
import {ClaudeScene} from './claude-scene.js';

const PLAYER = 'org.mpris.MediaPlayer2.ShairportSync';
const PATH = '/org/mpris/MediaPlayer2';
const IFACE = 'org.mpris.MediaPlayer2.Player';
const API = `<node><interface name="org.avalon.AirplayIsland">
<method name="ClaudeState"><arg type="s" direction="in"/><arg type="b" direction="out"/></method><method name="Present"><arg type="s" direction="in"/><arg type="b" direction="out"/></method><method name="Show"/><method name="PreviewVolume"><arg type="d" direction="in"/></method><method name="Focus"><arg type="i" direction="in"/></method><method name="GetState"><arg type="s" direction="out"/></method>
</interface></node>`;

export default class AirPlayIsland extends Extension {
    enable() {
        this._alive = true;
        this._playing = false;
        this._pending = false;
        this._proxy = null;
        this._closeId = 0;
        this._routeAt = 0;
        this._routeBusy = false;
        this._routeName = 'Аудіовихід';
        this._settings = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        this._cancellable = new Gio.Cancellable();
        this._indicator = new PanelMenu.Button(0.5, 'AirPlay Island');
        this._indicator.add_style_class_name('ai-panel-button');
        this._pill = new St.Widget({style_class: 'ai-pill', layout_manager:new Clutter.BinLayout(), y_align: Clutter.ActorAlign.CENTER});
        const mediaRow=new St.BoxLayout({x_expand:true,x_align:Clutter.ActorAlign.FILL,y_align:Clutter.ActorAlign.CENTER});
        this._smallIcon = new St.Icon({icon_name:'audio-x-generic-symbolic', icon_size:14, style_class:'ai-small-icon', y_align:Clutter.ActorAlign.CENTER});
        this._smallIcon.set_style('icon-shadow: none; padding: 0; margin: 0;');
        this._miniFrame=new St.Bin({width:16,height:16,y_align:Clutter.ActorAlign.CENTER,
            style:'padding: 0; margin: 0;',clip_to_allocation:true,child:this._smallIcon});

        mediaRow.add_child(this._miniFrame);
        this._mediaRow = mediaRow;
        this._pill.add_child(mediaRow);
        this._focusLabel = new St.Label({text:'', visible:false, style_class:'ai-focus-time', style:'margin:0; text-align:center;',x_align:Clutter.ActorAlign.CENTER, y_align:Clutter.ActorAlign.CENTER});
        this._pill.add_child(this._focusLabel);
        mediaRow.add_child(new St.Widget({x_expand:true}));
        this._wave = new St.DrawingArea({width:22, height:18, y_align:Clutter.ActorAlign.CENTER});
        this._wave.connect('repaint', area => this._drawWave(area));
        mediaRow.add_child(this._wave);
        this._indicator.add_child(this._pill);
        this._buildMenu();
        Main.panel.addToStatusArea(this.uuid, this._indicator, 0, 'center');
        this._clock = Main.panel.statusArea.dateMenu.container;
        this._clockParent = this._clock.get_parent();
        this._clockIndex = this._clockParent.get_children().indexOf(this._clock);
        this._moveClock();
        this._sessionId = Main.sessionMode.connect('updated', () => this._moveClock());
        this._indicator.menu.connect('open-state-changed', (_menu, open) => {
            if (open) {
                this._update();
                this._autoClose();
            } else {
                this._cancelClose();
            }
        });
        this._indicator.menu.actor.connect('key-press-event', () => {
            this._autoClose();
            return Clutter.EVENT_PROPAGATE;
        });
        this._indicator.menu.actor.connect('motion-event', () => {
            this._autoClose();
            return Clutter.EVENT_PROPAGATE;
        });
        this._bridge = Gio.DBusExportedObject.wrapJSObject(API, {
            Show: () => { this._indicator.menu.open(); this._autoClose(); },
            GetState: () => JSON.stringify(this._state()),
            ClaudeState: state => this._claude?.present(state) ?? false,
            Present: payload => {
                if(typeof payload!=='string'||payload.length>4096)return false;
                try {const data=JSON.parse(payload);
                    if(!['connection','download','cpu','ram','task','service','disk','network'].includes(data.kind)||typeof data.title!=='string'||typeof data.message!=='string'||typeof data.expires!=='number'||!Number.isFinite(data.expires)||data.expires<Date.now()/1000)return false;
                    return this._live.notice.present(data);
                } catch {return false;}
            },
            Focus: seconds => this._tools.startFocus(seconds),
            PreviewVolume: decibels => this._live.phoneMeter.show(decibels),
        });
        this._bridge.export(Gio.DBus.session, '/org/avalon/AirplayIsland');
        this._floating = new FloatingPanel(this._indicator);
        this._tools = new DesktopTools(this);
        this._liquid = new LiquidIsland(this);
        this._live = new LiveStates(this);
        this._players = new MediaPlayers(this);
        this._claude = new ClaudeScene(this);
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, () => {
            this._update(); return GLib.SOURCE_CONTINUE;
        });
        this._waveTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 90, () => {
            if (this._playing && this._wave.mapped && this._settings.get_boolean('enable-animations'))
                this._wave.queue_repaint();
            return GLib.SOURCE_CONTINUE;
        });
        this._update();
        this._cast = new CastControls(this.path);
        try {
            this._cast.enable();
        } catch (error) {
            console.error(`Cast Controls: ${error.message}`);
            this._cast?.disable();
            this._cast = null;
        }
    }
    _buildMenu() {
        const menu = this._indicator.menu;
        menu.actor.add_style_class_name('ai-menu');
        const item = new PopupMenu.PopupBaseMenuItem({reactive:false, can_focus:false, style_class:'ai-menu-item'});
        const body = new St.BoxLayout({vertical:true, style_class:'ai-body', x_expand:true});
        const header = new St.BoxLayout({style_class:'ai-header'});
        const badge = new St.Bin({style_class:'ai-art', y_align:Clutter.ActorAlign.CENTER});
        this._artIcon = new St.Icon({icon_name:'audio-x-generic-symbolic',icon_size:64});
        roundArtwork(this._artIcon,10);
        badge.set_child(this._artIcon);
        this._albumArt = new AlbumArt(this._artIcon,()=>this._indicator.menu.isOpen && this._settings.get_boolean('enable-animations'),gicon=>this._setMiniArtwork(gicon));
        header.add_child(badge);
        const labels = new St.BoxLayout({vertical:true, x_expand:true, y_align:Clutter.ActorAlign.CENTER, style_class:'ai-labels'});
        this._title = new St.Label({text:'Готовий до AirPlay', style_class:'ai-title', x_expand:true});
        this._title.clutter_text.ellipsize = Pango.EllipsizeMode.END;
        this._artist = new St.Label({text:'Музика з телефона', style_class:'ai-subtitle', x_expand:true});
        this._artist.clutter_text.ellipsize = Pango.EllipsizeMode.END;
        labels.add_child(this._title); labels.add_child(this._artist); header.add_child(labels);
        const gear = this._button('emblem-system-symbolic','Керування ПК',()=>{
            this._tools?.systemMenu.menu.toggle();
        });
        gear.add_style_class_name('ai-small-button');
        header.add_child(gear);
        body.add_child(header);
        const controls = new St.BoxLayout({style_class:'ai-controls', x_align:Clutter.ActorAlign.START});
        this._prev = this._button('media-skip-backward-symbolic','Попередній трек', () => this._command('Previous'));
        this._play = this._button('media-playback-start-symbolic','Відтворення / пауза', () => this._command('PlayPause'));
        this._play.add_style_class_name('ai-primary');
        this._next = this._button('media-skip-forward-symbolic','Наступний трек', () => this._command('Next'));
        controls.add_child(this._prev); controls.add_child(this._play); controls.add_child(this._next);
        labels.add_child(controls);
        const footer = new St.BoxLayout({style_class:'ai-footer'});
        footer.add_child(new St.Icon({icon_name:'audio-headphones-symbolic',icon_size:14,y_align:Clutter.ActorAlign.CENTER}));
        this._route = new St.Label({text:this._routeName,style_class:'ai-route',x_expand:true,y_align:Clutter.ActorAlign.CENTER});
        this._route.clutter_text.ellipsize = Pango.EllipsizeMode.END;
        footer.add_child(this._route);
        this._screen = this._button('view-fullscreen-symbolic','Розгорнути відео', () => {
            if (this._video) {
                if (this._video.is_fullscreen()) this._video.unmake_fullscreen();
                else this._video.make_fullscreen();
                this._video.activate(global.get_current_time());
                menu.close();
            }
        });
        this._screen.add_style_class_name('ai-small-button');
        footer.add_child(this._screen);
        const close = this._button('pan-up-symbolic','Згорнути', () => menu.close());
        close.add_style_class_name('ai-small-button');
        footer.add_child(close);
        body.add_child(footer);
        this._hint = new St.Label({text:'AirPlay → Ubuntu PC', style_class:'ai-hint'});
        body.add_child(this._hint);
        item.add_child(body);
        menu.addMenuItem(item);
    }
    _button(icon, label, callback) {
        const button = new St.Button({style_class:'ai-control', can_focus:true, reactive:true,
            accessible_name:label, y_align:Clutter.ActorAlign.CENTER,
            child:new St.Icon({icon_name:icon, icon_size:20})});
        button.connect('clicked', () => { this._autoClose(); callback(); });
        return button;
    }
    _moveClock() {
        if (!this._clock || Main.sessionMode.isLocked || Main.sessionMode.isGreeter) return;
        const parent = this._clock.get_parent();
        if (parent !== Main.panel._rightBox) {
            parent?.remove_child(this._clock);
            Main.panel._rightBox.insert_child_at_index(this._clock, 0);
        }
    }
    _property(key, fallback) {
        if (!this._proxy?.get_name_owner()) return fallback;
        return this._proxy.get_cached_property(key)?.deepUnpack() ?? fallback;
    }
    _update() {
        if (!this._alive) return;
        const status = this._property('PlaybackStatus','Stopped');
        let metadata = this._property('Metadata',{}) ?? {};
        // Unpack dictionary values; MPRIS uses nested variants.
        metadata = Object.fromEntries(Object.entries(metadata).map(([key,value]) =>
            [key, value instanceof GLib.Variant ? value.deepUnpack() : value]));
        this._albumArt.update(metadata['mpris:artUrl'] ?? '',String(metadata['mpris:trackid'] ?? metadata['xesam:title'] ?? ''));
        this._video = global.get_window_actors().map(actor => actor.meta_window).find(window =>
            /uxplay/i.test(window.get_wm_class() ?? '') || /uxplay/i.test(window.get_title() ?? ''));
        this._playing = status === 'Playing' || Boolean(this._video);
        this._status = status;
        const active = status === 'Playing' || status === 'Paused';
        let artists = metadata['xesam:artist'] ?? [];
        if (!Array.isArray(artists)) artists = [artists];
        if (this._video) {
            this._setTrack('Екран телефона','Ubuntu Screen');
        } else if (active) {
            this._setTrack(metadata['xesam:title'] || 'Музика',(artists.join(', ') || this._playerName?.replace('org.mpris.MediaPlayer2.','') || 'Програвач') + (status === 'Paused' ? ' · Пауза' : ''));
        } else {
            this._setTrack('Твій робочий простір','Фокус · звук · музика · AirPlay');
        }
        this._indicator.accessible_name = `AirPlay: ${this._title.text}, ${this._artist.text}`;
        if(!active || !this._albumArt.loaded){this._smallIcon.gicon=null;this._smallIcon.icon_name=this._video?'video-display-symbolic':active?'audio-x-generic-symbolic':'preferences-system-symbolic';this._smallIcon.icon_size=14;}else{this._smallIcon.gicon=this._artIcon.gicon;this._smallIcon.icon_size=16;}
        if(!active)this._setMiniArtwork(null);else if(this._albumArt.loaded)this._setMiniArtwork(this._artIcon.gicon);
        this._miniFrame.visible=active || Boolean(this._video);
        this._smallIcon.opacity = active || this._video ? 255 : 140;
        this._play.child.icon_name = status === 'Playing' ? 'media-playback-pause-symbolic' : 'media-playback-start-symbolic';
        const usable = active && !this._pending && !this._video;
        for (const [button,key] of [[this._prev,'CanGoPrevious'],[this._next,'CanGoNext'],[this._play,status === 'Playing' ? 'CanPause':'CanPlay']]) {
            button.reactive = usable && this._property(key,false);
            button.can_focus = button.reactive;
            button.opacity = button.reactive ? 255 : 80;
        }
        this._screen.visible = Boolean(this._video);
        if (!this._errorUntil || GLib.get_monotonic_time() > this._errorUntil) {
            this._hint.text = this._pending ? 'Надсилаю команду…' : 'Прокрути острівець, щоб змінити гучність';
            this._hint.visible = this._pending || this._live?.active==='focus';
            if(this._live?.active==='focus') this._hint.text='Фокус завершено · час на паузу';
        }
        const motionKey=`${active}:${this._title.text}`;
        if (motionKey!==this._motionKey) {
            const previous=this._motionKey;
            this._motionKey=motionKey;
            this._floating?.actor.ease({width:this._live?.active ? 248 : active ? 156 : 128,duration:this._settings.get_boolean('enable-animations') ? 300 : 0,
                mode:Clutter.AnimationMode.EASE_OUT_CUBIC});
            if (previous) this._liquid?.pulse();
        }
        this._wave.visible = this._playing && !this._live?.active;
        this._wave.queue_repaint();
        this._updateRoute();
        this._claude?.sync();
    }
    _setMiniArtwork(gicon) {
        this._smallIcon.gicon=gicon;
        if(!gicon)this._smallIcon.icon_name=this._video?'video-display-symbolic':['Playing','Paused'].includes(this._status)?'audio-x-generic-symbolic':'preferences-system-symbolic';
        this._smallIcon.icon_size=gicon?16:14;
        this._miniFrame.visible=Boolean(gicon || this._video || ['Playing','Paused'].includes(this._status));
        let uri=gicon instanceof Gio.FileIcon?gicon.get_file().get_uri():'';
        if(gicon instanceof Gio.BytesIcon){
            const bytes=gicon.get_bytes();
            const key=GLib.compute_checksum_for_bytes(GLib.ChecksumType.SHA256,bytes);
            const dir=GLib.build_filenamev([GLib.get_user_cache_dir(),'cortiva-island-art']);
            GLib.mkdir_with_parents(dir,0o700);
            const file=Gio.File.new_for_path(GLib.build_filenamev([dir,`${key}.png`]));
            if(!file.query_exists(null))file.replace_contents(bytes.get_data(),null,false,Gio.FileCreateFlags.PRIVATE,null);
            uri=file.get_uri();
            if(this._miniCacheFile&&!this._miniCacheFile.equal(file)){
                try{this._miniCacheFile.delete(null);}catch{}
            }
            this._miniCacheFile=file;
        }
        if(uri!==this._miniUri){this._miniUri=uri;this._miniFrame.set_style(uri?`padding: 0; margin: 0; border-radius: 5px; background-image: url("${uri}"); background-size: cover;`:'padding: 0; margin: 0; background-image: none;');}
        this._smallIcon.visible=!uri;
    }
    _setTrack(title,artist) {
        const key=`${title}:${artist}`;
        if(key===this._trackTextKey) return;
        this._trackTextKey=key;
        this._title.remove_all_transitions();this._artist.remove_all_transitions();
        const apply=()=>{
            this._title.text=title;this._artist.text=artist;
            this._indicator.accessible_name=`AirPlay: ${title}, ${artist}`;
            for(const label of [this._title,this._artist]) label.ease({opacity:255,translation_x:0,
                duration:this._settings.get_boolean('enable-animations') ? 180 : 0,mode:Clutter.AnimationMode.EASE_OUT_CUBIC});
        };
        if(this._indicator.menu.isOpen && this._settings.get_boolean('enable-animations')) {
            this._artist.ease({opacity:0,translation_x:-5,duration:110});
            this._title.ease({opacity:0,translation_x:-5,duration:110,onComplete:apply});
        } else apply();
    }
    _drawWave(area) {
        const cr = area.get_context();
        const [w,h] = area.get_surface_size();
        cr.setSourceRGBA(this._playing ? .56:.38, this._playing ? .85:.40, this._playing ? .68:.43, 1);
        cr.setLineWidth(2.5); cr.setLineCap(Cairo.LineCap.ROUND);
        const motion = this._playing && this._settings.get_boolean('enable-animations');
        const time = GLib.get_monotonic_time()/1000000;
        for (let i=0;i<4;i++) {
            const height = motion ? 4+10*(.5+.5*Math.sin(time*5+i*1.3)) : 5;
            const x = (w-18)/2+2+i*5;
            cr.moveTo(x,(h-height)/2); cr.lineTo(x,(h+height)/2); cr.stroke();
        }
        cr.$dispose();
    }
    _command(method) {
        if (!this._proxy || this._pending) return;
        const target=this._proxy;
        this._pending = true; this._update();
        const send=()=>{
            this._commandTimer=0;
            if(!this._alive) return;
            if(this._proxy!==target || !target.get_name_owner()) {
                this._pending=false;this._update();return;
            }
            target.call(method,null,Gio.DBusCallFlags.NONE,3000,this._cancellable,(proxy,result) => {
                if (!this._alive) return;
                this._pending = false;
                try { proxy.call_finish(result); }
                catch (error) {
                    this._hint.text = 'Не вдалося виконати команду'; this._hint.show();
                    this._errorUntil = GLib.get_monotonic_time()+5000000;
                }
                this._update();
            });
        };
        if(method==='Previous' || method==='Next') {
            this._commandTimer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,300,()=>{send();return GLib.SOURCE_REMOVE;});
        } else send();
    }
    _updateRoute() {
        const now = GLib.get_monotonic_time();
        if (this._routeBusy || now-this._routeAt < 10000000) return;
        this._routeAt = now; this._routeBusy = true;
        const process = Gio.Subprocess.new(['wpctl','inspect','@DEFAULT_AUDIO_SINK@'],Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_SILENCE);
        process.communicate_utf8_async(null,this._cancellable,(proc,result) => {
            if (!this._alive) return;
            this._routeBusy = false;
            try {
                const [,text] = proc.communicate_utf8_finish(result);
                const match = text?.match(/node\.description = "([^"]+)"/);
                this._routeName = match ? match[1].replace(' Audio Codec Analog Stereo',' USB Audio') : 'Аудіовихід недоступний';
                this._route.text = this._routeName;
            } catch (error) { this._route.text = 'Аудіовихід недоступний'; }
        });
    }
    _autoClose() {
        this._cancelClose();
        if (!this._indicator.menu.isOpen) return;
        this._closeId = GLib.timeout_add(GLib.PRIORITY_DEFAULT,6500,() => {
            this._closeId = 0;
            const [px,py]=global.get_pointer();
            const [mx,my]=this._indicator.menu.actor.get_transformed_position();
            const [mw,mh]=this._indicator.menu.actor.get_transformed_size();
            if (px>=mx && px<=mx+mw && py>=my && py<=my+mh) { this._autoClose(); return GLib.SOURCE_REMOVE; }
            this._indicator.menu.close();
            return GLib.SOURCE_REMOVE;
        });
    }
    _cancelClose() {
        if (this._closeId) GLib.Source.remove(this._closeId);
        this._closeId = 0;
    }
    _modelStatus() {
        try {
            const path=GLib.build_filenamev([GLib.get_home_dir(),'.local','share','island-desktop','assistant','status.json']);
            const [ok,bytes]=GLib.file_get_contents(path);if(!ok||bytes.length>65536)return null;
            const data=JSON.parse(new TextDecoder().decode(bytes));
            return data.active && Date.now()/1000-data.heartbeat<15 ? data : null;
        } catch {return null;}
    }
    _state() {
        const [x,y] = this._pill.get_transformed_position();
        const [width,height] = this._pill.get_transformed_size();
        return {menuOpen:this._indicator.menu.isOpen, title:this._title.text, artist:this._artist.text,
            claudeState:this._claude?.state ?? "", foregroundPid:global.display.focus_window?.get_pid() ?? 0, modelBridge:true, modelStatus:this._modelStatus(), route:this._routeName, status:this._status, pill:{x,y,width,height},
            overview:{visible:Main.overview.visible,search:(()=>{const a=Main.overview.searchEntry;const [x,y]=a.get_transformed_position();const [width,height]=a.get_transformed_size();return {x,y,width,height};})()},
            clockRight:this._clock.get_parent() === Main.panel._rightBox,
            panelReveal:{trigger:this._floating?.hoverRevealMode??(this._floating?.edgeIntent?'pressure':'hover'),barriers:this._floating?.barriers?.length??0},
            panelShown:this._floating?.shown, windowGrab:Boolean(this._floating?.grabbing), panel:{x:this._floating?.panel.x,y:this._floating?.panel.y,width:this._floating?.panel.width,height:this._floating?.panel.height,translation:this._floating?.panel.translation_y}, panelScale:this._floating?.panel.scale_x,
            card:(()=>{const a=this._indicator.menu.actor;const [x,y]=a.get_transformed_position();const [width,height]=a.get_transformed_size();return {x,y,width,height,scaleX:a.scale_x,scaleY:a.scale_y,visible:a.visible};})(),
            controls:[this._prev,this._play,this._next].map(a=>{const [x,y]=a.get_transformed_position();const [width,height]=a.get_transformed_size();return {x,y,width,height,reactive:a.reactive};}),
            miniatureGeometry:(()=>{const a=this._miniFrame;const [x,y]=a.get_transformed_position();return {x,y,width:a.width,height:a.height};})(), miniatureArtwork:Boolean(this._albumArt?.loaded && this._smallIcon.gicon?.equal(this._artIcon.gicon)), systemVolume:this._live?{visible:this._live.systemMeter.actor.visible,active:this._live.systemMeter.active,level:this._live.systemMeter.level,fill:this._live.systemMeter.fill,scaleX:this._live.systemMeter.actor.scale_x,scaleY:this._live.systemMeter.actor.scale_y,opacity:this._live.systemMeter.actor.opacity,dragging:this._live.systemMeter.dragging??false,x:this._live.systemMeter.actor.x,y:this._live.systemMeter.actor.y,width:this._live.systemMeter.actor.width,height:this._live.systemMeter.actor.height}:null,
            phoneVolume:{visible:this._live?.phoneMeter.actor.visible,active:this._live?.phoneMeter.active,level:this._live?.phoneMeter.level,opacity:this._live?.phoneMeter.actor.opacity,x:this._live?.phoneMeter.actor.x,y:this._live?.phoneMeter.actor.y,width:this._live?.phoneMeter.actor.width,height:this._live?.phoneMeter.actor.height}, connectionNotice:{active:this._live?.notice.active,width:this._live?.notice.actor.width,height:this._live?.notice.actor.height}, events:this._live?.events ?? [], transient:this._live?.active ?? '', transientText:this._live?.label.text ?? '', fullscreen:this._floating?.fullscreen, islandVisible:this._floating?.actor.visible, artworkLoaded:this._albumArt?.loaded, toolsOpen:Boolean(this._tools?.systemMenu.menu.isOpen), focusActive:Boolean(this._tools?.until), player:this._playerName,
            volume:this._tools?.volume.text, dnd:this._tools?.dnd.state,
            reducedMotion:!this._settings.get_boolean('enable-animations')};
    }
    disable() {
        this._claude?.destroy();this._claude=null;
        if(this._commandTimer) GLib.Source.remove(this._commandTimer);this._commandTimer=0;
        this._live?.destroy();this._live=null;
        this._title?.remove_all_transitions();this._artist?.remove_all_transitions();
        this._liquid?.destroy();this._liquid=null;
        this._albumArt?.destroy();this._albumArt=null;
        this._tools?.destroy(); this._tools = null;
        this._players?.destroy(); this._players = null;
        this._floating?.destroy(); this._floating = null;
        this._cast?.disable();
        this._cast = null;
        this._alive = false;
        this._cancellable?.cancel();
        this._cancelClose();
        for (const id of [this._timer,this._waveTimer]) if (id) GLib.Source.remove(id);
        this._timer = this._waveTimer = 0;
        if (this._sessionId) Main.sessionMode.disconnect(this._sessionId);
        this._sessionId = 0;
        if (this._proxy) {
            if (this._propertyId) this._proxy.disconnect(this._propertyId);
            if (this._ownerId) this._proxy.disconnect(this._ownerId);
        }
        this._bridge?.unexport(); this._bridge = null;
        if (this._clock && this._clockParent) {
            this._clock.get_parent()?.remove_child(this._clock);
            this._clockParent.insert_child_at_index(this._clock,this._clockIndex);
        }
        this._indicator?.destroy(); this._indicator = null;
        this._proxy = null; this._settings = null; this._clock = null;
    }
}
