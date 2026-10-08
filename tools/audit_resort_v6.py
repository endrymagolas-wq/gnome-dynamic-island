"""Offline source audit after reopening V6. Do not run during benchmarks."""
import bpy,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'art/island/pip_v6_poses.py';scope={'__file__':str(path)}
exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),scope);scope['setup']()
rig=scope['r'];mesh=bpy.data.objects['Pip_V5_Generated'];samples=[]
for t in (.5,.625,.75,.875):
    scope['pose']('walk',t*math.tau)
    samples.append(rig.pose.bones['Foot.L'].head.y*scope['SCALE']-scope['STANCE_SPEED']*t)
assert max(samples)-min(samples)<.00001,'Planted stride slips relative to runtime travel'
scope['pose']('permission',.8);wrist=rig.pose.bones['LowerArm.R'].tail.copy()
assert wrist.z>1.8,'Permission hand must rise above adapted shoulder'
assert rig.animation_data.action is None
scope['s'].frame_set(scope['s'].frame_current);bpy.context.view_layer.update()
assert (rig.pose.bones['LowerArm.R'].tail-wrist).length<.00001
actions={a.name:{'range':list(a.frame_range),'retained':a.use_fake_user} for a in bpy.data.actions}
assert len([n for n in actions if n.startswith('Pip_Source_')])==14
assert len([n for n in actions if n.startswith('Resort_Pip_')])==15
images=[{'name':i.name,'packed':bool(i.packed_file)} for i in bpy.data.images if i.users and i.source=='FILE']
assert all(i['packed'] for i in images)
invalid=[b.name+':'+c.name for b in rig.pose.bones for c in b.constraints if not c.is_valid]
assert not invalid and len(rig.data.bones)==43
assert all(v.groups for v in mesh.data.vertices)
report={'source':'art/island/resort-v6.blend','sourceSha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
    'rigBones':43,'meshVertices':len(mesh.data.vertices),'meshFaces':len(mesh.data.polygons),
    'weightedVertices':sum(bool(v.groups) for v in mesh.data.vertices),'invalidConstraints':invalid,
    'images':images,'actions':actions,'walkSpeedMetresPerSecond':scope['STANCE_SPEED'],
    'plantedFootWorldY':samples,'plantedFootMaxDriftMetres':max(samples)-min(samples),
    'permissionWristHeight':wrist.z,'gestureSurvivesFrameEvaluation':True}
(ROOT/'docs/evidence/resort/source-v6-audit.json').write_text(json.dumps(report,indent=2))
print('PASS V6 saved mesh, rig, source/task actions, packed textures and planted stride')
