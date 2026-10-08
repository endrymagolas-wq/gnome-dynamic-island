"""Independent ray/depth check on saved primitive geometry, run inside Blender."""
import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
p=Path(bpy.data.filepath).parents[2];s=bpy.data.scenes['Construction_Bake'];camera=s.camera
q=camera.rotation_euler.to_quaternion();direction=q@Vector((0,0,-1));footDepth=(-camera.location).dot(direction)
records=[]
for stage in range(1,5):
    vertices=[];polygons=[]
    for o in s.objects:
        if o.type!='MESH' or o.get('stage',999)>stage:continue
        matrix=Matrix.LocRotScale(o.location,o.rotation_euler.to_quaternion(),o.scale);offset=len(vertices)
        vertices.extend(matrix@v.co for v in o.data.vertices)
        polygons.extend(tuple(offset+i for i in face.vertices) for face in o.data.polygons)
    tree=BVHTree.FromPolygons(vertices,polygons)
    image=bpy.data.images.load(str(p/f'wallpaper/assets/construction-depth-{stage}.png'),check_existing=False);pixels=list(image.pixels)
    count=0
    for yy in range(10,150,7):
        for xx in range(10,150,7):
            index=((159-yy)*160+xx)*4
            if pixels[index+3]<.99:continue
            origin=camera.location+q@Vector((((xx+.5)/160-.5)*2.5,(.5-(yy+.5)/160)*2.5,0))
            hit=tree.ray_cast(origin,direction)
            if hit[0] is None:continue
            # Antialiased boundary pixels blend depths from different faces.
            # Validate interior pixels whose neighboring rays hit the same face.
            neighbors=[tree.ray_cast(origin+q@Vector((dx*2.5/160,dy*2.5/160,0)),direction) for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]]
            if any(n[2]!=hit[2] for n in neighbors):continue
            value=pixels[index];linear=value/12.92 if value<=.04045 else ((value+.055)/1.055)**2.4
            expected=hit[3]-footDepth;actual=linear*4-2
            assert abs(expected-actual)<.055,(stage,xx,yy,expected,actual)
            records.append({'stage':stage,'pixel':[xx,yy],'meshOffset':expected,'renderOffset':actual});count+=1
    assert count>=12,(stage,count)
    bpy.data.images.remove(image)
report={'method':'Independent orthographic BVH rays through the original cabana meshes versus linearized baked camera-depth offsets. No sprite-plane approximation.','samples':records,'maxErrorMetres':max(abs(x['meshOffset']-x['renderOffset']) for x in records)}
(p/'docs/evidence/resort/cabana-depth-v3-probes.json').write_text(json.dumps(report,indent=2));print(json.dumps({'samples':len(records),'maxErrorMetres':report['maxErrorMetres']}))
