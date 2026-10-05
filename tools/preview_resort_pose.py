"""Cheap isolated rig diagnostic while the main MCP is rendering water."""
import bpy,ast,math,json
from pathlib import Path
from mathutils import Vector,Matrix
root=Path(__file__).resolve().parents[1];s=bpy.data.scenes['Character_Bake'];bpy.context.window.scene=s
rig=next(o for o in s.objects if o.type=='ARMATURE');rig.rotation_euler.z=0
tree=ast.parse((root/'art/island/bake_character.py').read_text())
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('rot','solve_arm','pose')]
exec(compile(ast.Module(body=functions,type_ignores=[]),'pose-diagnostic','exec'),globals())
pose('editing',0);rig.rotation_euler.z=math.pi
cup=next(o for o in s.objects if o.name.startswith('Worker coffee cup'));cup.hide_render=True
bpy.context.view_layer.update();s.render.filepath=str(root/'wallpaper/assets/typing-preview.png');bpy.ops.render.render(write_still=True)
hands={side:list(rig.matrix_world@rig.pose.bones[side+'Hand'].head) for side in ('Left','Right')}
(root/'docs/evidence/resort/typing-hands.json').write_text(json.dumps(hands,indent=2))
