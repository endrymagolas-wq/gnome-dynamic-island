"""Run offline in Blender after reopening the saved V4 source."""
import bpy, hashlib, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'art/island/pip_poses.py'; scope={'__file__':str(path)}
exec(compile(path.read_text(),str(path),'exec'),scope);scope['setup']()
rig=scope['r']; samples=[]
for t in (.5,.625,.75,.875):
    scope['pose']('walk',t*math.tau)
    samples.append(rig.pose.bones['Foot.L'].head.y*scope['SCALE']-scope['STANCE_SPEED']*t)
assert max(samples)-min(samples)<.00001,'Planted foot slides relative to runtime travel'
scope['pose']('permission',.8)
wrist=rig.pose.bones['LowerArm.R'].tail.copy()
assert wrist.z>2.3,'Permission hand must rise above the shoulder'
assert rig.animation_data.action is None,'Source animation must not overwrite the gesture during rendering'
scope['s'].frame_set(scope['s'].frame_current)
bpy.context.view_layer.update()
assert (rig.pose.bones['LowerArm.R'].tail-wrist).length<.00001,'Frame evaluation overwrote the gesture'
actions={a.name:{'range':list(a.frame_range),'retained':a.use_fake_user} for a in bpy.data.actions}
assert len([n for n in actions if n.startswith('Pip_Source_')])==14
assert len([n for n in actions if n.startswith('Resort_Pip_')])==10
assert all(a['retained'] for a in actions.values())
images=[{'name':i.name,'packed':bool(i.packed_file)} for i in bpy.data.images if i.users and i.source=='FILE']
assert all(i['packed'] for i in images)
invalid=[b.name+':'+c.name for b in rig.pose.bones for c in b.constraints if not c.is_valid]
assert not invalid
report={'source':'art/island/resort-v4.blend','sourceSha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
    'scenes':sorted(s.name for s in bpy.data.scenes),'rigBones':len(rig.data.bones),
    'meshVertices':len(bpy.data.objects['BlueDemon'].data.vertices),'invalidConstraints':invalid,
    'images':images,'actions':actions,'walkSpeedMetresPerSecond':scope['STANCE_SPEED'],
    'plantedFootWorldY':samples,'plantedFootMaxDriftMetres':max(samples)-min(samples),
    'permissionWristHeight':wrist.z,'gestureSurvivesFrameEvaluation':True}
(ROOT/'docs/evidence/resort/source-v4-audit.json').write_text(json.dumps(report,indent=2))
print('PASS V4 saved source, actions, packed textures and planted stride')
