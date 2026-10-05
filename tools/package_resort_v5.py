"""Swap validated V5 sprites and metadata, preserving all approved water layers."""
import json, shutil, os, sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];LIVE=ROOT/'wallpaper/assets';STAGE=LIVE/'v5-stage'
assert json.loads((STAGE/'sprites-progress.json').read_text())['stage']=='complete'
meta=json.loads((STAGE/'scene-v2.json').read_text())
assert 'Stable Fast 3D' in meta['character']['source']
atlas=Image.new('RGBA',(2048,2880))
for row in range(17):
    for frame in range(16):
        with Image.open(STAGE/'character-frames'/f'{row:02}_{frame:02}.png') as cell:
            assert cell.size==(128,160)
            bounds=cell.getchannel('A').getbbox();assert bounds
            assert bounds[0]>0 and bounds[1]>0 and bounds[2]<128 and bounds[3]<160,(row,frame,bounds)
            atlas.paste(cell,(frame*128,row*160))
with Image.open(LIVE/'character.png') as old:
    atlas.paste(old.crop((0,2720,2048,2880)),(0,2720))
atlas.save(STAGE/'character.png');(STAGE/'scene.json').write_text(json.dumps(meta,indent=2))
if '--promote' in sys.argv:
    backup=ROOT.parent/'runtime-backups/v4-before-pip-v5';backup.mkdir(parents=True,exist_ok=True)
    for name in ('character.png','scene.json'):
        if not (backup/name).exists():shutil.copyfile(LIVE/name,backup/name)
        temporary=LIVE/(name+'.tmp');shutil.copyfile(STAGE/name,temporary);os.replace(temporary,LIVE/name)
print('V5 sprites validated and '+('promoted' if '--promote' in sys.argv else 'staged'))
