"""Adapt Quaternius' CC0 BlueDemon mesh and rig to the Pip turnaround.

Keep the authored topology, skin weights, fingers, IK and animation library.
Round the silhouette, remove the baseball bat, and add friendly facial details.
"""
import bpy, bmesh, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
s = bpy.data.scenes['Mascot_Pip']; bpy.context.window.scene = s
r = bpy.data.objects['CharacterArmature']; o = bpy.data.objects['BlueDemon']
r.animation_data.action = None
for bone in r.pose.bones: bone.matrix_basis.identity()
s.frame_set(1); bpy.context.view_layer.update()

def material(name, color, roughness=.55):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = roughness
    return m
white = material('Pip warm eye white', (.91, .96, .89), .23)
dark = material('Pip glossy chocolate eyes', (.018, .012, .009), .30)
dark.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value = .08
dark.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = .25
smile = material('Pip gentle smile', (.035, .15, .12), .65)
coral = material('Pip coral freckles', (.86, .31, .17), .65)
yellow = material('Pip sunny swim shorts', (.98, .58, .055), .82)

if not o.get('pip_adapted'):
    # Connected components distinguish the authored bat from the hands.
    parent = list(range(len(o.data.vertices)))
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for edge in o.data.edges:
        a, b = edge.vertices; parent[find(a)] = find(b)
    groups = {}
    for v in o.data.vertices: groups.setdefault(find(v.index), []).append(v)
    eye_ids = set()
    for vs in groups.values():
        if len(vs) == 186: eye_ids.update(v.index for v in vs)
    o.data.materials.append(white); white_index = len(o.data.materials) - 1
    o.data.materials.append(yellow); yellow_index = len(o.data.materials) - 1
    for face in o.data.polygons:
        if all(i in eye_ids for i in face.vertices): face.material_index = white_index
        elif .60 < face.center.z * .54 < 1.08 and abs(face.center.x * .54) < .72:
            face.material_index = yellow_index
    remove = set()
    for vs in groups.values():
        if len(vs) in (210, 194, 25): remove.update(v.index for v in vs)
    for v in o.data.vertices:
        z = v.co.z * .54
        if z > 1.95:
            # Broader cheeks and softly lowered ear tips, rather than horns.
            v.co.x *= 1.18
            v.co.y *= 1.10
            if z > 2.55: v.co.z = (2.55 + (z - 2.55) * .50) / .54
            if v.index in eye_ids:
                sign = 1 if v.co.x > 0 else -1
                center = Vector((sign*.339*1.18, -.389*1.1, 2.282)) / .54
                v.co = center + (v.co - center) * 1.28
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in remove], context='VERTS')
    bm.to_mesh(o.data); bm.free(); o.data.update()
    for face in o.data.polygons: face.use_smooth = True
    for mod in list(o.modifiers):
        if mod.type == 'NODES': o.modifiers.remove(mod)
    sub = o.modifiers.new('Pip rounded silhouette', 'SUBSURF')
    sub.levels = 2; sub.render_levels = 2
    o['pip_adapted'] = True

# Upgrading an already reviewed adaptation also removes the original loincloth.
if not o.get('pip_clean_shorts'):
    bm=bmesh.new(); bm.from_mesh(o.data); seen=set(); discard=[]
    for seed in bm.verts:
        if seed in seen: continue
        part=[]; stack=[seed]; seen.add(seed)
        while stack:
            v=stack.pop(); part.append(v)
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other not in seen: seen.add(other); stack.append(other)
        if len(part)==25 and max(v.co.z*.54 for v in part)<1:
            discard.extend(part)
    if discard: bmesh.ops.delete(bm,geom=discard,context='VERTS')
    bm.to_mesh(o.data); bm.free(); o['pip_clean_shorts']=True

m = bpy.data.materials['Atlas']; n = m.node_tree.nodes; links = m.node_tree.links
p = n['Principled BSDF']; p.inputs['Roughness'].default_value = .52
p.inputs['Subsurface Weight'].default_value = .08
color = n.get('Pip tropical color') or n.new('ShaderNodeMixRGB')
color.name = 'Pip tropical color'; color.blend_type = 'MULTIPLY'; color.use_clamp = True
color.inputs[0].default_value = 1; color.inputs[2].default_value = (1.05, 1.75, 1.40, 1)
links.new(n['Image Texture'].outputs['Color'], color.inputs[1]); links.new(color.outputs[0], p.inputs['Base Color'])

def head_parent(obj):
    # Preserve a world-space placement while attaching to the existing Head.
    bpy.context.view_layer.update(); matrix = obj.matrix_world.copy()
    obj.parent = r; obj.parent_type = 'BONE'; obj.parent_bone = 'Head'
    bpy.context.view_layer.update(); obj.matrix_world = matrix

for side in (-1, 1):
    name = 'Pip pupil ' + str(side)
    if not bpy.data.objects.get(name):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16,
            radius=1, location=(side*.400, -.665, 2.29))
        eye = bpy.context.object; eye.name = name; eye.scale = (.145, .06, .17)
        eye.data.materials.append(dark)
        for face in eye.data.polygons: face.use_smooth = True
        head_parent(eye)

# Fold the outer ear tips into a floppy silhouette, leaving the weighted head.
if not o.get('pip_floppy_ears'):
    for v in o.data.vertices:
        x, z = abs(v.co.x*.54), v.co.z*.54
        if z>2.48 and x>.70:
            v.co.z -= (.30*min(1,(x-.70)/.55))/.54
    o.data.update(); o['pip_floppy_ears']=True

# Ray cast the existing head surface for the small smile and cheek dots.
bpy.context.view_layer.update()
tree = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
def surface(x, z):
    hit, _, _, _ = tree.ray_cast(Vector((x/.54, -3/.54, z/.54)), Vector((0,1,0)))
    return (hit.y*.54-.013) if hit else -.63
if not bpy.data.objects.get('Pip gentle smile curve'):
    curve = bpy.data.curves.new('Pip gentle smile curve', 'CURVE')
    curve.dimensions = '3D'; curve.bevel_depth = .016; curve.bevel_resolution = 3
    path = curve.splines.new('POLY'); path.points.add(24)
    for i, point in enumerate(path.points):
        x = -.28 + i / 24 * .56; z = 2.005 + .13 * (x/.28)**2
        point.co = (x, surface(x,z), z, 1)
    obj = bpy.data.objects.new('Pip gentle smile curve', curve)
    s.collection.objects.link(obj); curve.materials.append(smile); head_parent(obj)
for side in (-1,1):
    for i,(x,z) in enumerate(((.53,2.16),(.59,2.20),(.57,2.10))):
        name = f'Pip cheek {side} {i}'
        if not bpy.data.objects.get(name):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8,
                radius=.024, location=(side*x,surface(side*x,z)-.009,z))
            dot = bpy.context.object; dot.name = name; dot.scale.y = .25
            dot.data.materials.append(coral); head_parent(dot)
if not bpy.data.objects.get('Pip button nose'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16,
        radius=1, location=(0,surface(0,2.20)-.045,2.20))
    nose=bpy.context.object; nose.name='Pip button nose'; nose.scale=(.115,.070,.072)
    nose.data.materials.append(material('Pip mint nose',(.15,.60,.48),.5))
    for face in nose.data.polygons: face.use_smooth=True
    head_parent(nose)
s.camera.data.ortho_scale = 3.25
s.render.filepath = str(ROOT/'wallpaper/assets/pip-v4-review.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort-v4.blend'), compress=True)
print('Pip: authored full-body rig retained; bat removed; friendly face added.')
