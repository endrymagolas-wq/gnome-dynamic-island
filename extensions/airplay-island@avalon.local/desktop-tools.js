import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Clutter from 'gi://Clutter';
import St from 'gi://St';
import Pango from 'gi://Pango';
import {DailyTools} from './daily-tools.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

export class DesktopTools {
    constructor(owner) {
        this.owner = owner;
        this.alive = true;
        this.until = 0;
        this.focusFile=Gio.File.new_for_path(GLib.build_filenamev([GLib.get_user_cache_dir(),'cortiva-focus-until']));
        try {
            const [ok,data]=this.focusFile.load_contents(null);
            const until=Number(new TextDecoder().decode(data));
            if(ok && until>0 && until<GLib.get_real_time()+14400000000) this.until=until;
        } catch { /* No active saved timer. */ }
        this.cancellable = new Gio.Cancellable();
        this.settings = new Gio.Settings({schema_id:'org.gnome.desktop.notifications'});
        this.mainMenu=owner._indicator.menu;
        this.systemMenu=new PopupMenu.PopupSubMenuMenuItem('Керування ПК',false);
        this.mainMenu.addMenuItem(this.systemMenu);
        this.systemMenu.actor.hide();
        const menu=this.systemMenu.menu;
        this.focus = menu.addAction('Фокус · 25 хвилин', () => {
            this.startFocus(this.until ? 0 : 1500);
        });
        this.dnd = new PopupMenu.PopupSwitchMenuItem('Не турбувати', !this.settings.get_boolean('show-banners'));
        this.dnd.connect('toggled', (_item,state) => this.settings.set_boolean('show-banners',!state));
        this.changed = this.settings.connect('changed::show-banners', () => this.dnd.setToggleState(!this.settings.get_boolean('show-banners')));
        menu.addMenuItem(this.dnd);
        const volume = new PopupMenu.PopupBaseMenuItem({reactive:false,can_focus:false});
        this.volume = new St.Label({text:'Гучність',x_expand:true,y_align:Clutter.ActorAlign.CENTER});
        volume.add_child(this.volume);
        for (const [icon,label,arg] of [['audio-volume-low-symbolic','Тихіше','5%-'],['audio-volume-muted-symbolic','Увімкнути / вимкнути звук','toggle'],['audio-volume-high-symbolic','Гучніше','5%+']]) {
            volume.add_child(owner._button(icon,label,()=>this.adjustVolume(arg)));
        }
        menu.addMenuItem(volume);
        menu.addAction('Знімок екрана', () => {
            this.mainMenu.close();
            this.shot = GLib.timeout_add(GLib.PRIORITY_DEFAULT,220,()=>{
                this.shot=0; Main.screenshotUI.open(); return GLib.SOURCE_REMOVE;
            });
        });
        menu.addAction('Налаштування звуку', () => Gio.Subprocess.new(['gnome-control-center','sound'],Gio.SubprocessFlags.NONE));
        this.historyMenu=new PopupMenu.PopupSubMenuMenuItem('Історія помічника',false);
        this.mainMenu.addMenuItem(this.historyMenu);this.historyMenu.actor.hide();
        const historyRow=new PopupMenu.PopupBaseMenuItem({reactive:false,can_focus:false});
        const historyButton=new St.Button({label:'Історія помічника  ›',reactive:true,can_focus:true,
            accessible_name:'Історія помічника',x_expand:true,x_align:Clutter.ActorAlign.FILL,
            style:'text-align:left;font-size:12px;padding:5px 0;'});
        historyButton.connect('clicked',()=>this.openHistory());historyRow.add_child(historyButton);
        menu.addMenuItem(historyRow);
        this.daily=new DailyTools(owner,this);
        owner._indicator.connect('scroll-event',(_actor,event)=>{
            const direction=event.get_scroll_direction();
            if (direction===Clutter.ScrollDirection.UP) this.adjustVolume('5%+');
            else if (direction===Clutter.ScrollDirection.DOWN) this.adjustVolume('5%-');
            else return Clutter.EVENT_PROPAGATE;
            return Clutter.EVENT_STOP;
        });
        this.timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT,1,()=>{
            this.update(); return GLib.SOURCE_CONTINUE;
        });
        this.update();
    }
    openHistory() {
        this.owner._autoClose();this.refreshHistory();
        this.systemMenu.menu.close(false);this.historyMenu.menu.open(true);
    }
    refreshHistory() {
        const menu=this.historyMenu.menu;
        menu.removeAll();
        const backRow=new PopupMenu.PopupBaseMenuItem({reactive:false,can_focus:false});
        const back=new St.Button({label:'‹  Керування ПК',reactive:true,can_focus:true,
            accessible_name:'Повернутися до керування ПК',x_expand:true,
            style:'text-align:left;font-size:12px;padding:5px 0;'});
        back.connect('clicked',()=>{this.owner._autoClose();this.historyMenu.menu.close(false);this.systemMenu.menu.open(true);});
        backRow.add_child(back);menu.addMenuItem(backRow);
        const data=this.owner._modelStatus();
        const rows=Array.isArray(data?.history)?data.history.slice(0,5):[];
        const stages={queued:'Очікує',shown:'Показано',recovered:'Стан покращився',expired:'Минуло',superseded:'Оновлено',quiet:'Без повтору'};
        const label=(text,size,color)=>{
            const item=new St.Label({text:String(text).replace(/[\x00-\x1f\x7f]/g,'').slice(0,100),
                x_expand:true,x_align:Clutter.ActorAlign.FILL,width:276,style:`font-size:${size}px;color:${color};`});
            item.clutter_text.set_ellipsize(Pango.EllipsizeMode.END);
            item.clutter_text.set_line_wrap(false);item.clutter_text.set_single_line_mode(true);
            return item;
        };
        if(!rows.length){menu.addMenuItem(new PopupMenu.PopupMenuItem(data?'Поки немає подій':'Помічник недоступний',{reactive:false}));return;}
        for(const row of rows){
            if(!row || typeof row.title!=='string' || !Number.isFinite(row.at))continue;
            const item=new PopupMenu.PopupBaseMenuItem({reactive:false,can_focus:false});
            const box=new St.BoxLayout({vertical:true,x_expand:true,x_align:Clutter.ActorAlign.FILL,clip_to_allocation:true,style:'width:276px;spacing:3px;'});
            const date=GLib.DateTime.new_from_unix_local(Math.floor(Math.max(0,Math.min(row.at,Date.now()/1000))));
            box.add_child(label(`${date.format('%H:%M')} · ${row.title}`,12,'#f5f5f7'));
            box.add_child(label(`${stages[row.stage]??'Подія'} · ${row.message??''}`,10,'#a1a1aa'));
            if(row.advice)box.add_child(label(row.advice,10,'#c4c4cc'));
            if(row.kind){
                const alreadyMuted=this.daily.readPreferences().muted_kinds.includes(row.kind);
                const mute=new St.Button({label:alreadyMuted?'Категорію вимкнено':'Не показувати цю категорію',reactive:true,can_focus:true,accessible_name:`Не показувати ${row.title}`,style:'font-size:10px;color:#a1a1aa;padding:3px 0;'});
                mute.connect('clicked',()=>this.daily.mute(row.kind,mute));box.add_child(mute);
            }
            item.add_child(box);menu.addMenuItem(item);
        }
    }
    saveFocus() {
        try {this.focusFile.replace_contents(new TextEncoder().encode(String(this.until)),null,false,Gio.FileCreateFlags.PRIVATE,null);}
        catch(error) {console.warn(`Island focus storage: ${error.message}`);}
    }
    startFocus(seconds) {
        seconds=Math.max(0,Math.min(14400,Number(seconds) || 0));
        this.until=seconds ? GLib.get_real_time()+seconds*1000000 : 0;
        this.saveFocus();this.update();
    }
    adjustVolume(arg) {
        const args=arg==='toggle' ? ['wpctl','set-mute','@DEFAULT_AUDIO_SINK@','toggle'] : ['wpctl','set-volume','-l','1.0','@DEFAULT_AUDIO_SINK@',arg];
        this.run(args,()=>this.readVolume());
    }
    run(args,callback) {
        try {
            const proc=Gio.Subprocess.new(args,Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_PIPE);
            proc.communicate_utf8_async(null,this.cancellable,(p,result)=>{
                if (!this.alive) return;
                try {
                    const [,out]=p.communicate_utf8_finish(result);
                    if (p.get_successful()) callback?.(out);
                    else this.volume.text='Аудіовихід недоступний';
                } catch { this.volume.text='Аудіовихід недоступний'; }
            });
        } catch { this.volume.text='Аудіовихід недоступний'; }
    }
    readVolume() {
        this.run(['wpctl','get-volume','@DEFAULT_AUDIO_SINK@'],out=>{
            const match=out.match(/Volume:\s+([\d.]+)/);
            this.volume.text=match ? `Гучність · ${Math.round(Number(match[1])*100)}%${out.includes('MUTED') ? ' · без звуку':''}` : 'Аудіовихід недоступний';
        });
    }
    update() {
        this.daily?.updateState();
        if (this.until && GLib.get_real_time()>=this.until && this.owner._live) {
            this.until=0; this.saveFocus(); this.owner._live?.focusFinished(); Main.notify('Фокус завершено','25 хвилин минуло. Час зробити паузу.');
        }
        const seconds=this.until ? Math.max(0,Math.ceil((this.until-GLib.get_real_time())/1000000)) : 0;
        const time=`${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
        this.owner._focusLabel.text=this.until ? time : GLib.DateTime.new_now_local().format('%H:%M');
        this.owner._focusLabel.visible=!this.owner._live?.active;
        this.focus.label.text=this.until ? `Зупинити фокус · ${time}` : 'Фокус · 25 хвилин';
        if (this.owner._indicator.menu.isOpen && !this.volumeBusy) {
            this.volumeBusy=true;
            this.run(['wpctl','get-volume','@DEFAULT_AUDIO_SINK@'],out=>{
                this.volumeBusy=false;
                const match=out.match(/Volume:\s+([\d.]+)/);
                this.volume.text=match ? `Гучність · ${Math.round(Number(match[1])*100)}%${out.includes('MUTED') ? ' · без звуку':''}` : 'Аудіовихід недоступний';
            });
        }
    }
    destroy() {
        this.alive=false; this.cancellable.cancel();this.daily?.destroy();
        if (this.timer) GLib.Source.remove(this.timer);
        if (this.shot) GLib.Source.remove(this.shot);
        this.settings.disconnect(this.changed);
    }
}
