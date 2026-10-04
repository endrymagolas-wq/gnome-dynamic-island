import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Clutter from 'gi://Clutter';
import St from 'gi://St';
import Pango from 'gi://Pango';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Slider} from 'resource:///org/gnome/shell/ui/slider.js';
import {getMixerControl} from 'resource:///org/gnome/shell/ui/status/volume.js';

const KINDS={connection:'Підключення AirPlay',download:'Завантаження',cpu:'Навантаження CPU',ram:'Пам’ять',task:'Довгі задачі',service:'Збої служб',disk:'Місце на диску',network:'Стан мережі'};
const clean=(value,max=72)=>String(value??'').replace(/[\x00-\x1f\x7f]/g,'').slice(0,max);
export class DailyTools {
    constructor(owner,tools) {
        this.owner=owner;this.tools=tools;this.alive=true;this.busy=false;this.cancel=new Gio.Cancellable();this.streamSignals=[];this.controlSignals=[];this.dragging=0;
        this.base=GLib.build_filenamev([GLib.get_home_dir(),'.local','share','island-desktop','assistant']);
        this.dataDir=GLib.getenv('ISLAND_ASSISTANT_DATA_DIR')||this.base;
        this.settingsMenu=this.page('Помічник');this.diagnosticMenu=this.page('Ресурси');this.mixerMenu=this.page('Звук програм');
        this.addButton(tools.systemMenu.menu,'Чому комп гальмує?',()=>this.openDiagnosis());
        this.addButton(tools.systemMenu.menu,'Звук окремих програм',()=>this.openMixer());
        this.addButton(tools.systemMenu.menu,'Налаштування помічника',()=>this.openSettings());
        this.mixerMenu.menu.connect('open-state-changed',(_menu,open)=>{if(!open)this.clearStreams();});
        this.control=getMixerControl();
        for(const signal of ['stream-added','stream-removed','state-changed'])this.controlSignals.push(this.control.connect(signal,()=>this.scheduleMixer()));
    }
    page(title) {
        const item=new PopupMenu.PopupSubMenuMenuItem(title,false);
        this.owner._indicator.menu.addMenuItem(item);item.actor.hide();return item;
    }
    label(text,size=12,color='#f5f5f7') {
        const label=new St.Label({text:clean(text,100),width:276,x_expand:true,x_align:Clutter.ActorAlign.FILL,
            style:`font-size:${size}px;color:${color};`});
        label.clutter_text.set_ellipsize(Pango.EllipsizeMode.END);label.clutter_text.set_single_line_mode(true);label.clutter_text.set_line_wrap(false);return label;
    }
    row() {return new PopupMenu.PopupBaseMenuItem({reactive:false,can_focus:false});}
    addButton(menu,text,action) {
        const row=this.row();const button=new St.Button({label:text,reactive:true,can_focus:true,accessible_name:text,x_expand:true,
            x_align:Clutter.ActorAlign.FILL,style:'font-size:12px;padding:5px 0;'});
        button.connect('clicked',()=>{this.owner._autoClose();action();});row.add_child(button);menu.addMenuItem(row);return button;
    }
    header(page) {
        page.menu.removeAll();this.addButton(page.menu,'‹  Керування ПК',()=>{page.menu.close(false);this.tools.systemMenu.menu.open(true);});
    }
    open(page) {
        this.owner._autoClose();this.tools.systemMenu.menu.close(false);this.tools.historyMenu.menu.close(false);page.menu.open(true);
    }
    readPreferences() {
        try {
            const [ok,data]=GLib.file_get_contents(GLib.build_filenamev([this.dataDir,'preferences.json']));
            if(!ok||data.length>4096)throw new Error('invalid');
            const prefs=JSON.parse(new TextDecoder().decode(data));
            return {enabled:prefs.enabled!==false,economy:prefs.economy!==false,muted_kinds:Array.isArray(prefs.muted_kinds)?prefs.muted_kinds.filter(k=>Object.hasOwn(KINDS,k)):[]};
        } catch {return {enabled:true,economy:true,muted_kinds:[]};}
    }
    invoke(args,done) {
        if(this.busy){done?.({ok:false,error:'Дочекайся поточної дії'});return;}
        this.busy=true;
        try {
            const proc=Gio.Subprocess.new(['python3',`${this.base}/assistantctl.py`,...args],Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_PIPE);
            proc.communicate_utf8_async(null,this.cancel,(p,result)=>{
                if(!this.alive)return;
                this.busy=false;
                try {const [,out]=p.communicate_utf8_finish(result);if(out.length>16384)throw new Error('oversized');const reply=JSON.parse(out);done?.(reply);}
                catch {done?.({ok:false,error:'Не вдалося виконати дію'});}
            });
        } catch {this.busy=false;done?.({ok:false,error:'Помічник недоступний'});}
    }
    addText(menu,text,size=12,color='#f5f5f7') {const row=this.row();row.add_child(this.label(text,size,color));menu.addMenuItem(row);return row;}
    openSettings() {this.refreshSettings();this.open(this.settingsMenu);this.updateState();}
    refreshSettings(error=null) {
        const menu=this.settingsMenu.menu;this.header(this.settingsMenu);const prefs=this.readPreferences();
        const enabled=new PopupMenu.PopupSwitchMenuItem('Помічник · моніторинг',prefs.enabled);
        const economy=new PopupMenu.PopupSwitchMenuItem('Економний режим Laya',prefs.economy);
        enabled.connect('toggled',(_item,on)=>this.invoke([on?'on':'off'],reply=>this.refreshSettings(reply.ok?null:reply.error)));
        economy.connect('toggled',(_item,on)=>this.invoke([on?'economy-on':'economy-off'],reply=>this.refreshSettings(reply.ok?null:reply.error)));
        menu.addMenuItem(enabled);menu.addMenuItem(economy);
        this.assistantState=this.addText(menu,'',10,'#a1a1aa').get_children().at(-1);this.updateState();
        if(error)this.addText(menu,error,10,'#f1b4b4');
        this.addText(menu,'Повідомлення',10,'#a1a1aa');
        for(const [kind,title] of Object.entries(KINDS)){
            const toggle=new PopupMenu.PopupSwitchMenuItem(title,!prefs.muted_kinds.includes(kind));
            toggle.connect('toggled',(_item,on)=>this.invoke([on?'unmute':'mute',kind],reply=>this.refreshSettings(reply.ok?null:reply.error)));
            menu.addMenuItem(toggle);
        }
    }
    updateState() {
        if(!this.assistantState||!this.settingsMenu.menu.isOpen)return;
        const prefs=this.readPreferences();const status=this.owner._modelStatus();
        const states={sleeping:'Laya спить',loading:'Laya завантажується',busy:'Laya аналізує подію',ready:'Laya готова'};
        const modelState=status?.classifier?.reason==='unavailable'?'Laya недоступна; працюють базові правила':status?.classifier?.reason==='system_pressure'?'Laya призупинена через навантаження':states[status?.classifier?.state]??'Laya';
        this.assistantState.text=!prefs.enabled?'Помічник вимкнений':status?`Моніторинг працює · ${modelState}`:'Служба запускається або недоступна';
    }
    mute(kind,button) {
        if(!Object.hasOwn(KINDS,kind))return;
        this.invoke(['mute',kind],reply=>{if(button?.get_parent())button.label=reply.ok?'Вимкнено для цієї категорії':'Спробуй ще раз';});
    }
    openDiagnosis() {
        this.header(this.diagnosticMenu);this.addText(this.diagnosticMenu.menu,'Перевіряю ресурси…');this.open(this.diagnosticMenu);
        this.invoke(['diagnose'],reply=>{
            if(!this.diagnosticMenu.menu.isOpen)return;
            this.header(this.diagnosticMenu);const menu=this.diagnosticMenu.menu;const d=reply.diagnosis;
            if(!reply.ok||!d){this.addText(menu,reply.error??'Діагностика недоступна');return;}
            this.addText(menu,d.summary);this.addText(menu,`CPU ${d.cpu}% · RAM ${d.ram}%`,11,'#c4c4cc');
            if(d.top_cpu)this.addText(menu,`${d.top_cpu.name} · ${d.top_cpu.cpu_total_percent}% усіх CPU`,11);
            if(d.top_ram)this.addText(menu,`${d.top_ram.name} · RAM ≈ ${(d.top_ram.rss_mib/1024).toFixed(1)} ГіБ`,11);
            this.addText(menu,d.advice,11,'#c4c4cc');this.addText(menu,'Короткий знімок навантаження',10,'#a1a1aa');
            this.addButton(menu,'Оновити',()=>this.openDiagnosis());
        });
    }
    openMixer() {this.refreshMixer();this.open(this.mixerMenu);}
    scheduleMixer() {
        if(!this.mixerMenu.menu.isOpen)return;
        if(this.dragging){this.mixerPending=true;return;}
        if(this.mixerTimer)return;
        this.mixerTimer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,100,()=>{this.mixerTimer=0;if(this.alive&&this.mixerMenu.menu.isOpen)this.refreshMixer();return GLib.SOURCE_REMOVE;});
    }
    clearStreams() {
        for(const [stream,id] of this.streamSignals){try{stream.disconnect(id);}catch{}}
        this.streamSignals=[];this.mixerRows=[];this.dragging=0;
    }
    refreshMixer() {
        this.clearStreams();this.header(this.mixerMenu);const menu=this.mixerMenu.menu;
        const streams=(this.control.get_sink_inputs()||[]).filter(s=>!s.is_event_stream);
        if(!streams.length){this.addText(menu,'Запусти звук у потрібній програмі',11,'#a1a1aa');return;}
        const grouped=new Map();
        for(const stream of streams){
            const rawName=stream.get_name()||'Програма';
            const key=stream.get_application_id?.()||stream.get_name()||`stream-${stream.get_id()}`;
            if(!grouped.has(key))grouped.set(key,{name:clean(rawName,32),members:[]});
            grouped.get(key).members.push(stream);
        }
        const groups=[...grouped.values()];
        for(const group of groups.slice(0,6)){
            const row=this.row();const box=new St.BoxLayout({vertical:true,x_expand:true,x_align:Clutter.ActorAlign.FILL,clip_to_allocation:true,style:'width:276px;spacing:5px;'});
            const heading=new St.BoxLayout({x_expand:true});const {name,members}=group;
            const title=this.label(members.length>1?`${name} · ${members.length} потоки`:name,12);title.width=236;heading.add_child(title);
            const mute=new St.Button({reactive:true,can_focus:true,accessible_name:`Увімкнути / вимкнути звук ${name}`,child:new St.Icon({icon_name:'audio-volume-high-symbolic',icon_size:16}),style:'padding:2px 4px;'});
            heading.add_child(mute);box.add_child(heading);
            const slider=new Slider(0);slider.x_expand=true;slider.accessible_name=`Гучність усіх потоків ${name}`;box.add_child(slider);row.add_child(box);menu.addMenuItem(row);
            let syncing=false;let inDrag=false;
            const live=()=>members.filter(s=>this.control.lookup_stream_id(s.get_id())===s);
            const sync=()=>{
                if(!slider.get_parent())return;
                const current=live();if(!current.length)return;
                syncing=true;if(!inDrag)slider.value=Math.max(0,Math.min(1,Math.max(...current.map(s=>s.volume))/this.control.get_vol_max_norm()));
                mute.child.icon_name=current.every(s=>s.is_muted)?'audio-volume-muted-symbolic':'audio-volume-high-symbolic';syncing=false;
            };
            slider.connect('notify::value',()=>{
                if(syncing)return;
                const value=Math.max(0,Math.min(1,slider.value));syncing=true;
                for(const stream of live()){stream.volume=Math.round(value*this.control.get_vol_max_norm());stream.push_volume();stream.change_is_muted(value<=0);}
                syncing=false;sync();this.owner._autoClose();
            });
            slider.connect('drag-begin',()=>{inDrag=true;this.dragging++;});slider.connect('drag-end',()=>{inDrag=false;sync();this.dragging=Math.max(0,this.dragging-1);if(this.mixerPending){this.mixerPending=false;this.scheduleMixer();}});
            mute.connect('clicked',()=>{const current=live();const muted=!current.every(s=>s.is_muted);for(const stream of current)stream.change_is_muted(muted);this.owner._autoClose();});
            for(const stream of members)for(const signal of ['notify::volume','notify::is-muted'])this.streamSignals.push([stream,stream.connect(signal,()=>{if(!syncing)sync();})]);
            this.mixerRows.push({ids:members.map(s=>s.get_id()),name,slider,mute});sync();
        }
        if(groups.length>6)this.addText(menu,`Ще ${groups.length-6} програм у налаштуваннях звуку`,10,'#a1a1aa');
    }
    destroy() {
        this.alive=false;this.cancel.cancel();this.clearStreams();if(this.mixerTimer)GLib.Source.remove(this.mixerTimer);
        for(const id of this.controlSignals)this.control.disconnect(id);this.controlSignals=[];
    }
}
