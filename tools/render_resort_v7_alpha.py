"""A geometry alpha matte for V7, including furniture and relocated rocks."""
import bpy, sys, json, hashlib
from pathlib import Path
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
out=Path(sys.argv[sys.argv.index('--')+1]).resolve()
s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=64
s.render.resolution_percentage=100;s.render.film_transparent=True
s.render.use_compositing=False;s.render.image_settings.color_mode='RGBA'
s.render.image_settings.color_depth='8';s.frame_set(1)
hold=bpy.data.materials.new('V7 temporary water holdout');hold.use_nodes=True
n=hold.node_tree.nodes;n.clear();shader=n.new('ShaderNodeHoldout');output=n.new('ShaderNodeOutputMaterial')
hold.node_tree.links.new(shader.outputs[0],output.inputs[0])
water=bpy.data.objects['Water - periodic geometric waves'];water.data.materials.clear();water.data.materials.append(hold)
bpy.data.objects['V3 waterline foam'].hide_render=False
s.render.filepath=str(out);bpy.ops.render.render(write_still=True)
out.with_suffix('.json').write_text(json.dumps({'source':bpy.data.filepath,'sourceSha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'foamIncluded':True,'matteSha256':hashlib.sha256(out.read_bytes()).hexdigest()},indent=2))
