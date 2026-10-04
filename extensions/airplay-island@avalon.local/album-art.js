import Gio from 'gi://Gio';
import Soup from 'gi://Soup?version=3.0';
import Clutter from 'gi://Clutter';

export class AlbumArt {
    constructor(icon,animate,onArtwork) {
        this.icon=icon;this.animate=animate;this.onArtwork=onArtwork;this.alive=true;this.key=null;
        this.session=new Soup.Session({timeout:6});
    }
    update(url,track) {
        const key=`${track}:${url}`;
        if (key===this.key) return;
        this.key=key;this.cancellable?.cancel();this.cancellable=new Gio.Cancellable();
        this.icon.remove_all_transitions();this.icon.opacity=255;this.loaded=false;
        if (!url || typeof url!=='string') {this.replace(null);return;}
        if (url.startsWith('file://')) {
            const file=Gio.File.new_for_uri(url);
            file.query_info_async('standard::type,standard::size',Gio.FileQueryInfoFlags.NONE,0,this.cancellable,(f,result)=>{
                if (!this.alive || key!==this.key) return;
                try {
                    const info=f.query_info_finish(result);
                    if (info.get_file_type()===Gio.FileType.REGULAR && info.get_size()<4*1024*1024) {
                        this.replace(new Gio.FileIcon({file:f}));this.loaded=true;
                    }
                } catch { this.replace(null); }
            });
        } else if (/^https?:\/\//.test(url)) {
            const message=Soup.Message.new('GET',url);
            if (!message) return;
            this.session.send_and_read_async(message,0,this.cancellable,(session,result)=>{
                if (!this.alive || key!==this.key) return;
                try {
                    const bytes=session.send_and_read_finish(result);
                    if (message.status_code===200 && bytes.get_size()<4*1024*1024) {
                        this.replace(new Gio.BytesIcon({bytes}));this.loaded=true;
                    }
                } catch { this.replace(null); }
            });
        }
    }
    replace(gicon) {
        const key=this.key;
        const apply=()=>{
            if(!this.alive || key!==this.key) return;
            this.icon.gicon=gicon;this.onArtwork?.(gicon);
            if(!gicon) this.icon.icon_name='audio-x-generic-symbolic';
            this.icon.icon_size=gicon ? 64 : 30;
            this.icon.ease({opacity:255,duration:this.animate?.() ? 180 : 0,mode:Clutter.AnimationMode.EASE_OUT_CUBIC});
        };
        this.icon.remove_all_transitions();
        if(this.animate?.()) this.icon.ease({opacity:0,duration:100,onComplete:apply});
        else apply();
    }
    destroy() {this.icon.remove_all_transitions(); this.alive=false;this.cancellable?.cancel();this.session.abort(); }
}
