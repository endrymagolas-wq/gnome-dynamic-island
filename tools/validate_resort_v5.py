"""Verify that saved source, shipped atlas and native evidence describe V5."""
import hashlib,json
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1];out=root/'docs/evidence/resort';assets=root/'wallpaper/assets'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((out/'source-v5-audit.json').read_text())
assert source['sourceSha256']==sha(root/source['source'])
assert source['rigBones']==43 and source['meshVertices']==source['weightedVertices']==19980
assert not source['invalidConstraints'] and source['gestureSurvivesFrameEvaluation']
assert source['plantedFootMaxDriftMetres']<.00001 and source['permissionWristHeight']>1.8
native=json.loads((out/'v5/native-reactions.json').read_text())
for name,digest in native['assets'].items():assert sha(assets/name)==digest,name
expected=['starting',*[f'editing-{i}' for i in range(1,5)],'testing','failed','permission','done','browsing','working','idle']
for event in expected:
    assert native[event]['state']==event.split('-')[0]
    assert (out/'v5'/f'{event}.jpg').stat().st_size>10000
assert native['failed']['smokeVisiblePixels']>100
controls=json.loads((out/'v5/native-controls.json').read_text())
for name,digest in controls['assets'].items():assert sha(assets/name)==digest,name
assert all(k in controls for k in ['manualPause','waterOff','720p','qualityOff'])
perf=json.loads((out/'performance-v5.json').read_text())
for name,digest in perf['assets'].items():assert sha(assets/name)==digest,name
with Image.open(assets/'character.png') as atlas:
    assert atlas.size==(2048,2880)
    for row in range(17):
        for frame in range(16):
            bounds=atlas.crop((frame*128,row*160,(frame+1)*128,(row+1)*160)).getchannel('A').getbbox()
            assert bounds and bounds[0]>0 and bounds[1]>0 and bounds[2]<128 and bounds[3]<160,(row,frame,bounds)
report={'source':source['sourceSha256'],'assets':perf['assets'],'spriteFrames':272,'clippedFrames':0,
    'nativeCases':expected,'controls':list(controls),'performance':'performance-v5.json',
    'unchangedWaterEvidence':'encoded-water-v4.json; hashes checked by report_resort_v5.py',
    'limitations':'Physical lock/resume, exclusive fullscreen and multi-monitor behavior remain manual; depth uses a vertical actor plane.'}
(out/'validation-v5.json').write_text(json.dumps(report,indent=2))
print('PASS V5 source, 272 shipped sprites, real transport/native reactions, controls and matching performance assets')
