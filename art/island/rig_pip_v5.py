"""Adapt the retained Quaternius skeleton to the generated mascot's A-pose.

Run once in the V5 Blender project through Blender MCP. V4 stays untouched.
"""
import bpy, math
from mathutils import Vector

s = bpy.data.scenes['Mascot_Pip']
bpy.context.window.scene = s
mesh = bpy.data.objects['Pip_V5_Generated']
old = bpy.data.objects['CharacterArmature']
old.name = 'CharacterArmature_V4_archive'
rig = old.copy(); rig.data = old.data.copy()
rig.name = 'CharacterArmature'; s.collection.objects.link(rig)
rig.animation_data_clear(); rig.animation_data_create()
rig.location = (0,0,0); rig.rotation_mode = 'XYZ'
rig.rotation_euler = (0,0,0); rig.scale = (1,1,1)
for p in rig.pose.bones: p.matrix_basis.identity()
for p in rig.pose.bones:
    for c in p.constraints:
        if hasattr(c,'target') and c.target == old: c.target = rig

# Put the generated front along -Y and the soles on Z=0.
bpy.ops.object.select_all(action='DESELECT')
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
mesh.scale = (2.8,)*3; mesh.location.z = .4644*2.8
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

def spine(v):
    v = v.copy(); z = v.z
    points = [(0,0),(.97,.80),(1.395,1.18),(1.96,1.46),(2.062,1.52),(2.568,2.28)]
    for (a,b),(c,d) in zip(points,points[1:]):
        if z <= c: v.z = b+(z-a)/(c-a)*(d-b); break
    v.y -= .22
    return v

def limb(v):
    sign = 1 if v.x>=0 else -1; x=abs(v.x)
    points=[(.365,.42,1.40),(1.204,.69,1.14),(1.737,.91,.90),(2.31,1.04,.76)]
    for (a,b,c),(d,e,f) in zip(points,points[1:]):
        if x <= d:
            t=(x-a)/(d-a)
            return Vector((sign*(b+t*(e-b)),(v.y-.20)*.45,c+t*(f-c)+(v.z-1.83)*.35))
    return Vector((sign*1.04,(v.y-.20)*.45,.76))

bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
# Snapshot the original joints before moving any parent. Connected children can
# otherwise inherit a changed parent's tail and get transformed a second time.
coordinates={b.name:(b.head.copy(),b.tail.copy()) for b in rig.data.edit_bones}
for b in rig.data.edit_bones: b.use_connect=False
for b in rig.data.edit_bones:
    transform=limb if b.name.startswith(('UpperArm','LowerArm','Pinky','Middle','Index','Thumb')) else spine
    original_head,original_tail=coordinates[b.name]
    b.head=transform(original_head); b.tail=transform(original_tail)
    if b.name.startswith('Shoulder'):
        b.tail=(.42 if b.name.endswith('.L') else -.42,0,1.40)
    if b.name.startswith(('Root','Body','PoleTarget')): b.use_deform=False
bpy.ops.object.mode_set(mode='OBJECT')
for p in rig.pose.bones: p.matrix_basis.identity()
rig.data.pose_position='REST'
bpy.ops.object.select_all(action='DESELECT')
mesh.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
rig.data.pose_position='POSE'
# Keep the entire face and floppy ears rigidly attached to Head, avoiding
# heat weights that let nearby short arms pull the ears while waving.
head=mesh.vertex_groups.get('Head')
for v in mesh.data.vertices:
    if v.co.z > 1.57:
        for group in mesh.vertex_groups: group.remove([v.index])
        head.add([v.index],1,'REPLACE')
for o in s.objects:
    if o.type not in ('CAMERA','LIGHT') and o not in (mesh,rig):o.hide_render=True
mesh.hide_render=False;rig.hide_render=False
bpy.context.view_layer.update()
result={'rig':rig.name,'bones':len(rig.data.bones),'weighted_vertices':sum(bool(v.groups) for v in mesh.data.vertices),'vertices':len(mesh.data.vertices)}
