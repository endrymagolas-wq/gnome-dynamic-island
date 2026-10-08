"""Reproducible Blender 4.5 island. Run in an empty owned scene via MCP.
Heavy rendering is build-time only. All motion is exactly periodic at 12 seconds.
"""
import bpy, math, json, random
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'wallpaper' / 'assets'
OUT.mkdir(parents=True, exist_ok=True)
random.seed(23)
NAME = 'Resort_Island'
if NAME in bpy.data.scenes:
    scene = bpy.data.scenes[NAME]
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
else:
    scene = bpy.data.scenes.new(NAME)
bpy.context.window.scene = scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 50
scene.render.fps = 30
scene.frame_start, scene.frame_end = 1, 360
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = False
scene.eevee.taa_render_samples = 32
scene.eevee.use_raytracing = True
scene.eevee.use_shadows = True
scene.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('Resort_Sky')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.55,.77,.85,1)
world.node_tree.nodes['Background'].inputs[1].default_value = .65

def mat(name, color, rough=.55):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough
    return m
sand=mat('Warm coral sand',(.76,.61,.37))
wood=mat('Honey teak',(.28,.12,.05))
white=mat('Warm ivory plaster',(.83,.79,.65))
roof=mat('Coral roof',(.48,.15,.075))
mint=mat('Lagoon shutters',(.07,.35,.30))
glass=mat('Blue window',(.08,.22,.26),.15)
green=mat('Palm emerald',(.09,.31,.09))
rock=mat('Warm limestone',(.36,.40,.34))

def mesh(name, verts, faces, material):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name,me); scene.collection.objects.link(ob)
    if material: me.materials.append(material)
    return ob
def cube(name, pos, size, material, bevel=.035):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos)
    o=bpy.context.object; o.name=name; o.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    if bevel:
        m=o.modifiers.new('Soft crafted edges','BEVEL'); m.width=bevel; m.segments=3
        o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return o
def uv(name,pos,scale,material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=pos)
    o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(material)
    for p in o.data.polygons:p.use_smooth=True
    return o
def cyl(name,a,b,r,material):
    d=Vector(b)-Vector(a)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=r,depth=d.length,location=(Vector(a)+Vector(b))/2)
    o=bpy.context.object;o.name=name;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();o.data.materials.append(material)
    return o

def ground(x,y):
    r=math.sqrt((x/5.5)**2+(y/4.3)**2)
    return .43 if r<.72 else .43-(r-.72)*2.35
verts=[]; faces=[]; rings=40; sectors=160
for j in range(rings+1):
    r=.001+j/rings*1.55
    for i in range(sectors):
        a=2*math.pi*i/sectors
        rr=r*(1+.04*math.sin(a*3)+.025*math.cos(a*5))
        x,y=5.5*rr*math.cos(a),4.3*rr*math.sin(a)
        z=ground(x,y)
        verts.append((x,y,z))
for j in range(rings):
    for i in range(sectors):
        a=j*sectors+i;b=j*sectors+(i+1)%sectors
        faces.append((a,b,b+sectors,a+sectors))
island=mesh('Island sand and submerged shelf',verts,faces,sand)
for p in island.data.polygons:p.use_smooth=True
cube('Seabed',(0,0,-3.5),(160,160,.2),mat('Deep aquamarine seabed',(.06,.5,.43)),0)

# Cottage, real shaded geometry and reflections in the same scene as water.
cube('Terrace',(0,1,.53),(3.8,3.0,.18),wood)
for i in range(24):cube('Deck plank',(-1.82+i*.158,.9,.634),(.145,2.75,.018),wood,.006)
cube('Cottage',(0,1.45,1.62),(2.85,1.8,1.95),white)
mesh('Pitched coral roof',[(-1.65,.35,2.58),(1.65,.35,2.58),(0,.35,3.48),(-1.65,2.55,2.58),(1.65,2.55,2.58),(0,2.55,3.48)],[(0,3,5,2),(2,5,4,1),(0,2,1),(3,4,5)],roof)
for side in [-1,1]:
    for row in range(9):
        x=side*(row+.5)*.18;z=3.48-abs(x)/1.65*.9+.025
        for j in range(14):
            o=cube('Roof tile',(x,.39+j*.158,z),(.185,.151,.035),roof,.012)
            o.rotation_euler[1]=side*math.atan(.9/1.65)
cube('Door',(-.4,.531,1.32),(.67,.065,1.38),wood)
uv('Door knob',(-.18,.475,1.30),(.035,.035,.035),mint)
for x in [-1.03,.80]:
    cube('Window frame',(x,.525,1.78),(.65,.06,.72),wood)
    cube('Window glass',(x,.48,1.78),(.52,.025,.59),glass)
    for dx in [-.39,.39]:cube('Shutter',(x+dx,.48,1.78),(.18,.08,.73),mint)
    cube('Window mullion',(x,.45,1.78),(.035,.03,.61),white)
for x in [-1.65,1.65]:cyl('Porch post',(x,-.22,.63),(x,-.22,2.65),.055,white)
cube('Porch canopy',(0,.06,2.67),(3.55,.92,.12),wood)
cube('Porch step',(0,-.69,.48),(2.4,.32,.13),wood)
# Work desk and coffee seating occupy navigable registered positions.
cube('Outdoor desk',(-2.3,-.4,1.10),(1.2,.62,.09),wood)
for x in [-2.8,-1.8]:
    for y in [-.63,-.17]:cube('Desk leg',(x,y,.76),(.06,.06,.67),wood)
cube('Laptop base',(-2.3,-.43,1.17),(.48,.32,.025),mint)
o=cube('Laptop screen',(-2.3,-.24,1.35),(.48,.035,.34),glass);o.rotation_euler[0]=-.15
for x in [-.8,.8]:
    cube('Coffee bench foot',(x,-2.1,.69),(.10,.12,.5),wood)
cube('Coffee bench',(0,-2.1,.97),(2.0,.44,.11),wood)
cube('Coffee bench back',(0,-1.91,1.22),(2.0,.08,.42),mint)
cube('Coffee table',(1.35,-2.15,.96),(.65,.65,.09),wood)
cyl('Coffee table stem',(1.35,-2.15,.43),(1.35,-2.15,.94),.08,wood)
cyl('Coffee cup',(1.35,-2.15,1.01),(1.35,-2.15,1.14),.065,white)

# Prefer imported CC0 assets; own geometry is only the tailored architecture.
assets=ROOT/'art'/'thirdparty'
def find_asset(word):
    return next((p for p in assets.rglob('*.glb') if p.stem.lower()==word.lower()),None)
def imported(path,name,loc,height):
    before=set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects=list(set(scene.objects)-before)
    for o in objects:
        if o.type=='MESH':
            if 'leaf' in o.name.lower():
                for i in range(len(o.data.materials)):o.data.materials[i]=green
            elif 'rock' in name.lower():
                for i in range(len(o.data.materials)):o.data.materials[i]=rock
    bounds=[o.matrix_world@Vector(c) for o in objects if o.type=='MESH' for c in o.bound_box]
    lo=Vector(tuple(min(v[i] for v in bounds) for i in range(3)))
    hi=Vector(tuple(max(v[i] for v in bounds) for i in range(3)))
    root=bpy.data.objects.new(name,None);scene.collection.objects.link(root)
    for o in objects:
        if o.parent is None:o.parent=root
    s=height/max(hi.z-lo.z,.01);root.scale=(s,s,s)
    root.location=Vector(loc)-Vector(((lo.x+hi.x)*.5,(lo.y+hi.y)*.5,lo.z))*s
    return root
for idx,(x,y,h) in enumerate([(-3.6,.8,3.5),(3.2,1.2,3.9),(3.75,-1.5,3.5),(-3.0,2.25,3.2)]):
    path=find_asset('tree_palmDetailedTall') or find_asset('tree_palm')
    if path:imported(path,'Palm '+str(idx),(x,y,ground(x,y)),h)
    else:
        cyl('Palm trunk',(x,y,.43),(x+.2,y,h),.105,wood)
        for k in range(9):
            a=k*2*math.pi/9
            points=[(x+.2,y,h),(x+.2+math.cos(a)*.7,y+math.sin(a)*.7,h+.18),(x+.2+math.cos(a)*1.6,y+math.sin(a)*1.6,h-.38)]
            v=[]
            for j,p in enumerate(points):
                w=[.04,.25,.015][j]
                v.extend([(p[0]+math.sin(a)*w,p[1]-math.cos(a)*w,p[2]),(p[0]-math.sin(a)*w,p[1]+math.cos(a)*w,p[2])])
            mesh('Palm frond',v,[(0,1,3,2),(2,3,5,4)],green)
for i,(x,y) in enumerate([(-4,-1.8),(-4.1,-1.3),(4.0,.1),(3.9,.65),(1.8,3.3),(-2.5,-3)]):
    path=find_asset('rock_largeA')
    if path:imported(path,'Coastal rock '+str(i),(x,y,ground(x,y)),.6+random.random()*.35)
    else:uv('Coastal limestone',(x,y,ground(x,y)+.18),(.6,.4,.4),rock)
for i in range(10):
    x=random.uniform(-1.7,1.7)
    cube('Stepping stone',(x,-.8-random.random()*.7,.449),(.25,.22,.045),white,.05)

# Ocean: actual displaced mesh, transmission, absorption and ray traced reflection.
watermat=mat('Lagoon water',(.08,.65,.58),.14)
watermat.use_raytrace_refraction=True
p=watermat.node_tree.nodes['Principled BSDF'];p.inputs['Transmission Weight'].default_value=.65;p.inputs['IOR'].default_value=1.333
absorb=watermat.node_tree.nodes.new('ShaderNodeVolumeAbsorption')
absorb.inputs['Color'].default_value=(.13,.65,.58,1);absorb.inputs['Density'].default_value=.08
watermat.node_tree.links.new(absorb.outputs[0],watermat.node_tree.nodes['Material Output'].inputs['Volume'])
v=[];f=[];N=180
for j in range(N+1):
    for i in range(N+1):v.append(((i/N-.5)*80,(j/N-.5)*80,0))
for j in range(N):
    for i in range(N):
        a=j*(N+1)+i;f.append((a,a+1,a+N+2,a+N+1))
water=mesh('Water - periodic geometric waves',v,f,watermat)
volume=water.modifiers.new('Closed water volume','SOLIDIFY');volume.thickness=3.1
for poly in water.data.polygons:poly.use_smooth=True
water.shape_key_add(name='Basis')
for name,fn,expr in [('Sine',lambda x,y:.035*math.sin(x*.9+y*.45)+.013*math.sin(x*1.7-y*.8),'sin(2*pi*(frame-1)/360)'),('Cosine',lambda x,y:.035*math.cos(x*.9+y*.45)+.013*math.cos(x*1.7-y*.8),'cos(2*pi*(frame-1)/360)')]:
    key=water.shape_key_add(name=name);key.slider_min=-1
    for i,co in enumerate(v):key.data[i].co.z=fn(co[0],co[1])
    key.driver_add('value').driver.expression=expr
foam=mat('Delicate shore foam',(.77,.91,.85),.8)
v=[];f=[]
for i in range(256):
    a=i*math.tau/256
    r=.903+.023*math.sin(a*3)+.013*math.cos(a*5)
    for dr in [-.005,.008]:v.append((5.5*(r+dr)*math.cos(a),4.3*(r+dr)*math.sin(a),.027))
for i in range(256):f.append((2*i,2*i+1,(2*i+3)%512,(2*i+2)%512))
shore=mesh('Fine foam at waterline',v,f,foam)
for axis in [0,1]:shore.driver_add('scale',axis).driver.expression='1+0.004*sin(2*pi*(frame-1)/360)'

def light(name,pos,power,size,color):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=pos;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
light('Soft afternoon sun',(-6,-8,12),1800,7,(1,.86,.67))
light('Sky bounce',(5,4,10),800,8,(.62,.85,1))
sun=bpy.data.lights.new('Warm daylight','SUN');sun.energy=2.4;sun.angle=.12;sun.color=(1,.92,.79)
sunob=bpy.data.objects.new('Warm daylight',sun);scene.collection.objects.link(sunob);sunob.rotation_euler=(.5,-.4,-.5)
camdata=bpy.data.cameras.new('Resort perspective');cam=bpy.data.objects.new('Fixed resort camera',camdata);scene.collection.objects.link(cam)
cam.location=(11,-16,14);cam.rotation_euler=(Vector((0,0,.25))-cam.location).to_track_quat('-Z','Y').to_euler();camdata.lens=44;scene.camera=cam
scene.frame_set(1)
bpy.context.view_layer.update()
def project(x,y,z):
    p=world_to_camera_view(scene,cam,Vector((x,y,z)))
    return {'x':p.x*1920,'y':(1-p.y)*1080,'depth':p.z}
targets={'desk':[-2.3,-.77,.43],'testing':[2.4,-.4,.43],'permission':[2.3,-2.7,ground(2.3,-2.7)],'done':[0,-2.25,.66],'idle':[0,-2.25,.66],'browsing':[-2.3,1.8,.43]}
meta={'ground':{'ellipse':[5.5,4.3],'plateauRadius':.72,'height':.43,'slope':2.35},'width':1920,'height':1080,'fps':30,'frames':360,'seconds':12,'camera':{'location':list(cam.location),'rotation':list(cam.rotation_euler),'lens':44,'sensor':36,'matrixWorld': [list(r) for r in cam.matrix_world]},'targets':targets,'projections':{k:project(*v) for k,v in targets.items()},'depthRange':[0,50],'assetsImported':bool(find_asset('tree_palm') or find_asset('palm'))}
(OUT/'scene.json').write_text(json.dumps(meta,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art'/'island'/'resort.blend'))
scene.render.filepath=str(OUT/'draft.png');bpy.ops.render.render(write_still=True)
result={'scene':scene.name,'objects':len(scene.objects),'preview':str(OUT/'draft.png'),'source':str(ROOT/'art'/'island'/'resort.blend')}
