"""Reproducible sunny resort look; preserve the V3 coast and periodic water."""
import bpy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
s = bpy.data.scenes['Resort_Island']
bpy.context.window.scene = s

def tint(name, color, factor):
    m = bpy.data.materials[name]
    n, links = m.node_tree.nodes, m.node_tree.links
    p = next(x for x in n if x.type == 'BSDF_PRINCIPLED')
    node = n.get('V4 resort palette')
    if not node:
        node = n.new('ShaderNodeMixRGB'); node.name = 'V4 resort palette'
        if p.inputs['Base Color'].links:
            links.new(p.inputs['Base Color'].links[0].from_socket, node.inputs[1])
        else:
            node.inputs[1].default_value = p.inputs['Base Color'].default_value
        links.new(node.outputs[0], p.inputs['Base Color'])
    node.inputs[0].default_value = factor
    node.inputs[2].default_value = (*color, 1)

s.view_settings.exposure = .20
s.view_settings.look = 'AgX - Medium High Contrast'
bpy.data.objects['Resort sky fill'].data.energy = 440
bpy.data.objects['Resort sky fill'].data.color = (.77, .91, 1)
bpy.data.objects['Resort warm key'].data.energy = 550
water = bpy.data.materials['Lagoon water']
water.node_tree.nodes['Volume Absorption'].inputs['Color'].default_value = (.025, .82, .70, 1)
water.node_tree.nodes['Volume Absorption'].inputs['Density'].default_value = .34
tint('V3 deep lagoon sand', (.68, .78, .61), .85)
tint('V2 scanned coastal sand', (.92, .80, .52), .35)
foliage = bpy.data.materials['Resort Nobiax v3 leaf and bark'].node_tree.nodes
foliage['Mix (Legacy)'].inputs[2].default_value = (.085, .40, .025, 1)
tint('V2 painted turquoise wood', (.018, .68, .55), .45)
for name in [m.name for m in bpy.data.materials if m.name.startswith('V2 terracotta')]:
    tint(name, (.66, .18, .075), .55)

# Reuse the existing woven cushions, retaining their weave normal/roughness.
for index, o in enumerate(sorted((o for o in s.objects if o.name.startswith('V2 linen')), key=lambda o:o.name)):
    name = 'V4 coral linen' if index % 2 == 0 else 'V4 aqua linen'
    m = bpy.data.materials.get(name)
    if not m:
        m = bpy.data.materials['V2 cream linen'].copy(); m.name = name
    if o.data.materials:
        o.material_slots[0].link = 'OBJECT'; o.material_slots[0].material = m
    tint(name, (.82, .19, .11) if index % 2 == 0 else (.015, .52, .46), .76)
s.frame_set(1)
s.render.resolution_percentage = 50
s.cycles.samples = 48
s.render.film_transparent = False
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'art/island/resort-v4.blend'), compress=True)
print('Saved V4 palette source; V3 source and runtime preserved.')
