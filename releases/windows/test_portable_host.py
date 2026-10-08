"""Exercise the packaged Python/host over an ephemeral loopback port.

No live Lively, receiver, taskbar or existing host is touched. Userdata is a new
temporary directory and process state observation is disabled for this fixture.
"""
import argparse, http.client, json, os, socket, subprocess, tempfile, time
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.package.resolve();checks=0
    def check(value,label):
        nonlocal checks
        assert value,label;checks+=1
    python=root/'python/python.exe'
    runtime=json.loads(subprocess.check_output([str(python),'-c','import sys,psutil,json; print(json.dumps({"python":sys.version.split()[0],"psutil":psutil.__version__,"module":psutil.__file__,"executable":sys.executable}))'],text=True))
    versions=runtime['python']+' '+runtime['psutil']
    check(versions=='3.13.14 7.2.2','Packaged runtimes load without global Python')
    check(Path(runtime['module']).resolve().is_relative_to(root/'python'),'psutil is imported from this package')
    check(Path(runtime['executable']).resolve()==python,'No global Python executable is used')
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='island-package-host-') as tmp:
        env=dict(os.environ,LOCALAPPDATA=tmp)
        process=subprocess.Popen([str(python),str(root/'wallpaper/server.py'),'--no-observer','--port',str(port)],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            connection=Path(tmp)/'ResortIsland/connection.json'
            for _ in range(100):
                if connection.exists():break
                if process.poll() is not None:raise RuntimeError('Packaged host failed: '+process.stderr.read())
                time.sleep(.05)
            check(connection.exists(),'Isolated local connection created')
            auth=json.loads(connection.read_text());check(auth['url']==f'http://127.0.0.1:{port}/event','Ephemeral local auth endpoint')
            def request(method,path,headers=None,body=None):
                c=http.client.HTTPConnection('127.0.0.1',port,timeout=10);c.request(method,path,body,headers or {});r=c.getresponse();status=r.status;data=r.read();headers=dict(r.getheaders());c.close();return status,data,headers
            status,data,_=request('GET','/wallpaper/release.json');check(status==200,'Package identity is served');check(json.loads(data)['tag']=='windows-v0.4.0-beta.1','Exact release tag')
            status,data,_=request('GET','/wallpaper/assets/scene.json');scene=json.loads(data);check(status==200 and scene['ground']['ellipse']==[7.2,5.5],'Accepted organic geometry');check(scene['effects']=={'construction':False,'smoke':False},'Legacy row/decor effects absent')
            status,data,h=request('GET','/wallpaper/assets/water-720.mp4',{'Range':'bytes=128-255'});check(status==206 and len(data)==128,'Portable HTTP byte ranges');check(h.get('Content-Range','').startswith('bytes 128-255/'),'Range registration')
            expected=(root/'wallpaper/assets/water-720.mp4').read_bytes()[128:256];check(data==expected,'Range returns correct portable water bytes')
            status,_,_=request('GET','/assistant/claude_hook.py');check(status==404,'Non-wallpaper source is not served')
            status,_,_=request('GET','/wallpaper/release.json',{'Host':f'example.invalid:{port}'});check(status==403,'Foreign Host is rejected')
            event=json.dumps({'state':'testing','source':'claude'})
            status,_,_=request('POST','/event',{'Content-Type':'application/json'},event);check(status==403,'Unauthenticated app event rejected')
            status,_,_=request('POST','/event',{'Content-Type':'application/json','Authorization':'Bearer '+auth['token']},event);check(status==200,'Authenticated sanitized app state works')
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
    result={'pass':True,'checks':checks,'runtime':versions,'scope':'Actual packaged Python/psutil and isolated ephemeral-port HTTP host; native Lively/desktop not changed'}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
