"""V3 offline layers, with leaf alpha retained in the depth render."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'wallpaper/assets'

def static_layers():
    s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
    if bpy.data.objects.get('V2 actor review instance'):bpy.data.objects['V2 actor review instance'].hide_render=True
    s.render.resolution_percentage=100;s.cycles.samples=64;s.render.use_persistent_data=True
    s.render.engine='CYCLES';s.render.film_transparent=False;s.render.image_settings.color_mode='RGBA';s.frame_set(1)
    s.render.filepath=str(OUT/'poster-v3.png');bpy.ops.render.render(write_still=True)
    water=bpy.data.objects['Water - periodic geometric waves'];original=list(water.data.materials)
    hold=bpy.data.materials.get('V3 water holdout') or bpy.data.materials.new('V3 water holdout');hold.use_nodes=True
    n=hold.node_tree.nodes;n.clear();a=n.new('ShaderNodeHoldout');b=n.new('ShaderNodeOutputMaterial');hold.node_tree.links.new(a.outputs[0],b.inputs[0])
    foam=bpy.data.objects['V3 waterline foam'];foam.hide_render=True
    water.data.materials.clear();water.data.materials.append(hold);s.render.film_transparent=True
    try:
        s.render.filepath=str(OUT/'static-v3-untrimmed.png');bpy.ops.render.render(write_still=True)
    finally:
        water.data.materials.clear()
        for m in original:water.data.materials.append(m)
        foam.hide_render=False;s.render.film_transparent=False
    shore_mask()
    return {'poster':str(OUT/'poster-v3.png'),'static':str(OUT/'static-v3-untrimmed.png')}

def shore_mask():
    """Expose the baked moving shoreline rather than freezing it in the plate."""
    s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
    terrain=bpy.data.objects['Island sand and submerged shelf'].material_slots[0].material
    world=s.world;engine=s.render.engine;view=s.view_settings.view_transform;exposure=s.view_settings.exposure
    water=bpy.data.objects['Water - periodic geometric waves'];foam=bpy.data.objects['V3 waterline foam']
    water_hidden=water.hide_render;foam_hidden=foam.hide_render;slots=[];mats={}
    black=bpy.data.worlds.new('V3 mask temporary black world');black.use_nodes=True;black.node_tree.nodes['Background'].inputs[1].default_value=0
    def material(original):
        if original in mats:return mats[original]
        dm=bpy.data.materials.new('V3 temporary shoreline mask');dm.use_nodes=True;n=dm.node_tree.nodes;n.clear();l=dm.node_tree.links
        em=n.new('ShaderNodeEmission');em.inputs[0].default_value=(0,0,0,1);out=n.new('ShaderNodeOutputMaterial');l.new(em.outputs[0],out.inputs[0])
        if original==terrain:
            geo=n.new('ShaderNodeNewGeometry');xyz=n.new('ShaderNodeSeparateXYZ');l.new(geo.outputs['Position'],xyz.inputs[0])
            band=n.new('ShaderNodeMapRange');band.inputs['From Min'].default_value=.17;band.inputs['From Max'].default_value=.30
            band.inputs['To Min'].default_value=1;band.inputs['To Max'].default_value=0;l.new(xyz.outputs['Z'],band.inputs[0]);l.new(band.outputs[0],em.inputs[0])
        if original and original.use_nodes:
            p=next((x for x in original.node_tree.nodes if x.type=='BSDF_PRINCIPLED'),None)
            if p and p.inputs['Alpha'].links:
                src=p.inputs['Alpha'].links[0].from_node
                if src.type=='TEX_IMAGE' and src.image:
                    tex=n.new('ShaderNodeTexImage');tex.image=src.image;t=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader')
                    l.new(tex.outputs['Alpha'],mix.inputs[0]);l.new(t.outputs[0],mix.inputs[1]);l.new(em.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs[0]);dm.surface_render_method='DITHERED'
        mats[original]=dm;return dm
    try:
        water.hide_render=True;foam.hide_render=True;s.world=black;s.render.engine='BLENDER_EEVEE_NEXT';s.render.resolution_percentage=100
        s.render.film_transparent=False;s.render.image_settings.color_depth='8';s.view_settings.view_transform='Raw';s.view_settings.exposure=0
        for o in s.objects:
            if o.type not in ('MESH','CURVE','SURFACE','FONT','META') or o.hide_render:continue
            for slot in o.material_slots:
                old=slot.material;slots.append((slot,slot.link,old));slot.link='OBJECT';slot.material=material(old)
        s.render.filepath=str(OUT/'shore-alpha-mask.png');bpy.ops.render.render(write_still=True)
    finally:
        for slot,link,old in slots:slot.material=old;slot.link=link
        water.hide_render=water_hidden;foam.hide_render=foam_hidden;s.world=world;s.render.engine=engine;s.view_settings.view_transform=view;s.view_settings.exposure=exposure
        for dm in mats.values():
            if dm.users==0:bpy.data.materials.remove(dm)
        bpy.data.worlds.remove(black)
    return {'shoreMask':str(OUT/'shore-alpha-mask.png')}

def depth_layer():
    s=bpy.data.scenes['Resort_Island'];bpy.context.window.scene=s
    if bpy.data.objects.get('V2 actor review instance'):bpy.data.objects['V2 actor review instance'].hide_render=True
    s.render.resolution_percentage=100;s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=64
    exposure=s.view_settings.exposure;s.view_settings.exposure=0;s.view_settings.view_transform='Standard'
    s.render.image_settings.color_depth='16';s.render.film_transparent=False
    replacements={};old_slots=[]
    def depth_material(original):
        if original in replacements:return replacements[original]
        dm=bpy.data.materials.new('V3 depth '+(original.name if original else 'default'));dm.use_nodes=True
        n=dm.node_tree.nodes;n.clear();l=dm.node_tree.links
        cam=n.new('ShaderNodeCameraData');divide=n.new('ShaderNodeMath');divide.operation='DIVIDE';divide.inputs[1].default_value=50
        em=n.new('ShaderNodeEmission');out=n.new('ShaderNodeOutputMaterial')
        l.new(cam.outputs['View Z Depth'],divide.inputs[0]);l.new(divide.outputs[0],em.inputs[0]);l.new(em.outputs[0],out.inputs[0])
        # Retain UV alpha of the licensed leaves. An opaque depth card would
        # incorrectly hide the worker through every gap between leaflets.
        if original and original.use_nodes:
            p=next((x for x in original.node_tree.nodes if x.type=='BSDF_PRINCIPLED'),None)
            if p and p.inputs['Alpha'].links:
                src=p.inputs['Alpha'].links[0].from_node
                if src.type=='TEX_IMAGE' and src.image:
                    tex=n.new('ShaderNodeTexImage');tex.image=src.image
                    transparent=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader')
                    l.new(tex.outputs['Alpha'],mix.inputs[0]);l.new(transparent.outputs[0],mix.inputs[1]);l.new(em.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs[0]);dm.surface_render_method='DITHERED'
        replacements[original]=dm;return dm
    try:
        for o in s.objects:
            if o.type not in ('MESH','CURVE','SURFACE','FONT','META') or o.hide_render:continue
            for slot in o.material_slots:
                old=slot.material;old_slots.append((slot,slot.link,old));slot.link='OBJECT';slot.material=depth_material(old)
        s.render.filepath=str(OUT/'depth-v3.png');bpy.ops.render.render(write_still=True)
    finally:
        for slot,link,material in old_slots:slot.material=material;slot.link=link
        s.view_settings.exposure=exposure;s.view_settings.view_transform='AgX';s.render.image_settings.color_depth='8';s.render.engine='CYCLES'
        for dm in replacements.values():
            if dm.users==0:bpy.data.materials.remove(dm)
    return {'depth':str(OUT/'depth-v3.png'),'leafAlpha':True}
