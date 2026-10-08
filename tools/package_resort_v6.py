"""Validate and package four coherent offline lighting bundles."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'wallpaper/assets/v6-stage';LIVE=ROOT/'wallpaper/assets'
os.environ['RESORT_RENDER_OUT']=str(STAGE)
import package_resort as pack
p=argparse.ArgumentParser();p.add_argument('--preview',action='store_true');p.add_argument('--promote',action='store_true');p.add_argument('--phase',choices=['day','morning','evening','night']);args=p.parse_args()
assert not(args.preview and args.promote)
assert not(args.phase and args.promote),'A partial lighting set cannot be promoted'
phases=(args.phase,) if args.phase else ('day',) if args.preview else ('day','morning','evening','night')
for phase in phases:
 out=STAGE if phase=='day' else STAGE/'phases'/phase
 for mode in (('sprites','layers') if args.preview else ('sprites','layers','water')):
  assert json.loads((out/(mode+'-progress.json')).read_text())['stage']=='complete',(phase,mode)
 # Full beauty RGB includes exactly the same offline glow and reflections as
 # the water frame. Only its alpha comes from the separate water holdout pass.
 with Image.open(out/'poster-v3.png') as beauty,Image.open(out/'static-v3-untrimmed.png') as holdout,Image.open(out/'shore-alpha-mask.png') as shore:
  static=beauty.convert('RGBA');static.putalpha(ImageChops.multiply(holdout.getchannel('A'),ImageChops.invert(shore.convert('L'))));static.save(out/'static.png')
 atlas=Image.new('RGBA',(2048,3200))
 for row in range(19):
  for f in range(16):
   with Image.open(out/'character-frames'/f'{row:02}_{f:02}.png') as cell:
    box=cell.getchannel('A').getbbox();assert box and box[0]>0 and box[1]>0 and box[2]<128 and box[3]<160,(phase,row,f,box)
    atlas.paste(cell,(f*128,row*160))
 for stage in range(5):
  with Image.open(out/f'construction-{stage}.png') as cell:atlas.paste(cell,(stage*160,3040))
 atlas.save(out/'character.png')
 ambient=Image.new('RGBA',(2048,2880))
 for clip in range(3):
  for frame in range(96):
   with Image.open(out/'ambient-frames'/f'{clip:02}_{frame:03}.png') as cell:
    box=cell.getchannel('A').getbbox();assert box and box[0]>0 and box[1]>0 and box[2]<128 and box[3]<160,(phase,'ambient',clip,frame,box)
    ambient.paste(cell,(frame%16*128,(clip*6+frame//16)*160))
 ambient.save(out/'ambient.png')
 depth=Image.new('RGBA',(800,160))
 for stage in range(5):
  with Image.open(out/f'construction-depth-{stage}.png') as cell:depth.paste(cell,(stage*160,0))
 depth.save(out/'construction-depth.png')
 smoke=Image.new('RGBA',(1536,1024))
 for f in range(24):
  with Image.open(out/'smoke-frames'/f'{f:02}.png') as cell:smoke.paste(cell,(f%6*256,f//6*256))
 smoke.save(out/'smoke.png')
 for source,target in [('poster-v3.png','poster.png'),('depth-v3.png','depth.png'),('scene-v2.json','scene.json')]:shutil.copyfile(out/source,out/target)
 if phase=='day':
  depth=Image.new('RGBA',(2048,3040))
  for row in range(19):
   for f in range(16):
    with Image.open(out/'character-depth-frames'/f'{row:02}_{f:02}.png') as cell:depth.paste(cell,(f*128,row*160))
  depth.save(out/'character-depth.png')
  depth=Image.new('RGBA',(2048,2880))
  for clip in range(3):
   for f in range(96):
    with Image.open(out/'ambient-depth-frames'/f'{clip:02}_{f:03}.png') as cell:depth.paste(cell,(f%16*128,(clip*6+f//16)*160))
  depth.save(out/'ambient-depth.png')
 if args.preview:
  for name in ('water-1080.mp4','water-720.mp4'):shutil.copyfile(out/'water-draft.mp4',out/name)
 else:
  pack.OUT=out
  for frame in range(1,362):
   with Image.open(out/'water-final'/f'{frame:04}.png') as cell:assert cell.size==(1920,1080)
  pack.encode('water-final','water-1080.mp4',1920);pack.encode('water-final','water-720.mp4',1280);pack.loop('water-final','final-loop.json')
  env=os.environ.copy();env['RESORT_TEST_ASSETS']=str(out);env['RESORT_WATER_REPORT']=f'encoded-water-v6-{phase}.json'
  subprocess.run([sys.executable,str(ROOT/'tools/check_resort_water.py')],env=env,check=True)
meta=json.loads((STAGE/'scene.json').read_text())
if not args.preview and not args.phase:meta['lighting']={'phases':{'day':'','morning':'phases/morning/','evening':'phases/evening/','night':'phases/night/'},'schedule':[{'phase':'morning','minute':360},{'phase':'day','minute':540},{'phase':'evening','minute':1080},{'phase':'night','minute':1260}],'fadeSeconds':120}
(STAGE/'scene.json').write_text(json.dumps(meta,indent=2))
if args.promote:
 names=['poster.png','static.png','depth.png','character.png','character-depth.png','ambient.png','ambient-depth.png','construction-depth.png','smoke.png','scene.json','water-1080.mp4','water-720.mp4']
 backup=ROOT.parent/'runtime-backups/v5-before-fairy';backup.mkdir(parents=True,exist_ok=True)
 for name in names:
  if (LIVE/name).exists() and not (backup/name).exists():shutil.copyfile(LIVE/name,backup/name)
 for phase in phases:
  out=STAGE if phase=='day' else STAGE/'phases'/phase;dest=LIVE if phase=='day' else LIVE/'phases'/phase;dest.mkdir(parents=True,exist_ok=True)
  for name in (names if phase=='day' else ['poster.png','static.png','character.png','ambient.png','smoke.png','water-1080.mp4','water-720.mp4']):
   tmp=dest/(name+'.tmp');shutil.copyfile(out/name,tmp);os.replace(tmp,dest/name)
 print('Promoted complete four-phase V6 bundle. Reload Lively.')
else:print('V6 bundle staged; no live assets replaced.')
