"""Append the shipped CC0 source to a V3/V4 scene, retaining authored actions."""
import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'art/thirdparty/quaternius-pip'
if not bpy.data.scenes.get('Mascot_Pip'):
    scene=bpy.data.scenes.new('Mascot_Pip')
    with bpy.data.libraries.load(str(folder/'BlueDemon.blend'),link=False) as (src,dst):
        dst.objects=src.objects;dst.actions=src.actions
    for obj in dst.objects:scene.collection.objects.link(obj)
    for action in dst.actions:
        action.name='Pip_Source_'+action.name.split('.')[0];action.use_fake_user=True
    camera=bpy.data.objects.new('Pip review camera',bpy.data.cameras.new('Pip orthographic'))
    scene.collection.objects.link(camera);scene.camera=camera
    base=bpy.data.scenes['Resort_Island']
    for obj in base.objects:
        if obj.type=='LIGHT':
            lamp=obj.copy();lamp.data=obj.data.copy();scene.collection.objects.link(lamp)
for image in bpy.data.images:
    if image.name.startswith('Atlas_Monsters'):
        image.filepath=str(folder/'Atlas_Monsters.png');image.reload();image.pack()
path=ROOT/'art/island/customize_pip.py'
exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),{'__file__':str(path)})
