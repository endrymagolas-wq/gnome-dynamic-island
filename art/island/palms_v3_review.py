"""Replace rejected palm cards with CC0 Nobiax v3 curved feathered palms."""
import bpy,math
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[2];folder=ROOT.parent/'asset-downloads/resort-v2/palms-better'
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
for o in s.objects:
    if o.type=='MESH' and any(m and m.name=='V2 Nobiax textured palm' for m in o.data.materials):o.hide_render=True
c=bpy.data.collections.get('Resort V3 palms')
if c:
    for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
else:c=bpy.data.collections.new('Resort V3 palms');s.collection.children.link(c)
p=bpy.data.objects.get('palm_bend')
if not p:
    before=set(s.objects);bpy.ops.wm.obj_import(filepath=str(folder/'palm_bend.obj'));p=next(o for o in set(s.objects)-before if o.type=='MESH')
for col in list(p.users_collection):col.objects.unlink(p)
c.objects.link(p);p.name='Resort V3 curved palm 0'
rotation=p.rotation_euler.to_matrix().to_4x4()
for v in p.data.vertices:v.co=rotation@v.co
p.rotation_euler=(0,0,0);p.data.update()
height=max(v.co.z for v in p.data.vertices)-min(v.co.z for v in p.data.vertices)
m=bpy.data.materials.get('Resort Nobiax v3 leaf and bark') or bpy.data.materials.new('Resort Nobiax v3 leaf and bark');m.use_nodes=True
n=m.node_tree.nodes;n.clear();l=m.node_tree.links
bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs[0],out.inputs[0])
bs.inputs['Roughness'].default_value=.76;bs.inputs['Specular IOR Level'].default_value=.22
bs.inputs['Subsurface Weight'].default_value=.06
diff=n.new('ShaderNodeTexImage');diff.image=bpy.data.images.load(str(folder/'diffuse.png'),check_existing=True);diff.image.alpha_mode='STRAIGHT'
l.new(diff.outputs['Color'],bs.inputs['Base Color']);l.new(diff.outputs['Alpha'],bs.inputs['Alpha'])
normal=n.new('ShaderNodeTexImage');normal.image=bpy.data.images.load(str(folder/'normal.png'),check_existing=True);normal.image.colorspace_settings.name='Non-Color'
nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.35;l.new(normal.outputs[0],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal'])
m.surface_render_method='DITHERED';p.data.materials.clear();p.data.materials.append(m)
for i,(x,y,h,ang) in enumerate([(-3.6,1.3,4.8,-.3),(3.5,2.0,4.7,3.5),(3.7,-.7,3.4,1.65)]):
    o=p if i==0 else p.copy()
    if i:c.objects.link(o)
    o.name='Resort V3 curved palm '+str(i);o.location=(x,y,.43);o.scale=(h/height,)*3;o.rotation_euler.z=ang;o.hide_render=False
for im in (diff.image,normal.image):im.pack()
s.render.resolution_percentage=50;s.cycles.samples=48;s.render.filepath=str(ROOT/'wallpaper/assets/resort-v3-review.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort-v2.blend'),compress=True)
bpy.ops.render.render(write_still=True)
result={'preview':s.render.filepath,'palms':3,'source':'Yughues / Nobiax Free Palm TreeZ v3, CC0'}
