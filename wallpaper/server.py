"""Loopback-only Windows wallpaper host; no scene rendering or model inference."""
import argparse, ctypes, json, math, mimetypes, os, secrets, threading, time
from ctypes import wintypes
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'assistant'))
from claude_hook import state_for
STATES={'starting','editing','testing','failed','permission','done','working','browsing','idle'}
DATA=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'ResortIsland'
DATA.mkdir(parents=True,exist_ok=True)
LOCK=threading.Lock()
CURRENT={'state':'idle','source':'desktop','seq':0,'until':0,'paused':False}
BENCH={}

def publish(state, source='claude', now=None):
    if state not in STATES:return False
    now=time.time() if now is None else now
    with LOCK:
        if source=='desktop' and CURRENT['until']>now:return False
        CURRENT.update(state=state,source=source,seq=CURRENT['seq']+1,until=now+(20 if state=='done' else 180) if source=='claude' else 0)
    return True

def covered(region,windows):
    remaining=[region]
    for w in windows:
        next_regions=[]
        for r in remaining:
            x=max(r[0],w[0]);y=max(r[1],w[1]);right=min(r[2],w[2]);bottom=min(r[3],w[3])
            if x>=right or y>=bottom:next_regions.append(r);continue
            if r[1]<y:next_regions.append((r[0],r[1],r[2],y))
            if bottom<r[3]:next_regions.append((r[0],bottom,r[2],r[3]))
            if r[0]<x:next_regions.append((r[0],y,x,bottom))
            if right<r[2]:next_regions.append((right,y,r[2],bottom))
        remaining=next_regions
    return not remaining

def observe_windows():
    if sys.platform!='win32':return {'state':'idle','paused':False}
    u=ctypes.WinDLL('user32',use_last_error=True);k=ctypes.WinDLL('kernel32',use_last_error=True)
    u.GetForegroundWindow.restype=wintypes.HWND
    u.OpenInputDesktop.restype=wintypes.HANDLE
    u.CloseDesktop.argtypes=[wintypes.HANDLE]
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
    k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    desktop=u.OpenInputDesktop(0,False,0x0100)
    locked=not bool(desktop)
    if desktop:u.CloseDesktop(desktop)
    hwnd=u.GetForegroundWindow();pid=wintypes.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
    handle=k.OpenProcess(0x1000,False,pid.value);name=''
    if handle:
        buf=ctypes.create_unicode_buffer(32768);n=wintypes.DWORD(len(buf))
        if k.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(n)):name=Path(buf.value).stem.lower()
        k.CloseHandle(handle)
    state='working' if any(s in name for s in ['code','claude','codex','antigravity','terminal','powershell','pycharm']) else 'browsing' if any(s in name for s in ['chrome','firefox','edge','brave']) else 'idle'
    rects=[]
    callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    @callback
    def visit(h,_):
        if not u.IsWindowVisible(h) or u.IsIconic(h):return True
        cls=ctypes.create_unicode_buffer(128);u.GetClassNameW(h,cls,128)
        if cls.value in ('Progman','WorkerW','Shell_TrayWnd','Shell_SecondaryTrayWnd'):return True
        # Layered/translucent and cloaked windows cannot establish opaque coverage.
        if u.GetWindowLongW(h,-20)&0x80000:return True
        cloaked=wintypes.DWORD()
        ctypes.windll.dwmapi.DwmGetWindowAttribute(h,14,ctypes.byref(cloaked),4)
        if cloaked.value:return True
        r=wintypes.RECT()
        if u.GetWindowRect(h,ctypes.byref(r)):rects.append((r.left,r.top,r.right,r.bottom))
        return True
    u.EnumWindows(visit,0)
    work=wintypes.RECT()
    u.SystemParametersInfoW(0x0030,0,ctypes.byref(work),0)
    region=(work.left,work.top,work.right,work.bottom)
    return {'state':state,'paused':locked or covered(region,rects),'locked':locked}

def monitor():
    last=None
    while True:
        try:
            v=observe_windows()
            with LOCK:CURRENT['paused']=v['paused']
            if v['state']!=last or CURRENT['until'] and time.time()>=CURRENT['until']:
                publish(v['state'],'desktop');last=v['state']
        except OSError:pass
        time.sleep(1)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,status,body,kind='application/json'):
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):
            self.send(403,b'{}');return
        path=self.path.split('?',1)[0]
        if path=='/events':
            with LOCK:payload=json.dumps(CURRENT).encode()
            self.send(200,payload);return
        if path=='/bench-metrics':self.send(200,json.dumps(BENCH).encode());return
        if path=='/':path='/wallpaper/index.html'
        target=(ROOT/path.lstrip('/')).resolve()
        if not target.is_relative_to(ROOT/'wallpaper') or not target.is_file():self.send(404,b'{}');return
        self.send(200,target.read_bytes(),mimetypes.guess_type(target)[0] or 'application/octet-stream')
    def do_POST(self):
        if self.path=='/bench-metrics':
            # Diagnostics are opt-in, bounded, numeric scene playback data only.
            if self.headers.get('Origin')!=f'http://127.0.0.1:{self.server.server_port}':self.send(403,b'{}');return
            try:
                length=int(self.headers.get('Content-Length',0))
                if not 0<length<=2048:raise ValueError()
                data=json.loads(self.rfile.read(length))
                if data.get('format') not in ('video','atlas','still'):raise ValueError()
                clean={'format':data['format']}
                for key,value in data.items():
                    if key=='state':
                        if value not in STATES:raise ValueError()
                        clean[key]=value
                    elif key=='position':
                        if not isinstance(value,list) or len(value)!=3 or not all(isinstance(v,(int,float)) and math.isfinite(v) and abs(v)<=100 for v in value):raise ValueError()
                        clean[key]=value
                    elif key in ('clock','frames','totalVideoFrames','droppedVideoFrames','meanFrameMs','p95FrameMs','paused','videoPaused','videoWidth','videoHeight','stage','smokeVisiblePixels','actorVisiblePixels','restTime'):
                        if not isinstance(value,(int,float,bool)) or not math.isfinite(value) or not 0<=value<=1e9:raise ValueError()
                        clean[key]=value
                    elif key=='seated':
                        if not isinstance(value,bool):raise ValueError()
                        clean[key]=value
                    elif key=='ambient':
                        if value not in (None,'drink','nod','yawn'):raise ValueError()
                        clean[key]=value
                    elif key=='actorRect':
                        if not isinstance(value,list) or len(value)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=4096 for v in value):raise ValueError()
                        clean[key]=value
                    elif key=='transition':
                        if value is not None:
                            if not isinstance(value,dict) or value.get('kind') not in ('sit','stand'):raise ValueError()
                            elapsed=value.get('elapsed')
                            if not isinstance(elapsed,(int,float)) or not math.isfinite(elapsed) or not 0<=elapsed<=10:raise ValueError()
                            value={'kind':value['kind'],'elapsed':elapsed}
                        clean[key]=value
                    elif key=='lighting':
                        if value is not None:
                            phases=('morning','day','evening','night')
                            if not isinstance(value,dict) or value.get('mode') not in ('auto',*phases) or value.get('a') not in phases or value.get('b') not in (None,*phases):raise ValueError()
                            for field,limit in (('mix',1),('decoderCount',2),('clockDelta',12)):
                                number=value.get(field)
                                if not isinstance(number,(int,float)) or not math.isfinite(number) or not 0<=number<=limit:raise ValueError()
                            value={field:value[field] for field in ('mode','a','b','mix','decoderCount','clockDelta')}
                        clean[key]=value
                BENCH.clear();BENCH.update(clean)
                self.send(200,b'{}')
            except (ValueError,TypeError,AttributeError):self.send(400,b'{}')
            return
        if self.path!='/event' or self.headers.get('Authorization')!='Bearer '+self.server.token:
            self.send(403,b'{}');return
        try:
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<=1024:raise ValueError()
            data=json.loads(self.rfile.read(length));state=data.get('state')
            if not publish(state):raise ValueError()
            self.send(200,b'{"ok":true}')
        except (ValueError,TypeError,AttributeError):self.send(400,b'{}')

def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18765);p.add_argument('--no-observer',action='store_true');args=p.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.token=secrets.token_urlsafe(32)
    connection=DATA/'connection.json';connection.write_text(json.dumps({'url':f'http://127.0.0.1:{args.port}/event','token':server.token}))
    if not args.no_observer:threading.Thread(target=monitor,daemon=True).start()
    print(f'Resort wallpaper: http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    finally:server.server_close();connection.unlink(missing_ok=True)
if __name__=='__main__':main()
