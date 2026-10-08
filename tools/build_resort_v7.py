"""Give the three resort residents usable places, without changing V6 coast/camera.

Run with Blender 4.5: --background --python tools/build_resort_v7.py -- OUTPUT_DIR.
The protected V6 file is read only. This script refuses to overwrite its V7 copy.
Furniture is ordinary editable mesh/curve geometry; the wallpaper still uses
offline image layers, not a live Blender or WebGL scene.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = Path(args[0]).resolve() if args else ROOT.parents[1] / 'outputs/resort-v7/layout'
SOURCE = ROOT / 'art/island/resort-v6.blend'
DEST = OUT / 'resort-v7.blend'
assert SOURCE.exists(), SOURCE
assert not DEST.exists(), f'Preserve the existing editable scene: {DEST}'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s = bpy.data.scenes['Resort_Island']
bpy.context.window.scene = s
meta = json.loads((ROOT / 'wallpaper/assets/scene.json').read_text(encoding='utf-8'))
camera_before = [list(row) for row in s.camera.matrix_world]
terrain_before = [tuple(v.co) for v in s.objects['Island sand and submerged shelf'].data.vertices]

collection = bpy.data.collections.new('V7 resident lounge and tea terrace')
s.collection.children.link(collection)
groups = {}


def ground(x, y):
    g = meta['ground']
    r = math.hypot(x/g['ellipse'][0], y/g['ellipse'][1])
    if g.get('coastPerturb') and r > g['plateauRadius']:
        a = math.atan2(y/g['ellipse'][1], x/g['ellipse'][0])
        dr = g['coastPerturb'][0]*math.sin(3*a)+g['coastPerturb'][1]*math.cos(5*a+g['coastPerturb'][2])
        band = .18
        r = r-dr if r >= g['plateauRadius']+band+dr else (r+dr*g['plateauRadius']/band)/(1+dr/band)
    return g['height']-max(0, r-g['plateauRadius'])*g['slope']


def material(name, color, roughness=.68):
    m = bpy.data.materials.new('V7 '+name)
    m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Specular IOR Level'].default_value = .25
    return m


teak = bpy.data.materials['V2 scanned teak deck']
warm_teak = bpy.data.materials['V2 oiled teak']
cream = material('warm woven cream', (.89, .73, .48), .86)
mint = material('lagoon linen', (.055, .57, .46), .84)
lilac = material('soft lilac linen', (.51, .37, .67), .86)
coral = material('soft coral linen', (.85, .31, .18), .86)
ceramic = material('mint tea glaze', (.055, .63, .51), .24)
ivory = material('ivory tea glaze', (.91, .77, .53), .28)
tea_color = material('warm amber tea', (.30, .10, .025), .2)
brass = material('warm satin brass', (.65, .38, .11), .35)


def own(o, name, group=None):
    o.name = 'V7 '+name
    for c in list(o.users_collection):
        c.objects.unlink(o)
    collection.objects.link(o)
    o['resort_v7_owner'] = 'resident-lounge'
    if group:
        groups.setdefault(group, []).append(o)
    return o


def cube(name, location, size, mat, bevel=.035, group=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    o = own(bpy.context.object, name, group)
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    if bevel:
        b = o.modifiers.new('Soft crafted edge', 'BEVEL')
        b.width = bevel
        b.segments = 4
        o.modifiers.new('Broad face normals', 'WEIGHTED_NORMAL')
    return o


def sphere(name, location, size, mat, group=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=location)
    o = own(bpy.context.object, name, group)
    o.scale = size
    o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def cylinder(name, location, radius, depth, mat, group=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth, location=location)
    o = own(bpy.context.object, name, group)
    o.data.materials.append(mat)
    b = o.modifiers.new('Rounded rim', 'BEVEL')
    b.width = .015
    b.segments = 3
    o.modifiers.new('Smooth normals', 'WEIGHTED_NORMAL')
    return o


def curve(name, points, radius, mat, group=None):
    d = bpy.data.curves.new('V7 '+name, 'CURVE')
    d.dimensions = '3D'
    d.resolution_u = 12
    d.bevel_depth = radius
    d.bevel_resolution = 4
    spline = d.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for b, p in zip(spline.bezier_points, points):
        b.co = p
        b.handle_left_type = b.handle_right_type = 'AUTO'
    o = bpy.data.objects.new('V7 '+name, d)
    collection.objects.link(o)
    o['resort_v7_owner'] = 'resident-lounge'
    d.materials.append(mat)
    if group:
        groups.setdefault(group, []).append(o)
    return o


def leg(name, x, y, top, width, group):
    foot = ground(x, y)-.006
    assert top > foot+.12
    return cube(name, (x, y, (top+foot)/2), (width, width, top-foot), teak, .023, group)


hidden = []
for o in s.objects:
    if o.name.startswith(('Coffee ', 'Laptop ', 'V2 linen seat cushion', 'V2 linen back cushion')):
        o.hide_render = True
        o.hide_set(True)
        o['v7_replaced_retained'] = True
        hidden.append(o.name)

# Clear the left lounge footprint. Retain the same scanned rocks along the
# outer beach rather than deleting them or changing the terrain/water loop.
relocated = []
for name, x, y in [('V2 scanned boulder 0', -4.42, -1.15),
                   ('V2 scanned boulder 1', -4.15, -2.02),
                   ('V2 scanned boulder 5', -4.10, -2.58)]:
    o = s.objects.get(name)
    if o:
        before = list(o.location)
        old_ground = ground(o.location.x, o.location.y)
        o.location.x, o.location.y = x, y
        o.location.z += ground(x, y)-old_ground
        relocated.append({'name': name, 'before': before, 'after': list(o.location)})

# Keep the superseded table in the editable file, while three slim cabin
# work consoles give each app an actual surface without blocking the daybed.
table = s.objects.get('V3 scanned work table')
if table:
    table.hide_render = True
    table.hide_set(True)
    table['v7_replaced_retained'] = True
    hidden.append(table.name)


SEAT_Y = -1.82
CUSHION_TOP = .97
seats = {}
for key, x, color in [('claude', -1.42, cream), ('codex', 0, mint), ('apps', 1.42, lilac)]:
    group = 'seat-'+key
    # Seat width 1.10m, overall width 1.28m; every resident has its own place.
    cube(group+' base', (x, SEAT_Y, .805), (1.20, .64, .12), teak, .035, group)
    cube(group+' seat cushion', (x, SEAT_Y-.045, .905), (1.10, .52, .13), color, .064, group)
    cube(group+' back frame', (x, SEAT_Y+.265, 1.08), (1.20, .10, .58), teak, .04, group)
    back = cube(group+' back cushion', (x, SEAT_Y+.225, 1.18), (1.10, .14, .39), color, .065, group)
    back.rotation_euler[0] = -.08
    for dx in [-.565, .565]:
        cube(group+' arm', (x+dx, SEAT_Y, 1.09), (.15, .56, .13), warm_teak, .055, group)
        leg(group+' front leg', x+dx*.82, SEAT_Y-.255, .815, .10, group)
        leg(group+' back leg', x+dx*.82, SEAT_Y+.255, .815, .10, group)
    seats[key] = {'id': group, 'position': [x, SEAT_Y-.045, CUSHION_TOP],
                  'approach': [x, -2.70, ground(x, -2.70)], 'heading': 0,
                  'surfaceHeight': CUSHION_TOP, 'rootOffset': .31,
                  'transitionSeconds': 1.05, 'hopHeight': .12, 'usableWidth': 1.10}

# Shelves attach to the front of the existing porch, rather than filling the
# walking lane with free-standing desk legs. Laptops use real editable meshes.
screen_mat = material('quiet laptop screen', (.018, .13, .15), .32)
screen_shader = next(n for n in screen_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
screen_shader.inputs['Emission Color'].default_value = (.015, .28, .25, 1)
screen_shader.inputs['Emission Strength'].default_value = .25
for key, x in [('claude', -1.20), ('codex', 0), ('apps', 1.20)]:
    group = 'work-'+key
    cube(group+' porch shelf', (x, -.61, 1.065), (.80, .20, .08), warm_teak, .025, group)
    for dx in [-.25, .25]:
        cube(group+' shelf bracket', (x+dx, -.545, .925), (.055, .12, .25), teak, .012, group)
    cube(group+' laptop base', (x, -.61, 1.114), (.43, .165, .018), brass, .007, group)
    cube(group+' laptop lid', (x, -.542, 1.252), (.43, .028, .26), teak, .014, group)
    cube(group+' laptop screen', (x, -.56, 1.252), (.378, .008, .207), screen_mat, .006, group)
    for row in range(3):
        for col in range(7):
            cube(group+' laptop key', (x-.14+col*.046, -.652+row*.026, 1.126),
                 (.029, .019, .004), ceramic, .002, group)

# A daybed long enough for the full-size blue demon, with a modest low frame.
# The feet anchor is at the south end; the lying clip points its head north.
bx, by = -2.95, -1.42
BED_TOP = .84
group = 'daybed'
cube('daybed teak frame', (bx, by, .685), (1.51, 1.98, .12), teak, .055, group)
cube('daybed deep mattress', (bx, by, .775), (1.45, 1.94, .13), cream, .07, group)
for dx in [-.61, .61]:
    for dy in [-.81, .81]:
        leg('daybed leg', bx+dx, by+dy, .70, .105, group)
cube('daybed head rail', (bx, by+.91, .925), (1.51, .10, .49), teak, .045, group)
cube('daybed mint pillow', (bx, by+.68, .902), (1.26, .36, .124), mint, .06, group)
cube('daybed folded coral throw', (bx, by-.65, .858), (1.32, .30, .035), coral, .014, group)
bed = {'id': 'daybed', 'position': [bx, -2.23, BED_TOP],
       'approach': [bx, -2.77, ground(bx, -2.77)], 'heading': 0,
       'surfaceHeight': BED_TOP, 'rootOffset': -.4491118, 'seconds': 14,
       'transitionSeconds': 1.35, 'usableLength': 1.94, 'usableWidth': 1.45,
       'anchor': 'feet at south end; head points +Y', 'rootOffsetStatus': 'measured deformed lie mesh back contact'}

# Compact tea station, with kettle, pot, a serving tray, and three proper cups.
# Counter behind the actor: hand-held pouring is rendered in the activity clip.
tx, ty, TEA_TOP = 3.36, -1.40, 1.105
group = 'tea-station'
cube('tea counter', (tx, ty, TEA_TOP-.0475), (1.16, .66, .095), warm_teak, .045, group)
for dx in [-.45, .45]:
    for dy in [-.22, .22]:
        leg('tea bar leg', tx+dx, ty+dy, TEA_TOP-.05, .10, group)
cube('tea lower shelf', (tx, ty, .58), (1.03, .49, .07), teak, .025, group)
cube('tea linen runner', (tx-.13, ty, TEA_TOP+.012), (.72, .57, .024), cream, .014, group)
cube('tea rounded serving tray', (tx-.18, ty+.03, TEA_TOP+.045), (.70, .46, .055), teak, .065, group)

px, py, pz = tx+.28, ty+.06, TEA_TOP
sphere('tea mint pot body', (px, py, pz+.16), (.17, .145, .155), ceramic, group)
cylinder('tea pot lid', (px, py, pz+.302), .126, .03, ceramic, group)
sphere('tea pot lid knob', (px, py, pz+.337), (.035, .035, .032), brass, group)
curve('tea pot spout', [(px+.10, py-.035, pz+.11), (px+.20, py-.045, pz+.13),
                       (px+.25, py-.055, pz+.255)], .032, ceramic, group)
curve('tea pot handle', [(px-.12, py, pz+.255), (px-.25, py, pz+.24),
                        (px-.25, py, pz+.095), (px-.12, py, pz+.08)], .025, ceramic, group)
for i, cup_mat in enumerate([ivory, mint, lilac]):
    cx, cy, z = tx-.43+i*.19, ty-.06, TEA_TOP+.075
    cylinder(f'tea cup {i+1} saucer', (cx, cy, z), .081, .022, cup_mat, group)
    cylinder(f'tea cup {i+1}', (cx, cy, z+.062), .061, .106, cup_mat, group)
    cylinder(f'tea cup {i+1} amber surface', (cx, cy, z+.114), .049, .005, tea_color, group)
    curve(f'tea cup {i+1} handle', [(cx+.056, cy, z+.092), (cx+.097, cy, z+.08),
                                 (cx+.095, cy, z+.043), (cx+.056, cy, z+.034)], .009, cup_mat, group)
cube('tea folded towel', (tx+.29, ty, .637), (.35, .31, .08), lilac, .035, group)
tea = {'id': 'tea-station', 'position': [tx, -2.10, ground(tx, -2.10)],
       'approach': [tx, -2.10, ground(tx, -2.10)], 'heading': 0,
       'seconds': 10, 'counterHeight': TEA_TOP}

bpy.context.view_layer.update()


def bounds(objects):
    points = [o.matrix_world @ Vector(p) for o in objects for p in o.bound_box]
    return [min(p.x for p in points), min(p.y for p in points),
            max(p.x for p in points), max(p.y for p in points)]


obstacles = [{'name': 'terrace', 'bounds': bounds([s.objects['Terrace']])}]
for group_name, objects in groups.items():
    obstacles.append({'name': group_name, 'bounds': bounds(objects)})


def point(x, y):
    return [x, y, ground(x, y)]


targets = {}
for key, x, desk in [('claude', -1.42, (-1.20, -1.10)),
                     ('codex', 0, (0, -1.10)), ('apps', 1.42, (1.20, -1.10))]:
    targets[key] = {'desk': point(*desk), 'testing': point(x, -2.78),
                    'failed': point(x, -2.78), 'permission': point(x, -3.00),
                    'browsing': point(*desk),
                    'idle': seats[key]['position'], 'done': seats[key]['position']}
    for state in ['starting', 'editing', 'working']:
        targets[key][state] = targets[key]['desk']

patch = {
    'version': 7,
    'source': 'art/island/resort-v7.blend',
    'navigation': {'clearance': .30, 'obstacles': obstacles},
    'activities': {'seats': seats, 'bed': bed, 'tea': tea, 'targets': targets,
                   'minimumGroundHeight': .1, 'initialIdleSeconds': 10,
                   'transitionSeconds': 1.05, 'seatSeconds': 12,
                   'groundNote': 'Terrain unchanged from V6. Chair/daybed surfaces use surfaceHeight and measured rootOffset; walkers follow original analytical sand height.'},
    'targets': targets['claude'],
    'seating': {'states': ['idle', 'done'], 'position': [-1.42, SEAT_Y-.045, CUSHION_TOP-.31],
                'approach': seats['claude']['approach'], 'seconds': 1.05, 'hopHeight': .12,
                'cushionTop': CUSHION_TOP},
}
meta.update(patch)
s['resort_version'] = 7
s['resort_v7_layout'] = 'Three assigned armchairs, one shared daybed and one shared tea station'
s.frame_set(1)
s.render.engine = 'CYCLES'  # Root chooses EEVEE for previews; retained source engine is explicit.
assert camera_before == [list(row) for row in s.camera.matrix_world], 'Camera moved'
assert terrain_before == [tuple(v.co) for v in s.objects['Island sand and submerged shelf'].data.vertices], 'Terrain changed'
bpy.ops.wm.save_as_mainfile(filepath=str(DEST), compress=True)
(OUT / 'scene.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
(OUT / 'scene-patch.json').write_text(json.dumps(patch, indent=2), encoding='utf-8')
(OUT / 'layout-audit.json').write_text(json.dumps({
    'source': str(SOURCE), 'editableCopy': str(DEST), 'cameraUnchanged': True,
    'terrainUnchanged': True, 'createdObjects': len(collection.objects),
    'retainedHiddenObjects': hidden, 'relocatedObjects': relocated,
    'obstacles': obstacles, 'activityApproachGround': {
        **{key: value['approach'][2] for key, value in seats.items()},
        'bed': bed['approach'][2], 'tea': tea['approach'][2]},
    'activityContactOffsets': {'sit': .31, 'lie': -.4491118},
}, indent=2), encoding='utf-8')
print('V7 editable resort saved:', DEST)
print('V7 geometry objects:', len(collection.objects))
print('V7 layout metadata:', OUT / 'scene.json')
