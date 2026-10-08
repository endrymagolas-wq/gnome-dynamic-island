"""Non-destructive visual grading of licensed assets and shoreline review."""
import bpy,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s

def grade(m,name,color,factor):
    n=m.node_tree.nodes;l=m.node_tree.links
    p=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    old=n.get(name)
    if old:return
    source=p.inputs['Base Color'].links[0].from_socket if p.inputs['Base Color'].links else None
    mix=n.new('ShaderNodeMixRGB');mix.name=name;mix.inputs[0].default_value=factor;mix.inputs[2].default_value=(*color,1)
    if source:l.new(source,mix.inputs[1])
    l.new(mix.outputs[0],p.inputs['Base Color'])

m=bpy.data.materials['V2 Nobiax textured palm'];n=m.node_tree.nodes;l=m.node_tree.links
p=next(x for x in n if x.type=='BSDF_PRINCIPLED');p.inputs['Roughness'].default_value=.82;p.inputs['Specular IOR Level'].default_value=.22
if not n.get('Resort foliage grade'):
    coord=n.new('ShaderNodeTexCoord');sep=n.new('ShaderNodeSeparateXYZ');l.new(coord.outputs['Generated'],sep.inputs[0])
    mask=n.new('ShaderNodeMath');mask.operation='GREATER_THAN';mask.inputs[1].default_value=.70;l.new(sep.outputs['Z'],mask.inputs[0])
    diffuse=next(x for x in n if x.type=='TEX_IMAGE' and x.image.colorspace_settings.name=='sRGB')
    hue=n.new('ShaderNodeMixRGB');hue.name='Resort foliage grade';hue.inputs[2].default_value=(.035,.19,.014,1)
    l.new(mask.outputs[0],hue.inputs[0]);l.new(diffuse.outputs['Color'],hue.inputs[1]);l.new(hue.outputs[0],p.inputs['Base Color'])
for m in bpy.data.materials:
    if m.name.startswith('boulder_01'):grade(m,'Resort warm limestone',(.52,.46,.34),.50)

# A compact submerged shelf fades into ocean depth, rather than a wide dark disc.
island=bpy.data.objects['Island sand and submerged shelf']
for vert in island.data.vertices:
    x,y=vert.co.x,vert.co.y;r=math.sqrt((x/5.5)**2+(y/4.3)**2)
    if r>.91:vert.co.z=.43-(r-.72)*2.35-((r-.91)*6)**2
island.data.update()
for m in bpy.data.materials:
    if m.name.startswith('snow.hair') and m.use_nodes:
        for p in m.node_tree.nodes:
            if p.type=='BSDF_PRINCIPLED':
                for link in list(p.inputs['Base Color'].links):m.node_tree.links.remove(link)
                p.inputs['Base Color'].default_value=(.10,.038,.014,1)
s.cycles.samples=48;s.render.resolution_percentage=50;s.render.film_transparent=False;s.frame_set(1)
s.render.filepath=str(ROOT/'wallpaper/assets/resort-v2-review.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort-v2.blend'))
bpy.ops.render.render(write_still=True)
result={'preview':s.render.filepath,'final':False}
