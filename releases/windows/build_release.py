"""Build explicit portable Windows components from a reviewed source snapshot.

No live install is modified. All binary/data copies are allowlisted. Rebuild into
a fresh --out directory; this script refuses to replace an existing component.
"""
import argparse, hashlib, json, shutil, zipfile
from pathlib import Path

VERSION='0.4.0-beta.1'
TAG='windows-v'+VERSION
ARCHIVES={
 'island':('IslandDesktop-Windows',f'island-desktop-windows-{VERSION}.zip'),
 'airplay':('Cortiva-AirPlay-Windows',f'cortiva-airplay-windows-{VERSION}.zip'),
 'wallpaper':('FairyLagoon-V7-Windows','fairy-lagoon-v7-wallpaper-windows.zip'),
 'full':('IslandDesktop-Windows-Full',f'island-desktop-windows-full-{VERSION}.zip'),
 'blender':('FairyLagoon-V7-Blender','fairy-lagoon-v7-blender-sources.zip'),
}
WALLPAPER_FILES=('index.html','player.js','scene-model.js','resort-life.js','lighting-model.js','lighting-runtime.js','server.py','bootstrap.html','emit.py','LivelyInfo.json','LivelyProperties.json','sync-properties.ps1')
ASSET_FILES=('scene.json','static.png','poster.png','depth.png','character.png','character-depth.png','ambient.png','ambient-depth.png','life.png','life-depth.png','smoke.png','construction-depth.png','water-1080.mp4','water-720.mp4')
PHASE_FILES=('static.png','poster.png','character.png','ambient.png','life.png','smoke.png','water-1080.mp4','water-720.mp4')
SCRIPT_FILES=('Release-Common.ps1','Start-Wallpaper.ps1','Restore-Wallpaper.ps1','start-desktop.ps1','Stop-Desktop.ps1','Start-AirPlay.ps1','Enable-AirPlay-Firewall.ps1')
DENIED_PARTS={'__pycache__','.git','obj','.pytest_cache','verification','qa','state','logs'}
DENIED_NAMES={'connection.json','events.json','settings.json','pin.txt','paired-devices.txt','receiver-key.pem','identity.txt','remote.txt','coverart.bin','registry-1.28.bin'}

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()

def copy(src,dst):
    assert src.is_file(),f'Missing input: {src}'
    if src.suffix.lower() in ('.pdb','.pyc','.log') or src.name.lower() in DENIED_NAMES: raise ValueError(f'Private/debug file: {src.name}')
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)

def tree(src,dst,filter_fn=lambda p:True):
    assert src.is_dir(),f'Missing input directory: {src}'
    for p in sorted(src.rglob('*')):
        if p.is_file() and not any(a.lower() in DENIED_PARTS for a in p.relative_to(src).parts) and p.suffix.lower() not in ('.pdb','.pyc','.log') and p.name.lower() not in DENIED_NAMES and filter_fn(p):copy(p,dst/p.relative_to(src))

def unzip(src,dst):
    with zipfile.ZipFile(src) as z:
        for info in z.infolist():
            path=Path(info.filename)
            if path.is_absolute() or '..' in path.parts or ':' in info.filename:raise ValueError('Unsafe dependency archive path')
            if not info.is_dir():
                dest=dst/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(info))

def cmd(dst,name,script):
    dst.joinpath(name).write_text('@echo off\r\npowershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0'+script+'" %*\r\nif errorlevel 1 (echo. & echo Startup failed. Review the message above. & pause)\r\n',encoding='ascii',newline='')

def notices(source,dst):
    copy(source/'LICENSE',dst/'LICENSE')
    copy(source/'THIRD_PARTY_NOTICES.md',dst/'THIRD_PARTY_NOTICES.md')
    copy(source/'windows/THIRD_PARTY_NOTICES.md',dst/'WINDOWS_THIRD_PARTY_NOTICES.md')
    copy(source/'windows/NAudio-LICENSE.txt',dst/'licenses/NAudio-LICENSE.txt')
    tree(source/'LICENSES',dst/'LICENSES')
    if (source/'windows/licenses').exists():tree(source/'windows/licenses',dst/'licenses')
    for name in ('INSTALL_WINDOWS.md','AIRPLAY_WINDOWS.md','WALLPAPER_V7.md','WINDOWS_RELEASE.md','RELEASE_VALIDATION.md','FEATURE_INVENTORY.md'):
        if (source/'docs'/name).is_file():
            copy(source/'docs'/name,dst/'docs'/name)
            guide=dst/'docs'/name
            guide.write_text(guide.read_text(encoding='utf-8').replace('../windows/README.md','https://github.com/endrymagolas-wq/gnome-dynamic-island/blob/'+TAG+'/windows/README.md').replace('../README.md','https://github.com/endrymagolas-wq/gnome-dynamic-island/blob/'+TAG+'/README.md'),encoding='utf-8')

def scripts(source,dst,names):
    for name in names:copy(source/'releases/windows'/name,dst/name)

def island(source,dst):
    copy(source/'windows/IslandDesktop.exe',dst/'IslandDesktop.exe')
    tree(source/'windows/app',dst/'app');tree(source/'windows/runtime',dst/'runtime')
    for file in ('control.ps1','start.ps1','stop.ps1'):copy(source/'windows'/file,dst/file)
    scripts(source,dst,('Release-Common.ps1','start-desktop.ps1','Stop-Desktop.ps1'))
    cmd(dst,'Start-Desktop.cmd','start-desktop.ps1');cmd(dst,'Stop-Desktop.cmd','Stop-Desktop.ps1')

def receiver(source,native,dst):
    inventory=json.loads((native/'manifest.json').read_text())
    for name,record in inventory['files'].items():
        p=native/name
        assert p.is_file() and p.stat().st_size==record['bytes'] and sha(p)==record['sha256'],f'Native dependency differs from receiver manifest: {name}'
    for folder in ('bin','etc','lib','libexec','share','source'):tree(native/folder,dst/'receiver'/folder)
    for name in ('LICENSE-UxPlay','manifest.json'):copy(native/name,dst/'receiver'/name)
    tree(source/'windows/receiver-build',dst/'receiver-build',lambda p:'tests' not in p.parts)
    scripts(source,dst,('Start-AirPlay.ps1','Enable-AirPlay-Firewall.ps1'))
    cmd(dst,'Start-AirPlay.cmd','Start-AirPlay.ps1')
    cmd(dst,'Enable-AirPlay-Firewall.cmd','Enable-AirPlay-Firewall.ps1')

def dependencies(deps,dst):
    manifest=json.loads((deps/'dependencies.json').read_text())
    for item in manifest['downloads']:
        file=deps/item['file'];assert file.is_file() and sha(file)==item['sha256'],f'Dependency changed: {file.name}'
    unzip(deps/'python-3.13.14-embed-amd64.zip',dst/'python')
    (dst/'python/python313._pth').write_text('python313.zip\n.\nLib/site-packages\nimport site\n',encoding='ascii')
    wheel=next(p for p in deps.glob('psutil-7.2.2-*-win_amd64.whl'))
    unzip(wheel,dst/'python/Lib/site-packages')
    unzip(deps/'lively_command_utility.zip',dst/'tools/lively-cli')
    copy(deps/'Lively-GPL-3.0.txt',dst/'licenses/Lively-GPL-3.0.txt')
    copy(deps/'lively-v2.0.4.0-source.zip',dst/'licenses/sources/lively-v2.0.4.0-source.zip')
    copy(deps/'psutil-7.2.2.tar.gz',dst/'licenses/sources/psutil-7.2.2.tar.gz')
    copy(deps/'dependencies.json',dst/'dependency-downloads.json')
    (dst/'licenses/PORTABLE_RUNTIMES.md').write_text('''# Portable runtimes\n\nPython 3.13.14 Windows embeddable x64 is redistributed with its PSF LICENSE.txt\nin python/. Exact download and hashes: dependency-downloads.json.\nCorresponding Python source: https://www.python.org/ftp/python/3.13.14/Python-3.13.14.tar.xz\nPython release: https://www.python.org/downloads/release/python-31314/\n\npsutil 7.2.2 is BSD-3-Clause. Its license is in\npython/Lib/site-packages/psutil-7.2.2.dist-info/LICENSE; original source\nis retained in licenses/sources/psutil-7.2.2.tar.gz.\n\nLively CLI 2.0.4.0 is GPL-3.0; license and exact tagged corresponding source\nare retained in licenses/. Lively Wallpaper itself is installed separately:\nhttps://www.rocksdanister.com/lively/ . No Lively installer is run by this package.\n''',encoding='utf-8')

def art_notices(source,dst):
    copy(source/'art/ASSET_SOURCES.md',dst/'licenses/ASSET_SOURCES.md')
    for p in (source/'art/thirdparty').rglob('*'):
        if p.is_file() and ('license' in p.name.lower() or p.name.lower()=='readme.md'):copy(p,dst/'licenses/art'/p.relative_to(source/'art/thirdparty'))

def wallpaper(source,deps,dst):
    metadata=json.loads((source/'wallpaper/assets/scene.json').read_text())
    assert metadata['ground']['ellipse']==[7.2,5.5] and metadata['effects']=={'construction':False,'smoke':False},'Wrong/rejected scene selected'
    for file in WALLPAPER_FILES:copy(source/'wallpaper'/file,dst/'wallpaper'/file)
    for file in ASSET_FILES:copy(source/'wallpaper/assets'/file,dst/'wallpaper/assets'/file)
    for phase in ('morning','evening','night'):
        for file in PHASE_FILES:copy(source/'wallpaper/assets/phases'/phase/file,dst/'wallpaper/assets/phases'/phase/file)
    copy(source/'assistant/claude_hook.py',dst/'assistant/claude_hook.py')
    info=json.loads((dst/'wallpaper/LivelyInfo.json').read_text(encoding='utf-8-sig'))
    info['Title']='Fairy Lagoon V7 · three residents'
    info['Desc']='Expanded tropical island with three personal nooks, tea, resting and app-state reactions. Four lighting phases and rendered 3D water. See included asset credits.'
    (dst/'wallpaper/LivelyInfo.json').write_text(json.dumps(info,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    dependencies(deps,dst);art_notices(source,dst)
    scripts(source,dst,('Release-Common.ps1','Start-Wallpaper.ps1','Restore-Wallpaper.ps1'))
    cmd(dst,'Start-Wallpaper.cmd','Start-Wallpaper.ps1');cmd(dst,'Restore-Wallpaper.cmd','Restore-Wallpaper.ps1')

def blender(source,dst):
    copy(source/'releases/windows/BLENDER_PRIVACY_INTEGRITY_PUBLIC.json',dst/'BLENDER_SOURCE_INTEGRITY.json')
    for name in ('resort-v6.blend','resort-v7.blend','resort-v7-actions.blend'):copy(source/'art/island'/name,dst/'art/island'/name)
    tree(source/'art/island',dst/'art/island',lambda p:p.suffix=='.py')
    for name in ('build_resort_v7.py','build_resort_v7_organic.py','bake_resort_v7_activities.py','render_resort_v7.py','render_resort_v7_alpha.py','probe_resort_v7_ground.py','package_resort_v7.py'):
        copy(source/'tools'/name,dst/'tools'/name)
    copy(source/'wallpaper/assets/scene.json',dst/'wallpaper/assets/scene.json')
    tree(source/'art/thirdparty',dst/'art/thirdparty');art_notices(source,dst)
    (dst/'EDITABLE.md').write_text('''# Editable Fairy Lagoon V7\n\nOpen art/island/resort-v7.blend in Blender 4.5 LTS. The enlarged beach,\nthree scattered personal nooks and furniture are editable 3D objects.\nImages used by the scene are packed in the file; it requires no private cache.\nThe accepted camera is retained for alignment with the video water.\n\nresort-v7-actions.blend contains the rig, tea and lying/scratch actions.\nresort-v6.blend is the base used by tools/build_resort_v7_organic.py.\nRun rebuild scripts from this extracted project root into a NEW output folder.\nRendering requires Blender 4.5 LTS; packaging rendered layers requires Pillow.\nThe complete published repository includes runtime tests and the retained water.\nAsset provenance and licenses are in licenses/ASSET_SOURCES.md and art/thirdparty/.\n''',encoding='utf-8')

def readme(dst,component):
    common='''Requires Windows x64 (Windows 10 build 19041+ / Windows 11). Extract the WHOLE\nZIP to a writable folder and keep its subfolders together. Run launchers as a\nnormal user; firewall setup is a separate optional administrator action.\nNo installed app pins, credentials, pairing keys, personal screenshots or settings\nare included. Settings are generated in your LOCALAPPDATA at first use.\n\nSource: https://github.com/endrymagolas-wq/gnome-dynamic-island/tree/windows-v0.4.0-beta.1\nLicenses retain their own terms; see THIRD_PARTY_NOTICES.md and licenses/.\n'''
    texts={
     'island':'''Run IslandDesktop.exe (or Start-Desktop.cmd). .NET is bundled.\nThe island, native media controls, top navigation, dock and tray are included.\nAirPlay and the Lively wallpaper are separate optional downloads. To add\nAirPlay, copy the complete receiver/ folder from Cortiva-AirPlay-Windows into\nthis folder, then use the island's AirPlay controls. Do not simultaneously run\nStart-AirPlay.cmd. Stop-Desktop.cmd closes this package and restores the taskbar.\n''',
     'airplay':'''Run Start-AirPlay.cmd. A console shows your locally generated four-digit\nPIN. Select Cortiva Island in AirPlay on a phone/Mac in the same local network.\nThe console must remain open; closing it terminates the receiver. No island\nGUI is provided in this standalone component. Native runtime and exact\nUxPlay source/patch/build recipe are included. No .NET/Python/Lively install\nis needed. Enable-AirPlay-Firewall.ps1 can be run explicitly as administrator\nif required; -Remove reverses only this folder's LocalSubnet rules.\nDo not start it while another island/standalone receiver is listening.\nYouTube AirPlay works for compatible non-DRM streams; Google Cast is not provided.\n''',
     'wallpaper':'''Install the free official Lively Wallpaper application first:\nhttps://www.rocksdanister.com/lively/ . Then run Start-Wallpaper.cmd.\nPython, psutil and the Lively command utility are bundled. The launcher starts\nthe loopback-only local host, registers Fairy Lagoon V7 and activates it.\nOptional Claude Code hooks: powershell -NoProfile -ExecutionPolicy Bypass\n-File .\\Start-Wallpaper.ps1 -InstallHooks (only if you choose this integration).\nRestore-Wallpaper.cmd closes this package's active wallpaper and owned host,\nand restores its previously recorded Lively entry or Windows ordinary wallpaper.\nIt leaves wallpapers changed later by you alone. Port 18765 must be available;\nthe launcher refuses to replace an unrelated host.\n''',
     'full':'''Install the free official Lively Wallpaper application first:\nhttps://www.rocksdanister.com/lively/ . Run Start-Desktop.cmd for the full set.\nThe island, dock/media, AirPlay receiver, rendered V7 wallpaper, portable .NET,\nPython, psutil and Lively command utility are included. Lively itself is external.\nThe island owns the receiver; do not run Start-AirPlay.cmd concurrently.\nPIN and AirPlay media controls are shown in the island. The standalone console\nlauncher is provided only for use while island AirPlay is disabled/stopped.\nStop-Desktop.cmd closes the island from this package, restores its taskbar,\ncloses the owned host and restores its previous Lively wallpaper.\nRestore-Wallpaper.cmd can restore only the wallpaper while leaving the island.\nOptional Claude Code hooks: powershell -NoProfile -ExecutionPolicy Bypass\n-File .\\start-desktop.ps1 -InstallHooks . No hooks or firewall rules are changed\nwithout running those explicit options/scripts.\nThe editable Blender source is a separate download.\n''',
     'blender':'''See EDITABLE.md. This is the editable accepted organic V7 scene/actions,\nV6 base, build/render scripts and asset provenance. Blender is external.\nIt is separate from the full Windows runtime download.\n''',
    }
    (dst/'START_HERE.txt').write_text('Island Desktop / Fairy Lagoon '+VERSION+'\n\n'+texts[component]+'\n'+common,encoding='utf-8')

def package_manifest(dst,component):
    info={'version':VERSION,'tag':TAG,'component':component,'packageId':'island-'+VERSION+'-'+component,'architecture':'win-x64','source':'https://github.com/endrymagolas-wq/gnome-dynamic-island/tree/'+TAG}
    (dst/'release.json').write_text(json.dumps(info,indent=2)+'\n')
    if (dst/'wallpaper').exists():(dst/'wallpaper/release.json').write_text(json.dumps(info,indent=2)+'\n')
    files={p.relative_to(dst).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(dst.rglob('*')) if p.is_file() and p.name!='package-manifest.json' and not any(a.lower() in DENIED_PARTS for a in p.relative_to(dst).parts) and p.suffix.lower() not in ('.pdb','.pyc','.log')}
    (dst/'package-manifest.json').write_text(json.dumps({'release':info,'files':files},indent=2)+'\n')

def archive(stage,dest):
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(stage.rglob('*')):
            if p.is_file() and not any(a.lower() in DENIED_PARTS for a in p.relative_to(stage).parts) and p.suffix.lower() not in ('.pdb','.pyc','.log') and p.name.lower() not in DENIED_NAMES:
                info=zipfile.ZipInfo((Path(stage.name)/p.relative_to(stage)).as_posix(),date_time=(2026,10,8,0,0,0))
                # PNG/MP4/source ZIPs are already compressed. Store them intact;
                # compress native/runtime binaries and text with a bounded CPU cost.
                info.compress_type=zipfile.ZIP_STORED if p.suffix.lower() in ('.png','.jpg','.mp4','.zip','.whl','.gz','.xz','.zst') else zipfile.ZIP_DEFLATED
                info.compress_level=1;info.external_attr=0o644<<16
                with p.open('rb') as src,z.open(info,'w') as out:shutil.copyfileobj(src,out,1024*1024)

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--receiver',type=Path,required=True);p.add_argument('--dependencies',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--components',nargs='+',choices=ARCHIVES,default=list(ARCHIVES));p.add_argument('--stage-only',action='store_true');args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True);results=[]
    for component in args.components:
        folder,zipname=ARCHIVES[component];dst=args.out/folder
        if dst.exists():raise FileExistsError(f'Preserve existing package stage: {dst}')
        dst.mkdir();notices(args.source,dst)
        if component in ('island','full'):island(args.source,dst)
        if component in ('airplay','full'):receiver(args.source,args.receiver,dst)
        if component in ('wallpaper','full'):wallpaper(args.source,args.dependencies,dst)
        if component=='blender':blender(args.source,dst)
        readme(dst,component);package_manifest(dst,component)
        result={'component':component,'folder':dst.name,'archive':zipname,'uncompressedBytes':sum(x.stat().st_size for x in dst.rglob('*') if x.is_file())}
        if not args.stage_only:
            output=args.out/zipname;archive(dst,output);result.update(bytes=output.stat().st_size,sha256=sha(output))
        results.append(result);print(json.dumps(result),flush=True)
    (args.out/'release-components.json').write_text(json.dumps({'version':VERSION,'tag':TAG,'components':results},indent=2)+'\n')
    if not args.stage_only:(args.out/'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['archive']}\n" for r in results),encoding='ascii')

if __name__=='__main__':main()
