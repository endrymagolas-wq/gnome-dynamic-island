"""Read-only archive structure/hash gate; no desktop or settings mutations."""
import argparse,hashlib,json,zipfile
from pathlib import Path,PurePosixPath
import build_release as b

def main():
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--components',nargs='+',choices=b.ARCHIVES,default=list(b.ARCHIVES));a=p.parse_args();results=[]
    for component in a.components:
        folder,name=b.ARCHIVES[component];archive=a.packages/name;checks=0
        with zipfile.ZipFile(archive) as z:
            names=z.namelist();assert len(names)==len(set(names)),'Duplicate ZIP entries';checks+=1
            for name in names:
                path=PurePosixPath(name)
                assert not path.is_absolute() and '..' not in path.parts and ':' not in name,'Unsafe ZIP path';checks+=1
                assert path.parts[0]==folder,'Unexpected extracted root';checks+=1
                assert not any(a.lower() in b.DENIED_PARTS for a in path.parts),'Private/test cache folder';checks+=1
                assert path.name.lower() not in b.DENIED_NAMES and path.suffix.lower() not in ('.pdb','.pyc','.log'),'Private/debug state';checks+=1
            assert z.testzip() is None,'ZIP CRC mismatch';checks+=1
            manifest=json.loads(z.read(folder+'/package-manifest.json'))
            assert manifest['release']['tag']=='windows-v0.4.0-beta.1' and manifest['release']['component']==component,'Wrong release selection';checks+=1
            expected={folder+'/'+n for n in manifest['files']}|{folder+'/package-manifest.json'}
            assert set(names)==expected,'ZIP differs from package manifest';checks+=1
            for name,record in manifest['files'].items():
                member=folder+'/'+name;info=z.getinfo(member);assert info.file_size==record['bytes'],'Manifest size differs';checks+=1
                h=hashlib.sha256()
                with z.open(member) as f:
                    for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
                assert h.hexdigest()==record['sha256'],'Manifest file hash differs';checks+=1
            if component=='island':assert not any(n.startswith(folder+'/receiver/') or n.startswith(folder+'/wallpaper/') for n in names),'Core is not independent';checks+=1
            if component in ('wallpaper','full'):
                scene=json.loads(z.read(folder+'/wallpaper/assets/scene.json'));assert scene['ground']['ellipse']==[7.2,5.5] and scene['effects']=={'construction':False,'smoke':False},'Rejected/stale geometry';checks+=1
                assert folder+'/python/Lib/site-packages/psutil-7.2.2.dist-info/LICENSE' in names,'Missing psutil BSD license';checks+=1
            if component in ('island','full'):assert folder+'/LICENSES/NAudio-LICENSE.txt' in names,'Missing NAudio MIT license';checks+=1
        results.append({'component':component,'archive':archive.name,'bytes':archive.stat().st_size,'sha256':b.sha(archive),'checks':checks,'pass':True})
        print(json.dumps(results[-1]),flush=True)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps({'pass':True,'scope':'Actual ZIP CRC/path/allowlist/exact inventory and member hashes; native QA independent','archives':results},indent=2)+'\n')

if __name__=='__main__':main()
