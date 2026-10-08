"""Rebuild V5 from retained V4 + original HQ GLB, through Blender MCP or CLI.

Only run in a freshly opened resort-v4.blend. Saves a separate V5 project.
"""
import bpy,bmesh,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
assert Path(bpy.data.filepath).name=='resort-v4.blend','Start from retained V4 source'
s=bpy.data.scenes['Mascot_Pip'];bpy.context.window.scene=s
before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'art/thirdparty/pip-sf3d/pip-hq-original.glb'))
mesh=next(o for o in set(bpy.data.objects)-before if o.type=='MESH')
mesh.name='Pip_V5_Generated';mesh.parent=None
mesh.rotation_mode='XYZ';mesh.rotation_euler=(0,0,math.pi)
mesh.location=(0,0,.4644);mesh.scale=(1,1,1)
bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);bpy.context.view_layer.objects.active=mesh
bpy.ops.mesh.customdata_custom_splitnormals_clear()
bm=bmesh.new();bm.from_mesh(mesh.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
bm.to_mesh(mesh.data);bm.free()
for face in mesh.data.polygons:face.use_smooth=True
nt=mesh.data.materials[0].node_tree
for link in list(nt.links):
    if link.to_socket.name=='Normal':nt.links.remove(link)
nt.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.42
def load(path):
    scope={'__file__':str(path)}
    exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),scope)
    return scope
load(ROOT/'art/island/rig_pip_v5.py')
bpy.ops.file.pack_all()
load(ROOT/'art/island/pip_v5_poses.py')['save_actions']()
print('Saved reproducible V5 source:',bpy.data.filepath)
