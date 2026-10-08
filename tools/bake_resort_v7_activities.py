"""Offline EEVEE life clips for the retained Pip rig, with matching depth.

Run with Blender -b art/island/resort-v6.blend --python this-file -- --out DIR
--phase day --preview. Remove --preview for the atlas. Other phases need colour
only: --no-depth. Existing source files and .blend files are never overwritten.
Every frame is resumable; --resume also requires the same manifest settings.
Optional --save-actions writes a NEW editable actions.blend beside the atlases.
The companions use the same clips with their existing runtime colour filters.
"""
import argparse, hashlib, json, math, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIPS = ['stand', 'sit', 'drink', 'lie', 'scratch', 'brew', 'recline', 'rise']
WIDTH, HEIGHT, COLUMNS, FRAMES, FPS = 256, 192, 8, 24, 8
COUNTS = {name: 16 if name in ('recline', 'rise') else FRAMES for name in CLIPS}


def arguments():
    raw = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--phase', choices=['day', 'morning', 'evening', 'night'], default='day')
    p.add_argument('--preview', action='store_true')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--frames', type=int, help='Bound the number of frames per clip for a partial test')
    p.add_argument('--clips', help='Bound a preview to comma-separated clip names')
    p.add_argument('--sample', type=float, default=.5, help='Normalised preview phase')
    p.add_argument('--no-depth', action='store_true')
    p.add_argument('--save-actions', action='store_true')
    p.add_argument('--pack-only', action='store_true')
    p.add_argument('--pack-python', type=Path, default=Path(os.environ.get(
        'RESORT_PACK_PYTHON', Path.home()/'AppData/Local/Programs/Python/Python313/python.exe')))
    return p.parse_args(raw)


def pack(out, preview=False):
    """Pillow lives in the host Python, not the Blender installation."""
    from PIL import Image, ImageDraw
    meta = json.loads((out/'life.json').read_text(encoding='utf-8'))
    if preview:
        sheet = Image.new('RGBA', (WIDTH*4, (HEIGHT+24)*2), '#204642')
        draw = ImageDraw.Draw(sheet)
        for row, name in enumerate(CLIPS):
            path = out/'colour'/f'{name}-preview.png'
            if not path.exists(): continue
            with Image.open(path) as frame:
                sheet.alpha_composite(frame.convert('RGBA'), (row%4*WIDTH, row//4*(HEIGHT+24)))
            draw.text((row%4*WIDTH+8, row//4*(HEIGHT+24)+HEIGHT+4), name, fill='white')
        sheet.convert('RGB').save(out/'life-contact-sheet.jpg', quality=94)
        return
    for folder, filename in [('colour', 'life.png'), ('depth', 'life-depth.png')]:
        if not (out/folder).exists():
            continue
        target = Image.new('RGBA', (WIDTH*COLUMNS, HEIGHT*3*len(CLIPS)))
        for row, name in enumerate(CLIPS):
            count = meta['frameCounts'].get(name, FRAMES)
            for frame in range(FRAMES):
                path = out/folder/f'{name}-{min(frame, count-1):03}.png'
                if not path.exists():
                    raise RuntimeError(f'Cannot package an incomplete atlas: {path}')
                with Image.open(path) as source:
                    target.paste(source.convert('RGBA'), (frame%COLUMNS*WIDTH,
                                (row*3+frame//COLUMNS)*HEIGHT))
        target.save(out/filename, optimize=True)


def bake(a):
    global bpy, Vector, Matrix, Quaternion
    import bpy
    from mathutils import Vector, Matrix, Quaternion
    from bpy_extras.object_utils import world_to_camera_view

    assert a.out.is_absolute(), '--out must be absolute; all outputs stay under it'
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    base = bpy.data.scenes.get('Resort_Island')
    scene = bpy.data.scenes.get('Mascot_Pip')
    rig = bpy.data.objects.get('CharacterArmature')
    mesh = bpy.data.objects.get('Pip_V5_Generated')
    assert base and scene and rig and mesh, 'Audit failed: expected retained V6 scene/rig missing'
    audit = {'source':bpy.data.filepath, 'scene':scene.name, 'rig':rig.name,
             'mesh':mesh.name, 'vertices':len(mesh.data.vertices),
             'camera':base.camera.name, 'bones':[b.name for b in rig.data.bones],
             'objects':[{'name':o.name,'type':o.type,'hidden':o.hide_render} for o in scene.objects]}
    (out/'source-audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    # Existing source helpers author the rig pose but are never asked to render
    # or save. EEVEE is set explicitly before every render in this script.
    def load(relative):
        p = ROOT/relative
        scope = {'__file__':str(p)}
        exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'), scope)
        return scope
    load('art/island/resort_time_of_day.py')['apply'](a.phase)
    poses = load('art/island/pip_v6_poses.py')
    poses['setup']()
    bpy.context.window.scene = scene
    cup = poses['cup']
    for o in scene.objects:
        if o.type not in ('CAMERA','LIGHT','ARMATURE'):
            o.hide_render = o != mesh
        if o.type == 'ARMATURE':
            o.hide_render = o != rig
        if o.type == 'LIGHT':
            original = next((p for p in base.objects if p.type=='LIGHT' and o.name.startswith(p.name)), None)
            if original:
                o.data.energy, o.data.color = original.data.energy, original.data.color
                o.rotation_euler = original.rotation_euler
    mesh.hide_render = mesh.hide_viewport = False
    rig.hide_viewport = False
    scene.world = base.world
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.eevee.taa_render_samples = 32 if not a.preview else 16
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.use_compositing = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.fps = FPS
    scene.view_settings.view_transform = base.view_settings.view_transform
    scene.view_settings.look = base.view_settings.look
    scene.view_settings.exposure = base.view_settings.exposure
    camera = scene.camera
    camera.rotation_euler = base.camera.rotation_euler
    camera.location = Vector((0, .24, .66)) + camera.rotation_euler.to_quaternion()@Vector((0,0,10))
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 3.2
    camera.data.dof.use_dof = False
    bpy.context.view_layer.update()

    # Props match the retained warm ivory mug and teal/coral furniture palette.
    def material(name, colour, roughness=.44):
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        node = mat.node_tree.nodes.get('Principled BSDF')
        node.inputs['Base Color'].default_value = (*colour,1)
        node.inputs['Roughness'].default_value = roughness
        return mat
    porcelain = material('V7 kettle warm porcelain', (.73,.77,.65))
    tea = material('V7 flowing amber tea', (.22,.065,.015), .22)
    steam_mat = material('V7 soft tea steam', (.64,.78,.74), .8)
    for old in list(bpy.data.objects):
        if old.name.startswith('V7 Life '):
            bpy.data.objects.remove(old, do_unlink=True)
    kettle = bpy.data.objects.new('V7 Life kettle root', None)
    scene.collection.objects.link(kettle)
    parts = []
    def sphere(name, radius, location, scale, mat, parent=None):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius, location=location)
        obj = bpy.context.object
        obj.name = 'V7 Life '+name
        obj.scale = scale
        for p in obj.data.polygons: p.use_smooth = True
        obj.data.materials.append(mat)
        obj.parent = parent
        parts.append(obj)
        return obj
    def tube(name, points, radius, mat, parent=None):
        data = bpy.data.curves.new('V7 Life '+name, 'CURVE')
        data.dimensions, data.resolution_u, data.bevel_depth, data.bevel_resolution = '3D', 12, radius, 3
        spline = data.splines.new('BEZIER')
        spline.bezier_points.add(len(points)-1)
        for point, xyz in zip(spline.bezier_points, points):
            point.co = xyz
            point.handle_left_type = point.handle_right_type = 'AUTO'
        obj = bpy.data.objects.new('V7 Life '+name, data)
        scene.collection.objects.link(obj)
        obj.data.materials.append(mat)
        obj.parent = parent
        parts.append(obj)
        return obj
    sphere('kettle body', .13, (0,0,0), (1,.88,.9), porcelain, kettle)
    sphere('kettle lid', .08, (0,0,.105), (1,1,.22), porcelain, kettle)
    sphere('kettle knob', .022, (0,0,.135), (1,1,.8), porcelain, kettle)
    tube('kettle spout',[(.095,0,.015),(.165,0,.035),(.24,0,.105)],.027,porcelain,kettle)
    tube('kettle handle',[(-.075,.065,.09),(-.15,.07,.09),(-.19,.07,0),(-.12,.07,-.07)],.018,porcelain,kettle)
    stream = tube('visible tea pour',[(0,0,0),(0,0,-.1),(0,0,-.2)], .009, tea)
    steam = [tube('steam '+str(i),[(0,0,0),(.008,0,.07),(-.005,0,.14)],.004,steam_mat) for i in range(2)]

    def reset():
        poses['pose']('browsing',0)
        rig.scale = (poses['SCALE'],)*3
        rig.rotation_euler = (0,0,0)
        rig.location = (0,0,0)
        cup.hide_render = True
        for obj in parts: obj.hide_render = True
    def snapshot():
        return {b.name:b.matrix_basis.copy() for b in rig.pose.bones}
    def apply_snapshot(data):
        for b in rig.pose.bones: b.matrix_basis = data[b.name]
    def standing(phase):
        reset()
        poses['arm']('L',(.86,-.035,.92+.012*math.sin(phase)))
        poses['arm']('R',(-.86,-.035,.92+.012*math.sin(phase+1)))
        rig.pose.bones['Head'].rotation_quaternion @= Quaternion((0,0,1), .025*math.sin(phase))
    def seated(phase, drink=False):
        reset()
        poses['pose']('done',0)
        rig.scale = (poses['SCALE'],)*3
        rig.rotation_euler = (0,0,0)
        u = (phase/math.tau)%1
        def ease(v):
            v=max(0,min(1,v));return v*v*(3-2*v)
        lift = (ease((u-.08)/.30) if u < .4 else 1 if u < .62 else 1-ease((u-.62)/.30)) if drink else 0
        # The rim, rather than the centre of the mug, touches the mouth.
        # Move the wrist inward as it rises; this avoids the old shoulder sip.
        poses['arm']('R',(-.26+.275*lift,-.55-.24*lift,1.15+.63*lift))
        poses['arm']('L',(.46,-.45,.89))
        rig.pose.bones['Head'].rotation_quaternion @= Quaternion((1,0,0), -.16*lift+.02*math.sin(phase)*(1-lift))
        bpy.context.view_layer.update()
        cup.location = rig.matrix_world@rig.pose.bones['LowerArm.R'].tail+Vector((0,-.03,.035))
        cup.rotation_euler = (-.26*lift,0,0)
        cup.scale = (1.25,)*3
        cup.hide_render = not drink
    def lying(phase, scratch=False):
        reset()
        # Straight legs + softened knees, face upward. Object transform makes
        # the body horizontal; the root stays at the foot end of the mattress.
        poses['arm']('L',(.31,-.31,1.10))
        stroke = .12*math.sin(phase*3) if scratch else .015*math.sin(phase)
        rub_height = .045*math.cos(phase*3) if scratch else 0
        poses['arm']('R',(-.16+stroke,-.34,1.00+rub_height))
        rig.pose.bones['Head'].rotation_quaternion @= Quaternion((1,0,0),-.05)
        rig.rotation_euler = (-math.pi/2,0,0)
        rig.location = (0,0,0)
    def brewed(phase):
        standing(phase)
        u = (phase/math.tau)%1
        pouring = math.sin(math.pi*max(0,min(1,(u-.18)/.58)))**2 if .18 < u < .76 else 0
        poses['arm']('L',(.27,-.63,1.13))
        poses['arm']('R',(-.28,-.66,1.66+.04*pouring))
        rig.pose.bones['Head'].rotation_quaternion @= Quaternion((1,0,0), .10)
        bpy.context.view_layer.update()
        hand = rig.matrix_world@rig.pose.bones['LowerArm.R'].tail
        kettle.location = hand+Vector((.035,-.032,-.075))
        kettle.rotation_euler = (0,.66*pouring,0)
        for obj in parts[:5]: obj.hide_render = False
        cup.location = rig.matrix_world@rig.pose.bones['LowerArm.L'].tail+Vector((0,-.01,.025))
        cup.scale = (1.25,)*3
        cup.rotation_euler = (0,0,0)
        cup.hide_render = False
        bpy.context.view_layer.update()
        start = kettle.matrix_world@Vector((.24,0,.105))
        end = cup.location+Vector((0,0,.035))
        for i, point in enumerate(stream.data.splines[0].bezier_points):
            point.co = start.lerp(end,i/2)
        stream.hide_render = pouring < .18
        for i,obj in enumerate(steam):
            obj.location = cup.location+Vector((.025*(i-.5),0,.09))
            obj.rotation_euler.z = .3*math.sin(phase+i)
            obj.hide_render = pouring < .4

    # Measure contact once at rest. Keep a fixed clearance through the whole
    # scratching loop so the mattress contact does not bob with the hand.
    lying(0)
    bpy.context.view_layer.update()
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    lie_points = [evaluated.matrix_world@v.co for v in evaluated.data.vertices]
    lie_min = min(p.z for p in lie_points)
    lie_offset = -lie_min+.015
    lie_bbox = [[min(p[i] for p in lie_points),max(p[i] for p in lie_points)] for i in range(3)]

    def pose(name, phase=0, transition=0):
        if name in ('stand',): standing(phase)
        elif name in ('sit','drink'): seated(phase,name=='drink')
        elif name in ('lie','scratch'): lying(phase,name=='scratch')
        elif name == 'brew': brewed(phase)
        else:
            standing(0)
            first = snapshot()
            lying(0)
            last = snapshot()
            t = transition if name=='recline' else 1-transition
            # Slow settling near the mattress and a small knee tuck make the
            # change read as reclining/getting up, not a hard atlas switch.
            t = t*t*(3-2*t)
            apply_snapshot({n:first[n].lerp(last[n],t) for n in first})
            rig.rotation_euler = (-math.pi/2*t,0,0)
            rig.location = (0,0,0)
        bpy.context.view_layer.update()

    origin = world_to_camera_view(scene,camera,Vector((0,0,0)))
    camera_right = camera.rotation_euler.to_quaternion()@Vector((1,0,0))
    projected_right = world_to_camera_view(scene,camera,camera_right)
    ppm = abs(projected_right.x-origin.x)*WIDTH
    depth_origin = -(camera.matrix_world.inverted()@Vector((0,0,0))).z
    meta = {'atlas':'life.png','depthAtlas':None if a.no_depth else 'life-depth.png',
            'width':WIDTH,'height':HEIGHT,'frames':FRAMES,'fps':FPS,
            'columns':COLUMNS,'rowsPerClip':3,'clips':CLIPS,'frameCounts':COUNTS,
            'ppm':ppm,'anchorX':origin.x*WIDTH,'anchorY':(1-origin.y)*HEIGHT,
            'depthScale':4,'depthBias':2,'phase':a.phase,'engine':'BLENDER_EEVEE_NEXT',
            'lying':{'headDirection':[0,1,0],'rootOffset':lie_offset,'bounds':lie_bbox,
                     'rootAt':'feet','contactClearance':.015},
            'facialRig':False,'teapot':True,'pourStream':True,
            'sip':{'headBackRadians':.16,'cupTiltRadians':.26,
                   'raise':[.08,.38],'hold':[.38,.62],'lower':[.62,.92]},
            'bakerSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    previous = out/'life.json'
    if a.resume and previous.exists():
        old = json.loads(previous.read_text(encoding='utf-8'))
        assert all(old.get(k)==meta[k] for k in ('width','height','frames','fps','columns','rowsPerClip','phase','bakerSha256')), 'Resume settings differ'
    previous.write_text(json.dumps(meta,indent=2),encoding='utf-8')

    depth_material = bpy.data.materials.new('V7 Life temporary camera depth')
    depth_material.use_nodes = True
    nodes = depth_material.node_tree.nodes
    nodes.clear()
    links = depth_material.node_tree.links
    cam = nodes.new('ShaderNodeCameraData')
    sub = nodes.new('ShaderNodeMath'); sub.operation='SUBTRACT'; sub.inputs[1].default_value=depth_origin
    add = nodes.new('ShaderNodeMath'); add.operation='ADD'; add.inputs[1].default_value=2
    div = nodes.new('ShaderNodeMath'); div.operation='DIVIDE'; div.inputs[1].default_value=4
    emission = nodes.new('ShaderNodeEmission'); output = nodes.new('ShaderNodeOutputMaterial')
    links.new(cam.outputs['View Z Depth'],sub.inputs[0]); links.new(sub.outputs[0],add.inputs[0])
    links.new(add.outputs[0],div.inputs[0]); links.new(div.outputs[0],emission.inputs[0])
    links.new(emission.outputs[0],output.inputs[0])
    material_slots = [(slot,slot.link,slot.material) for o in [mesh,cup]+parts for slot in o.material_slots]
    colour_settings = (scene.view_settings.view_transform,scene.view_settings.look,scene.view_settings.exposure)
    started = time.monotonic()
    frames = []
    selected = a.clips.split(',') if a.clips else CLIPS
    assert all(name in CLIPS for name in selected), 'Unknown activity clip'
    for name in selected:
        if a.preview:
            frames.append((name,'preview', a.sample, a.sample))
        else:
            count = min(COUNTS[name], a.frames or COUNTS[name])
            for frame in range(count):
                frames.append((name,f'{frame:03}',frame/COUNTS[name],frame/(COUNTS[name]-1)))
    for mode in (['colour'] if a.no_depth else ['colour','depth']):
        folder = out/mode
        folder.mkdir(exist_ok=True)
        if mode == 'depth':
            for slot,_,_ in material_slots: slot.link='OBJECT'; slot.material=depth_material
            scene.view_settings.view_transform='Standard'
            scene.view_settings.look='None'
            scene.view_settings.exposure=0
            scene.eevee.taa_render_samples=16
        for i,(name,filename,u,t) in enumerate(frames):
            path = folder/f'{name}-{filename}.png'
            if a.resume and path.exists(): continue
            pose(name,u*math.tau,t)
            scene.render.engine='BLENDER_EEVEE_NEXT'
            scene.render.filepath=str(path)
            bpy.ops.render.render(write_still=True)
            (out/'progress.json').write_text(json.dumps({'phase':a.phase,'mode':mode,'clip':name,
                'frame':i+1,'frames':len(frames),'seconds':round(time.monotonic()-started,2)}),encoding='utf-8')
        if mode == 'depth':
            for slot,link,mat in material_slots: slot.material=mat; slot.link=link
            scene.view_settings.view_transform,scene.view_settings.look,scene.view_settings.exposure=colour_settings
    if a.save_actions:
        all_actions = {}
        moving = [rig,cup,kettle]+parts
        for name in CLIPS:
            actions = {obj:None for obj in moving}
            curve_action = None
            for frame in range(COUNTS[name]+1):
                for obj in moving:
                    if obj.animation_data: obj.animation_data.action=None
                if stream.data.animation_data: stream.data.animation_data.action=None
                pose(name,(frame%COUNTS[name])/COUNTS[name]*math.tau,min(frame/(COUNTS[name]-1),1))
                data=snapshot(); location=rig.location.copy(); rotation=rig.rotation_euler.copy()
                rig.animation_data.action=actions[rig]
                apply_snapshot(data)
                rig.location,rig.rotation_euler=location,rotation
                for bone in rig.pose.bones:
                    for channel in ('location','rotation_quaternion' if bone.rotation_mode=='QUATERNION' else 'rotation_euler','scale'):
                        bone.keyframe_insert(channel,frame=frame+1,group=bone.name)
                for obj in moving:
                    transforms=(obj.location.copy(),obj.rotation_euler.copy(),obj.scale.copy(),obj.hide_render)
                    obj.animation_data_create()
                    obj.animation_data.action=actions[obj]
                    obj.location,obj.rotation_euler,obj.scale,obj.hide_render=transforms
                    for channel in ('location','rotation_euler','scale','hide_render'):
                        obj.keyframe_insert(channel,frame=frame+1)
                    actions[obj]=obj.animation_data.action
                    actions[obj].name='V7_Life_'+name+('' if obj==rig else '__'+obj.name)
                    actions[obj].use_fake_user=True
                stream_points=[p.co.copy() for p in stream.data.splines[0].bezier_points]
                stream.data.animation_data_create()
                stream.data.animation_data.action=curve_action
                for point,co in zip(stream.data.splines[0].bezier_points,stream_points):
                    point.co=co
                    point.keyframe_insert('co',frame=frame+1)
                curve_action=stream.data.animation_data.action
                curve_action.name='V7_Life_'+name+'__pour-curve'
                curve_action.use_fake_user=True
            all_actions[name]=(actions,curve_action)
        for obj,action in all_actions['drink'][0].items(): obj.animation_data.action=action
        stream.data.animation_data.action=all_actions['drink'][1]
        scene.frame_start,scene.frame_end=1,FRAMES
        scene.frame_set(12)
        bpy.ops.wm.save_as_mainfile(filepath=str(out/'actions.blend'),compress=True)
    complete = not a.frames or a.frames >= FRAMES
    if a.preview or complete:
        if not a.pack_python.exists():
            raise RuntimeError(f'Host Python for packaging not found: {a.pack_python}')
        command=[str(a.pack_python),str(Path(__file__).resolve()),'--out',str(out),'--pack-only']
        if a.preview: command.append('--preview')
        subprocess.run(command,check=True)
    (out/'progress.json').write_text(json.dumps({'phase':a.phase,'complete':complete,
        'preview':a.preview,'renders':len(frames)*(1 if a.no_depth else 2),
        'seconds':round(time.monotonic()-started,2)}),encoding='utf-8')
    print('V7_LIFE_DONE',json.dumps(meta))


if __name__ == '__main__':
    args = arguments()
    if args.pack_only: pack(args.out,args.preview)
    else: bake(args)
