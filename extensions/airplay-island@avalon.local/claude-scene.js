import St from 'gi://St';
import GLib from 'gi://GLib';
import Cairo from 'cairo';
import Clutter from 'gi://Clutter';

const LABELS = {starting:'Claude · до роботи', editing:'Claude · будує', testing:'Claude · перевіряє',
    failed:'блять…', permission:'Claude · потрібен дозвіл', done:'Claude · кава', working:'Claude · працює'};

export class ClaudeScene {
    constructor(owner) {
        this.owner = owner;
        this.state = '';
        this.floors = 0;
        this.x = 10;
        this.actor = new St.DrawingArea({width:210, height:24, visible:false,
            y_align:Clutter.ActorAlign.CENTER, accessible_name:'Claude'});
        owner._pill.add_child(this.actor);
        this.actor.connect('repaint', area => this.draw(area));
        this.timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 80, () => {
            if (this.state) {
                if (GLib.get_monotonic_time() > this.until) {
                    this.state = ''; this.sync();
                } else if (this.actor.mapped && owner._settings.get_boolean('enable-animations')) {
                    const target = this.target();
                    this.x += Math.max(-3, Math.min(3, target - this.x));
                    this.actor.queue_repaint();
                }
            }
            return GLib.SOURCE_CONTINUE;
        });
    }
    target() { return this.state === 'permission' ? 195 : this.state === 'testing' ? 126 : this.state === 'done' ? 20 : 56; }
    present(state) {
        if (!Object.hasOwn(LABELS, state)) return false;
        if (state === 'starting') { this.floors = 0; this.x = 10; }
        if (state === 'editing') this.floors = Math.min(4, this.floors + 1);
        this.state = state;
        this.since = GLib.get_monotonic_time();
        this.until = this.since + (state === 'done' ? 15 : 180) * 1000000;
        this.actor.accessible_name = LABELS[state];
        this.sync();
        this.actor.queue_repaint();
        return true;
    }
    sync() {
        // Volume, connection notices and focus timers retain priority.
        const visible = Boolean(this.state) && !this.owner._live?.active && !this.owner._tools?.until;
        this.actor.visible = visible;
        this.owner._mediaRow.visible = !visible;
        const width = this.owner._live?.active ? 248 : visible ? 232 : this.owner._playing ? 156 : 128;
        this.owner._floating?.actor.set_width(width);
    }
    draw(area) {
        const cr = area.get_context();
        const [w, h] = area.get_surface_size();
        cr.scale(w / 210, h / 24);
        const animated = this.owner._settings.get_boolean('enable-animations');
        const t = animated ? (GLib.get_monotonic_time() - this.since) / 1000000 : 1;
        const x = animated ? this.x : this.target();
        const line = (a,b,c,d) => {cr.moveTo(a,b); cr.lineTo(c,d); cr.stroke();};
        cr.setLineWidth(1.4); cr.setLineCap(Cairo.LineCap.ROUND);
        cr.setSourceRGBA(.45,.5,.58,1); line(5,23,205,23);
        // Desk and monitor.
        cr.setSourceRGBA(.85,.7,.5,1); line(45,16,85,16); line(48,16,48,23); line(82,16,82,23);
        cr.setSourceRGBA(.6,.85,1,1); cr.rectangle(67,5,13,8); cr.stroke(); line(73,13,73,16);
        // Each edit adds a storey; the newest storey grows into place.
        const growth = this.state === 'editing' ? Math.min(1,t / .6) : 1;
        const floors = Math.max(0,this.floors - 1) + (this.floors ? growth : 0);
        cr.setSourceRGBA(this.state === 'failed' ? .95 : .5,.65,.72,1);
        cr.rectangle(98,22-floors*4,22,floors*4); cr.stroke();
        for (let i=0; i<Math.floor(floors); i++) {line(102,20-i*4,105,20-i*4);line(112,20-i*4,115,20-i*4);}
        const bob = Math.abs(x-this.target())>2 ? Math.sin(t*12) : 0;
        cr.setSourceRGBA(1,.88,.73,1);
        cr.arc(x,7+bob,2.5,0,Math.PI*2); cr.stroke(); line(x,10+bob,x,17);
        const sitting = this.state === 'done';
        line(x,17,x-4,22); line(x,17,x+(sitting?7:4),sitting?17:22);
        if (this.state === 'permission') {
            line(x,12,x-5,15); line(x,12,x+4,9);line(x+4,9,x+5+Math.sin(t*9)*2,3);
        } else if (this.state === 'testing') {
            line(x,12,x-5,12); cr.arc(x-8,11,3,0,Math.PI*2);cr.stroke();line(x-6,14,x-4,17);
        } else {
            const tap = this.state === 'editing' ? Math.sin(t*18)*1.5 : 0;
            line(x,12,x+7,14+tap);line(x,12,x+3,15-tap);
        }
        if (sitting) {
            cr.setSourceRGBA(.9,.9,.95,1); cr.rectangle(x+6,10,4,4);cr.stroke();
            line(x+10,11,x+12,11);line(x+12,11,x+12,13);line(x+12,13,x+10,13);
            cr.setSourceRGBA(.55,.4,.3,1);line(x-4,18,x+3,18);line(x-4,18,x-4,23);
        }
        if (this.state === 'failed') {
            cr.setSourceRGBA(.7,.7,.75,.65);
            for(let i=0;i<3;i++) {const rise=(t*7+i*4)%12;cr.arc(105+i*4+Math.sin(t+i)*2,10-rise,2+i*.5,0,Math.PI*2);cr.fill();}
        }
        cr.setSourceRGBA(1,.92,.85,1);cr.selectFontFace('Sans',Cairo.FontSlant.NORMAL,Cairo.FontWeight.NORMAL);cr.setFontSize(8);
        cr.moveTo(137, this.state === 'permission' ? 23 : 13);
        cr.showText(this.state === 'failed' ? 'блять…' : this.state === 'permission' ? 'Дозвіл?' : this.state === 'testing' ? 'Тести' : this.state === 'done' ? 'Кава ☕' : 'Claude');
        cr.$dispose();
    }
    destroy() { if(this.timer) GLib.Source.remove(this.timer);this.timer=0;this.actor.destroy(); }
}
