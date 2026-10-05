"""Build-time Kenney rig sprites. Run after build_scene.py via Blender MCP."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'wallpaper/assets';SOURCE=ROOT/'art/thirdparty/animated-characters-protagonists'
for action in list(bpy.data.actions):
    if action.name.startswith('Resort_'):bpy.data.actions.remove(action)
name='Character_Bake'
if name in bpy.data.scenes:
    s=bpy.data.scenes[name]
    for o in list(s.objects):
        if len(o.users_scene)>1:
            for c in list(o.users_collection):
                if c in list(s.collection.children) or c==s.collection:c.objects.unlink(o)
        else:bpy.data.objects.remove(o,do_unlink=True)
else:s=bpy.data.scenes.new(name)
bpy.context.window.scene=s
bpy.ops.import_scene.fbx(filepath=str(SOURCE/'Model/characterMedium.fbx'))
rig=next(o for o in s.objects if o.type=='ARMATURE');rig.name='Resort_Worker_Rig';rig.scale=(.35,)*3
body=next(o for o in s.objects if o.type=='MESH')
bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.16,depth=.36)
cup=bpy.context.object;cup.name='Worker coffee cup';cup.parent=rig;cup.parent_type='BONE';cup.parent_bone='RightHand';cup.location=(.05,.18,0);cup.data.materials.append(bpy.data.materials['Warm ivory plaster'])
up=bpy.data.objects.new('Coffee cup world up',None);s.collection.objects.link(up)
constraint=cup.constraints.new('COPY_ROTATION');constraint.target=up;constraint.owner_space='WORLD';constraint.target_space='WORLD'
skin=bpy.data.materials.new('Kenney skater skin');skin.use_nodes=True
tex=skin.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(SOURCE/'Skins/skaterMaleA.png'));tex.image.pack();tex.interpolation='Closest'
skin.node_tree.links.new(tex.outputs['Color'],skin.node_tree.nodes['Principled BSDF'].inputs['Base Color']);body.data.materials.clear();body.data.materials.append(skin)
before=set(s.objects);beforeactions=set(bpy.data.actions)
bpy.ops.import_scene.fbx(filepath=str(SOURCE/'Animations/run.fbx'))
run=next(a for a in set(bpy.data.actions)-beforeactions if 'Run' in a.name);run.use_fake_user=True
for o in set(s.objects)-before:bpy.data.objects.remove(o,do_unlink=True)
s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=16;s.eevee.use_shadows=True
s.world=bpy.data.scenes['Resort_Island'].world
s.view_settings.exposure=bpy.data.scenes['Resort_Island'].view_settings.exposure
for o in bpy.data.scenes['Resort_Island'].objects:
    if o.type=='LIGHT':
        lamp=o.copy();lamp.data=o.data.copy();s.collection.objects.link(lamp)
camera=bpy.data.objects.new('Sprite camera',bpy.data.cameras.new('Sprite orthographic'));s.collection.objects.link(camera)
camera.rotation_euler=bpy.data.scenes['Resort_Island'].camera.rotation_euler
camera.location=Vector((0,0,.65))+camera.rotation_euler.to_quaternion()@Vector((0,0,10));camera.data.type='ORTHO';camera.data.ortho_scale=2.2;s.camera=camera
s.render.resolution_x=128;s.render.resolution_y=160;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.color_mode='RGBA'
s.view_settings.view_transform='AgX';s.render.fps=16
bpy.context.view_layer.update()
foot=world_to_camera_view(s,camera,Vector((0,0,0)))
poses=['idle','starting','editing','testing','failed','permission','done','browsing','working'];frames=16
meta=json.loads((OUT/'scene.json').read_text());meta['character']={'width':128,'height':160,'frames':frames,'fps':16,'ppm':160/2.2,'anchorX':foot.x*128,'anchorY':(1-foot.y)*160,'poses':poses}
(OUT/'scene.json').write_text(json.dumps(meta,indent=2))
def rot(name,xyz):
    b=rig.pose.bones.get(name)
    if b:b.rotation_mode='XYZ';b.rotation_euler=xyz
def solve_arm(side,target):
    # Two-bone analytic IK, baked into ordinary editable rotation channels.
    bpy.context.view_layer.update()
    upper=rig.pose.bones[side+'Arm'];lower=rig.pose.bones[side+'ForeArm']
    neutral=Matrix.Rotation(-rig.rotation_euler.z,4,'Z')@rig.matrix_world
    inverse=neutral.inverted();shoulder=neutral@upper.head;elbow=neutral@lower.head;hand=neutral@lower.tail
    a=(elbow-shoulder).length;b=(hand-elbow).length;delta=Vector(target)-shoulder
    distance=min(max(delta.length,abs(a-b)+.001),a+b-.001);direction=delta.normalized()
    pole=Vector((1 if side=='Left' else -1,0,-.15));pole=(pole-direction*pole.dot(direction)).normalized()
    cosine=max(-1,min(1,(a*a+distance*distance-b*b)/(2*a*distance)))
    wanted=shoulder+direction*a*cosine+pole*a*math.sqrt(max(0,1-cosine*cosine))
    def aim(bone,end):
        current=(bone.tail-bone.head).normalized();desired=(end-bone.head).normalized()
        q=current.rotation_difference(desired);head=bone.head.copy()
        bone.matrix=Matrix.Translation(head)@q.to_matrix().to_4x4()@Matrix.Translation(-head)@bone.matrix
        bpy.context.view_layer.update()
    aim(upper,inverse@wanted);aim(lower,inverse@(shoulder+direction*distance))

def pose(state,phase,clear=True):
    if clear:rig.animation_data_clear()
    for b in rig.pose.bones:b.rotation_mode='XYZ';b.rotation_euler=(0,0,0);b.location=(0,0,0);b.scale=(1,1,1)
    # Rest arms are a T-pose. Lower them first, then author the task gestures.
    solve_arm('Left',(.17,-.025,.52));solve_arm('Right',(-.17,-.025,.52))
    if state in ('editing','working','starting'):
        solve_arm('Left',(.13,-.30,.74+.009*math.sin(phase)))
        solve_arm('Right',(-.13,-.30,.74+.009*math.sin(phase+math.pi)))
        rot('Head',(.15,0,0))
    elif state=='permission':
        solve_arm('Right',(-.25+.04*math.sin(phase),-.05,1.12))
    elif state in ('done','idle'):
        rot('LeftUpLeg',(1.25,0,0));rot('RightUpLeg',(1.25,0,0));rot('LeftLeg',(-1.25,0,0));rot('RightLeg',(-1.25,0,0))
        rig.pose.bones['Hips'].location=(0,-.35,0)
        solve_arm('Right',(-.15,-.16,.90+.04*math.sin(phase)))
    elif state=='testing':rot('Head',(0,.15*math.sin(phase),-.25));solve_arm('Right',(-.20,-.14,.70))
    elif state=='failed':rot('Head',(.35,0,0));rot('Chest',(.12,0,0))
    elif state=='browsing':rot('LeftForeArm',(-1,0,0));rot('RightForeArm',(-1,0,0))

# Store editable task actions as well as the reusable source run action.
for state in poses:
    rig.animation_data_clear()
    for f in range(frames):
        pose(state,f/frames*math.tau,False)
        for bone in rig.pose.bones:
            bone.keyframe_insert('rotation_euler',frame=f+1,group=bone.name)
            bone.keyframe_insert('location',frame=f+1,group=bone.name)
        action=rig.animation_data.action
        action.name='Resort_'+state;action.use_fake_user=True
    rig.animation_data_clear()

framesdir=OUT/'character-frames';framesdir.mkdir(exist_ok=True)
for row in range(8+len(poses)):
    for f in range(frames):
        if row<8:
            rig.animation_data_create();rig.animation_data.action=run;s.frame_set(f+1);rig.rotation_euler[2]=row*math.tau/8+math.pi/2
        else:
            state=poses[row-8]
            s.frame_set(f+1);pose(state,f/frames*math.tau);rig.rotation_euler[2]=math.pi if state in ('starting','editing','working') else 2.6 if state=='testing' else 0
        cup.hide_render=row<8 or poses[row-8] not in ('done','idle')
        bpy.context.view_layer.update()
        s.render.filepath=str(framesdir/f'{row:02}_{f:02}.png');bpy.ops.render.render(write_still=True)
bpy.context.window.scene=bpy.data.scenes['Resort_Island']
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort.blend'))
result={'spriteFrames':(8+len(poses))*frames,'anchor':[foot.x*128,(1-foot.y)*160]}
