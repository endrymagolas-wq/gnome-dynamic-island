from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
import http.client, json, os, plistlib, socket, subprocess, sys, threading, time

root = Path(__file__).resolve().parent
package = root.parent.parent / 'receiver'
requests = []
events = []
logs = []
checks = []
relay = '--relay' in sys.argv
https = '--https' in sys.argv

class MediaHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        requests.append(self.path)

def check(value, name):
    checks.append(dict(name=name, passed=bool(value)))
    if not value:
        raise AssertionError(name)

def read_output(child):
    for line in child.stdout:
        logs.append(line)
        if line.startswith('@island '):
            events.append(json.loads(line[8:]))

def wait_for(predicate, timeout=12):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        result = predicate()
        if result:
            return result
        time.sleep(.2)
    return None

def frame(stream):
    first=stream.readline()
    headers={}
    while True:
        row=stream.readline()
        if row in (b'\r\n',b'\n',b''): break
        key,value=row.decode().split(':',1);headers[key.lower()]=value.strip()
    body=stream.read(int(headers.get('content-length','0')))
    return first,body

def main():
    child = control = server = reverse = None
    env = dict(os.environ)
    env.update(PATH=str(package/'bin')+';'+env.get('PATH',''),
               GST_PLUGIN_SYSTEM_PATH=str(package/'lib/gstreamer-1.0'), GST_PLUGIN_PATH='',
               GST_PLUGIN_SCANNER=str(package/'libexec/gstreamer-1.0/gst-plugin-scanner.exe'),
               GST_REGISTRY=str(root/'hls-registry.bin'),
               GSETTINGS_SCHEMA_DIR=str(package/'share/glib-2.0/schemas'),
               GIO_MODULE_DIR=str(package/'lib/gio/modules'),
               SSL_CERT_FILE=str(package/'etc/ssl/certs/ca-bundle.crt'), ISLAND_EVENTS='1')
    env['ISLAND_HLS_AUDIO_SINK']='wasapisink' if '--visual' in sys.argv else 'fakesink'
    try:
        server = ThreadingHTTPServer(('127.0.0.1',0),partial(MediaHandler,directory=str(root/'hls-fixture')))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        config=root/'hls-fixture.cfg';config.write_text('# Isolated HLS fixture\n')
        binary=package/'bin/uxplay.exe'
        child=subprocess.Popen([str(binary),'-n','Island HLS Fixture','-nh',
            '-p','17500','-m','02:00:00:00:75:00','-avdec','-as','fakesink','-vs',
            'd3d11videosink fullscreen-toggle-mode=6 fullscreen=false force-aspect-ratio=true' if '--visual' in sys.argv else 'fakesink sync=true',
            '-nofreeze','-hls','2','-rc',str(config)],env=env,cwd=root,stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',
            errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
        threading.Thread(target=read_output,args=(child,),daemon=True).start()
        check(wait_for(lambda:any(e.get('event')=='ready' for e in events)), 'Isolated HLS receiver starts')
        control=http.client.HTTPConnection('127.0.0.1',17501,timeout=3)
        headers={'X-Apple-Session-ID':'island-hls-fixture','Content-Type':'application/x-apple-binary-plist'}
        if relay:
            reverse=socket.create_connection(('127.0.0.1',17501),timeout=4)
            stream=reverse.makefile('rb')
            reverse.sendall(b'POST /reverse HTTP/1.1\r\nX-Apple-Session-ID: island-hls-fixture\r\nX-Apple-Purpose: event\r\nConnection: Upgrade\r\nUpgrade: PTTH/1.0\r\nContent-Length: 0\r\n\r\n')
            first,_=frame(stream)
            check(b'101' in first,'YouTube-style reverse HTTP channel is upgraded')
        body=plistlib.dumps({'uuid':'island-hls-fixture-video',
            'Content-Location':'mlhls://fixture/master.m3u8' if relay else 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_ts/master.m3u8' if https else f'http://127.0.0.1:{server.server_port}/video.m3u8',
            'Start-Position-Seconds':0.0},fmt=plistlib.FMT_BINARY)
        control.request('POST','/play',body,headers)
        response=control.getresponse()
        # AirPlay's empty control replies omit Content-Length and keep the
        # connection open. Do not wait for EOF as a generic HTTP client would.
        response.read(int(response.getheader('Content-Length','0')))
        check(response.status==200,'Binary-plist video-output request is accepted')
        if relay:
            master=b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1200000,CODECS="avc1.42c01e,mp4a.40.2",RESOLUTION=640x360\nmlhls://fixture/variant.m3u8\n'
            media=(root/'hls-fixture/video.m3u8').read_text()
            media='\n'.join(f'http://127.0.0.1:{server.server_port}/'+line if line.endswith('.ts') else line for line in media.splitlines())+'\n'
            for expected,data in [('mlhls://fixture/master.m3u8',master),('mlhls://fixture/variant.m3u8',media.encode())]:
                first,payload=frame(stream)
                check(first.startswith(b'POST /event '),'Reverse channel delivers an FCUP event')
                request=plistlib.loads(payload)['request']
                check(request['FCUP_Response_URL']==expected,'Native FCUP request selects '+expected.rsplit('/',1)[-1])
                reverse.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n')
                body=plistlib.dumps({'type':'unhandledURLResponse','params':{
                    'FCUP_Response_URL':expected,'FCUP_Response_StatusCode':200,
                    'FCUP_Response_RequestID':request['FCUP_Response_RequestID'],
                    'FCUP_Response_Data':data}},fmt=plistlib.FMT_BINARY)
                control.request('POST','/action',body,headers)
                response=control.getresponse();response.read(int(response.getheader('Content-Length','0')))
                check(response.status==200,'Native receiver accepts relayed '+expected.rsplit('/',1)[-1])
        check(wait_for(lambda:any(e.get('event')=='stream' and e.get('kind')=='video' for e in events)),
              'Request reaches actual HLS renderer callback')
        positions=[]
        def playback():
            control.request('GET','/playback-info',headers={'X-Apple-Session-ID':'island-hls-fixture'})
            response=control.getresponse();data=response.read(int(response.getheader('Content-Length','0')))
            if response.status==200 and data:
                info=plistlib.loads(data);positions.append(info)
                return info if info.get('position',-1)>2 else None
            return None
        info=wait_for(playback,15)
        if not https:
            check(any(e.get('stage')=='hls-playlist-request' for e in events) if relay else any(path.endswith('.m3u8') for path in requests),'Player fetches the HLS playlist')
            check(any(path.endswith('.ts') for path in requests),'Player downloads HLS media segments')
        check(info and info.get('rate')==1 and info.get('duration',0)>20,
              'Actual decoded HLS playback advances beyond two seconds')
        if '--controls' in sys.argv:
            def send(command):child.stdin.write(command+'\n');child.stdin.flush()
            def sample():
                control.request('GET','/playback-info',headers={'X-Apple-Session-ID':'island-hls-fixture'})
                response=control.getresponse();data=response.read(int(response.getheader('Content-Length','0')))
                info=plistlib.loads(data) if data else {}
                positions.append(info)
                return info
            def paused():
                info=sample();return info if info.get('rate')==0 and info.get('duration',0)>20 else None
            send('media-pause');paused_info=wait_for(paused,4)
            check(paused_info,'Local pause changes actual GStreamer rate')
            time.sleep(.6)
            check(abs(sample()['position']-paused_info['position'])<.25,'Paused decoded video position remains stable')
            send('media-seek 12.0')
            check(wait_for(lambda:abs(sample().get('position',0)-12)<1,4),'Local seek moves actual decoded playback to twelve seconds')
            send('media-play')
            check(wait_for(lambda:sample().get('rate')==1,4),'Local play resumes actual GStreamer playback')
            check(wait_for(lambda:sample().get('position',0)>13,4),'Resumed decoded video advances beyond the seek position')
            send('video-buffer 2')
            check(wait_for(lambda:any(e.get('event')=='video-state' and e.get('bufferSeconds')==2 for e in events),4),
                  'Buffer control changes the actual pipeline buffer duration')
            if '--visual' in sys.argv:
                first=len(events);send('video-window 1 1')
                check(wait_for(lambda:any(e.get('event')=='video-state' and e.get('window') and e.get('fullscreen') and e.get('keepAspect') for e in events[first:]),4),
                      'D3D11 fullscreen and preserved aspect ratio are applied to the actual video sink')
                first=len(events);send('video-window 0 0')
                check(wait_for(lambda:any(e.get('event')=='video-state' and e.get('window') and not e.get('fullscreen') and not e.get('keepAspect') for e in events[first:]),4),
                      'D3D11 returns to a window and applies stretch scaling')
                send('video-window 0 1')
    except Exception as error:
        checks.append(dict(name=type(error).__name__+': '+str(error),passed=False))
    finally:
        if control: control.close()
        if reverse: reverse.close()
        if child and child.poll() is None:
            try:
                child.stdin.write('quit\n');child.stdin.flush();child.wait(timeout=5)
            except Exception:
                child.kill();child.wait()
        if server: server.shutdown();server.server_close()
        report=dict(passed=sum(c['passed'] for c in checks),failed=sum(not c['passed'] for c in checks),
            tests=checks,stages=[e for e in events if e.get('event')=='phase'],requests=requests,
            playback=positions if 'positions' in locals() else [],
            scope='Independent local HLS output request and real GStreamer decoding. No phone or physical video proof.')
        label='hls-relay' if relay else 'hls-https' if https else 'hls'
        (root/(label+'-tests.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
        (root/(label+'-fixture.log')).write_text(''.join(logs),encoding='utf-8')
        print(json.dumps(dict(passed=report['passed'],failed=report['failed'],
            failures=[c['name'] for c in checks if not c['passed']])))
    return 1 if any(not c['passed'] for c in checks) else 0

raise SystemExit(main())
