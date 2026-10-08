"""Refresh reviewed portable stages, remove only test caches, then hash/ZIP."""
import argparse, json, shutil
from pathlib import Path
import build_release as b

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--components',nargs='+',choices=b.ARCHIVES,default=list(b.ARCHIVES));p.add_argument('--stage-only',action='store_true');p.add_argument('--scripts-only',action='store_true');a=p.parse_args();results=[]
    for component in a.components:
        name,zipname=b.ARCHIVES[component];dst=(a.out/name).resolve();assert dst.is_relative_to(a.out.resolve()) and dst.name==name and dst.is_dir()
        for file in sorted(dst.rglob('*'),reverse=True):
            if file.is_file() and (file.suffix in ('.pyc','.pdb','.log') or '__pycache__' in file.relative_to(dst).parts):file.unlink()
            elif file.is_dir() and file.name=='__pycache__' and not any(file.iterdir()):file.rmdir()
        b.notices(a.source,dst);b.readme(dst,component)
        if component in ('island','full'):
            b.scripts(a.source,dst,('Release-Common.ps1','start-desktop.ps1','Stop-Desktop.ps1'))
            b.copy(a.source/'windows/stop.ps1',dst/'stop.ps1')
            if not a.scripts_only:
                b.copy(a.source/'windows/IslandDesktop.exe',dst/'IslandDesktop.exe');b.tree(a.source/'windows/app',dst/'app')
        if component in ('wallpaper','full'):
            b.scripts(a.source,dst,('Release-Common.ps1','Start-Wallpaper.ps1','Restore-Wallpaper.ps1'))
            portable=dst/'licenses/PORTABLE_RUNTIMES.md'
            portable.write_text(portable.read_text().replace('psutil-7.2.2.dist-info/licenses/LICENSE','psutil-7.2.2.dist-info/LICENSE'))
        if component in ('airplay','full'):
            b.scripts(a.source,dst,('Start-AirPlay.ps1','Enable-AirPlay-Firewall.ps1'))
            if not a.scripts_only:b.receiver(a.source,a.source/'windows/receiver',dst)
        if component=='blender' and not a.scripts_only:b.blender(a.source,dst)
        b.package_manifest(dst,component)
        result={'component':component,'folder':dst.name,'archive':zipname,'uncompressedBytes':sum(x.stat().st_size for x in dst.rglob('*') if x.is_file())}
        if not a.stage_only:
            dest=a.out/zipname;b.archive(dst,dest);result.update(bytes=dest.stat().st_size,sha256=b.sha(dest))
        results.append(result);print(json.dumps(result),flush=True)
    (a.out/'release-components.json').write_text(json.dumps({'version':b.VERSION,'tag':b.TAG,'components':results},indent=2)+'\n')
    if not a.stage_only:(a.out/'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['archive']}\n" for r in results),encoding='ascii')

if __name__=='__main__':main()
