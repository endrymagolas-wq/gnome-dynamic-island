"""Offline V4 worker with isolated outputs; never started by the wallpaper."""
import bpy, json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'wallpaper/assets/v4-stage'
OUT.mkdir(exist_ok=True)
os.environ['RESORT_RENDER_OUT'] = str(OUT)
mode = sys.argv[sys.argv.index('--') + 1]
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
for device in prefs.devices: device.use = device.type == 'OPTIX'
s = bpy.data.scenes['Resort_Island']; bpy.context.window.scene = s
s.cycles.device = 'GPU'; s.cycles.denoiser = 'OPTIX'
s.render.use_persistent_data = True
start = time.monotonic()
def progress(stage, frame=0, total=0):
    (OUT / (mode + '-progress.json')).write_text(json.dumps({
        'stage': stage, 'frame': frame, 'frames': total,
        'seconds': round(time.monotonic() - start, 1), 'source': bpy.data.filepath,
    }))
def load(name):
    path = ROOT / 'art/island' / name
    scope = {'__file__': str(path)}
    exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), scope)
    return scope
if mode in ('draft', 'water'):
    s.render.resolution_percentage = 25 if mode == 'draft' else 100
    s.cycles.samples = 16 if mode == 'draft' else 64
    s.render.film_transparent = False
    folder = OUT / ('water-draft' if mode == 'draft' else 'water-final')
    folder.mkdir(exist_ok=True)
    for frame in range(1, 362):
        s.frame_set(frame); s.render.filepath = str(folder / f'{frame:04}.png')
        bpy.ops.render.render(write_still=True); progress(mode, frame, 361)
    progress('complete', 361, 361)
elif mode == 'sprites':
    poses = load('pip_poses.py')
    for first in range(0,272,16):
        poses['bake_sprites'](first,min(first+15,271)); progress('sprites',first+16,272)
    poses['save_actions'](); progress('complete',272,272)
elif mode == 'layers':
    progress('static'); layers = load('bake_v3_layers.py')
    layers['static_layers'](); layers['depth_layer']()
    progress('construction'); load('bake_construction.py'); load('bake_construction_depth.py')
    progress('smoke'); load('bake_smoke.py')
    bpy.context.window.scene = bpy.data.scenes['Resort_Island']
    s.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'art/island/resort-v4.blend'), compress=True)
    progress('complete')
elif mode == 'mascot-review':
    from mathutils import Vector
    poses=load('pip_poses.py');poses['setup']();poses['pose']('permission',.8)
    mascot=poses['s'];rig=poses['r'];rig.scale=(poses['SCALE'],)*3
    camera=mascot.camera;camera.location=(2,-5,2.5)
    camera.rotation_euler=(Vector((0,0,.73))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=1.85;mascot.cycles.device='GPU'
    mascot.render.resolution_x=512;mascot.render.resolution_y=640
    mascot.render.filepath=str(ROOT/'wallpaper/assets/pip-v4-review.png')
    bpy.ops.render.render(write_still=True);progress('complete')
else:
    raise ValueError(mode)
