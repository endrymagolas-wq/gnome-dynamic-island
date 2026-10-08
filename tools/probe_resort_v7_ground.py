"""Measure analytical walker height against evaluated Blender terrain rays."""
import bpy, json, math, random, sys
from pathlib import Path
from mathutils import Vector


def analytical(meta,x,y):
    g=meta['ground'];r=math.hypot(x/g['ellipse'][0],y/g['ellipse'][1])
    if g.get('coastPerturb') and r>g['plateauRadius']:
        a=math.atan2(y/g['ellipse'][1],x/g['ellipse'][0]);dr=g['coastPerturb'][0]*math.sin(3*a)+g['coastPerturb'][1]*math.cos(5*a+g['coastPerturb'][2]);band=.18
        r=r-dr if r>=g['plateauRadius']+band+dr else (r+dr*g['plateauRadius']/band)/(1+dr/band)
    return g['height']-max(0,r-g['plateauRadius'])*g['slope']


def probe(scene,meta,count=48):
    bpy.context.window.scene=scene;bpy.context.view_layer.update()
    obj=scene.objects['Island sand and submerged shelf'].evaluated_get(bpy.context.evaluated_depsgraph_get())
    world=obj.matrix_world.copy();inverse=world.inverted();direction=(inverse.to_3x3()@Vector((0,0,-1))).normalized()
    points=[]
    for key,seat in meta['activities']['seats'].items():points.append(('approach-'+key,*seat['approach'][:2]))
    for key in ['bed','tea']:points.append(('approach-'+key,*meta['activities'][key]['approach'][:2]))
    for key,targets in meta['activities']['targets'].items():
        for state,point in targets.items():
            if state not in ('idle','done'):points.append((key+'-'+state,*point[:2]))
    generator=random.Random(20261008);added=0
    while added<count:
        x=generator.uniform(-meta['ground']['ellipse'][0],meta['ground']['ellipse'][0]);y=generator.uniform(-meta['ground']['ellipse'][1],meta['ground']['ellipse'][1])
        if analytical(meta,x,y)>=meta['activities']['minimumGroundHeight']:
            points.append(('random-dry-'+str(added),x,y));added+=1
    results=[]
    for label,x,y in points:
        hit,location,normal,index=obj.ray_cast(inverse@Vector((x,y,8)),direction,distance=20)
        expected=analytical(meta,x,y);actual=(world@location).z if hit else None
        results.append({'label':label,'xy':[x,y],'hit':bool(hit),'analyticZ':expected,'meshZ':actual,'error':abs(actual-expected) if hit else None})
    maximum=max(p['error'] for p in results if p['error'] is not None)
    report={'status':'PASS' if all(p['hit'] for p in results) and maximum<.02 else 'FAIL','source':bpy.data.filepath,
            'probeCount':len(results),'randomDryProbes':count,'groundEllipse':meta['ground']['ellipse'],
            'maximumError':maximum,'tolerance':.02,'probes':results}
    return report


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    meta=json.loads(Path(args[0]).read_text(encoding='utf-8'))
    report=probe(bpy.data.scenes['Resort_Island'],meta)
    Path(args[1]).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Ground mesh ray probes:',report['status'],'count',report['probeCount'],'maxError',report['maximumError'])
    assert report['status']=='PASS',report['maximumError']
