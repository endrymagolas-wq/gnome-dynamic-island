"""Six-second seated coffee/nod/hand-cover-yawn clips, 16fps, existing rig.

The generated mesh has no facial rig: yawn uses posture and hand gesture,
not a claimed animated jaw or eyelid. No new topology or purchased animation.
"""
import bpy,math,os,json
from pathlib import Path
from mathutils import Vector,Quaternion
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['RESORT_RENDER_OUT'])
SOURCE=bpy.data.filepath
p=ROOT/'art/island/pip_v6_poses.py';poses={'__file__':str(p)}
exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),poses);poses['setup']()
s=poses['s'];r=poses['r'];cup=poses['cup'];s.cycles.device='GPU'
base=bpy.data.scenes['Resort_Island']
for lamp in s.objects:
 if lamp.type=='LIGHT':
  original=next((o for o in base.objects if o.type=='LIGHT' and lamp.name.startswith(o.name)),None)
  if original:lamp.data.energy=original.data.energy;lamp.data.color=original.data.color;lamp.rotation_euler=original.rotation_euler
depth_only=os.environ.get('RESORT_AMBIENT_DEPTH')=='1'
actions_only=os.environ.get('RESORT_AMBIENT_ACTIONS')=='1'
folder=OUT/('ambient-depth-frames' if depth_only else 'ambient-frames');folder.mkdir(exist_ok=True)
slots=[];saved=(s.render.engine,s.view_settings.view_transform,s.view_settings.look,s.view_settings.exposure)
if depth_only:
 bpy.context.view_layer.update();origin=-(s.camera.matrix_world.inverted()@Vector((0,0,0))).z
 m=bpy.data.materials.new('V6 ambient temporary depth');m.use_nodes=True;n=m.node_tree.nodes;n.clear();l=m.node_tree.links
 cam=n.new('ShaderNodeCameraData');sub=n.new('ShaderNodeMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=origin
 add=n.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=2
 div=n.new('ShaderNodeMath');div.operation='DIVIDE';div.inputs[1].default_value=4
 emit=n.new('ShaderNodeEmission');out=n.new('ShaderNodeOutputMaterial')
 l.new(cam.outputs['View Z Depth'],sub.inputs[0]);l.new(sub.outputs[0],add.inputs[0]);l.new(add.outputs[0],div.inputs[0]);l.new(div.outputs[0],emit.inputs[0]);l.new(emit.outputs[0],out.inputs[0])
 for name in ('Pip_V5_Generated','Pip coffee mug'):
  for slot in bpy.data.objects[name].material_slots:slots.append((slot,slot.link,slot.material));slot.link='OBJECT';slot.material=m
 s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=16;s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0
for clip,state in enumerate(('drink','nod','yawn')):
 action=None
 if actions_only:
  old=bpy.data.actions.get('Resort_Pip_ambient_'+state)
  if old:bpy.data.actions.remove(old)
 for f in range(96):
  phase=f/96*math.tau;poses['pose']('done',0);r.scale=(poses['SCALE'],)*3;r.rotation_euler.z=0
  mesh=bpy.data.objects['Pip_V5_Generated'];mesh.hide_viewport=True
  lift=(1-math.cos(phase))*.5 if state=='drink' else 0
  poses['arm']('R',(-.26,-.55,1.15+.62*lift))
  if state=='nod':r.pose.bones['Head'].rotation_quaternion @= Quaternion((1,0,0),.12*math.sin(2*phase))
  if state=='yawn':
   gesture=(1-math.cos(phase))*.5
   poses['arm']('L',(.46-.24*gesture,-.45-.1*gesture,.89+.96*gesture))
   r.pose.bones['Head'].rotation_quaternion @= Quaternion((1,0,0),-.12*gesture)
  mesh.hide_viewport=False;bpy.context.view_layer.update()
  cup.location=r.matrix_world@r.pose.bones['LowerArm.R'].tail+Vector((0,-.03,.035));cup.rotation_euler=(-.35*lift,0,0);cup.scale=(1.25,)*3;cup.hide_render=False
  if actions_only:
   transforms={b.name:b.matrix_basis.copy() for b in r.pose.bones};r.animation_data.action=action
   for b in r.pose.bones:
    b.matrix_basis=transforms[b.name]
    b.keyframe_insert('location',frame=f+1,group=b.name)
    b.keyframe_insert('rotation_quaternion' if b.rotation_mode=='QUATERNION' else 'rotation_euler',frame=f+1,group=b.name)
    b.keyframe_insert('scale',frame=f+1,group=b.name)
   action=r.animation_data.action;action.name='Resort_Pip_ambient_'+state;action.use_fake_user=True;r.animation_data.action=None
  else:
   s.render.filepath=str(folder/f'{clip:02}_{f:03}.png');bpy.ops.render.render(write_still=True)
if depth_only:
 for slot,link,old in slots:slot.material=old;slot.link=link
 s.render.engine,s.view_settings.view_transform,s.view_settings.look,s.view_settings.exposure=saved
 bpy.data.materials.remove(m)
metadata=OUT/'scene-v2.json';meta=json.loads(metadata.read_text())
meta['character']['ambient']={'atlas':'ambient.png','depthAtlas':'ambient-depth.png','clips':['drink','nod','yawn'],'frames':96,'fps':16,'columns':16,'rowsPerClip':6,'cycleSeconds':42,'facialRig':False}
metadata.write_text(json.dumps(meta,indent=2))
if actions_only:
 bpy.context.window.scene=base;bpy.ops.wm.save_as_mainfile(filepath=SOURCE,compress=True)
result={'clips':3,'frames':288,'fps':16,'secondsPerClip':6}
