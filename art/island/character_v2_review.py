"""Adapt the licensed Snow base; never re-create its topology or rig.

Run after appending CH-snow into Character_V2. Preserve authored face controls,
weights, corrective shapes, IK/FK, skin maps and eye shaders.
"""
import bpy, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
s=bpy.data.scenes['Character_V2'];bpy.context.window.scene=s
r=bpy.data.objects['RIG-Snow']
# animation_data_clear would destroy CloudRig's IK/FK and corrective drivers.
if r.animation_data:r.animation_data.action=None
for p in r.pose.bones:p.matrix_basis.identity()
props=r.pose.bones['Properties']
for side in ['left','right']:
    props['ik_'+side+'_upperarm']=0
    props['ik_'+side+'_thigh']=1
    props['ik_stretch_'+side+'_upperarm']=0
    props['ik_stretch_'+side+'_thigh']=0
for c in bpy.data.collections:
    if c.name.startswith(('snow.rig.widgets','snow.rig.helpers')):c.hide_render=True
for o in s.objects:
    if o.name.startswith(('WGT-','META-')) or 'helper' in o.name or 'deformer' in o.name:o.hide_render=True
# Retain the original normal and roughness maps; recolor only diffuse cloth.
for m in bpy.data.materials:
    col=(.70,.64,.49,1) if m.name.startswith('snow.shirt') else ((.035,.16,.14,1) if m.name.startswith('snow.pants') else None)
    if col and m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type=='BSDF_PRINCIPLED':
                for link in list(n.inputs['Base Color'].links):m.node_tree.links.remove(link)
                n.inputs['Base Color'].default_value=col

r.update_tag();bpy.context.view_layer.update()
# Use the existing FK controls, aligning the shoulder in armature space.
for side,sign in [('L',1),('R',-1)]:
    pb=r.pose.bones['FK-UpperArm.'+side]
    rest=pb.bone.matrix_local.to_quaternion()
    target=Vector((sign*.12,-.035,-1)).normalized()
    desired=Vector((0,1,0)).rotation_difference(target)
    pb.rotation_mode='QUATERNION';pb.rotation_quaternion=rest.inverted()@desired
    fore=r.pose.bones['FK-Forearm.'+side];fore.rotation_mode='XYZ';fore.rotation_euler=(0,0,sign*.12)
bpy.context.view_layer.update()

# All review lights are owned copies, no changes to wallpaper lighting.
for o in list(s.objects):
    if o.name.startswith('V2 review'):bpy.data.objects.remove(o,do_unlink=True)
world=bpy.data.worlds.get('V2 character studio') or bpy.data.worlds.new('V2 character studio');s.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.42,.47,.52,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.4
for name,pos,power,size,color in [('key',(-3,-4,5),400,4,(1,.91,.78)),('fill',(3,-2,2),180,3,(.8,.9,1)),('rim',(1,3,4),350,3,(1,.93,.82))]:
    d=bpy.data.lights.new('V2 review '+name,'AREA');d.energy=power;d.size=size;d.color=color
    o=bpy.data.objects.new('V2 review '+name,d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.9))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('V2 review camera');o=bpy.data.objects.new('V2 review camera',d);s.collection.objects.link(o)
o.location=(2,-6,2.7);o.rotation_euler=(Vector((0,0,.88))-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=2.15;s.camera=o
s.render.engine='CYCLES';s.cycles.device='GPU';s.cycles.samples=32;s.cycles.use_denoising=True
s.render.resolution_x=600;s.render.resolution_y=760;s.render.resolution_percentage=100;s.render.film_transparent=True
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.view_settings.view_transform='AgX'
s.render.filepath=str(ROOT/'wallpaper/assets/character-v2-review.png')
bpy.ops.render.render(write_still=True)
bpy.context.window.scene=bpy.data.scenes['Resort_Island']
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort-v2.blend'))
result={'preview':s.render.filepath,'base':'Snow v2 / Blender Foundation CC-BY-4.0','topology':'existing licensed mesh and rig','final':False}
