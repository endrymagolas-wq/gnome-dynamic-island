"""Customize the CC-BY Snow mesh without changing its authored rig or weights."""
import bpy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
hair = bpy.data.objects['GEO-snow_hair_base']
if not hair.get('resort_short_hair'):
    # Keep the existing textured waves; collapse the high ponytail into a short
    # crown. Apply identical displacements to each corrective shape key.
    groups = {g.index:g.name for g in hair.vertex_groups}
    keys = hair.data.shape_keys.key_blocks if hair.data.shape_keys else []
    for v in hair.data.vertices:
        pony = sum(g.weight for g in v.groups if 'Ponytail' in groups[g.group])
        old = v.co.copy(); new = old.copy()
        if old.z > 1.77:
            new.z = 1.77 + (old.z-1.77)*.45
        if pony > .25:
            new.y *= .50
        delta = new-old
        if keys:
            for key in keys:key.data[v.index].co += delta
        else:v.co = new
    hair['resort_short_hair'] = True
    hair.data.update()
for material in bpy.data.materials:
    if not material.use_nodes:continue
    color = (.095,.034,.012,1) if material.name.startswith('snow.hair') else None
    if color:
        for n in material.node_tree.nodes:
            if n.type=='BSDF_PRINCIPLED':
                for link in list(n.inputs['Base Color'].links):material.node_tree.links.remove(link)
                n.inputs['Base Color'].default_value=color
                n.inputs['Roughness'].default_value=.65
# Remove only orphaned materials/images belonging to the appended Snow asset.
for material in list(bpy.data.materials):
    if material.name.startswith('snow.') and material.users==0:
        bpy.data.materials.remove(material)
resized=[]
for im in list(bpy.data.images):
    if 'character-snow' not in im.filepath:continue
    if im.users==0:bpy.data.images.remove(im);continue
    if im.source!='TILED' and max(im.size)>1024:
        ratio=1024/max(im.size);im.scale(max(1,int(im.size[0]*ratio)),max(1,int(im.size[1]*ratio)))
        im.pack();resized.append(im.name)
bpy.ops.file.pack_all()
s=bpy.data.scenes['Character_V2'];bpy.context.window.scene=s
s.render.filepath=str(ROOT/'wallpaper/assets/character-v2-review.png')
bpy.ops.render.render(write_still=True)
bpy.context.window.scene=bpy.data.scenes['Resort_Island']
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort-v2.blend'),compress=True)
result={'preview':s.render.filepath,'resized':resized,'rig_drivers':len(bpy.data.objects['RIG-Snow'].animation_data.drivers)}
