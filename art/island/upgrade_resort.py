"""V2 art direction, applied to the owned prototype through Blender MCP.

The image in art/references is a reference, never a backdrop or animated water.
Keep the prototype source intact; save this review to resort-v2.blend.
"""
import bpy, math, random
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
s=bpy.data.scenes['Resort_Island']; bpy.context.window.scene=s
random.seed(74)
collection=bpy.data.collections.get('Resort V2 detailing')
if collection:
    for o in list(collection.objects): bpy.data.objects.remove(o,do_unlink=True)
else:
    collection=bpy.data.collections.new('Resort V2 detailing');s.collection.children.link(collection)

def own(o,name):
    o.name=name
    for c in list(o.users_collection):c.objects.unlink(o)
    collection.objects.link(o)
    return o

def material(name,color,rough=.55,scale=6,bump=.035):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes=True; n=m.node_tree.nodes;n.clear();l=m.node_tree.links
    p=n.new('ShaderNodeBsdfPrincipled');p.inputs['Roughness'].default_value=rough
    out=n.new('ShaderNodeOutputMaterial');l.new(p.outputs[0],out.inputs[0])
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=scale;tex.inputs['Detail'].default_value=3
    ramp=n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color=tuple(x*.78 for x in color)+(1,)
    ramp.color_ramp.elements[1].color=tuple(min(x*1.08,1) for x in color)+(1,)
    l.new(tex.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],p.inputs['Base Color'])
    b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.3;b.inputs['Distance'].default_value=bump
    l.new(tex.outputs['Fac'],b.inputs['Height']);l.new(b.outputs[0],p.inputs['Normal'])
    return m

plaster=material('V2 lime plaster',(.86,.84,.76),.82,80,.009)
sand=material('V2 fine coral sand',(.58,.45,.27),.88,135,.006)
stone=material('V2 weathered coastal limestone',(.47,.44,.36),.82,8,.065)
teak=material('V2 oiled teak',(.37,.18,.068),.48,14,.012)
leaf=material('V2 palm foliage',(.035,.16,.009),.44,26,.01)
leaf.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value=.08
bark=material('V2 coconut bark',(.29,.18,.085),.78,18,.025)
mint=material('V2 painted turquoise wood',(.055,.37,.32),.49,45,.005)
tiles=[material('V2 terracotta '+str(i),(.51+i*.013,.21+i*.008,.10+i*.005),.7,34,.008) for i in range(6)]
linen=material('V2 cream linen',(.69,.64,.49),.9,170,.006)

def mesh(name,v,f,mat):
    me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update()
    ob=bpy.data.objects.new(name,me);collection.objects.link(ob);me.materials.append(mat)
    for p in me.polygons:p.use_smooth=True
    return ob
def cube(name,loc,size,mat,bevel=.02):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=own(bpy.context.object,name);o.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    mod=o.modifiers.new('Rounded crafted edges','BEVEL');mod.width=bevel;mod.segments=3
    o.modifiers.new('Smooth broad surfaces','WEIGHTED_NORMAL');return o
def sphere(name,loc,size,mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=loc)
    o=own(bpy.context.object,name);o.scale=size;o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    return o
def curve(name,points,r,mat):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.resolution_u=12;d.bevel_depth=r;d.bevel_resolution=3
    p=d.splines.new('BEZIER');p.bezier_points.add(len(points)-1)
    for b,pt in zip(p.bezier_points,points):b.co=pt;b.handle_left_type='AUTO';b.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,d);collection.objects.link(o);d.materials.append(mat);return o

# Hide the rejected geometry, retaining it in the editable source for comparison.
for o in s.objects:
    if o.name in collection.objects:continue
    name=o.name
    ancestor=o
    roots=[]
    while ancestor:roots.append(ancestor.name);ancestor=ancestor.parent
    if any(x.startswith(('Palm ','Coastal rock ')) for x in roots) or name.startswith(('Roof tile','Fine foam','Pitched coral roof','Stepping stone')):
        o.hide_render=True
    if o.type=='MESH' and o.data.materials:
        if name.startswith(('Cottage','Porch post')):o.data.materials[0]=plaster
        elif name.startswith(('Terrace','Deck plank','Porch','Outdoor desk','Desk leg','Door','Coffee')):o.data.materials[0]=teak
        elif name.startswith('Shutter'):o.data.materials[0]=mint
        elif name.startswith('Island sand'):o.data.materials[0]=sand

# Curved Mediterranean barrel tiles replace the flat cuboid roof blocks.
pitch=math.atan(.9/1.65)
for side in [-1,1]:
    for col in range(14):
        for row in range(10):
            center=Vector((side*(row+.5)*.166,.36+col*.163,3.48-(row+.5)*.166*.9/1.65))
            down=Vector((side*math.cos(pitch),0,-math.sin(pitch)))
            normal=Vector((side*math.sin(pitch),0,math.cos(pitch)))
            v=[]
            for a in [0,1]:
                for j in range(9):
                    angle=math.pi*j/8
                    pos=center+down*(a-.5)*.21+Vector((0,math.cos(angle)*.084,0))+normal*(math.sin(angle)*.044+.025)
                    v.append(tuple(pos))
            o=mesh('V2 barrel roof tile',v,[(j,j+1,j+10,j+9) for j in range(8)],random.choice(tiles))
            thick=o.modifiers.new('Ceramic thickness','SOLIDIFY');thick.thickness=.013
curve('V2 roof ridge',[(-.01,.26,3.52),(-.01,2.65,3.52)],.085,tiles[3])
for x in [-1.67,1.67]:cube('V2 roof fascia',(x,1.45,2.60),(.075,2.42,.10),teak)
for x in [-1.43,1.43]:cube('V2 stucco corner',(x,1.45,1.66),(.08,1.86,1.98),plaster)
for x in [-1.03,.8]:
    for side in [-1,1]:
        for z in range(11):cube('V2 shutter louver',(x+side*.39,.428,1.46+z*.059),(.17,.052,.018),mint,.006)
    cube('V2 window sill',(x,.37,1.38),(.78,.22,.055),plaster)
for j in range(11):cube('V2 porch slat',(0,-.33+j*.074,2.75),(3.6,.046,.044),teak,.008)

# More natural palm geometry is a review fallback while licensed models download.
# Every leaflet is actual geometry, with a curved tapered trunk and rachis.
for idx,(x,y,h,bend) in enumerate([(-3.6,1.2,4.25,-.85),(3.1,1.6,4.5,.75),(3.75,-.65,3.75,.55)]):
    base=.43;v=[];f=[];sections=35;seg=14
    for j in range(sections+1):
        t=j/sections;cx=x+bend*t*t;cy=y+.20*math.sin(t*1.7);z=base+h*t
        radius=.15*(1-.38*t)*(1+.07*math.sin(t*85))
        for k in range(seg):
            a=math.tau*k/seg;v.append((cx+radius*math.cos(a),cy+radius*math.sin(a),z))
    for j in range(sections):
        for k in range(seg):a=j*seg+k;b=j*seg+(k+1)%seg;f.append((a,b,b+seg,a+seg))
    mesh('V2 tapered coconut trunk',v,f,bark)
    top=Vector((x+bend,y+.20*math.sin(1.7),base+h))
    for frond in range(12):
        a=frond*math.tau/12+idx*.73;direc=Vector((math.cos(a),math.sin(a),0));cross=Vector((-math.sin(a),math.cos(a),0))
        length=1.8+random.random()*.4
        def rach(t):return top+direc*length*t+Vector((0,0,.57*math.sin(t*math.pi)-.65*t*t))
        curve('V2 palm rachis',[rach(t) for t in [0,.25,.5,.75,1]],.014,leaf)
        vv=[];ff=[]
        for j in range(1,26):
            t=j/27;root=rach(t);extent=.47*math.sin(math.pi*t)**.7
            for sign in [-1,1]:
                tip=root+cross*sign*extent+direc*.11+Vector((0,0,-.12*extent))
                mid=root.lerp(tip,.55)+Vector((0,0,.035))
                offset=direc*.026;start=len(vv)
                vv.extend([tuple(root-offset*.25),tuple(root+offset*.25),tuple(mid+offset),tuple(tip),tuple(mid-offset)])
                ff.extend([(start,start+1,start+2,start+4),(start+2,start+3,start+4)])
        mesh('V2 individual palm leaflets',vv,ff,leaf)
    for k in range(4):sphere('V2 coconut',top+Vector((math.cos(k*1.7)*.15,math.sin(k*1.7)*.15,-.15)),(.12,.12,.15),bark)

# Smooth irregular rocks; scanned CC0 assets can replace these independently.
for idx,(x,y,z,size) in enumerate([(-4,-1.4,.32,(.8,.62,.55)),(-3.75,-2.0,.17,(.43,.39,.29)),(3.85,.15,.37,(.90,.75,.71)),(4.17,.93,.29,(.62,.61,.47)),(1.8,3.25,.21,(.52,.48,.42)),(-2.75,-2.6,.23,(.48,.37,.30))]):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4,radius=1,location=(x,y,z));o=own(bpy.context.object,'V2 coastal boulder');o.scale=size;o.rotation_euler=(random.random(),random.random(),random.random())
    for vert in o.data.vertices:
        co=vert.co;fac=1+.09*math.sin(co.x*5+co.y*3)+.05*math.cos(co.z*7);co*=fac
    o.data.materials.append(stone)
    for p in o.data.polygons:p.use_smooth=True

for x in [-.61,.61]:
    sphere('V2 linen seat cushion',(x,-2.12,1.045),(.45,.19,.075),linen)
    o=cube('V2 linen back cushion',(x,-1.96,1.25),(.81,.10,.30),linen,.07)
    o.rotation_euler[0]=-.12
for x,y in [(-1.68,.1),(1.62,.12),(-3.0,1.6)]:
    pot=material('V2 clay planter',(.37,.17,.08),.75,20,.006)
    sphere('V2 terracotta planter',(x,y,.64),(.18,.18,.21),pot)
    for k in range(7):
        a=k*2.4;curve('V2 plant stem',[(x,y,.8),(x+.13*math.cos(a),y+.13*math.sin(a),1.06),(x+.23*math.cos(a),y+.23*math.sin(a),1.09)],.018,leaf)
        sphere('V2 broad tropical leaf',(x+.18*math.cos(a),y+.18*math.sin(a),1.05),(.11,.045,.025),leaf)

# Foam is deliberately omitted until the shoreline pass is rebuilt against depth.
# Avoid rendering the old floating elliptical white stripe over the new scene.
# Frame the entire palm canopy and leave the sea breathing room.
s.camera.location=(11,-18,13)
s.camera.rotation_euler=(Vector((0,0,.85))-s.camera.location).to_track_quat('-Z','Y').to_euler()
s.camera.data.lens=38
for lamp in s.objects:
    if lamp.type=='LIGHT' and lamp.data.type=='AREA':lamp.data.energy=450 if 'key' in lamp.name.lower() else 220
s.cycles.samples=32;s.cycles.use_denoising=True;s.render.resolution_percentage=50
s.render.film_transparent=False;s.frame_set(1)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort-v2.blend'))
s.render.filepath=str(ROOT/'wallpaper/assets/resort-v2-review.png')
bpy.ops.render.render(write_still=True)
result={'source':str(ROOT/'art/island/resort-v2.blend'),'preview':s.render.filepath,'newObjects':len(collection.objects),'final':False}
