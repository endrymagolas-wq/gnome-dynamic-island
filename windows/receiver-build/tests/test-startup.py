"""Exercise real Windows HLS startup with Explorer-like locale environments."""
from pathlib import Path
import hashlib,json,os,subprocess,threading,time

root=Path(__file__).resolve().parent
package=root.parent.parent/'receiver'
binary=package/'bin/uxplay.exe'
checks=[]

def check(value,name):
    checks.append(dict(name=name,passed=bool(value)))
    if not value:raise AssertionError(name)

def run_case(name,locale):
    child=None;events=[];ready=threading.Event()
    config=root/'startup-fixture.cfg';config.write_text('# Isolated Windows startup fixture\n',encoding='utf-8')
    env=dict(os.environ)
    for variable in ('LANGUAGE','LANG','LC_ALL','LC_MESSAGES'):env.pop(variable,None)
    env.update(locale)
    env.update(PATH=str(package/'bin')+';'+env.get('PATH',''),
        GST_PLUGIN_SYSTEM_PATH=str(package/'lib/gstreamer-1.0'),GST_PLUGIN_PATH='',
        GST_PLUGIN_SCANNER=str(package/'libexec/gstreamer-1.0/gst-plugin-scanner.exe'),
        GST_REGISTRY=str(root/'startup-registry.bin'),
        GSETTINGS_SCHEMA_DIR=str(package/'share/glib-2.0/schemas'),
        GIO_MODULE_DIR=str(package/'lib/gio/modules'),
        SSL_CERT_FILE=str(package/'etc/ssl/certs/ca-bundle.crt'),ISLAND_EVENTS='1',
        ISLAND_HLS_AUDIO_SINK='fakesink')
    try:
        child=subprocess.Popen([str(binary),'-n','Island Startup Test','-nh','-p','17600',
            '-m','02:00:00:00:76:00','-as','fakesink','-vs','fakesink','-nofreeze',
            '-hls','2','-lang','uk:en','-rc',str(config)],env=env,cwd=root,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
        def read():
            for line in child.stdout:
                if line.startswith('@island '):
                    event=json.loads(line[8:]);events.append(event)
                    if event.get('event')=='ready':ready.set()
        reader=threading.Thread(target=read,daemon=True);reader.start()
        check(ready.wait(8),name+': HLS receiver reaches ready')
        time.sleep(3)
        check(child.poll() is None,name+': stays running after startup')
        child.stdin.write('quit\n');child.stdin.flush()
        child.wait(timeout=5);reader.join(timeout=1)
        check(child.returncode==0,name+': exits cleanly on quit')
    finally:
        if child is not None:
            if child.poll() is None:child.kill();child.wait(timeout=5)
            for stream in (child.stdin,child.stdout):
                if stream:stream.close()

try:
    run_case('No POSIX locale variables',{})
    run_case('Empty POSIX locale variables',{key:'' for key in ('LANGUAGE','LANG','LC_ALL','LC_MESSAGES')})
    run_case('Explicit POSIX language preference',{'LANGUAGE':'uk:en','LANG':'en_GB.UTF-8'})
finally:
    report=dict(passed=sum(c['passed'] for c in checks),failed=sum(not c['passed'] for c in checks),
        tests=checks,binarySha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
        scope='Fresh packaged Windows native HLS startup without, with empty, and with explicit POSIX locale variables; actual receiver main loop and graceful stdin stop.')
    (root/'startup-tests.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
