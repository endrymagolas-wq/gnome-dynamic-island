"""Export navigation obstacles and seat registration from actual Blender geometry."""
import bpy,json,os
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('RESORT_RENDER_OUT',ROOT/'wallpaper/assets/v6-stage'))
s=bpy.data.scenes['Resort_Island']
def bounds(names):
    points=[o.matrix_world@Vector(p) for o in s.objects if o.name in names for p in o.bound_box]
    assert points,names
    return [min(p.x for p in points),min(p.y for p in points),max(p.x for p in points),max(p.y for p in points)]
obstacles=[{'name':'terrace','bounds':bounds(['Terrace'])},
 {'name':'coffee seating','bounds':bounds(['Coffee bench','Coffee table','V2 linen seat cushion','V2 linen seat cushion.001'])},
 {'name':'work table','bounds':bounds(['V3 scanned work table'])}]
meta=json.loads((OUT/'scene-v2.json').read_text())
meta['navigation']={'clearance':.30,'obstacles':obstacles}
# The seat surface is at .95m. Rig origin at .64m puts the shorts on its top,
# rather than keeping the standing feet origin at the .43m beach height.
meta['seating']={'states':['idle','done'],'approach':[-.61,-2.98,.43],
 'position':[-.61,-2.12,.64],'seconds':.9,'hopHeight':.14,'cushionTop':.95}
for state in ('idle','done'):meta['targets'][state]=meta['seating']['position'][:]
meta['targets']['desk']=[-2.3,-1.10,.43]
meta['projections']={}
for key,point in meta['targets'].items():
    p=world_to_camera_view(s,s.camera,Vector(point));meta['projections'][key]={'x':p.x*1920,'y':(1-p.y)*1080,'depth':p.z}
meta['construction']['atlasY']=3040
(OUT/'scene-v2.json').write_text(json.dumps(meta,indent=2))
result={'obstacles':obstacles,'seat':meta['seating']}
