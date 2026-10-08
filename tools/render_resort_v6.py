"""Offline V6 worker. Isolated layers; never launched by the wallpaper."""
import bpy,json,os,sys,time,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:];mode=args[0];phase=args[1] if len(args)>1 else 'day'
STAGE=ROOT/'wallpaper/assets/v6-stage'
OUT=STAGE if phase=='day' else STAGE/'phases'/phase;OUT.mkdir(parents=True,exist_ok=True)
os.environ['RESORT_RENDER_OUT']=str(OUT)
assert Path(bpy.data.filepath).name=='resort-v6.blend'
SOURCE=Path(bpy.data.filepath).resolve()
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
s.cycles.device='GPU';s.cycles.denoiser='OPTIX';s.render.use_persistent_data=True
start=time.monotonic()
def progress(stage,frame=0,total=0):
    (OUT/(mode+'-progress.json')).write_text(json.dumps({'stage':stage,'frame':frame,'frames':total,'seconds':round(time.monotonic()-start,1),'source':bpy.data.filepath}))
def load(name):
    p=ROOT/'art/island'/name;scope={'__file__':str(p)}
    exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),scope);return scope
load('resort_time_of_day.py')['apply'](phase)
if mode in ('draft','water'):
    s.render.resolution_percentage=25 if mode=='draft' else 100
    s.cycles.samples=16 if mode=='draft' else 48
    s.render.film_transparent=False
    folder=OUT/('water-draft' if mode=='draft' else 'water-final');folder.mkdir(exist_ok=True)
    for frame in range(1,362):
        s.frame_set(frame);s.render.filepath=str(folder/f'{frame:04}.png')
        bpy.ops.render.render(write_still=True);progress(mode,frame,361)
    progress('complete',361,361)
elif mode=='sprites':
    shutil.copyfile(ROOT/'wallpaper/assets/scene.json',OUT/'scene-v2.json')
    poses=load('pip_v6_poses.py');poses['setup']();poses['s'].cycles.device='GPU'
    # Match the current resort light colors/intensities, retaining local actor lights.
    for lamp in poses['s'].objects:
        if lamp.type=='LIGHT':
            original=next((o for o in s.objects if o.type=='LIGHT' and lamp.name.startswith(o.name)),None)
            if original:lamp.data.energy=original.data.energy;lamp.data.color=original.data.color;lamp.rotation_euler=original.rotation_euler
    for first in range(0,304,16):
        poses['bake_sprites'](first,min(first+15,303));progress('sprites',first+16,304)
    p=ROOT/'tools/configure_resort_v6.py';exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__file__':str(p)})
    if phase=='day':poses['save_actions'](SOURCE);load('bake_pip_depth.py')
    load('bake_pip_ambient.py')
    if phase=='day':
        os.environ['RESORT_AMBIENT_DEPTH']='1';load('bake_pip_ambient.py');os.environ.pop('RESORT_AMBIENT_DEPTH')
    progress('complete',304,304)
elif mode=='ambient':
    load('bake_pip_ambient.py')
    os.environ['RESORT_AMBIENT_DEPTH']='1';load('bake_pip_ambient.py');os.environ.pop('RESORT_AMBIENT_DEPTH')
    progress('complete',288,288)
elif mode=='ambient-actions':
    os.environ['RESORT_AMBIENT_ACTIONS']='1';load('bake_pip_ambient.py');os.environ.pop('RESORT_AMBIENT_ACTIONS')
    progress('complete',288,288)
elif mode=='layers':
    assert (OUT/'scene-v2.json').exists(),'Bake sprites before layers'
    progress('static');layers=load('bake_v3_layers.py');layers['static_layers']()
    s.render.use_compositing=False;layers['depth_layer']();s.render.use_compositing=True
    # Legacy layer workers save their input file. Redirect non-day workers to a
    # local working copy so they cannot overwrite the canonical day source.
    if phase!='day':bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'lighting-work.blend'),compress=True)
    progress('construction');load('bake_construction.py');load('bake_construction_depth.py')
    progress('smoke');load('bake_smoke.py')
    p=ROOT/'tools/configure_resort_v6.py';exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__file__':str(p)})
    bpy.context.window.scene=s;s.frame_set(1)
    if phase=='day':bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE),compress=True)
    progress('complete')
else:raise ValueError(mode)
