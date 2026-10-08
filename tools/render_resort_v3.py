"""Isolated offline render worker; invoked from Blender MCP, never wallpaper."""
import bpy,sys,time,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'wallpaper/assets'
mode=sys.argv[sys.argv.index('--')+1]
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
s.cycles.device='GPU';s.cycles.denoiser='OPTIX';s.render.use_persistent_data=True
if mode=='draft':
    s.render.resolution_percentage=25;s.cycles.samples=16
    folder=OUT/'v3-water-draft';folder.mkdir(exist_ok=True);start=time.monotonic()
    for frame in range(1,362):
        s.frame_set(frame);s.render.filepath=str(folder/f'{frame:04}.png');bpy.ops.render.render(write_still=True)
        (OUT/'v3-render-progress.json').write_text(json.dumps({'mode':mode,'frame':frame,'frames':361,'seconds':round(time.monotonic()-start,1)}))
elif mode=='sprites':
    path=ROOT/'art/island/snow_poses.py';scope={'__file__':str(path)}
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),scope)
    start=time.monotonic()
    for first in range(0,272,16):
        scope['bake_sprites'](first,min(first+15,271))
        (OUT/'v3-sprite-progress.json').write_text(json.dumps({'frame':first+16,'frames':272,'seconds':round(time.monotonic()-start,1)}))
    scope['save_actions']()
elif mode=='walk':
    path=ROOT/'art/island/snow_poses.py';scope={'__file__':str(path)}
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),scope)
    for first in range(0,128,16):
        scope['bake_sprites'](first,first+15)
        (OUT/'v3-walk-progress.json').write_text(json.dumps({'frame':first+16,'frames':128}))
    scope['save_actions']()
elif mode=='final':
    start=time.monotonic()
    def progress(stage,frame=0,total=0):
        (OUT/'v3-final-progress.json').write_text(json.dumps({'stage':stage,'frame':frame,'frames':total,'seconds':round(time.monotonic()-start,1)}))
    def load(name):
        path=ROOT/'art/island'/name;scope={'__file__':str(path)}
        exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),scope);return scope
    progress('static');layers=load('bake_v3_layers.py');layers['static_layers']();layers['depth_layer']()
    poses=load('snow_poses.py')
    for first in range(0,272,16):
        poses['bake_sprites'](first,min(first+15,271));progress('sprites',first+16,272)
    poses['save_actions']();progress('construction');load('bake_construction.py');load('bake_construction_depth.py')
    progress('smoke');load('bake_smoke.py')
    s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
    s.cycles.samples=64;s.cycles.device='GPU';s.render.resolution_percentage=100
    s.render.use_persistent_data=True;s.render.film_transparent=False
    folder=OUT/'v3-water-final';folder.mkdir(exist_ok=True)
    for frame in range(1,362):
        s.frame_set(frame);s.render.filepath=str(folder/f'{frame:04}.png');bpy.ops.render.render(write_still=True);progress('water',frame,361)
    s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort-v2.blend'),compress=True)
    progress('complete',361,361)
else:raise ValueError(mode)
