import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=bpy.data.scenes['Character_Bake'];bpy.context.window.scene=s
rig=next(o for o in s.objects if o.type=='ARMATURE');rig.animation_data_clear();rig.rotation_euler.z=0
for bone in rig.pose.bones:bone.rotation_mode='XYZ';bone.rotation_euler=(0,0,0);bone.location=(0,0,0)
bpy.context.view_layer.update()
data={}
for name in ['Hips','Head','LeftArm','LeftForeArm','LeftHand','RightArm','RightForeArm','RightHand']:
 b=rig.pose.bones[name];data[name]={'head':list(rig.matrix_world@b.head),'tail':list(rig.matrix_world@b.tail)}
(root/'docs/evidence/resort/rig-bones.json').write_text(json.dumps(data,indent=2))
