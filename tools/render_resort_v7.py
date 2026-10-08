"""EEVEE scene plates and matching depth. Retains the accepted V6 water loops.

The camera and water motion remain registered. V7 extends the dry beach, and
its newly rendered alpha covers the old coastline in the retained water.
All intermediate renders live outside the active wallpaper assets.
"""
import bpy, json, sys, os, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:]
out=Path(args[0]).resolve(); phase=args[1] if len(args)>1 else 'day'
out.mkdir(parents=True,exist_ok=True)
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
source=ROOT/'art/island/resort_time_of_day.py'
scope={'__file__':str(source)};exec(compile(source.read_text(),str(source),'exec'),scope)
scope['apply'](phase)
s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=64
s.eevee.use_raytracing=True
s.render.resolution_percentage=100;s.render.image_settings.color_mode='RGBA'
s.render.image_settings.color_depth='8';s.render.film_transparent=False;s.frame_set(1)
start=time.monotonic()
s.render.filepath=str(out/'beauty.png');bpy.ops.render.render(write_still=True)
os.environ['RESORT_RENDER_OUT']=str(out)
layers=ROOT/'art/island/bake_v3_layers.py';scope={'__file__':str(layers)}
exec(compile(layers.read_text(),str(layers),'exec'),scope)
if phase=='day':
    s.render.use_compositing=False
    scope['depth_layer']()
(out/'render-complete.json').write_text(json.dumps({'phase':phase,'engine':'BLENDER_EEVEE_NEXT','seconds':round(time.monotonic()-start,2),'source':bpy.data.filepath,'cameraUnchanged':True,'geometryVersion':s.get('resort_version',7)}))
