"""Use downloaded models and PBR maps for V2; no hand-built substitutes.

Inputs are recorded in art/ASSET_SOURCES.md. Images are packed in the review
blend, so the editable scene survives without the download cache.
"""
import bpy, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT.parent/'asset-downloads/resort-v2'
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
c=bpy.data.collections.get('Resort V2 licensed assets')
if c:
    for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
else:
    c=bpy.data.collections.new('Resort V2 licensed assets');s.collection.children.link(c)

def adopt(o):
    for col in list(o.users_collection):col.objects.unlink(o)
    c.objects.link(o)
def image(path,noncolor=False):
    im=bpy.data.images.load(str(path),check_existing=True)
    if noncolor:im.colorspace_settings.name='Non-Color'
    return im
def texture(matname,folder,asset,tile_size):
    m=bpy.data.materials.get(matname) or bpy.data.materials.new(matname);m.use_nodes=True
    n=m.node_tree.nodes;n.clear();l=m.node_tree.links
    p=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(p.outputs[0],out.inputs[0])
    coord=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeVectorMath');mapping.operation='SCALE';mapping.inputs[3].default_value=1/tile_size;l.new(coord.outputs['Object'],mapping.inputs[0])
    diff=n.new('ShaderNodeTexImage');diff.image=image(folder/'textures'/f'{asset}_diff_1k.jpg');diff.projection='BOX';diff.projection_blend=.3
    l.new(mapping.outputs[0],diff.inputs['Vector']);l.new(diff.outputs['Color'],p.inputs['Base Color'])
    rough=n.new('ShaderNodeTexImage');rough.image=image(folder/'textures'/f'{asset}_rough_1k.exr',True);rough.projection='BOX';rough.projection_blend=.3
    l.new(mapping.outputs[0],rough.inputs['Vector']);l.new(rough.outputs[0],p.inputs['Roughness'])
    disp=n.new('ShaderNodeTexImage');disp.image=image(folder/'textures'/f'{asset}_disp_1k.png',True);disp.projection='BOX';disp.projection_blend=.3
    l.new(mapping.outputs[0],disp.inputs['Vector']);bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.28;bump.inputs['Distance'].default_value=.012
    l.new(disp.outputs[0],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
    return m

sand=texture('V2 scanned coastal sand',ASSETS/'textures-pbr/coast_sand_01','coast_sand_01',2.5)
plaster=texture('V2 scanned white stucco',ASSETS/'textures-pbr/white_stucco','white_stucco',1.5)
wood=texture('V2 scanned teak deck',ASSETS/'textures-pbr/wood_floor_deck','wood_floor_deck',1.3)
# The scan is gray wet coastal sand; grade its albedo toward dry coral sand.
nt=sand.node_tree;p=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
color=next(n for n in nt.nodes if n.type=='TEX_IMAGE' and '_diff_' in n.image.name)
mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[0].default_value=.45;mix.inputs[2].default_value=(.78,.66,.44,1)
nt.links.new(color.outputs['Color'],mix.inputs[1]);nt.links.new(mix.outputs[0],p.inputs['Base Color'])
for o in s.objects:
    if o.type=='MESH' and o.data.materials:
        if o.name.startswith('Island sand'):o.data.materials[0]=sand
        elif o.name.startswith(('Cottage','V2 stucco','Porch post')):o.data.materials[0]=plaster
        elif o.name.startswith(('Deck plank','Terrace','V2 porch','Porch canopy','Outdoor desk','Desk leg','Coffee bench','Coffee table')):o.data.materials[0]=wood
    if o.name.startswith(('V2 tapered coconut','V2 palm','V2 individual palm','V2 coconut')):o.hide_render=True

before=set(s.objects);bpy.ops.import_scene.fbx(filepath=str(ASSETS/'palms/palm_tree.FBX'))
parts=list(set(s.objects)-before)
for o in parts:adopt(o)
# Adapt the licensed palm's silhouette rather than rebuilding it. Broader crowns
# and slightly curved thicker trunks suit the small resort scale.
for o in parts:
    if o.type!='MESH':continue
    bottom=min(v.co.z for v in o.data.vertices);top=max(v.co.z for v in o.data.vertices)
    for v in o.data.vertices:
        t=(v.co.z-bottom)/(top-bottom)
        fac=1.65 if t>.70 else 1.35
        v.co.x*=fac;v.co.y*=fac
        v.co.x+=35*t*t
    o.data.update()
bound=[o.matrix_world@Vector(v) for o in parts if o.type=='MESH' for v in o.bound_box]
lo=Vector(tuple(min(v[i] for v in bound) for i in range(3)));hi=Vector(tuple(max(v[i] for v in bound) for i in range(3)))
# Authored UV+alpha foliage and scanned bark. Keep mesh topology and UVs intact.
m=bpy.data.materials.get('V2 Nobiax textured palm') or bpy.data.materials.new('V2 Nobiax textured palm');m.use_nodes=True
n=m.node_tree.nodes;n.clear();l=m.node_tree.links;p=n.new('ShaderNodeBsdfPrincipled');p.inputs['Roughness'].default_value=.6
out=n.new('ShaderNodeOutputMaterial');l.new(p.outputs[0],out.inputs[0])
diff=n.new('ShaderNodeTexImage');diff.image=image(ASSETS/'palms/diffus.tga');l.new(diff.outputs['Color'],p.inputs['Base Color']);l.new(diff.outputs['Alpha'],p.inputs['Alpha'])
normal=n.new('ShaderNodeTexImage');normal.image=image(ASSETS/'palms/normal.tga',True);nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.55;l.new(normal.outputs['Color'],nm.inputs[1]);l.new(nm.outputs[0],p.inputs['Normal'])
m.surface_render_method='DITHERED'
for o in parts:
    if o.type=='MESH':o.data.materials.clear();o.data.materials.append(m)
root=bpy.data.objects.new('V2 licensed palm 0',None);c.objects.link(root)
for o in parts:
    if not o.parent:o.parent=root
center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
for idx,(x,y,height,angle) in enumerate([(-3.5,1.1,4.6,.4),(3.0,1.85,4.9,-.5),(3.6,-.7,4.1,1.4)]):
    if idx==0:r=root
    else:
        r=bpy.data.objects.new('V2 licensed palm '+str(idx),None);c.objects.link(r)
        mapping={}
        for original in parts:
            clone=original.copy();c.objects.link(clone);mapping[original]=clone
        for original,clone in mapping.items():clone.parent=mapping.get(original.parent,r)
    scale=height/(hi.z-lo.z);r.scale=(scale,)*3;r.rotation_euler[2]=angle
    rotated=Vector((center.x*math.cos(angle)-center.y*math.sin(angle),center.x*math.sin(angle)+center.y*math.cos(angle),center.z))
    r.location=Vector((x,y,.43))-rotated*scale

# Replace procedural boulders with the downloaded, textured CC0 scan.
rockfile=ASSETS/'rocks-boulder/boulder_01_1k.gltf'
if rockfile.exists():
    for o in s.objects:
        if o.name.startswith('V2 coastal boulder'):o.hide_render=True
    before=set(s.objects);bpy.ops.import_scene.gltf(filepath=str(rockfile))
    rocks=list(set(s.objects)-before)
    for o in rocks:adopt(o)
    rock=next(o for o in rocks if o.type=='MESH')
    dims=rock.dimensions.copy();loz=min((rock.matrix_world@Vector(v)).z for v in rock.bound_box)
    for idx,(x,y,height,angle) in enumerate([(-4,-1.4,.8,.2),(-3.9,-2,.42,2),(3.9,.15,1.05,.8),(4.15,.9,.6,2.4),(1.8,3.25,.55,1.1),(-2.75,-2.6,.43,-.6)]):
        o=rock if idx==0 else rock.copy()
        if idx:c.objects.link(o)
        o.name='V2 scanned boulder '+str(idx);scale=height/dims.z;o.scale=(scale,)*3
        o.rotation_euler[2]=angle;o.location=(x,y,.17-loz*scale)

# A temporary actual 3D actor shows scale/lighting in the review only.
if bpy.data.collections.get('CH-snow'):
    o=bpy.data.objects.new('V2 actor review instance',None);c.objects.link(o)
    o.instance_type='COLLECTION';o.instance_collection=bpy.data.collections['CH-snow']
    o.location=(-.3,-1.7,.43);o.scale=(.78,)*3;o['review_only']=True

s.camera.location=(11,-18,13);s.camera.rotation_euler=(Vector((0,0,.85))-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.lens=38
for lamp in s.objects:
    if lamp.type=='LIGHT' and lamp.data.type=='AREA':lamp.data.energy=450 if 'key' in lamp.name.lower() else 220
s.render.engine='CYCLES';s.cycles.samples=48;s.render.resolution_percentage=50;s.render.film_transparent=False
s.render.filepath=str(ROOT/'wallpaper/assets/resort-v2-review.png');s.frame_set(1)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort-v2.blend'))
bpy.ops.render.render(write_still=True)
result={'preview':s.render.filepath,'palms':'Nobiax existing FBX and UV maps','pbr':'Poly Haven sand/stucco/deck','actor':'Blender Studio Snow existing rig','final':False}
