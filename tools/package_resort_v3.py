"""Validate a complete V3 render before replacing the runtime asset bundle."""
import json,os,shutil
from pathlib import Path
from PIL import Image,ImageChops
from package_resort import encode,loop
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'wallpaper/assets'
progress=json.loads((OUT/'v3-final-progress.json').read_text())
assert progress['stage']=='complete','Do not package an unfinished or mixed scene render'
meta=json.loads((OUT/'scene-v2.json').read_text())
assert meta['character']['source'].startswith('Adapted Snow')
with Image.open(OUT/'static-v3-untrimmed.png') as source,Image.open(OUT/'shore-alpha-mask.png') as mask:
    static=source.convert('RGBA');static.putalpha(ImageChops.multiply(static.getchannel('A'),ImageChops.invert(mask.convert('L'))));static.save(OUT/'static-v3.png')
im=Image.new('RGBA',(2048,2880))
for row in range(17):
    for frame in range(16):
        with Image.open(OUT/'character-v2-frames'/f'{row:02}_{frame:02}.png') as cell:
            assert cell.size==(128,160);im.paste(cell,(frame*128,row*160))
for stage in range(5):
    with Image.open(OUT/f'construction-{stage}.png') as cell:im.paste(cell,(stage*160,2720))
im.save(OUT/'character-v3.png')
cabanaDepth=Image.new('RGBA',(800,160))
for stage in range(5):
    with Image.open(OUT/f'construction-depth-{stage}.png') as cell:cabanaDepth.paste(cell,(stage*160,0))
cabanaDepth.save(OUT/'construction-depth.png')
smoke=Image.new('RGBA',(1536,1024))
for f in range(24):
    with Image.open(OUT/'smoke-frames'/f'{f:02}.png') as cell:smoke.paste(cell,(f%6*256,f//6*256))
smoke.save(OUT/'smoke-v3.png')
for frame in range(1,362):
    with Image.open(OUT/'v3-water-final'/f'{frame:04}.png') as cell:assert cell.size==(1920,1080)
encode('v3-water-final','water-v3-1080.mp4',1920)
encode('v3-water-final','water-v3-720.mp4',1280)
loop('v3-water-final','v3-final-loop-check.json')
for source,target in [('poster-v3.png','poster.png'),('static-v3.png','static.png'),('depth-v3.png','depth.png'),('character-v3.png','character.png'),('smoke-v3.png','smoke.png'),('scene-v2.json','scene.json'),('water-v3-1080.mp4','water-1080.mp4'),('water-v3-720.mp4','water-720.mp4')]:
    staged=OUT/(target+'.tmp');shutil.copyfile(OUT/source,staged);os.replace(staged,OUT/target)
print('Packaged complete V3 bundle; restart the Lively player to load it.')
