"""Review coast, licensed furniture, and coordinated offline foam geometry."""
import bpy,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
table=bpy.data.objects['wooden_table_02'];table.name='V3 scanned work table'
table.location=(-2.3,-.4,.43);table.scale=(1.1,1,.837)
for o in s.objects:
    if o.name.startswith(('Outdoor desk','Desk leg')):o.hide_render=True
    if o.name=='V2 actor review instance':o.hide_render=True
    if o.name.startswith(('Coffee bench','V2 linen')) and not o.get('v3_seat_adjusted'):
        o.location.z-=.17;o['v3_seat_adjusted']=True
for m in table.data.materials:
    if m and m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type=='TEX_IMAGE' and n.image:
                path=ROOT.parent/'asset-downloads/resort-v2/furniture/textures'/Path(n.image.filepath.replace('\\','/')).name
                n.image.filepath=str(path);n.image.reload();n.image.pack()
island=bpy.data.objects['Island sand and submerged shelf']
def perturb(a):return .045*math.sin(3*a)+.035*math.cos(5*a+.4)
if not island.get('v3_natural_coast'):
    for v in island.data.vertices:
        x,y=v.co.x,v.co.y;r=math.hypot(x/5.5,y/4.3)
        a=math.atan2(y/4.3,x/5.5);dr=perturb(a)*min(1,max(0,(r-.72)/.18))
        if r>0:v.co.x*=1+dr/r;v.co.y*=1+dr/r
    island.data.update();island['v3_natural_coast']=True
# A sandy sea bed gives transmission rays a continuous underwater surface.
bed=bpy.data.objects.get('V3 lagoon sandy seabed')
if not bed:
    bpy.ops.mesh.primitive_plane_add(size=160,location=(0,0,-3.3));bed=bpy.context.object;bed.name='V3 lagoon sandy seabed'
    m=bpy.data.materials.new('V3 deep lagoon sand');m.use_nodes=True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.40,.48,.40,1)
    m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.95;bed.data.materials.append(m)
# Narrow broken foam, aligned to the perturbed shoreline and the same periodic
# geometric wave field as the sea; rendered together, never a floating overlay.
foam=bpy.data.objects.get('V3 waterline foam')
if not foam:
    vertices=[];faces=[];N=512
    for i in range(N):
        a=i*math.tau/N
        for d in (-.007,.011):
            r=.903+perturb(a)+d;vertices.append((5.5*r*math.cos(a),4.3*r*math.sin(a),.016))
    for i in range(N):faces.append((i*2,i*2+1,((i+1)%N)*2+1,((i+1)%N)*2))
    mesh=bpy.data.meshes.new('V3 periodic foam mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
    foam=bpy.data.objects.new('V3 waterline foam',mesh);s.collection.objects.link(foam)
    uv=mesh.uv_layers.new(name='Shore band UV')
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            index=mesh.loops[li].vertex_index;uv.data[li].uv=(index//2/N,index%2)
    foam.shape_key_add(name='Basis')
    for name,fn,expr in [('Sine',lambda x,y:.035*math.sin(x*.9+y*.45)+.013*math.sin(x*1.7-y*.8),'sin(2*pi*(frame-1)/360)'),('Cosine',lambda x,y:.035*math.cos(x*.9+y*.45)+.013*math.cos(x*1.7-y*.8),'cos(2*pi*(frame-1)/360)')]:
        key=foam.shape_key_add(name=name);key.slider_min=-1
        for i,(x,y,z) in enumerate(vertices):key.data[i].co.z=z+fn(x,y)
        key.driver_add('value').driver.expression=expr
    m=bpy.data.materials.new('V3 broken quiet shore foam');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links
    p=n['Principled BSDF'];p.inputs['Base Color'].default_value=(.65,.82,.75,1);p.inputs['Roughness'].default_value=.8
    coord=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=15;noise.inputs['Detail'].default_value=2
    l.new(coord.outputs['Object'],noise.inputs[0]);ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.46;ramp.color_ramp.elements[1].position=.64
    l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],p.inputs['Alpha']);m.surface_render_method='DITHERED';mesh.materials.append(m)
s.camera.data.lens=44
s.render.resolution_percentage=50;s.cycles.samples=48;s.frame_set(1)
s.render.filepath=str(ROOT/'wallpaper/assets/resort-v3-coast-review.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort-v2.blend'),compress=True)
bpy.ops.render.render(write_still=True)
result={'preview':s.render.filepath,'source':bpy.data.filepath,'final':False}
