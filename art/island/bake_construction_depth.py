"""Bake actual cabana depth offsets; its footprint cannot use an upright plane."""
import bpy,json,os
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ.get('RESORT_RENDER_OUT',ROOT/'wallpaper/assets'))
s=bpy.data.scenes['Construction_Bake'];original=bpy.context.window.scene;bpy.context.window.scene=s
s.frame_set(s.frame_current);bpy.context.view_layer.update()
foot_depth=-(s.camera.matrix_world.inverted()@Vector((0,0,0))).z
assert 9<foot_depth<12,'Construction camera must be evaluated before computing depth'
material=bpy.data.materials.new('Cabana depth temporary');material.use_nodes=True
n=material.node_tree.nodes;n.clear();links=material.node_tree.links
camera=n.new('ShaderNodeCameraData');subtract=n.new('ShaderNodeMath');subtract.operation='SUBTRACT';subtract.inputs[1].default_value=foot_depth
add=n.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=2
divide=n.new('ShaderNodeMath');divide.operation='DIVIDE';divide.inputs[1].default_value=4
emit=n.new('ShaderNodeEmission');output=n.new('ShaderNodeOutputMaterial')
links.new(camera.outputs['View Z Depth'],subtract.inputs[0]);links.new(subtract.outputs[0],add.inputs[0]);links.new(add.outputs[0],divide.inputs[0]);links.new(divide.outputs[0],emit.inputs['Color']);links.new(emit.outputs[0],output.inputs['Surface'])
slots=[];visibility={o:o.hide_render for o in s.objects}
for o in s.objects:
    if o.type=='MESH':
        for slot in o.material_slots:
            old=slot.material;slots.append((slot,slot.link,old));slot.link='OBJECT';slot.material=material
settings=(s.view_settings.view_transform,s.view_settings.look,s.view_settings.exposure,s.view_settings.gamma)
s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0;s.view_settings.gamma=1
try:
    for stage in range(5):
        for o in s.objects:
            if 'stage' in o:o.hide_render=o['stage']>stage
        s.render.filepath=str(OUT/f'construction-depth-{stage}.png');bpy.ops.render.render(write_still=True)
finally:
    for slot,link,old in slots:slot.link=link;slot.material=old
    for o,hidden in visibility.items():o.hide_render=hidden
    s.view_settings.view_transform,s.view_settings.look,s.view_settings.exposure,s.view_settings.gamma=settings
    bpy.context.window.scene=original;bpy.data.materials.remove(material)
path=OUT/'scene-v2.json';meta=json.loads(path.read_text());meta['construction'].update(depthAtlas='construction-depth.png',depthScale=4,depthBias=2);path.write_text(json.dumps(meta,indent=2))
print(json.dumps({'footCameraDepth':foot_depth,'encodedRange':[-2,2],'frames':5}))
