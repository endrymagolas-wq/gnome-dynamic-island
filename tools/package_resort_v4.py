"""Package the complete isolated V4 render, then promote the whole layer set."""
import json, os, shutil, sys, subprocess
from pathlib import Path
from PIL import Image, ImageChops
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'wallpaper/assets/v4-stage';LIVE=ROOT/'wallpaper/assets'
os.environ['RESORT_RENDER_OUT']=str(STAGE)
from package_resort import encode, loop
preview='--preview' in sys.argv
assert not (preview and '--promote' in sys.argv),'A draft review cannot replace the live wallpaper'
for mode in (('sprites','layers') if preview else ('water','sprites','layers')):
    report=json.loads((STAGE/(mode+'-progress.json')).read_text())
    assert report['stage']=='complete',f'{mode} render is unfinished'
meta=json.loads((STAGE/'scene-v2.json').read_text())
assert meta['character']['source'].startswith('Pip adapted from Quaternius')
assert abs(meta['construction']['anchorY']-116.0483)<.05
assert abs(meta['smoke']['anchorY']-185.67722)<.05
with Image.open(STAGE/'static-v3-untrimmed.png') as source,Image.open(STAGE/'shore-alpha-mask.png') as mask:
    static=source.convert('RGBA')
    static.putalpha(ImageChops.multiply(static.getchannel('A'),ImageChops.invert(mask.convert('L'))))
    static.save(STAGE/'static.png')
atlas=Image.new('RGBA',(2048,2880))
for row in range(17):
    for frame in range(16):
        with Image.open(STAGE/'character-frames'/f'{row:02}_{frame:02}.png') as cell:
            assert cell.size==(128,160);atlas.paste(cell,(frame*128,row*160))
for stage in range(5):
    with Image.open(STAGE/f'construction-{stage}.png') as cell:atlas.paste(cell,(stage*160,2720))
atlas.save(STAGE/'character.png')
depth=Image.new('RGBA',(800,160))
for stage in range(5):
    with Image.open(STAGE/f'construction-depth-{stage}.png') as cell:depth.paste(cell,(stage*160,0))
depth.save(STAGE/'construction-depth.png')
smoke=Image.new('RGBA',(1536,1024))
for f in range(24):
    with Image.open(STAGE/'smoke-frames'/f'{f:02}.png') as cell:smoke.paste(cell,(f%6*256,f//6*256))
smoke.save(STAGE/'smoke.png')
shutil.copyfile(STAGE/'poster-v3.png',STAGE/'poster.png')
shutil.copyfile(STAGE/'depth-v3.png',STAGE/'depth.png')
shutil.copyfile(STAGE/'scene-v2.json',STAGE/'scene.json')
if preview:
    for name in ('water-1080.mp4','water-720.mp4'):shutil.copyfile(STAGE/'water-draft.mp4',STAGE/name)
else:
    for frame in range(1,362):
        with Image.open(STAGE/'water-final'/f'{frame:04}.png') as cell:assert cell.size==(1920,1080)
    encode('water-final','water-1080.mp4',1920);encode('water-final','water-720.mp4',1280)
    loop('water-final','final-loop.json')
    # Check actual decoded video before it can replace the desktop bundle.
    testenv=os.environ.copy();testenv['RESORT_TEST_ASSETS']=str(STAGE)
    testenv['RESORT_WATER_REPORT']='encoded-water-v4.json'
    subprocess.run([sys.executable,str(ROOT/'tools/check_resort_water.py')],env=testenv,check=True)
if '--promote' in sys.argv:
    mappings={'poster-v3.png':'poster.png','static.png':'static.png','depth-v3.png':'depth.png',
        'character.png':'character.png','construction-depth.png':'construction-depth.png',
        'smoke.png':'smoke.png','scene-v2.json':'scene.json','water-1080.mp4':'water-1080.mp4',
        'water-720.mp4':'water-720.mp4'}
    # Preserve the running V3 asset set for rollback, outside tracked output.
    backup=ROOT.parent/'runtime-backups/v3-before-pip';backup.mkdir(parents=True,exist_ok=True)
    for target in mappings.values():
        if not (backup/target).exists():shutil.copyfile(LIVE/target,backup/target)
    for source,target in mappings.items():
        temporary=LIVE/(target+'.tmp');shutil.copyfile(STAGE/source,temporary);os.replace(temporary,LIVE/target)
    print('Promoted complete V4 asset set; reload Lively to read the new layers.')
else:
    print('V4 package staged; add --promote to replace the runtime asset set.')
