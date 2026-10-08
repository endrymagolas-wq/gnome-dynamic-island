"""Offline pose library for the existing Snow CloudRig; keeps all drivers.

Run setup(), pose(name, phase), then render a bounded frame batch via MCP.
FK control transforms are stored as editable actions by save_actions().
"""
import bpy, math
from mathutils import Vector, Matrix
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
POSES=['idle','starting','editing','testing','failed','permission','done','browsing','working']

def setup():
    global s,r,cup
    s=bpy.data.scenes['Character_V2'];bpy.context.window.scene=s
    r=bpy.data.objects['RIG-Snow']
    # Snow v2 has five constraints targeting absent ORG face bones. Keep them
    # editable but mute these already-invalid constraints for Blender 4.5.
    for bone in r.pose.bones:
        for constraint in bone.constraints:
            target=getattr(constraint,'target',None);name=getattr(constraint,'subtarget','')
            if target and target.type=='ARMATURE' and name and name not in target.data.bones:
                constraint.mute=True
    cup=bpy.data.objects.get('V2 worker coffee cup')
    if not cup:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.042,depth=.072)
        cup=bpy.context.object;cup.name='V2 worker coffee cup'
        cup.data.materials.append(bpy.data.materials['Warm ivory plaster'])
        # A reusable existing mug would be preferable; this is a review prop.
    return s

def aim(name,direction):
    b=r.pose.bones[name];q=(b.tail-b.head).normalized().rotation_difference(Vector(direction).normalized())
    h=b.head.copy();b.matrix=Matrix.Translation(h)@q.to_matrix().to_4x4()@Matrix.Translation(-h)@b.matrix
    bpy.context.view_layer.update()

def arm(side,target):
    a=r.pose.bones['FK-UpperArm.'+side];b=r.pose.bones['FK-Forearm.'+side]
    h=a.head.copy();lengthA=(b.head-h).length;lengthB=(b.tail-b.head).length
    delta=Vector(target)-h;d=min(delta.length,lengthA+lengthB-.003);v=delta.normalized()
    pole=Vector((1 if side=='L' else -1,.12,-.12));pole=(pole-v*pole.dot(v)).normalized()
    c=max(-1,min(1,(lengthA**2+d*d-lengthB**2)/(2*lengthA*d)))
    elbow=h+v*lengthA*c+pole*lengthA*math.sqrt(max(0,1-c*c))
    aim(a.name,elbow-h);aim(b.name,h+v*d-b.head)

def pose(state,phase=0):
    if r.animation_data:r.animation_data.action=None
    for b in r.pose.bones:b.matrix_basis.identity()
    r.location=(0,0,0);r.rotation_euler=(0,0,0);r.scale=(1,1,1)
    props=r.pose.bones['Properties']
    for side in ['left','right']:
        props['ik_'+side+'_upperarm']=0;props['ik_'+side+'_thigh']=1
        props['ik_stretch_'+side+'_upperarm']=0;props['ik_stretch_'+side+'_thigh']=0
    r.update_tag();bpy.context.view_layer.update()
    cup.hide_render=state not in ('idle','done')
    if state=='walk':
        torso=r.pose.bones['MSTR-Spine_Torso'];m=torso.matrix.copy();m.translation.z-=.025*(1-math.cos(phase*2));torso.matrix=m
        for side,offset in [('L',0),('R',math.pi)]:
            p=phase+offset;t=(p/math.tau)%1;b=r.pose.bones['IK-MSTR-Foot.'+side];m=b.matrix.copy()
            # Swing first, then a linear planted stance that cancels forward
            # body travel. Both legs reuse the existing weighted IK chain.
            m.translation.y+=.15-.6*t if t<.5 else -.15+.6*(t-.5)
            m.translation.z+=.075*math.sin(t*math.tau) if t<.5 else 0;b.matrix=m
        bpy.context.view_layer.update()
        arm('L',(.22,-.13*math.cos(phase),.85));arm('R',(-.22,.13*math.cos(phase),.85))
    elif state in ('starting','editing','working'):
        arm('L',(.15,-.36,.97+.013*math.sin(phase)));arm('R',(-.15,-.36,.97+.013*math.sin(phase+math.pi)))
        r.pose.bones['FK-Head'].rotation_euler.x=.13
    elif state=='permission':
        arm('L',(.19,-.03,.85));arm('R',(-.37-.04*math.sin(phase),-.06,1.61+.025*math.cos(phase)))
    elif state in ('done','idle'):
        b=r.pose.bones['MSTR-Spine_Torso'];m=b.matrix.copy();m.translation.z-=.33;b.matrix=m
        for side in ['L','R']:
            b=r.pose.bones['IK-MSTR-Foot.'+side];m=b.matrix.copy();m.translation.y-=.29;b.matrix=m
        bpy.context.view_layer.update()
        arm('L',(.21,-.31,.57));arm('R',(-.13,-.19,1.16+.02*math.sin(phase)))
    elif state=='testing':
        arm('L',(.19,-.04,.84));arm('R',(-.21,-.23,1.03))
        r.pose.bones['FK-Head'].rotation_euler.z=.16*math.sin(phase)
    elif state=='failed':
        arm('L',(.20,-.07,.84));arm('R',(-.07,-.20,1.48))
        r.pose.bones['FK-Head'].rotation_euler.x=.24
    else:
        arm('L',(.20,-.04,.84));arm('R',(-.20,-.04,.84))
    bpy.context.view_layer.update()
    cup.location=r.matrix_world@r.pose.bones['FK-Wrist.R'].tail+Vector((0,-.028,.018))
    return {'drivers':len(r.animation_data.drivers),'state':state}

def review(state):
    setup();pose(state)
    s.render.filepath=str(ROOT/'wallpaper/assets'/('snow-'+state+'-review.png'))
    bpy.ops.render.render(write_still=True)
    return {'preview':s.render.filepath,'pose':state}

def sprite_setup():
    import json
    from bpy_extras.object_utils import world_to_camera_view
    setup();resort=bpy.data.scenes['Resort_Island']
    for o in list(s.objects):
        if o.type=='LIGHT' and o.name.startswith('V2 review'):o.hide_render=True
    for o in resort.objects:
        if o.type=='LIGHT' and not bpy.data.objects.get('Snow bake '+o.name):
            lamp=o.copy();lamp.data=o.data.copy();lamp.name='Snow bake '+o.name;s.collection.objects.link(lamp)
    s.world=resort.world;s.view_settings.exposure=resort.view_settings.exposure
    camera=s.camera;camera.rotation_euler=resort.camera.rotation_euler
    camera.location=Vector((0,0,.65))+camera.rotation_euler.to_quaternion()@Vector((0,0,10))
    camera.data.type='ORTHO';camera.data.ortho_scale=2.2
    s.render.resolution_x=128;s.render.resolution_y=160;s.render.resolution_percentage=100
    s.render.film_transparent=True;s.cycles.samples=16;s.cycles.use_denoising=True;s.render.fps=16
    s.render.use_persistent_data=True
    s.frame_start=1;s.frame_end=16
    s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8'
    bpy.context.view_layer.update();foot=world_to_camera_view(s,camera,Vector((0,0,0)))
    metadata=ROOT/'wallpaper/assets/scene-v2.json'
    meta=json.loads((metadata if metadata.exists() else ROOT/'wallpaper/assets/scene.json').read_text())
    cam=resort.camera
    meta['camera']={'location':list(cam.location),'rotation':list(cam.rotation_euler),'lens':cam.data.lens,'sensor':cam.data.sensor_width,'matrixWorld':[list(row) for row in cam.matrix_world]}
    meta['character']={'width':128,'height':160,'frames':16,'fps':16,'ppm':160/2.2,'anchorX':foot.x*128,'anchorY':(1-foot.y)*160,'poses':POSES,'source':'Adapted Snow v2, Blender Foundation, CC-BY-4.0'}
    meta['ground']['coastPerturb']=[.045,.035,.4]
    x,y,_=meta['targets']['permission'];rad=math.hypot(x/5.5,y/4.3);a=math.atan2(y/4.3,x/5.5)
    dr=.045*math.sin(3*a)+.035*math.cos(5*a+.4)
    rad=(rad+dr*.72/.18)/(1+dr/.18) if rad<.90+dr else rad-dr
    meta['targets']['permission'][2]=.43-max(0,rad-.72)*2.35
    # The adapted adult sits with lowered pelvis. Feet remain on the beach.
    for name in ('idle','done'):meta['targets'][name][2]=.43
    meta['targets']['failed']=list(meta['targets']['testing'])
    meta['projections']={}
    for name,point in meta['targets'].items():
        p=world_to_camera_view(resort,cam,Vector(point));meta['projections'][name]={'x':p.x*1920,'y':(1-p.y)*1080,'depth':p.z}
    for name,scene_name in [('construction','Construction_Bake'),('smoke','Smoke_Bake')]:
        if name in meta and scene_name in bpy.data.scenes:
            bake=bpy.data.scenes[scene_name]
            # Newly activated scenes can still have stale matrix_world caches.
            # These unparented orthographic cameras have explicit transforms.
            up=bake.camera.rotation_euler.to_quaternion()@Vector((0,1,0))
            meta[name]['anchorX']=meta[name]['width']/2
            meta[name]['anchorY']=(.5+bake.camera.location.dot(up)/bake.camera.data.ortho_scale)*meta[name]['height']
    if 'construction' in meta:
        p=world_to_camera_view(resort,cam,Vector((2.8,.3,.43)))
        meta['construction'].update(x=p.x*1920,y=(1-p.y)*1080,depth=p.z)
    if 'smoke' in meta:meta['smoke']['worldOrigin']=[3.1,-.15,1.65]
    (ROOT/'wallpaper/assets/scene-v2.json').write_text(json.dumps(meta,indent=2))
    return {'anchor':[foot.x*128,(1-foot.y)*160]}

def bake_sprites(start=0,end=31):
    sprite_setup();folder=ROOT/'wallpaper/assets/character-v2-frames';folder.mkdir(exist_ok=True)
    for index in range(start,end+1):
        row,f=divmod(index,16);state='walk' if row<8 else POSES[row-8]
        pose(state,f/16*math.tau)
        r.scale=(.78,)*3
        r.rotation_euler.z=row*math.tau/8+math.pi/2 if row<8 else math.pi if state in ('starting','editing','working') else 2.6 if state=='testing' else 0
        bpy.context.view_layer.update()
        cup.location=r.matrix_world@r.pose.bones['FK-Wrist.R'].tail+Vector((0,-.022,.014))
        cup.scale=(.78,)*3
        s.render.filepath=str(folder/f'{row:02}_{f:02}.png');bpy.ops.render.render(write_still=True)
    return {'start':start,'end':end,'frames':272,'drivers':len(r.animation_data.drivers)}

def save_actions():
    setup()
    if r.animation_data:r.animation_data.action=None
    for action in list(bpy.data.actions):
        if action.name.startswith('Resort_Snow_'):bpy.data.actions.remove(action)
    controls=[b for b in r.pose.bones if b.name.startswith(('FK-UpperArm','FK-Forearm','FK-Wrist','FK-Head','MSTR-Spine_Torso','IK-MSTR-Foot'))]
    for state in ['walk']+POSES:
        action=None
        for f in range(16):
            pose(state,f/16*math.tau)
            if action:r.animation_data.action=action
            for b in controls:
                b.keyframe_insert('location',frame=f+1,group=b.name)
                b.keyframe_insert('rotation_quaternion' if b.rotation_mode=='QUATERNION' else 'rotation_euler',frame=f+1,group=b.name)
            action=r.animation_data.action;action.name='Resort_Snow_'+state;action.use_fake_user=True
        r.animation_data.action=None
    pose('browsing');bpy.context.window.scene=bpy.data.scenes['Resort_Island']
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort-v2.blend'),compress=True)
    return {'actions':len(POSES)+1,'drivers':len(r.animation_data.drivers)}
