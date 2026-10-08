"""Compare actual palm UV alpha / mesh ray hits with the rendered depth matte."""
import bpy,json,array
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[1];s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
cam=s.camera;width,height=1920,1080;f=width*cam.data.lens/cam.data.sensor_width
depth=bpy.data.images.load(str(ROOT/'wallpaper/assets/depth-v3.png'),check_existing=True)
pixels=array.array('f',[0])*len(depth.pixels);depth.pixels.foreach_get(pixels)
leaf=bpy.data.materials['Resort Nobiax v3 leaf and bark']
tex=next(n.image for n in leaf.node_tree.nodes if n.type=='TEX_IMAGE' and n.image.colorspace_settings.name=='sRGB')
alphas=array.array('f',[0])*len(tex.pixels);tex.pixels.foreach_get(alphas)
palms=[];candidates=[]
for o in s.objects:
    if not o.name.startswith('Resort V3 curved palm'):continue
    mesh=o.data;mesh.calc_loop_triangles();triangles=list(mesh.loop_triangles)
    verts=[o.matrix_world@v.co for v in mesh.vertices]
    tree=BVHTree.FromPolygons(verts,[tuple(t.vertices) for t in triangles],all_triangles=True)
    palms.append((tree,verts,triangles,mesh.uv_layers.active))
    projected=[world_to_camera_view(s,cam,v) for v in verts]
    left,right=max(0,int(min(v.x for v in projected)*width)),min(width-1,int(max(v.x for v in projected)*width))
    top,bottom=max(0,int((1-max(v.y for v in projected))*height)),min(height-1,int((1-min(v.y for v in projected))*height))
    candidates.extend((x,y) for y in range(top,bottom,7) for x in range(left,right,7))
holes=[];opaque=[]
for x,y in candidates:
    direction=(cam.matrix_world.to_3x3()@Vector(((x-width/2)/f,(height/2-y)/f,-1))).normalized()
    hits=[]
    for tree,verts,tris,uvlayer in palms:
        location,normal,index,distance=tree.ray_cast(cam.location,direction)
        if location is not None:hits.append((distance,location,tris[index],verts,uvlayer))
    if not hits:continue
    distance,location,tri,verts,uvlayer=min(hits,key=lambda h:h[0])
    uv=barycentric_transform(location,*[verts[i] for i in tri.vertices],*[Vector((*uvlayer.data[i].uv,0)) for i in tri.loops])
    u=int((uv.x%1)*(tex.size[0]-1));v=int((uv.y%1)*(tex.size[1]-1));alpha=alphas[(v*tex.size[0]+u)*4+3]
    z=-(cam.matrix_world.inverted()@location).z
    measured=pixels[((height-1-y)*width+x)*4]*50
    item={'pixel':[x,y],'uvAlpha':round(alpha,3),'frontCardDepth':round(z,3),'renderedDepth':round(measured,3)}
    if alpha<.02 and measured-z>.5 and len(holes)<8:holes.append(item)
    if alpha>.98 and abs(measured-z)<.16 and len(opaque)<8:opaque.append(item)
    if len(holes)>=8 and len(opaque)>=8:break
assert len(holes)>=3 and len(opaque)>=3,(holes,opaque,'Depth must retain leaf alpha, not hide workers behind rectangular cards')
report={'method':'Independent BVH hits on licensed palm triangles, UV alpha samples and linear decoded depth PNG','transparentLeafGaps':holes,'opaqueLeaves':opaque}
path=ROOT/'docs/evidence/resort/leaf-depth-v3-probes.json';path.write_text(json.dumps(report,indent=2))
result={'transparentProbes':len(holes),'opaqueProbes':len(opaque),'evidence':str(path)}
