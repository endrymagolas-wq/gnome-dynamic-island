"""Optional isolated offline batch, launched from Blender MCP with its binary."""
import argparse,sys,json,time
from pathlib import Path
import bpy
p=argparse.ArgumentParser();p.add_argument('--start',type=int,required=True);p.add_argument('--end',type=int,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
assert 1<=a.start<=a.end<=361
root=Path(__file__).resolve().parents[1]
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
s.cycles.device='GPU';s.cycles.denoiser='OPTIX';s.render.use_persistent_data=True
path=root/'art/island/bake_layers.py';scope={'__file__':str(path)}
exec(compile(path.read_text(),str(path),'exec'),scope)
started=time.monotonic()
scope['bake_water'](a.start,a.end,100,64,progress_name=f'render-progress-{a.start}.json')
(root/f'wallpaper/assets/render-progress-{a.start}.json').write_text(json.dumps({'start':a.start,'end':a.end,'complete':True,'seconds':time.monotonic()-started}))
