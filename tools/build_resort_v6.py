"""Rebuild the environment from retained V5 into a new, protected destination.

blender --background --python tools/build_resort_v6.py -- C:/scratch/resort-v6.blend
Never overwrites an existing file, including the shipped editable source.
"""
import bpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
destination=Path(args[0]).resolve() if args else ROOT.parent/'reproduction/v6/resort-v6.blend'
assert destination.name=='resort-v6.blend'
assert not destination.exists(),f'Preserve existing work: {destination}'
destination.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art/island/resort-v5.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(destination),compress=True)
def load(name):
 p=ROOT/'art/island'/name;scope={'__file__':str(p)}
 exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),scope);return scope
load('fairy_palette.py');load('resort_time_of_day.py')['apply']('day')
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
s.render.resolution_percentage=100;s.cycles.samples=48;s.frame_set(1)
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
s.cycles.device='GPU';s.cycles.denoiser='OPTIX'
bpy.ops.wm.save_as_mainfile(filepath=str(destination),compress=True)
print('Rebuilt protected V6 environment:',destination)
