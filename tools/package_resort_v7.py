"""Build a reviewable V7 bundle and promote only after complete renders.

Run with host Python and Pillow. Existing water/legacy reaction atlases are
linked into the preview bundle; accepted original V6 assets are retained.
"""
import argparse, json, shutil, os, hashlib
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parents[1]/'outputs/resort-v7'
LIVE=ROOT/'wallpaper/assets';STAGE=LIVE/'v7-stage'

def copy_or_link(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():return
    try:os.link(source,destination)
    except OSError:shutil.copyfile(source,destination)

def prepare(layout,activity,preview_day=False):
    STAGE.mkdir(exist_ok=True)
    meta=json.loads((layout/'scene.json').read_text())
    meta['source']='art/island/resort-v7.blend'
    life=json.loads((activity/'day/life.json').read_text())
    assert life['lying']['headDirection']==[0,1,0]
    meta['character']['life']=life
    mattePath=WORK/'plates/day/geometry-alpha.png'
    matteInfo=json.loads(mattePath.with_suffix('.json').read_text())
    assert Path(matteInfo['source']).resolve()==(layout/'resort-v7.blend').resolve()
    assert matteInfo['sourceSha256']==hashlib.sha256((layout/'resort-v7.blend').read_bytes()).hexdigest()
    assert matteInfo['matteSha256']==hashlib.sha256(mattePath.read_bytes()).hexdigest() and matteInfo['foamIncluded']
    meta['activities']['bed']['rootOffset']=-life['lying']['rootOffset']
    for key,p in meta['targets'].items():
        c=meta['camera'];m=c['matrixWorld'];d=[p[i]-c['location'][i] for i in range(3)]
        x=sum(d[i]*m[i][0] for i in range(3));y=sum(d[i]*m[i][1] for i in range(3));z=-sum(d[i]*m[i][2] for i in range(3))
        f=meta['width']*c['lens']/c['sensor']
        meta['projections'][key]={'x':meta['width']/2+f*x/z,'y':meta['height']/2-f*y/z,'depth':z}
    for phase in (('day',) if preview_day else ('day','morning','evening','night')):
        suffix=Path('.') if phase=='day' else Path('phases')/phase
        base=LIVE/suffix;dst=STAGE/suffix;dst.mkdir(parents=True,exist_ok=True)
        render=WORK/'plates'/phase
        rendered=json.loads((render/'render-complete.json').read_text())
        assert rendered['phase']==phase
        assert Path(rendered['source']).resolve()==(layout/'resort-v7.blend').resolve(),'Render is from a different scene revision'
        animated=activity/'day' if phase=='day' else activity/'phases'/phase
        complete=json.loads((animated/'progress.json').read_text())
        assert complete.get('complete') and not complete.get('preview'),(phase,complete)
        with Image.open(render/'beauty.png') as beauty,Image.open(mattePath) as matte:
            static=beauty.convert('RGBA');static.putalpha(matte.getchannel('A'));static.save(dst/'static.png')
        oldPoster=WORK/'rollback/assets'/suffix/'poster.png'
        if not oldPoster.exists():oldPoster=base/'poster.png'
        with Image.open(oldPoster) as old:
            Image.alpha_composite(old.convert('RGBA'),static).save(dst/'poster.png')
        for name in ('water-1080.mp4','water-720.mp4','character.png','ambient.png','smoke.png'):
            if (base/name).exists():copy_or_link(base/name,dst/name)
        shutil.copyfile(animated/'life.png',dst/'life.png')
    for name in ('character-depth.png','ambient-depth.png','construction-depth.png'):
        copy_or_link(LIVE/name,STAGE/name)
    shutil.copyfile(WORK/'plates/day/depth-v3.png',STAGE/'depth.png')
    shutil.copyfile(activity/'day/life-depth.png',STAGE/'life-depth.png')
    (STAGE/'scene.json').write_text(json.dumps(meta,indent=2))
    return meta

def promote(layout):
    editable=ROOT/'art/island/resort-v7.blend'
    assert not editable.exists(),'Retain any previous V7 editable source'
    backup=WORK/'rollback/assets';backup.mkdir(parents=True,exist_ok=True)
    for suffix in (Path('.'),Path('phases/morning'),Path('phases/evening'),Path('phases/night')):
        for name in ('static.png','poster.png','life.png'):
            target=LIVE/suffix/name;save=backup/suffix/name;save.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and not save.exists():shutil.copyfile(target,save)
            shutil.copyfile(STAGE/suffix/name,target)
    for name in ('scene.json','depth.png','life-depth.png'):
        target=LIVE/name
        if target.exists() and not (backup/name).exists():shutil.copyfile(target,backup/name)
        shutil.copyfile(STAGE/name,target)
    shutil.copyfile(layout/'resort-v7.blend',editable)
    shutil.copyfile(WORK/'activity/day/actions.blend',ROOT/'art/island/resort-v7-actions.blend')
    print('V7 promoted; V6 source and rollback assets retained:',backup)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--layout',type=Path,required=True);p.add_argument('--activity',type=Path,default=WORK/'activity');p.add_argument('--promote',action='store_true');p.add_argument('--preview-day',action='store_true');a=p.parse_args()
    assert not(a.promote and a.preview_day),'Preview-only bundle cannot be promoted'
    meta=prepare(a.layout,a.activity,a.preview_day)
    print('V7 '+('day preview' if a.preview_day else 'complete four-phase')+' bundle:',STAGE)
    if a.promote:promote(a.layout)
