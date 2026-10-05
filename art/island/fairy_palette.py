"""V6 art-direction experiment: painted resort surfaces and a luminous lagoon.

Run only in the isolated V6 source through Blender MCP.
"""
import bpy,math
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
assert bpy.data.filepath.endswith('resort-v6.blend')
def paint(name,color,roughness=.62):
    m=bpy.data.materials.get(name)
    if not m:return
    nt=m.node_tree;p=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    for l in list(nt.links):
        if l.to_node==p and l.to_socket.name in ('Base Color','Roughness','Normal'):nt.links.remove(l)
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=roughness
    return nt,p

paint('V2 scanned coastal sand',(.82,.59,.29),.85)
paint('V3 deep lagoon sand',(.015,.55,.70),.8)
paint('Deep aquamarine seabed',(.012,.38,.60),.8)
paint('V2 scanned white stucco',(.94,.76,.53),.7)
paint('Warm ivory plaster',(.94,.80,.58),.7)
paint('V2 scanned teak deck',(.44,.16,.055),.48)
paint('V2 oiled teak',(.52,.22,.065),.5)
paint('Honey teak',(.60,.30,.095),.5)
paint('wooden_table_02',(.55,.25,.08),.52)
paint('V2 painted turquoise wood',(.025,.65,.58),.4)
paint('Lagoon shutters',(.025,.65,.58),.4)
paint('boulder_01',(.49,.40,.56),.8)
paint('Warm limestone',(.64,.54,.68),.8)
paint('V2 weathered coastal limestone',(.56,.46,.63),.8)
paint('V2 coconut bark',(.36,.14,.055),.7)
paint('V2 clay planter',(.78,.25,.17),.6)
for i in range(6):paint('V2 terracotta '+str(i),(.73+.025*i,.17+.018*i,.10+.02*i),.58)
paint('Coral roof',(.85,.25,.16),.58)
paint('Palm emerald',(.06,.50,.13),.6)
paint('V2 palm foliage',(.08,.59,.16),.6)

# Retain the original leaf alpha and trunk/foliage classification, replacing
# photographic color and normal detail with a clean painted gradient.
nt,p=paint('Resort Nobiax v3 leaf and bark',(.08,.53,.10),.62)
mix=nt.nodes.get('Mix (Legacy)')
for link in list(nt.links):
    if link.to_node==mix and link.to_socket.name in ('Color1','Color2'):nt.links.remove(link)
mix.blend_type='MIX';mix.inputs['Color1'].default_value=(.27,.115,.04,1)
mix.inputs['Color2'].default_value=(.07,.55,.12,1)
nt.links.new(mix.outputs['Color'],p.inputs['Base Color'])
nt.links.new(nt.nodes['Math'].outputs[0],mix.inputs[0])
mix.inputs['Color1'].default_value=(.25,.095,.025,1)
mix.inputs['Color2'].default_value=(.035,.42,.11,1)
p.inputs['Specular IOR Level'].default_value=.15
p.inputs['Roughness'].default_value=.8
p.inputs['Subsurface Weight'].default_value=.05

w=bpy.data.materials['Lagoon water'].node_tree
p=next(n for n in w.nodes if n.type=='BSDF_PRINCIPLED')
p.inputs['Base Color'].default_value=(.045,.64,.64,1)
p.inputs['Transmission Weight'].default_value=.82
p.inputs['Roughness'].default_value=.075
w.nodes['Volume Absorption'].inputs['Color'].default_value=(.008,.90,.98,1)
w.nodes['Volume Absorption'].inputs['Density'].default_value=.28
w.nodes['Bump'].inputs['Strength'].default_value=.16
w.nodes['Bump'].inputs['Distance'].default_value=.045

# Broader, softer illumination and a blue/lilac shadow fill.
bpy.data.objects['Resort sunlight'].data.energy=1.7
bpy.data.objects['Resort sunlight'].data.angle=math.radians(9)
bpy.data.objects['Resort sunlight'].data.color=(1,.88,.70)
bpy.data.objects['Resort warm key'].data.energy=650
bpy.data.objects['Resort warm key'].data.size=9
bpy.data.objects['Resort sky fill'].data.energy=950
bpy.data.objects['Resort sky fill'].data.color=(.61,.72,1)
nt=s.world.node_tree;sky=nt.nodes['Sky Texture'];background=nt.nodes['Background']
tint=nt.nodes.get('Fairy blue sky tint') or nt.nodes.new('ShaderNodeMixRGB')
tint.name='Fairy blue sky tint';tint.inputs[0].default_value=.60
tint.inputs[2].default_value=(.08,.40,.60,1)
nt.links.new(sky.outputs[0],tint.inputs[1]);nt.links.new(tint.outputs[0],background.inputs[0])
background.inputs['Strength'].default_value=.12
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
s.view_settings.exposure=.10

# Keep every dry-land vertex unchanged so existing grounded routes remain valid.
# The original 21m drop made a dark visible wall below the transparent lagoon.
terrain=s.objects['Island sand and submerged shelf']
if not terrain.get('fairy_slope_v6'):
    terrain.data=terrain.data.copy()
    for v in terrain.data.vertices:
        if v.co.z<-.1:v.co.z=-.1+(v.co.z+.1)*.25
    terrain['fairy_slope_v6']=True
nt,p=paint('V2 scanned coastal sand',(.72,.48,.20),.85)
def node(kind,name):
    n=nt.nodes.get(name) or nt.nodes.new(kind);n.name=name;return n
geo=node('ShaderNodeNewGeometry','Fairy sand position')
xyz=node('ShaderNodeSeparateXYZ','Fairy sand height')
band=node('ShaderNodeMapRange','Fairy lagoon transition')
band.inputs['From Min'].default_value=-.7;band.inputs['From Max'].default_value=.22
gradient=node('ShaderNodeMixRGB','Fairy sand palette')
gradient.inputs[1].default_value=(.015,.55,.70,1)
gradient.inputs[2].default_value=(.72,.48,.20,1)
nt.links.new(geo.outputs['Position'],xyz.inputs[0]);nt.links.new(xyz.outputs['Z'],band.inputs[0])
nt.links.new(band.outputs[0],gradient.inputs[0]);nt.links.new(gradient.outputs[0],p.inputs['Base Color'])
paint('Deep aquamarine seabed',(.008,.50,.60),.8)
for o in s.objects:
    if o.type=='MESH' and bpy.data.materials.get('boulder_01') in list(o.data.materials):
        if not o.modifiers.get('Fairy broad rock forms'):
            o.modifiers.new('Fairy broad rock forms','DECIMATE').ratio=.12
            smooth=o.modifiers.new('Fairy soft rock edges','SMOOTH');smooth.factor=.7;smooth.iterations=4
        for polygon in o.data.polygons:polygon.use_smooth=True
result={'source':bpy.data.filepath,'palette':'painted coral / mint / lavender / bright cyan lagoon'}
