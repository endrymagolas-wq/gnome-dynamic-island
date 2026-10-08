"""Camera-space depth offsets for every animated Pip pixel, including cup."""
import bpy,math,os
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(os.environ['RESORT_RENDER_OUT']);folder=OUT/'character-depth-frames';folder.mkdir(exist_ok=True)
p=ROOT/'art/island/pip_v6_poses.py';poses={'__file__':str(p)}
exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),poses);poses['setup']()
s=poses['s'];r=poses['r'];cup=poses['cup'];bpy.context.view_layer.update()
foot_depth=-(s.camera.matrix_world.inverted()@Vector((0,0,0))).z
assert 9<foot_depth<12
m=bpy.data.materials.new('V6 temporary animated depth');m.use_nodes=True;n=m.node_tree.nodes;n.clear();l=m.node_tree.links
cam=n.new('ShaderNodeCameraData');subtract=n.new('ShaderNodeMath');subtract.operation='SUBTRACT';subtract.inputs[1].default_value=foot_depth
add=n.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=2
divide=n.new('ShaderNodeMath');divide.operation='DIVIDE';divide.inputs[1].default_value=4
emit=n.new('ShaderNodeEmission');output=n.new('ShaderNodeOutputMaterial')
l.new(cam.outputs['View Z Depth'],subtract.inputs[0]);l.new(subtract.outputs[0],add.inputs[0]);l.new(add.outputs[0],divide.inputs[0]);l.new(divide.outputs[0],emit.inputs[0]);l.new(emit.outputs[0],output.inputs[0])
slots=[]
for name in ('Pip_V5_Generated','Pip coffee mug'):
 for slot in bpy.data.objects[name].material_slots:
  slots.append((slot,slot.link,slot.material));slot.link='OBJECT';slot.material=m
settings=(s.view_settings.view_transform,s.view_settings.look,s.view_settings.exposure,s.render.engine)
s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0;s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=16
try:
 for row in range(19):
  state='walk' if row<8 else (poses['POSES']+poses['TRANSITIONS'])[row-8]
  for f in range(16):
   poses['pose'](state,f/15 if state in poses['TRANSITIONS'] else f/16*math.tau)
   r.scale=(poses['SCALE'],)*3;r.rotation_euler.z=row*math.tau/8+math.pi/2 if row<8 else math.pi if state in ('starting','editing','working') else 2.6 if state=='testing' else 0
   bpy.context.view_layer.update();cup.location=r.matrix_world@r.pose.bones['LowerArm.R'].tail+Vector((0,-.03,.035));cup.scale=(1.25,)*3;cup.rotation_euler=(0,0,0)
   s.render.filepath=str(folder/f'{row:02}_{f:02}.png');bpy.ops.render.render(write_still=True)
finally:
 for slot,link,old in slots:slot.material=old;slot.link=link
 s.view_settings.view_transform,s.view_settings.look,s.view_settings.exposure,s.render.engine=settings
 bpy.data.materials.remove(m)
result={'frames':304,'depthOrigin':foot_depth,'range':[-2,2]}
