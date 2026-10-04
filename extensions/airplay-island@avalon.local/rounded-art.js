import Clutter from 'gi://Clutter';

// Clip the actual offscreen artwork, not just its background's border radius.
export function roundArtwork(actor,radius) {
    const effect=new Clutter.ShaderEffect({shader_type:Clutter.ShaderType.FRAGMENT_SHADER});
    effect.set_shader_source(`
        uniform sampler2D tex;
        uniform float corner;
        uniform float edge;
        void main() {
            vec2 uv=cogl_tex_coord_in[0].xy;
            vec2 q=abs(uv-vec2(0.5))-vec2(0.5-corner);
            float distance=length(max(q,vec2(0.0)))+min(max(q.x,q.y),0.0)-corner;
            float mask=1.0-smoothstep(-edge,edge,distance);
            cogl_color_out=texture2D(tex,uv)*cogl_color_in*mask;
        }
    `);
    const update=()=>{
        const size=Math.max(1,Math.min(actor.width,actor.height));
        effect.set_uniform_value('corner',parseFloat(Math.min(.49,radius/size)));
        effect.set_uniform_value('edge',parseFloat(.5/size));
    };
    actor.connect('notify::allocation',update);update();actor.add_effect_with_name('ai-rounded-art',effect);
}
