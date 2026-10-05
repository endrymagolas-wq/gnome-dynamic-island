"""Bake only the replacement character; approved V4 water stays unchanged."""
import bpy, json, os, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'wallpaper/assets/v5-stage';OUT.mkdir(exist_ok=True)
os.environ['RESORT_RENDER_OUT']=str(OUT)
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
path=ROOT/'art/island/pip_v5_poses.py';scope={'__file__':str(path)}
exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),scope)
scope['setup']();scope['s'].cycles.device='GPU'
start=time.monotonic()
for first in range(0,272,16):
    scope['bake_sprites'](first,min(first+15,271))
    (OUT/'sprites-progress.json').write_text(json.dumps({'stage':'sprites','frame':first+16,'frames':272,'seconds':time.monotonic()-start}))
(OUT/'sprites-progress.json').write_text(json.dumps({'stage':'complete','frame':272,'frames':272,'seconds':time.monotonic()-start}))
