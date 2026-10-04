import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// Animate the existing native popup so focus, Escape and outside-click grabs stay native.
export class LiquidIsland {
    constructor(owner) {
        this.owner = owner;
        this.menu = owner._indicator.menu;
        this.surface = this.menu._boxPointer;
        this.content = this.surface.bin;
        this.originalOpen = this.surface.open;
        this.originalClose = this.surface.close;
        this.originalReposition = this.surface._reposition;
        this.surface.set_pivot_point(.5, 0);
        this.surface._reposition = box => {
            this.originalReposition.call(this.surface, box);
            const m = Main.layoutManager.primaryMonitor;
            const [, , width] = this.surface.get_preferred_size();
            const [ok, x, y] = this.surface.get_parent().transform_stage_point(
                Math.round(m.x + (m.width - width) / 2), m.y + 6);
            if (ok) box.set_origin(x, y);
        };
        this.surface.open = (_animation, onComplete) => this.open(onComplete);
        this.surface.close = (_animation, onComplete) => this.close(onComplete);
        this.hoverId = owner._indicator.connect('notify::hover', () => this.rest());
        owner._pill.set_pivot_point(.5, .5);
    }
    get duration() { return this.owner._settings.get_boolean('enable-animations') ? 440 : 0; }
    rest() {
        if (this.menu.isOpen) return;
        this.owner._pill.ease({scale_x:this.owner._indicator.hover ? 1.04 : 1,
            scale_y:this.owner._indicator.hover ? 1.06 : 1,
            duration:this.duration ? 180 : 0,mode:Clutter.AnimationMode.EASE_OUT_CUBIC});
    }
    pulse() {
        if (this.menu.isOpen || !this.duration) return;
        const pill = this.owner._pill;
        pill.remove_all_transitions();
        pill.ease({scale_x:1.08, scale_y:1.12, duration:180,
            mode:Clutter.AnimationMode.EASE_OUT_CUBIC, onComplete:() => this.rest()});
    }
    open(onComplete) {
        const a = this.surface;
        const reopening = a.visible;
        a.remove_all_transitions(); this.content.remove_all_transitions();
        const [, , width, height] = a.get_preferred_size();
        a.translation_x = 0; a.translation_y = 0;
        a.opacity = 255; a._muteKeys = false; a._muteInput = true;
        if (!reopening) {
            a.scale_x = (this.owner._floating?.actor.width ?? 128) / width;
            a.scale_y = 26 / height;
            this.content.opacity = 0;
        }
        a.show();
        this.owner._pill.opacity = 0;
        this.content.ease({opacity:255, delay:this.duration ? 120 : 0,
            duration:this.duration ? 180 : 0, mode:Clutter.AnimationMode.EASE_OUT_QUAD});
        a.ease({scale_x:1, scale_y:1, duration:this.duration,
            mode:Clutter.AnimationMode.EASE_OUT_BACK,
            onComplete:() => {a._muteInput = false; onComplete?.();}});
    }
    close(onComplete) {
        const a = this.surface;
        if (!a.visible) return;
        a.remove_all_transitions(); this.content.remove_all_transitions();
        a._muteInput = true; a._muteKeys = true;
        this.content.ease({opacity:0,duration:this.duration ? 100 : 0});
        const [, , width, height] = a.get_preferred_size();
        a.ease({scale_x:(this.owner._floating?.actor.width ?? 128) / width,
            scale_y:26 / height, duration:this.duration ? 280 : 0,
            mode:Clutter.AnimationMode.EASE_IN_OUT_CUBIC,
            onComplete:() => {
                a.hide(); a.scale_x=1; a.scale_y=1;
                this.content.opacity=255; this.owner._pill.opacity=255;
                this.rest(); onComplete?.();
            }});
    }
    destroy() {
        this.owner._indicator.disconnect(this.hoverId);
        this.surface.remove_all_transitions(); this.content.remove_all_transitions();
        this.surface.open=this.originalOpen; this.surface.close=this.originalClose;
        this.surface._reposition=this.originalReposition;
        this.surface.scale_x=1; this.surface.scale_y=1;
        this.content.opacity=255; this.owner._pill.opacity=255;
    }
}
