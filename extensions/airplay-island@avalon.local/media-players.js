import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
export class MediaPlayers {
    constructor(owner) {
        this.owner=owner; this.alive=true; this.players=new Map(); this.pending=new Set();
        this.cancellable=new Gio.Cancellable();
        this.timer=GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT,5,()=>{
            this.refresh(); return GLib.SOURCE_CONTINUE;
        });
        this.refresh();
    }
    refresh() {
        if (this.busy) return;
        this.busy=true;
        Gio.DBus.session.call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ListNames',null,
            new GLib.VariantType('(as)'),Gio.DBusCallFlags.NONE,3000,this.cancellable,(connection,result)=>{
                if (!this.alive) return;
                this.busy=false;
                try {
                    const [names]=connection.call_finish(result).deepUnpack();
                    const available=names.filter(name=>name.startsWith('org.mpris.MediaPlayer2.'));
                    for (const [name,entry] of this.players) if (!available.includes(name)) {
                        for (const id of entry.ids) entry.proxy.disconnect(id);
                        this.players.delete(name);
                    }
                    for (const name of available) if (!this.players.has(name) && !this.pending.has(name)) {
                        this.pending.add(name);
                        Gio.DBusProxy.new_for_bus(Gio.BusType.SESSION,Gio.DBusProxyFlags.DO_NOT_AUTO_START,null,name,
                            '/org/mpris/MediaPlayer2','org.mpris.MediaPlayer2.Player',this.cancellable,(_source,res)=>{
                                if (!this.alive) return;
                                this.pending.delete(name);
                                try {
                                    const proxy=Gio.DBusProxy.new_for_bus_finish(res);
                                    const ids=[proxy.connect('g-properties-changed',()=>this.choose()),proxy.connect('notify::g-name-owner',()=>this.choose())];
                                    this.players.set(name,{proxy,ids}); this.choose();
                                } catch (error) { console.warn(`Island player: ${error.message}`); }
                            });
                    }
                    this.choose();
                } catch (error) { console.warn(`Island media: ${error.message}`); }
            });
    }
    choose() {
        const entries=[...this.players].filter(([,e])=>e.proxy.get_name_owner());
        const status=e=>e.proxy.get_cached_property('PlaybackStatus')?.deepUnpack() ?? 'Stopped';
        const score=([name,e])=>(status(e)==='Playing' ? 20 : status(e)==='Paused' ? 10 : 0)+(name.includes('ShairportSync') ? 0 : 1);
        entries.sort((a,b)=>score(b)-score(a));
        this.owner._proxy=entries[0]?.[1].proxy ?? null;
        this.owner._playerName=entries[0]?.[0] ?? '';
        this.owner._update();
    }
    destroy() {
        this.alive=false; this.cancellable.cancel();
        if (this.timer) GLib.Source.remove(this.timer);
        for (const entry of this.players.values()) for (const id of entry.ids) entry.proxy.disconnect(id);
        this.players.clear();
    }
}
