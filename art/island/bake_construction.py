import bpy,json,math,os
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ.get('RESORT_RENDER_OUT',ROOT/'wallpaper/assets'))
s=bpy.data.scenes.get('Construction_Bake') or bpy.data.scenes.new('Construction_Bake');bpy.context.window.scene=s
for o in list(s.objects):
        if len(o.users_scene)>1:
            for c in list(o.users_collection):
                if c in list(s.collection.children) or c==s.collection:c.objects.unlink(o)
        else:bpy.data.objects.remove(o,do_unlink=True)
source=bpy.data.scenes['Resort_Island'];s.world=source.world;s.view_settings.exposure=source.view_settings.exposure
s.view_settings.view_transform=source.view_settings.view_transform;s.view_settings.look=source.view_settings.look
for o in source.objects:
    if o.type=='LIGHT':
        lamp=o.copy();lamp.data=o.data.copy();s.collection.objects.link(lamp)
camera=bpy.data.objects.new('Construction sprite camera',bpy.data.cameras.new('Construction orthographic'));s.collection.objects.link(camera);camera.rotation_euler=source.camera.rotation_euler;camera.location=Vector((0,0,.65))+camera.rotation_euler.to_quaternion()@Vector((0,0,10));camera.data.type='ORTHO';camera.data.ortho_scale=2.5;s.camera=camera
s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=32;s.eevee.use_shadows=True;s.render.resolution_x=160;s.render.resolution_y=160;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.color_mode='RGBA';s.view_settings.view_transform='AgX'
def box(name,loc,size,material,stage):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=size;o.data.materials.append(bpy.data.materials[material]);o['stage']=stage;return o
box('Guest cabana foundation',(0,0,.06),(1.3,1.1,.12),'Honey teak',1)
for x in [-.55,.55]:
    for y in [-.45,.45]:box('Guest cabana post',(x,y,.52),(.055,.055,1),'Honey teak',1)
box('Guest cabana wall',(0,0,.52),(1.1,.9,.9),'Warm ivory plaster',2)
box('Guest cabana door',(-.2,-.456,.39),(.28,.02,.65),'Honey teak',2)
box('Guest cabana window',(.27,-.456,.64),(.25,.02,.27),'Blue window',2)
for side in [-1,1]:
    o=box('Guest cabana roof',(side*.36,0,1.16),(.84,1.2,.09),'Coral roof',3);o.rotation_euler[1]=side*.4
box('Guest cabana deck',(0,-.67,.09),(1.35,.4,.12),'Honey teak',4)
for stage in range(5):
    for o in s.objects:
        if 'stage' in o:o.hide_render=o['stage']>stage
    s.render.filepath=str(OUT/f'construction-{stage}.png');bpy.ops.render.render(write_still=True)
p=world_to_camera_view(source,source.camera,Vector((2.8,.3,.43)))
foot=world_to_camera_view(s,camera,Vector((0,0,0)))
metadata=OUT/('scene-v2.json' if os.environ.get('RESORT_RENDER_OUT') or Path(bpy.data.filepath).name=='resort-v2.blend' else 'scene.json')
meta=json.loads(metadata.read_text());meta['construction']={'width':160,'height':160,'atlasY':2720,'x':p.x*1920,'y':(1-p.y)*1080,'depth':p.z,'ppm':160/2.5,'anchorX':foot.x*160,'anchorY':(1-foot.y)*160};metadata.write_text(json.dumps(meta,indent=2))
bpy.context.window.scene=source
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
result={'stages':5}
