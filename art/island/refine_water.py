"""Offline glossy lagoon material. Run after build_scene, before all layer bakes."""
import bpy, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
# Directional environment gives water something to reflect; a constant world cannot.
nt=s.world.node_tree;nt.nodes.clear()
sky=nt.nodes.new('ShaderNodeTexSky');sky.sky_type='NISHITA';sky.sun_elevation=math.radians(35);sky.sun_rotation=math.radians(-55);sky.sun_size=math.radians(1.2);sky.sun_intensity=.6
bg=nt.nodes.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=.12
out=nt.nodes.new('ShaderNodeOutputWorld');nt.links.new(sky.outputs[0],bg.inputs[0]);nt.links.new(bg.outputs[0],out.inputs[0])
if not any(o.type=='LIGHT' for o in s.objects):
    for name,pos,power,size,color in [('Resort warm key',(-6,-8,12),1800,7,(1,.86,.67)),('Resort sky fill',(5,4,10),800,8,(.62,.85,1))]:
        d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
        o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
    d=bpy.data.lights.new('Resort sunlight','SUN');d.energy=2.4;d.angle=.035;d.color=(1,.95,.85)
    o=bpy.data.objects.new('Resort sunlight',d);s.collection.objects.link(o);o.rotation_euler=(.6,-.4,-.5)
for lamp in s.objects:
    if lamp.type=='LIGHT' and lamp.data.type=='SUN':
        lamp.data.energy=2.4;lamp.data.angle=.035;lamp.data.color=(1,.95,.85);lamp.rotation_euler=(.6,-.4,-.5)
water=bpy.data.objects['Water - periodic geometric waves'];m=water.data.materials[0]
m.use_raytrace_refraction=True;nt=m.node_tree;nt.nodes.clear()
p=nt.nodes.new('ShaderNodeBsdfPrincipled');p.inputs['Base Color'].default_value=(.78,.95,1,1);p.inputs['Roughness'].default_value=.075;p.inputs['IOR'].default_value=1.333;p.inputs['Transmission Weight'].default_value=1
out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(p.outputs[0],out.inputs['Surface'])
absorb=nt.nodes.new('ShaderNodeVolumeAbsorption');absorb.inputs['Color'].default_value=(.10,.72,.65,1);absorb.inputs['Density'].default_value=.22;nt.links.new(absorb.outputs[0],out.inputs['Volume'])
coord=nt.nodes.new('ShaderNodeTexCoord');offset=nt.nodes.new('ShaderNodeVectorMath');offset.operation='ADD';nt.links.new(coord.outputs['Object'],offset.inputs[0])
# Circular advection is periodic in both position and velocity, including the seam.
for axis,expr in [(0,'0.35*cos(2*pi*(frame-1)/360)'),(1,'0.35*sin(2*pi*(frame-1)/360)')]:offset.inputs[1].driver_add('default_value',axis).driver.expression=expr
noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3.2;noise.inputs['Detail'].default_value=2;noise.inputs['Roughness'].default_value=.6;nt.links.new(offset.outputs[0],noise.inputs['Vector'])
bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.55;bump.inputs['Distance'].default_value=.13;nt.links.new(noise.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
s.cycles.device='GPU';s.cycles.denoiser='OPTIX';s.cycles.adaptive_threshold=.04;s.cycles.adaptive_min_samples=8;s.render.use_persistent_data=True;s.view_settings.exposure=-.6
s.eevee.use_raytracing=True;s.render.film_transparent=False;s.frame_set(1)
s.render.resolution_percentage=50;s.eevee.taa_render_samples=64
s.render.filepath=str(ROOT/'wallpaper/assets/water-lookdev.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/island/resort.blend'))
result={'lights':len([o for o in s.objects if o.type=='LIGHT']),'preview':s.render.filepath}
