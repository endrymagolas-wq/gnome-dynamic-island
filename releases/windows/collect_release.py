"""Create public artifact metadata and checksums, without local machine paths."""
import argparse,json,zipfile
from pathlib import Path
import build_release as b

NATIVE_SOURCE_NAME='cortiva-airplay-native-corresponding-sources-'+b.VERSION+'.zip'
NATIVE_SOURCE_SHA='81372689243525d1d3486fbca9306ad979d3b2f9b7894a60a612645fa1419f6c'

def main():
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--extra',nargs='*',default=[]);a=p.parse_args();results=[]
    for component,(folder,name) in b.ARCHIVES.items():
        file=a.packages/name;assert file.is_file(),f'Missing final ZIP: {name}'
        with zipfile.ZipFile(file) as z:
            release=json.loads(z.read(folder+'/release.json'));assert release['tag']==b.TAG and release['component']==component
            manifest=json.loads(z.read(folder+'/package-manifest.json'))
            assert set(z.namelist())=={folder+'/'+n for n in manifest['files']}|{folder+'/package-manifest.json'},'Non-final archive inventory'
        results.append({'component':component,'folder':folder,'archive':name,'bytes':file.stat().st_size,'sha256':b.sha(file),'externalDependencies':(['Lively Wallpaper'] if component in ('wallpaper','full') else ['Blender 4.5 LTS'] if component=='blender' else []),'download':'https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/'+b.TAG+'/'+name})
    source=a.packages/NATIVE_SOURCE_NAME;assert source.is_file() and b.sha(source)==NATIVE_SOURCE_SHA,'Corresponding native source archive changed'
    results.append({'component':'native-corresponding-sources','archive':source.name,'bytes':source.stat().st_size,'sha256':NATIVE_SOURCE_SHA,'download':'https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/'+b.TAG+'/'+source.name})
    for name in a.extra:
        file=a.packages/name;assert file.is_file() and file.parent.resolve()==a.packages.resolve(),'Extra artifact must be in packages'
        results.append({'component':'supplemental','archive':file.name,'bytes':file.stat().st_size,'sha256':b.sha(file),'download':'https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/'+b.TAG+'/'+file.name})
    (a.packages/'release-components.json').write_text(json.dumps({'version':b.VERSION,'tag':b.TAG,'components':results},indent=2)+'\n')
    (a.packages/'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['archive']}\n" for r in results),encoding='ascii')
    print(json.dumps({'tag':b.TAG,'artifacts':len(results),'bytes':sum(r['bytes'] for r in results)}))

if __name__=='__main__':main()
