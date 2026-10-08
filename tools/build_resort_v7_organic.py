"""Expanded organic island: three scattered personal nooks, not furniture rows.

Blender 4.5 background --python tools/build_resort_v7_organic.py -- NEW_OUT_DIR
Reads immutable V6; every output destination must be new. No render is launched.
"""
import ast
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
OUT=Path(args[0]).resolve() if args else ROOT.parents[1]/'outputs/resort-v7/organic'
DEST=OUT/'resort-v7.blend'
assert not DEST.exists(),f'Preserve existing editable scene: {DEST}'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art/island/resort-v6.blend'))
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
meta=json.loads((ROOT/'wallpaper/assets/scene.json').read_text(encoding='utf-8'))
old_camera=[list(row) for row in s.camera.matrix_world]
meta['ground']['ellipse']=[7.2,5.5]
collection=bpy.data.collections.new('V7 Organic resident gardens');s.collection.children.link(collection)
groups={}
# Reuse only the owned primitive helpers, not the rejected row layout.
helper_ast=ast.parse((ROOT/'tools/build_resort_v7.py').read_text(encoding='utf-8'))
helper_names={'ground','material','own','cube','sphere','cylinder','curve','leg','bounds','point'}
exec(compile(ast.Module(body=[n for n in helper_ast.body if isinstance(n,ast.FunctionDef) and n.name in helper_names],type_ignores=[]),str(ROOT/'tools/build_resort_v7.py'),'exec'))
teak=bpy.data.materials['V2 scanned teak deck'];warm_teak=bpy.data.materials['V2 oiled teak']
cream=material('organic warm linen',(.84,.69,.47),.87)
mint=material('organic quiet mint',(.07,.45,.36),.84)
lilac=material('organic dusty violet',(.46,.34,.58),.86)
coral=material('organic faded coral',(.72,.34,.23),.86)
ceramic=material('organic tea glaze',(.10,.52,.41),.3)
tea_color=material('organic amber tea',(.24,.09,.025),.26)
rug_material=material('organic braided straw',(.59,.42,.23),.95)

# The whole shoreline (including every shape-key foam pose) expands with
# the same exact XY transform. Z and the perspective camera are unchanged.
sx,sy=7.2/5.5,5.5/4.3
terrain=s.objects['Island sand and submerged shelf']
terrain.scale.x*=sx;terrain.scale.y*=sy
foam=s.objects['V3 waterline foam'];foam.scale.x*=sx;foam.scale.y*=sy
hidden=[]
for o in s.objects:
    if o.name.startswith(('Coffee ','V2 linen seat cushion','V2 linen back cushion')):
        o.hide_render=True;o.hide_set(True);o['v7_replaced_retained']=True;hidden.append(o.name)

# Rock clusters follow the new beach edge, giving the new living space a
# believable outer boundary while keeping the inner sand free to wander.
rock_moves=[]
for name,x,y in [('V2 scanned boulder 0',-5.95,-.45),('V2 scanned boulder 1',-5.8,-1.7),
                 ('V2 scanned boulder 2',5.8,.4),('V2 scanned boulder 3',5.9,1.6),
                 ('V2 scanned boulder 4',2.3,4.1),('V2 scanned boulder 5',-5.55,-2.45)]:
    o=s.objects.get(name)
    if o:
        before=list(o.location);o.location=(x,y,ground(x,y)-.08)
        rock_moves.append({'name':name,'before':before,'after':list(o.location)})

# Reuse the real leaf/trunk mesh and its alpha/material classification.
# A shorter leaning palm shelters the western nook without a new canopy row.
palm=s.objects['Resort V3 curved palm 2'].copy();palm.data=palm.data.copy()
collection.objects.link(palm);palm.name='V7 organic western shade palm'
palm.location=(-4.60,.10,.43);palm.rotation_euler.z+=math.pi
palm.scale*=.80;palm['resort_v7_owner']='organic-western-garden'


def boxes(name,components,mat,group):
    """Several connected or separate teak pieces in one editable mesh."""
    vertices=[];faces=[]
    for location,size in components:
        first=len(vertices)
        for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]:
            vertices.append((location[0]+x*size[0]/2,location[1]+y*size[1]/2,location[2]+z*size[2]/2))
        faces.extend(tuple(first+i for i in f) for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])
    mesh=bpy.data.meshes.new('V7 '+name);mesh.from_pydata(vertices,[],faces);mesh.update()
    o=bpy.data.objects.new('V7 '+name,mesh);collection.objects.link(o);mesh.materials.append(mat)
    o['resort_v7_owner']='organic-nook';groups.setdefault(group,[]).append(o)
    bevel=o.modifiers.new('Soft teak edges','BEVEL');bevel.width=.025;bevel.segments=3
    o.modifiers.new('Broad face normals','WEIGHTED_NORMAL');return o


def legs(name,xy,top,group,width=.10):
    components=[]
    for x,y in xy:
        floor=ground(x,y)-.01
        components.append(((x,y,(floor+top)/2),(width,width,top-floor)))
    return boxes(name,components,teak,group)


seats={}
# Each personal nook has its own silhouette, palette and sand clearing.
x,y=-3.10,-2.30;group='mint-west-nook';top=.97
cube('western teak seat',(x,y,.805),(1.20,.72,.12),teak,.045,group)
legs('western four feet',[(x+a,y+b) for a in [-.48,.48] for b in [-.27,.27]],.81,group)
cube('western mint seat',(x,y-.02,.905),(1.10,.58,.13),mint,.065,group)
cube('western mint back',(x,y+.30,1.14),(1.10,.15,.46),mint,.075,group)
boxes('western rounded armrests',[((x+a,y,1.08),(.14,.61,.12)) for a in [-.565,.565]],warm_teak,group)
seats['claude']={'id':group,'position':[x,y-.02,top],'approach':point(x,y-.87),'heading':0,'surfaceHeight':top,'rootOffset':.31,'transitionSeconds':1.05,'hopHeight':.12}

x,y=3.30,-1.70;group='violet-east-nook';top=.93
cylinder('eastern round teak seat',(x,y,.77),.62,.12,teak,group)
legs('eastern tripod feet',[(x-.46,y-.22),(x+.46,y-.22),(x,y+.39)],.80,group)
sphere('eastern violet cushion',(x,y-.04,.862),(.58,.47,.068),lilac,group)
curve('eastern curved back',[(x-.56,y-.03,1.04),(x-.48,y+.34,1.10),(x,y+.48,1.20),(x+.48,y+.34,1.10),(x+.56,y-.03,1.04)],.095,warm_teak,group)
seats['codex']={'id':group,'position':[x,y-.04,top],'approach':point(x,y-.96),'heading':0,'surfaceHeight':top,'rootOffset':.31,'transitionSeconds':1.05,'hopHeight':.12}

x,y=-.45,-3.65;group='cream-front-nook';top=.86
cube('front low teak seat',(x,y,.695),(1.16,.69,.13),warm_teak,.055,group)
legs('front low feet',[(x+a,y+b) for a in [-.46,.46] for b in [-.23,.23]],.70,group)
cube('front cream cushion',(x,y-.02,.795),(1.08,.58,.13),cream,.065,group)
cube('front soft low back',(x,y+.27,1.02),(1.10,.17,.39),cream,.065,group)
sphere('front oval straw rug',(x,y-.10,.434),(1.08,.75,.010),rug_material)
seats['apps']={'id':group,'position':[x,y-.02,top],'approach':point(x,y-.82),'heading':0,'surfaceHeight':top,'rootOffset':.31,'transitionSeconds':1.05,'hopHeight':.10}

# Shared nap nook far from the three personal seats. It stays wide enough
# for the measured 1.30m belly-up body at full scale.
x,y=-4.65,-1.10;group='western-nap-nook';BED_TOP=.84
cube('nap low teak base',(x,y,.685),(1.51,1.98,.12),teak,.055,group)
legs('nap four feet',[(x+a,y+b) for a in [-.61,.61] for b in [-.81,.81]],.70,group)
cube('nap thick cream mattress',(x,y,.775),(1.45,1.94,.13),cream,.075,group)
cube('nap head rail',(x,y+.91,.925),(1.51,.10,.49),teak,.045,group)
cube('nap mint pillow',(x,y+.68,.902),(1.26,.36,.124),mint,.075,group)
cube('nap soft folded throw',(x,y-.65,.858),(1.32,.30,.035),coral,.014,group)
bed={'id':group,'position':[x,-1.91,BED_TOP],'approach':point(x,-2.50),'heading':0,
     'surfaceHeight':BED_TOP,'rootOffset':-.4491118,'seconds':14,'transitionSeconds':1.35,
     'usableLength':1.94,'usableWidth':1.45,'anchor':'feet south; head +Y'}

# The tea station is a separate convivial corner on the enlarged front-right
# beach. There is no computer row or furniture wall across the cabin entrance.
x,y=2.35,-3.45;group='front-tea-nook';TEA_TOP=1.025
cube('tea small teak table',(x,y,TEA_TOP-.045),(1.05,.65,.09),warm_teak,.055,group)
legs('tea four feet',[(x+a,y+b) for a in [-.40,.40] for b in [-.23,.23]],TEA_TOP-.04,group)
cube('tea braided placemat',(x-.12,y,TEA_TOP+.008),(.70,.48,.016),rug_material,.035,group)
px,py,pz=x+.28,y+.06,TEA_TOP
sphere('tea mint pot',(px,py,pz+.15),(.17,.145,.15),ceramic,group)
cylinder('tea pot lid',(px,py,pz+.288),.125,.025,ceramic,group)
curve('tea pot spout',[(px+.10,py-.035,pz+.10),(px+.20,py-.045,pz+.13),(px+.25,py-.055,pz+.25)],.032,ceramic,group)
curve('tea pot handle',[(px-.12,py,pz+.25),(px-.25,py,pz+.235),(px-.25,py,pz+.09),(px-.12,py,pz+.075)],.025,ceramic,group)
for i,mat in enumerate([cream,mint,lilac]):
    cx,cy=x-.37+i*.19,y-.06
    cylinder('tea cup '+str(i+1),(cx,cy,pz+.075),.062,.12,mat,group)
    cylinder('tea cup '+str(i+1)+' surface',(cx,cy,pz+.137),.05,.005,tea_color,group)
tea={'id':group,'position':point(x,-4.27),'approach':point(x,-4.27),'heading':0,'seconds':10,'counterHeight':TEA_TOP}

# Tiny personal details, not more workstations: a book and a small cup beside
# the front lounge, plus the existing planted porch and four retained palms.
cube('front side stone table',(.65,-3.55,.67),(.38,.38,.48),teak,.065)
cube('front quiet book',(.65,-3.55,.925),(.23,.17,.035),coral,.014)
cylinder('front tiny cup',(.73,-3.64,.985),.047,.09,cream)

bpy.context.view_layer.update()
obstacles=[{'name':'terrace','bounds':bounds([s.objects['Terrace']])},
           {'name':'single original work table','bounds':bounds([s.objects['V3 scanned work table']])}]
for name,objects in groups.items():obstacles.append({'name':name,'bounds':bounds(objects)})
# Protect walking feet from the new coast rocks and western palm trunk.
for move in rock_moves:obstacles.append({'name':move['name'],'bounds':bounds([s.objects[move['name']]])})
obstacles.append({'name':'western palm trunk','bounds':[-4.72,-.02,-4.48,.22]})
targets={
 'claude':{'desk':point(-2.30,-1.10),'testing':point(-1.35,-2.30),'failed':point(-1.35,-2.30),'permission':point(-1.65,-3.40),'browsing':point(-2.30,-1.10)},
 'codex':{'desk':point(2.30,-1.55),'testing':point(1.05,-2.05),'failed':point(1.05,-2.05),'permission':point(1.15,-3.05),'browsing':point(2.30,-1.55)},
 'apps':{'desk':point(.35,-2.85),'testing':point(.35,-2.85),'failed':point(.35,-2.85),'permission':point(.80,-3.95),'browsing':point(.35,-2.85)},
}
for key,value in targets.items():
    value['idle']=seats[key]['position'];value['done']=seats[key]['position']
    for state in ['starting','editing','working']:value[state]=value['desk']
patch={'version':7,'layout':'organic-personal-nooks','source':'art/island/resort-v7-organic.blend','ground':meta['ground'],
       'effects':{'construction':False,'smoke':False},
       'navigation':{'clearance':.30,'obstacles':obstacles},
       'activities':{'seats':seats,'bed':bed,'tea':tea,'targets':targets,'workLane':False,
                     'minimumGroundHeight':.1,'initialIdleSeconds':10,'transitionSeconds':1.05,'seatSeconds':12,
                     'poseOverrides':{key:{state:'testing' for state in ['starting','editing','working']} for key in ['codex','apps']},
                     'groundNote':'XY enlarged from ellipse 5.5/4.3 to 7.2/5.5; shoreline foam scaled identically; all Z and camera unchanged.'},
       'targets':targets['claude'],'seating':{'states':['idle','done'],'position':[-3.10,-2.32,.66],
                    'approach':seats['claude']['approach'],'seconds':1.05,'hopHeight':.12,'cushionTop':.97}}
meta.update(patch)
assert old_camera==[list(row) for row in s.camera.matrix_world],'Perspective camera changed'
s['resort_version']=7;s['resort_v7_layout']='Organic personal nooks on expanded island'
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
(OUT/'scene.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
(OUT/'scene-patch.json').write_text(json.dumps(patch,indent=2),encoding='utf-8')
(OUT/'layout-audit.json').write_text(json.dumps({'editableCopy':str(DEST),'source':'V6 original','cameraUnchanged':True,
   'groundEllipse':meta['ground']['ellipse'],'terrainXYScale':[sx,sy],'terrainZUnchanged':True,'foamScaledWithCoast':True,
   'newObjects':len(collection.objects),'personalNookRoots':{k:v['position'] for k,v in seats.items()},
   'retainedOriginalSingleWorkstation':True,'retainedHiddenObjects':hidden,'relocatedCoastRocks':rock_moves,
   'obstacles':obstacles,'approachGround':{**{k:v['approach'][2] for k,v in seats.items()},'bed':bed['approach'][2],'tea':tea['approach'][2]},
},indent=2),encoding='utf-8')
print('Expanded organic V7 saved:',DEST)
print('New objects:',len(collection.objects),'original single workstation retained')
probe_path=ROOT/'tools/probe_resort_v7_ground.py'
probe_scope={'__file__':str(probe_path),'__name__':'resort_ground_probe'}
exec(compile(probe_path.read_text(encoding='utf-8'),str(probe_path),'exec'),probe_scope)
ground_report=probe_scope['probe'](s,meta)
(OUT/'ground-probes.json').write_text(json.dumps(ground_report,indent=2),encoding='utf-8')
print('Ground mesh ray probes:',ground_report['status'],'maxError',ground_report['maximumError'])
assert ground_report['status']=='PASS',ground_report['maximumError']
