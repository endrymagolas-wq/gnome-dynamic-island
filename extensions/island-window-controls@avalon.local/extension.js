import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

// Explicit profiles prevent unknown titlebars, tabs and dialogs being covered.
// No application resources or compositor prototypes are changed.
export default class WindowControls extends Extension {
    enable() {
        this._windows = new Map();
        this._signals = [];
        this._pending = new Set();
        this._tracker = Shell.WindowTracker.get_default();
        const [, bytes] = Gio.File.new_for_path(`${this.path}/profiles.json`).load_contents(null);
        this._profiles = JSON.parse(new TextDecoder().decode(bytes)).map(p => ({...p, regex: new RegExp(p.match, 'i')}));
        this._connect(global.display, 'window-created', (_d, window) => this._defer(window));
        this._connect(global.display, 'notify::focus-window', () => this._syncAll());
        this._connect(Main.overview, 'showing', () => this._syncAll());
        this._connect(Main.overview, 'hidden', () => this._syncAll());
        this._connect(Main.sessionMode, 'updated', () => this._syncAll());
        this._connect(global.display, 'grab-op-begin', () => {this._grabbing = true;});
        this._connect(global.display, 'grab-op-end', () => {this._grabbing = false; this._syncAll();});
        for (const actor of global.get_window_actors()) this._attach(actor.meta_window);
        this._colorTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 2000, () => {
            for (const entry of this._windows.values()) this._sampleColor(entry);
            return GLib.SOURCE_CONTINUE;
        });
    }
    _connect(object, name, callback) {
        this._signals.push([object, object.connect(name, callback)]);
    }
    _defer(window) {
        const id = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            this._pending.delete(id);
            this._attach(window);
            return GLib.SOURCE_REMOVE;
        });
        this._pending.add(id);
    }
    _attach(window) {
        if (this._windows.has(window) || window.get_window_type() !== Meta.WindowType.NORMAL || window.get_transient_for()) return;
        const actor = window.get_compositor_private();
        if (!actor) return;
        const app = this._tracker.get_window_app(window);
        const ids = [window.get_wm_class(), window.get_gtk_application_id(), app?.get_id()].filter(Boolean);
        const profile = this._profiles.find(p => ids.some(id => p.regex.test(id)));
        if (!profile) return;
        const box = new St.BoxLayout({reactive: true, height: profile.height, width: profile.width,
            style: `background-color: ${profile.background}; padding: 0 10px 0 0; spacing: 0;`,
            x_align: Clutter.ActorAlign.END, y_align: Clutter.ActorAlign.START});
        const spacer = new St.Widget({x_expand: true});
        box.add_child(spacer);
        const entry = {actor, box, window, profile, signals: [], buttons: []};
        for (const [label, color, symbol, action] of [
            ['Згорнути', '#ffbd2e', '−', () => window.minimize()],
            ['Розгорнути або відновити', '#28c840', '+', () => {
                if (window.get_maximized() === Meta.MaximizeFlags.BOTH) window.unmaximize(Meta.MaximizeFlags.BOTH);
                else window.maximize(Meta.MaximizeFlags.BOTH);
            }],
            ['Закрити', '#ff5f57', '×', () => window.delete(global.get_current_time())],
        ]) {
            const dot = new St.DrawingArea({width: 14, height: 14, style_class: 'cw-dot',
                x_align: Clutter.ActorAlign.CENTER, y_align: Clutter.ActorAlign.CENTER});
            const button = new St.Button({child: dot, reactive: true, can_focus: true, accessible_name: label,
                width: 24, height: profile.height, style_class: 'cw-button'});
            dot.connect('repaint', area => {
                const cr=area.get_context();
                const [w,h]=area.get_surface_size();
                const rgb=[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)/255);
                cr.setSourceRGB(...rgb);cr.arc(w/2,h/2,Math.min(w,h)/2-.5,0,Math.PI*2);cr.fill();
                if(button.hover) {
                    cr.setSourceRGBA(.1,.1,.1,.65);cr.setLineWidth(1);cr.setLineCap(1);
                    if(symbol==='×') {
                        cr.moveTo(w/2-2,h/2-2);cr.lineTo(w/2+2,h/2+2);
                        cr.moveTo(w/2+2,h/2-2);cr.lineTo(w/2-2,h/2+2);
                    } else {
                        cr.moveTo(w/2-2.5,h/2);cr.lineTo(w/2+2.5,h/2);
                        if(symbol==='+'){cr.moveTo(w/2,h/2-2.5);cr.lineTo(w/2,h/2+2.5);}
                    }
                    cr.stroke();
                }
                cr.$dispose();
            });
            button.connect('notify::hover',()=>dot.queue_repaint());
            button.connect('clicked', () => {
                if (!this._windows.has(window) || !button.reactive) return;
                // Return keyboard input to the client after using Shell controls.
                global.stage.set_key_focus(null);
                action();
            });
            box.add_child(button);
            entry.buttons.push(button);
        }
        actor.add_child(box);
        Main.layoutManager.trackChrome(box, {affectsStruts: false, affectsInputRegion: true, trackFullscreen: false});
        this._windows.set(window, entry);
        for (const name of ['position-changed', 'size-changed', 'notify::fullscreen', 'notify::minimized'])
            entry.signals.push([window, window.connect(name, () => this._sync(entry))]);
        entry.signals.push([window, window.connect('unmanaged', () => this._detach(window))]);
        this._sync(entry);
    }
    _sync(entry) {
        const {window, box, profile} = entry;
        const frame = window.get_frame_rect(), buffer = window.get_buffer_rect();
        box.set_position(frame.x - buffer.x + frame.width - profile.width, frame.y - buffer.y);
        box.visible = !window.minimized && !window.is_fullscreen() && frame.width >= profile.width + 100 &&
            !Main.overview.visible && !Main.sessionMode.isLocked && !Main.sessionMode.isGreeter;
        box.opacity = 255;
        entry.buttons[0].reactive = window.can_minimize();
        entry.buttons[1].reactive = window.can_maximize();
        entry.buttons[2].reactive = window.can_close();
        for (const button of entry.buttons) {
            button.can_focus = button.reactive;
            button.opacity = button.reactive ? (window.has_focus() ? 255 : 150) : 80;
        }
        this._sampleColor(entry);
    }
    async _sampleColor(entry) {
        const {window, box, profile, actor} = entry;
        if (entry.sampling || !box.visible || !window.has_focus() || this._grabbing) return;
        const now = GLib.get_monotonic_time();
        if (entry.sampledAt && now - entry.sampledAt < 1500000) return;
        const frame = window.get_frame_rect();
        const x = Math.round(frame.x + frame.width - profile.width - 6), y = Math.round(frame.y + 4);
        if (x < 0 || y < 0 || x >= global.stage.width || y >= global.stage.height) return;
        const hit = global.stage.get_actor_at_pos(Clutter.PickMode.ALL, x, y);
        if (!hit || (hit !== actor && !actor.contains(hit))) return;
        entry.sampling = true;
        entry.sampledAt = now;
        try {
            const screenshot = new Shell.Screenshot();
            const [color] = await screenshot.pick_color(x, y);
            if (this._windows.get(window) !== entry || !window.has_focus()) return;
            const current = window.get_frame_rect();
            if (current.x !== frame.x || current.y !== frame.y || current.width !== frame.width) return;
            const background = `rgb(${color.red},${color.green},${color.blue})`;
            if (background !== entry.background) {
                entry.background = background;
                box.set_style(`background-color: ${background}; padding: 0 10px 0 0; spacing: 0;`);
            }
        } catch (error) {
            // Retain the explicit profile fallback when sampling is unavailable.
        } finally {
            entry.sampling = false;
        }
    }
    _syncAll() {for (const entry of this._windows.values()) this._sync(entry);}
    _detach(window) {
        const entry = this._windows.get(window);
        if (!entry) return;
        this._windows.delete(window);
        for (const [object, id] of entry.signals) object.disconnect(id);
        Main.layoutManager.untrackChrome(entry.box);
        entry.box.destroy();
    }
    disable() {
        if (this._colorTimer) GLib.Source.remove(this._colorTimer);
        this._colorTimer = 0;
        for (const id of this._pending ?? []) GLib.Source.remove(id);
        this._pending?.clear();
        for (const [object, id] of this._signals ?? []) object.disconnect(id);
        this._signals = [];
        for (const window of [...(this._windows?.keys() ?? [])]) this._detach(window);
    }
}
