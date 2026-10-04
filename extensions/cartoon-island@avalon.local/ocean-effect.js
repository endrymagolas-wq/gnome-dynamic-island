import Shell from 'gi://Shell';
import GObject from 'gi://GObject';
import Gio from 'gi://Gio';
import {CAMERA} from './world.js';
const file=Gio.File.new_for_uri(import.meta.url).get_parent().get_child('ocean.glsl');
const [,bytes]=file.load_contents(null);const source=new TextDecoder().decode(bytes);
export const OceanEffect=GObject.registerClass(class OceanEffect extends Shell.GLSLEffect {
    vfunc_build_pipeline(){this.add_glsl_snippet(Shell.SnippetHook.FRAGMENT,source,'cogl_color_out=oceanPixel(cogl_tex_coord_in[0].st)*cogl_color_in;',true);}
    update(time,width,height){
        if(!this.uniforms){this.uniforms={};for(const key of ['waterTime','waterSize','waterYaw','waterPitch'])this.uniforms[key]=this.get_uniform_location(key);}
        this.set_uniform_float(this.uniforms.waterTime,1,[time]);
        this.set_uniform_float(this.uniforms.waterSize,2,[width,height]);
        this.set_uniform_float(this.uniforms.waterYaw,1,[CAMERA.yaw]);
        this.set_uniform_float(this.uniforms.waterPitch,1,[CAMERA.pitch]);
    }
});
