from pathlib import Path
from collections import deque
import argparse, struct, shutil, json, hashlib, zipfile, difflib, subprocess, os

root = Path(__file__).resolve().parent
project = root.parent.parent
parser = argparse.ArgumentParser(description='Package the Windows UCRT64 AirPlay receiver and its dependencies.')
for argument in ('prefix','build','source','archive','output'):
    parser.add_argument('--'+argument,type=Path)
args = parser.parse_args()
prefix = (args.prefix or root / 'msys64/ucrt64').resolve()
output = (args.output or project / 'outputs/island-windows/receiver').resolve()
source = (args.source or root / 'UxPlay-3dbf7ceee65932154e85a2f83963d53520a799fa').resolve()
build = (args.build or root / 'build-ucrt64').resolve()
archive_path = (args.archive or root / 'uxplay-windows-source.zip').resolve()
output.mkdir(parents=True, exist_ok=True)

def imports(path):
    data = path.read_bytes()
    nt = struct.unpack_from('<I', data, 0x3c)[0]
    if data[nt:nt+4] != b'PE\0\0': raise RuntimeError(f'Not PE: {path}')
    sections, opts = struct.unpack_from('<H',data,nt+6)[0], struct.unpack_from('<H',data,nt+20)[0]
    opt = nt+24
    dd = opt + (112 if struct.unpack_from('<H',data,opt)[0] == 0x20b else 96)
    rva = struct.unpack_from('<I',data,dd+8)[0]
    ranges=[]
    for i in range(sections):
        entry = opt+opts+40*i
        size, va, raw_size, raw = struct.unpack_from('<IIII',data,entry+8)
        ranges.append((va, max(size,raw_size), raw))
    def offset(rva):
        for va,size,raw in ranges:
            if va <= rva < va+size: return raw+rva-va
        if rva < len(data): return rva
        raise RuntimeError('Bad RVA')
    if not rva: return []
    pos=offset(rva); names=[]
    while any(data[pos:pos+20]):
        name_rva=struct.unpack_from('<I',data,pos+12)[0]
        at=offset(name_rva); end=data.index(b'\0',at)
        names.append(data[at:end].decode('ascii'));pos+=20
    return names

plugins = ['coreelements','app','audioconvert','audioresample','audioparsers','typefindfunctions','playback','libav',
           'videoparsersbad','videoconvertscale','d3d11','wasapi','wasapi2','autodetect','volume','videofilter',
           'jpeg','png','imagefreeze','pango','cairo','hls','adaptivedemux2','soup','isomp4','mpegtsdemux',
           'videorate','audiorate','deinterlace','audiofx','id3demux','audiotestsrc','videotestsrc','wavparse','level']
queue=deque()
def seed(path, destination):
    if not path.exists(): raise RuntimeError(f'Missing seed: {path}')
    destination.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,destination)
    queue.append(path)
seed(build/'uxplay.exe',output/'bin/uxplay.exe')
for exe in ['gst-inspect-1.0.exe','gst-launch-1.0.exe','gio-querymodules.exe']:
    seed(prefix/'bin'/exe,output/'bin'/exe)
for plugin in plugins:
    seed(prefix/f'lib/gstreamer-1.0/libgst{plugin}.dll',output/f'lib/gstreamer-1.0/libgst{plugin}.dll')
seed(prefix/'libexec/gstreamer-1.0/gst-plugin-scanner.exe',output/'libexec/gstreamer-1.0/gst-plugin-scanner.exe')
seed(prefix/'lib/gio/modules/libgiognutls.dll',output/'lib/gio/modules/libgiognutls.dll')
available={p.name.lower():p for p in (prefix/'bin').glob('*.dll')}
system = Path('C:/Windows/System32')
seen=set(); missing=set(); system_imports=set()
while queue:
    path=queue.popleft()
    key=path.name.lower()
    if key in seen: continue
    seen.add(key)
    for name in imports(path):
        dependency=available.get(name.lower())
        if dependency:
            if dependency.name.lower() not in seen: seed(dependency,output/'bin'/dependency.name)
        elif (system/name).exists() or name.lower().startswith(('api-ms-','ext-ms-')):
            system_imports.add(name)
        else: missing.add(name)
if missing: raise RuntimeError(f'Unresolved imports: {sorted(missing)}')
# Generate the GIO cache with its own tool. Hand-written CRLF cache entries on
# Windows leave a trailing CR on the extension name, silently selecting the
# dummy TLS backend even though the GnuTLS DLL is present.
cache_env=dict(os.environ)
cache_env['PATH']=str(output/'bin')+';'+cache_env.get('PATH','')
subprocess.run([str(output/'bin/gio-querymodules.exe'),str(output/'lib/gio/modules')],
               env=cache_env,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
cache=(output/'lib/gio/modules/giomodule.cache').read_bytes()
if b'gio-tls-backend\n' not in cache or b'\r' in cache: raise RuntimeError('Invalid portable TLS module cache')
for directory in ['share/licenses','share/glib-2.0/schemas']:
    if (prefix/directory).exists(): shutil.copytree(prefix/directory,output/directory,dirs_exist_ok=True)
# These MSYS2 packages omit duplicate common license files. Bundle the complete
# applicable GNU texts explicitly as well as the package-specific notices above.
for component in ['gstreamer','libplist']:
    license_dir=output/'share/licenses'/component
    license_dir.mkdir(parents=True,exist_ok=True)
    shutil.copy2(prefix/'share/licenses/glib2/COPYING',license_dir/'COPYING-LGPL-2.1')
ffmpeg_license=output/'share/licenses/ffmpeg'
ffmpeg_license.mkdir(parents=True,exist_ok=True)
shutil.copy2(source/'LICENSE',ffmpeg_license/'COPYING-GPL-3.0')
cert = prefix/'etc/ssl/certs/ca-bundle.crt'
if cert.exists():
    (output/'etc/ssl/certs').mkdir(parents=True,exist_ok=True);shutil.copy2(cert,output/'etc/ssl/certs/ca-bundle.crt')
src_output=output/'source';src_output.mkdir(exist_ok=True)
if archive_path != (src_output/'uxplay-3dbf7ce-source.zip').resolve():
    shutil.copy2(archive_path,src_output/'uxplay-3dbf7ce-source.zip')
shutil.copy2(source/'LICENSE',output/'LICENSE-UxPlay')
changes=[]
with zipfile.ZipFile(archive_path) as archive:
    for name in ['uxplay.cpp','lib/raop_ntp.c','lib/httpd.c','renderers/video_renderer.c','renderers/video_renderer.h','island_bridge.h','island_player.h']:
        key=f'{source.name}/{name}'
        base=archive.read(key).decode('utf-8').splitlines(True) if key in archive.namelist() else []
        final=(source/name).read_text(encoding='utf-8').splitlines(True)
        changes.extend(difflib.unified_diff(base,final,fromfile='a/'+name if base else '/dev/null',tofile='b/'+name))
(src_output/'island-windows.patch').write_text(''.join(changes),encoding='utf-8',newline='\n')
files={str(p.relative_to(output)).replace('\\','/'):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in output.rglob('*') if p.is_file() and p.name!='manifest.json'}
version_env=dict(os.environ,PATH=str(prefix/'bin')+';'+os.environ.get('PATH',''))
gst_version=subprocess.check_output([str(prefix/'bin/gst-inspect-1.0.exe'),'--version'],env=version_env,text=True).splitlines()[0].rsplit(' ',1)[-1]
gcc_version=subprocess.check_output([str(prefix/'bin/gcc.exe'),'-dumpfullversion'],env=version_env,text=True).strip()
manifest={'uxplayRevision':'3dbf7ceee65932154e85a2f83963d53520a799fa','uxplayVersion':'1.74','gstreamerVersion':gst_version,'toolchain':'MSYS2 UCRT64 GCC '+gcc_version,'plugins':plugins,'systemImports':sorted(system_imports),'files':files,'totalBytes':sum(f['bytes'] for f in files.values())}
(output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'libraries':len(seen),'plugins':len(plugins),'files':len(files),'MiB':round(manifest['totalBytes']/2**20,1),'missingImports':sorted(missing)}))
