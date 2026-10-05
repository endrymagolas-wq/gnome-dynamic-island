"""Record checks against the currently shipped bundle, with exact asset hashes."""
import datetime, hashlib, json, os, subprocess, sys
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1];os.chdir(root)
out=root/'docs/evidence/resort';env=os.environ.copy();env['RESORT_WATER_REPORT']='encoded-water-v4.json'
checks=[]
for command in [
    [sys.executable,'tests/check_claude.py'],[sys.executable,'tests/check_resort_host.py'],
    ['node','tests/cartoon-island.mjs'],['node','tests/resort-scene.mjs'],
    [sys.executable,'tests/check_resort_depth.py'],[sys.executable,'tests/check_resort_construction_depth.py'],
    [sys.executable,'tools/check_resort_water.py'],['node','--check','wallpaper/player.js'],
    [sys.executable,'-m','compileall','-q','assistant','wallpaper','tools','art/island']]:
    result=subprocess.run(command,env=env,text=True,capture_output=True)
    checks.append({'command':' '.join(command),'exit':result.returncode,'output':result.stdout+result.stderr})
    assert result.returncode==0,checks[-1]
with Image.open(root/'wallpaper/assets/character.png') as atlas:
    for row in range(17):
        for frame in range(16):
            box=atlas.crop((frame*128,row*160,(frame+1)*128,(row+1)*160)).getchannel('A').getbbox()
            assert box and box[0]>0 and box[1]>0 and box[2]<128 and box[3]<160,(row,frame,box)
audit=json.loads((out/'source-v4-audit.json').read_text())
assert audit['sourceSha256']==hashlib.sha256((root/audit['source']).read_bytes()).hexdigest()
assert audit['gestureSurvivesFrameEvaluation']
report={'recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,
    'spriteCells':272,'clippedSpriteCells':0,'sourceAuditMatchesSavedBlend':True,
    'assets':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'wallpaper/assets').iterdir() if p.name in ['scene.json','character.png','water-1080.mp4','static.png','depth.png']},
    'limits':'Physical Win+L/resume, exclusive fullscreen and multiple displays remain manual. The unchanged Windows os.getuid baseline failure is recorded in windows-baseline-v3.json.'}
(out/'validation-v4.json').write_text(json.dumps(report,indent=2))
print('PASS V4 hook, host, routes, depth, decoded seam, sprite bounds and saved-source binding')
