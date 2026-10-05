"""Offline Pip sprite baking using Quaternius' existing weighted full-body rig."""
import bpy, json, math, os
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from bpy_extras.object_utils import world_to_camera_view
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('RESORT_RENDER_OUT', ROOT/'wallpaper/assets/v6-stage'))
POSES = ['idle','starting','editing','testing','failed','permission','done','browsing','working']
TRANSITIONS = ['sit','stand']
SCALE = .62
STANCE_SPEED = .96 * SCALE

def setup():
    global s, r, cup
    s = bpy.data.scenes['Mascot_Pip']; bpy.context.window.scene = s
    r = bpy.data.objects['CharacterArmature']
    # Archived V4 geometry must not participate in viewport dependency updates.
    for o in s.objects:
        if o.type in ('MESH','ARMATURE') and o.name not in ('CharacterArmature','Pip_V5_Generated','Pip coffee mug','Pip sand bounce'):
            o.hide_viewport = True
    base = bpy.data.scenes['Resort_Island']
    s.world = base.world
    s.view_settings.view_transform = base.view_settings.view_transform
    s.view_settings.look = base.view_settings.look
    s.view_settings.exposure = base.view_settings.exposure
    camera = s.camera; camera.rotation_euler = base.camera.rotation_euler
    camera.location = Vector((0,0,.65)) + camera.rotation_euler.to_quaternion() @ Vector((0,0,10))
    camera.data.type = 'ORTHO'; camera.data.ortho_scale = 2.2
    s.render.engine = 'CYCLES'; s.cycles.samples = 32; s.cycles.use_denoising = True
    s.render.resolution_x = 128; s.render.resolution_y = 160; s.render.resolution_percentage = 100
    s.render.film_transparent = True; s.render.image_settings.color_mode = 'RGBA'
    s.render.image_settings.color_depth = '8'; s.render.fps = 16
    s.render.use_persistent_data = True
    cup = bpy.data.objects.get('Pip coffee mug')
    if not cup:
        original = bpy.data.objects['V2 worker coffee cup']
        cup = original.copy(); cup.data = original.data.copy(); cup.name = 'Pip coffee mug'
        cup.parent = None; cup.location = (0,0,0); cup.scale = (1,1,1)
        s.collection.objects.link(cup)
    bounce = bpy.data.objects.get('Pip sand bounce')
    if not bounce:
        bpy.ops.mesh.primitive_plane_add(size=20)
        bounce = bpy.context.object; bounce.name = 'Pip sand bounce'
        bounce.visible_camera = False
        bounce.data.materials.append(bpy.data.materials['V2 scanned coastal sand'])
    bounce.visible_glossy = False
    return s

def aim(name, direction):
    b = r.pose.bones[name]
    q = (b.tail-b.head).normalized().rotation_difference(Vector(direction).normalized())
    h = b.head.copy()
    b.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ b.matrix
    bpy.context.view_layer.update()

def arm(side, target):
    a = r.pose.bones['UpperArm.'+side]; b = r.pose.bones['LowerArm.'+side]
    h = a.head.copy(); la = (b.head-h).length; lb = (b.tail-b.head).length
    delta = Vector(target)-h; d = max(.01,min(delta.length,la+lb-.003)); v = delta.normalized()
    pole = Vector((1 if side=='L' else -1,.18,-.15))
    pole = (pole-v*pole.dot(v)).normalized()
    c = max(-1,min(1,(la*la+d*d-lb*lb)/(2*la*d)))
    elbow = h+v*la*c+pole*la*math.sqrt(max(0,1-c*c))
    aim(a.name,elbow-h); aim(b.name,h+v*d-b.head)

def pose(state, phase=0):
    if state in TRANSITIONS:
        t=max(0,min(1,phase));t=t*t*(3-2*t)
        pose('browsing',0);standing={b.name:b.matrix_basis.copy() for b in r.pose.bones}
        pose('done',0);seated={b.name:b.matrix_basis.copy() for b in r.pose.bones}
        for b in r.pose.bones:
            b.matrix_basis=standing[b.name].lerp(seated[b.name],t if state=='sit' else 1-t)
        cup.hide_render=(t<.5 if state=='sit' else t>.5)
        bpy.context.view_layer.update();return state
    mesh = bpy.data.objects['Pip_V5_Generated']
    mesh.hide_viewport = True
    # Existing authored Walk/Idle motions provide the body and foot dynamics.
    name = 'Walk' if state=='walk' else 'Idle'
    source = bpy.data.actions.get('Pip_Source_'+name) or bpy.data.actions.get(name+'.001')
    assert source is not None, 'Import and retain the original Pip source actions before baking'
    r.animation_data.action = source
    for b in r.pose.bones: b.matrix_basis.identity()
    r.location = (0,0,0); r.rotation_euler = (0,0,0); r.scale = (1,1,1)
    frame = (phase/math.tau % 1)*30
    s.frame_set(int(frame), subframe=frame-int(frame)); bpy.context.view_layer.update()
    # Shorten the existing limbs along their bone axes, retaining their width
    # and original weights. This gives the mascot a compact, cuddly silhouette.
    for side in ('L','R'):
        r.pose.bones['UpperArm.'+side].scale.y=1.0
        r.pose.bones['LowerArm.'+side].scale.y=1.0
        for bone in r.pose.bones:
            if bone.name.endswith('.'+side) and bone.name.startswith(('Pinky','Middle','Index','Thumb')):
                bone.scale.y=1.0
    bpy.context.view_layer.update()
    for b in r.pose.bones:
        if b.name.startswith(('Shoulder','UpperArm','LowerArm','Pinky','Middle','Index','Thumb')): b.matrix_basis.identity()
    bpy.context.view_layer.update()
    if state=='walk':
        arm('L',(.91,-.15*math.sin(phase),.90))
        arm('R',(-.91,.15*math.sin(phase),.90))
        # Retain the authored body/arm motion and weighted leg IK. Linear foot
        # travel during stance exactly cancels the runtime's ground velocity.
        for side,offset in (('L',0),('R',.5)):
            t=(phase/math.tau+offset)%1
            b=r.pose.bones['Foot.'+side];matrix=b.matrix.copy()
            matrix.translation.y=.060495 + (.24-.96*t if t<.5 else -.24+.96*(t-.5))
            matrix.translation.z=.03395 + (.14*math.sin(t*math.tau) if t<.5 else 0)
            b.matrix=matrix
        bpy.context.view_layer.update()
    if state in ('starting','editing','working'):
        arm('L',(.30,-.65,1.42+.025*math.sin(phase)))
        arm('R',(-.30,-.65,1.42+.025*math.sin(phase+math.pi)))
        r.pose.bones['Head'].rotation_quaternion @= Quaternion((1,0,0),.12)
    elif state=='permission':
        arm('L',(.91,-.05,.90))
        arm('R',(-.76-.07*math.sin(phase),-.18,1.96+.06*math.cos(phase)))
    elif state in ('done','idle'):
        b = r.pose.bones['Body']; matrix = b.matrix.copy(); matrix.translation.z -= .18; b.matrix = matrix
        for side in ('L','R'):
            b = r.pose.bones['Foot.'+side]; matrix = b.matrix.copy(); matrix.translation.y -= .55; matrix.translation.z += .16; b.matrix = matrix
        bpy.context.view_layer.update()
        arm('L',(.46,-.45,.89)); arm('R',(-.26,-.55,1.73+.045*math.sin(phase)))
        r.pose.bones['Head'].rotation_quaternion @= Quaternion((0,0,1),.06*math.sin(phase))
    elif state=='testing':
        arm('L',(.91,-.12,.90)); arm('R',(-.42,-.52,1.62))
        r.pose.bones['Head'].rotation_quaternion @= Quaternion((0,0,1),.18*math.sin(phase))
    elif state=='failed':
        arm('L',(.91,-.07,.90)); arm('R',(-.20,-.60,1.90))
        r.pose.bones['Head'].rotation_quaternion @= Quaternion((1,0,0),.20)
    elif state!='walk':
        arm('L',(.91,-.04,.90)); arm('R',(-.91,-.04,.90))
    bpy.context.view_layer.update()
    cup.hide_render = state not in ('done','idle')
    bpy.data.objects['Pip_V5_Generated'].hide_render=False
    # Rendering evaluates animation again at this frame. Freeze the adjusted
    # pose so the source Idle action cannot overwrite gestures or retimed feet.
    transforms={b.name:b.matrix_basis.copy() for b in r.pose.bones}
    r.animation_data.action=None
    for b in r.pose.bones:b.matrix_basis=transforms[b.name]
    mesh.hide_viewport = False
    bpy.context.view_layer.update()
    return state

def sprite_metadata():
    setup(); bpy.context.view_layer.update()
    foot = world_to_camera_view(s,s.camera,Vector((0,0,0)))
    path = OUT/'scene-v2.json'
    meta = json.loads((path if path.exists() else ROOT/'wallpaper/assets/scene.json').read_text())
    meta['character'] = {'width':128,'height':160,'frames':16,'fps':16,'ppm':160/2.2,
        'anchorX':foot.x*128,'anchorY':(1-foot.y)*160,'poses':POSES,'walkSpeed':STANCE_SPEED,
        'source':'Pip generated from project reference via Stable Fast 3D; adapted Quaternius CC0 rig',
        'reference':'art/references/pip-v5-front.png','transitions':TRANSITIONS,
        'depthAtlas':'character-depth.png','depthScale':4,'depthBias':2}
    path.write_text(json.dumps(meta,indent=2))
    return meta

def bake_sprites(start=0,end=303):
    sprite_metadata(); folder = OUT/'character-frames'; folder.mkdir(exist_ok=True)
    for index in range(start,end+1):
        row,f = divmod(index,16); state = 'walk' if row<8 else (POSES+TRANSITIONS)[row-8]
        pose(state,f/15 if state in TRANSITIONS else f/16*math.tau); r.scale = (SCALE,)*3
        r.rotation_euler.z = row*math.tau/8+math.pi/2 if row<8 else math.pi if state in ('starting','editing','working') else 2.6 if state=='testing' else 0
        bpy.context.view_layer.update()
        cup.location = r.matrix_world @ r.pose.bones['LowerArm.R'].tail + Vector((0,-.03,.035))
        cup.scale = (1.25,)*3; cup.rotation_euler = (0,0,0)
        s.render.filepath = str(folder/f'{row:02}_{f:02}.png'); bpy.ops.render.render(write_still=True)
    return {'frames':end-start+1,'rigBones':len(r.data.bones),'sourceWalk':'Walk.001'}

def save_actions(filepath=None):
    setup()
    for a in list(bpy.data.actions):
        if a.name.startswith('Resort_Pip_'): bpy.data.actions.remove(a)
    for state in ['walk']+POSES+TRANSITIONS:
        action = None
        for f in range(17):
            pose(state,min(1,f/15) if state in TRANSITIONS else (f%16)/16*math.tau)
            transforms = {b.name:b.matrix_basis.copy() for b in r.pose.bones}
            r.animation_data.action = action
            for b in r.pose.bones:
                b.matrix_basis = transforms[b.name]
                b.keyframe_insert('location',frame=f+1,group=b.name)
                b.keyframe_insert('rotation_quaternion' if b.rotation_mode=='QUATERNION' else 'rotation_euler',frame=f+1,group=b.name)
                b.keyframe_insert('scale',frame=f+1,group=b.name)
            action = r.animation_data.action; action.name = 'Resort_Pip_'+state; action.use_fake_user = True
        r.animation_data.action = None
    pose('browsing'); r.scale = (SCALE,)*3
    bpy.context.window.scene = bpy.data.scenes['Resort_Island']
    bpy.ops.wm.save_as_mainfile(filepath=str(filepath or ROOT/'art/island/resort-v6.blend'),compress=True)
