"""Separate build-time volumetric smoke loop; no volumetrics at runtime."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'wallpaper/assets'
s=bpy.data.scenes.get('Smoke_Bake') or bpy.data.scenes.new('Smoke_Bake');bpy.context.window.scene=s
for o in list(s.objects):
        if len(o.users_scene)>1:
            for c in list(o.users_collection):
                if c in list(s.collection.children) or c==s.collection:c.objects.unlink(o)
        else:bpy.data.objects.remove(o,do_unlink=True)
source=bpy.data.scenes['Resort_Island'];s.world=source.world;s.view_settings.exposure=source.view_settings.exposure
for o in source.objects:
    if o.type=='LIGHT':
        lamp=o.copy();lamp.data=o.data.copy();s.collection.objects.link(lamp)
cam=bpy.data.objects.new('Smoke camera',bpy.data.cameras.new('Smoke orthographic'));s.collection.objects.link(cam);cam.rotation_euler=source.camera.rotation_euler;cam.location=Vector((0,0,.65))+cam.rotation_euler.to_quaternion()@Vector((0,0,10));cam.data.type='ORTHO';cam.data.ortho_scale=2.5;s.camera=cam
s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=64;s.render.resolution_x=256;s.render.resolution_y=256;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.color_mode='RGBA';s.view_settings.view_transform='AgX'
clouds=[]
for i in range(3):
    m=bpy.data.materials.new('Smoke volume '+str(i));m.use_nodes=True;nt=m.node_tree;nt.nodes.clear()
    vol=nt.nodes.new('ShaderNodeVolumePrincipled');vol.inputs['Color'].default_value=(.26,.28,.25,1);vol.inputs['Density'].default_value=.4
    tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=4
    mult=nt.nodes.new('ShaderNodeMath');mult.operation='MULTIPLY';mult.inputs[1].default_value=.8
    output=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(tex.outputs['Fac'],mult.inputs[0]);nt.links.new(mult.outputs[0],vol.inputs['Density']);nt.links.new(vol.outputs[0],output.inputs['Volume'])
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1);o=bpy.context.object;o.name='Smoke puff '+str(i);o.data.materials.append(m);clouds.append((o,mult))
folder=OUT/'smoke-frames';folder.mkdir(exist_ok=True)
for frame in range(24):
    for i,(o,density) in enumerate(clouds):
        phase=(frame/24+i/3)%1;o.location=(.08*math.sin(phase*math.tau+i),0,.1+phase*1.1);size=.12+phase*.25;o.scale=(size,size,size*1.2);density.inputs[1].default_value=math.sin(phase*math.pi)*1.0
    s.render.filepath=str(folder/f'{frame:02}.png');bpy.ops.render.render(write_still=True)
foot=world_to_camera_view(s,cam,Vector((0,0,0)))
metadata=OUT/('scene-v2.json' if Path(bpy.data.filepath).name=='resort-v2.blend' else 'scene.json')
meta=json.loads(metadata.read_text());meta['smoke']={'width':256,'height':256,'frames':24,'fps':12,'columns':6,'ppm':256/2.5,'anchorX':foot.x*256,'anchorY':(1-foot.y)*256,'worldOrigin':[3.1,-.15,1.65]};metadata.write_text(json.dumps(meta,indent=2));bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
result={'smokeFrames':24}
