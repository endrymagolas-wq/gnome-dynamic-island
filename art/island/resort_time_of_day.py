"""Four offline lighting presets; geometry/camera/water period stay identical."""
import bpy,math
PRESETS={
 'morning':{'sun':1.1,'sunColor':(1,.70,.39),'rotation':(1.10,-.30,-.65),'key':450,'fill':650,'skyMix':.65,'sky':(.11,.34,.50),'world':.12,'exposure':.15,'window':0},
 'day':{'sun':1.7,'sunColor':(1,.88,.70),'rotation':(.6,-.4,-.5),'key':650,'fill':950,'skyMix':.6,'sky':(.08,.40,.60),'world':.12,'exposure':.10,'window':0},
 'evening':{'sun':.70,'sunColor':(1,.36,.14),'rotation':(1.30,-.15,-.95),'key':220,'fill':650,'skyMix':.84,'sky':(.17,.13,.32),'world':.10,'exposure':.20,'window':1.3},
 'night':{'sun':.15,'sunColor':(.26,.49,1),'rotation':(.85,-.25,-.50),'key':95,'fill':450,'skyMix':1,'sky':(.025,.060,.18),'world':.30,'exposure':.55,'window':3.0},
}
def apply(phase):
 s=bpy.data.scenes['Resort_Island'];p=PRESETS[phase]
 sun=s.objects['Resort sunlight'];sun.data.energy=p['sun'];sun.data.color=p['sunColor'];sun.rotation_euler=p['rotation']
 s.objects['Resort warm key'].data.energy=p['key'];s.objects['Resort sky fill'].data.energy=p['fill']
 s.objects['Resort sky fill'].data.color=(.61,.72,1)
 nt=s.world.node_tree;tint=nt.nodes['Fairy blue sky tint'];tint.inputs[0].default_value=p['skyMix'];tint.inputs[2].default_value=(*p['sky'],1)
 nt.nodes['Background'].inputs['Strength'].default_value=p['world'];s.view_settings.exposure=p['exposure']
 shader=next(n for n in bpy.data.materials['Blue window'].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 shader.inputs['Emission Color'].default_value=(1,.40,.08,1);shader.inputs['Emission Strength'].default_value=p['window']
 s['lighting_phase']=phase
 # A restrained offline highlight glow, matching the requested game-shader feel.
 # The runtime receives already-composited pixels, never a realtime 3D shader.
 s.use_nodes=True;nt=s.node_tree
 render=next(n for n in nt.nodes if n.type=='R_LAYERS')
 composite=next(n for n in nt.nodes if n.type=='COMPOSITE')
 glow=nt.nodes.get('Fairy gentle glow') or nt.nodes.new('CompositorNodeGlare')
 glow.name='Fairy gentle glow';glow.glare_type='FOG_GLOW';glow.quality='HIGH'
 glow.inputs['Threshold'].default_value=1.6;glow.inputs['Strength'].default_value=.25;glow.inputs['Size'].default_value=.3
 nt.links.new(render.outputs['Image'],glow.inputs['Image']);nt.links.new(glow.outputs['Image'],composite.inputs['Image'])
 return p
