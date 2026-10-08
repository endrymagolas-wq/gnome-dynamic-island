"""Offline layer render. Call bake_static(), bake_water(start,end) via MCP."""
import bpy, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'wallpaper/assets'
def setup():
    s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
    s.render.resolution_percentage=100;s.eevee.taa_render_samples=128;s.cycles.samples=64;s.render.film_transparent=False
    s.frame_set(1);return s
def bake_static():
    s=setup();s.render.filepath=str(OUT/'poster.png');bpy.ops.render.render(write_still=True)
    w=bpy.data.objects['Water - periodic geometric waves'];old=list(w.data.materials)
    h=bpy.data.materials.new('Water alpha holdout');h.use_nodes=True;h.node_tree.nodes.clear()
    node=h.node_tree.nodes.new('ShaderNodeHoldout');out=h.node_tree.nodes.new('ShaderNodeOutputMaterial');h.node_tree.links.new(node.outputs[0],out.inputs['Surface'])
    w.data.materials.clear();w.data.materials.append(h);s.render.film_transparent=True
    s.render.filepath=str(OUT/'static.png');bpy.ops.render.render(write_still=True)
    w.data.materials.clear()
    for m in old:w.data.materials.append(m)
    # Camera-space depth, sRGB encoded; decoded back to linear depth by player.
    dm=bpy.data.materials.new('Camera-depth matte');dm.use_nodes=True;dm.node_tree.nodes.clear()
    nt=dm.node_tree;camera=nt.nodes.new('ShaderNodeCameraData');divide=nt.nodes.new('ShaderNodeMath');divide.operation='DIVIDE';divide.inputs[1].default_value=50
    emission=nt.nodes.new('ShaderNodeEmission');output=nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(camera.outputs['View Z Depth'],divide.inputs[0]);nt.links.new(divide.outputs[0],emission.inputs[0]);nt.links.new(emission.outputs[0],output.inputs[0])
    exposure=s.view_settings.exposure;s.view_settings.exposure=0
    s.render.engine='BLENDER_EEVEE_NEXT';s.view_layers[0].material_override=dm;s.view_settings.view_transform='Standard';s.render.image_settings.color_depth='16';s.eevee.use_raytracing=False
    # EEVEE ignores ViewLayer.material_override: override unique mesh datablocks.
    materials={}
    for o in s.objects:
        if o.type=='MESH' and o.data not in materials:
            materials[o.data]=list(o.data.materials);o.data.materials.clear();o.data.materials.append(dm)
    s.render.filepath=str(OUT/'depth.png');bpy.ops.render.render(write_still=True)
    for data,original in materials.items():
        data.materials.clear()
        for material in original:data.materials.append(material)
    s.view_layers[0].material_override=None;s.view_settings.view_transform='AgX';s.view_settings.exposure=exposure;s.render.image_settings.color_depth='8';s.eevee.use_raytracing=True;s.render.film_transparent=False;s.render.engine='CYCLES'
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort.blend'))
def bake_water(start=1,end=360,percentage=100,samples=128,progress_name="render-progress.json"):
    s=setup();s.render.resolution_percentage=percentage;s.eevee.taa_render_samples=samples;s.cycles.samples=samples
    folder=OUT/'water-frames';folder.mkdir(exist_ok=True)
    for frame in range(start,end+1):
        s.frame_set(frame);s.render.filepath=str(folder/f'{frame:04}.png');bpy.ops.render.render(write_still=True)
        (OUT/progress_name).write_text(json.dumps({'frame':frame,'frames':360}))
    return {'start':start,'end':end}
