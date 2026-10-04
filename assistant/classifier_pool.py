"""Nonblocking owned classifier lifecycle; idle unload releases its entire RSS."""
import json,queue,subprocess,sys,threading,time
from pathlib import Path

class ClassifierPool:
    def __init__(self):
        self.proc=None;self.messages=queue.Queue(maxsize=8);self.generation=0;self.ready=False;self.job=None;self.last_used=0;self.started=0;self.reason='idle';self.loads=0
    def start(self):
        if self.proc is not None:return
        self.generation+=1;generation=self.generation
        self.proc=subprocess.Popen([sys.executable,str(Path(__file__).with_name('classifier_worker.py'))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
        proc=self.proc;self.ready=False;self.started=time.monotonic();self.last_used=self.started;self.reason='loading';self.loads+=1
        def reader():
            try:
                for line in proc.stdout:
                    if len(line)>65536:continue
                    try:value=json.loads(line)
                    except ValueError:continue
                    if not isinstance(value,dict):continue
                    try:self.messages.put_nowait((generation,value))
                    except queue.Full:break
            finally:
                try:proc.stdout.close()
                except OSError:pass
        threading.Thread(target=reader,daemon=True).start()
    def submit(self,key,state,questions):
        if self.job is not None:return False
        self.start();self.job={'id':key,'since':time.monotonic()};self.last_used=time.monotonic()
        try:self.proc.stdin.write(json.dumps({'id':key,'state':state,'questions':questions},ensure_ascii=False)+'\n');self.proc.stdin.flush()
        except (BrokenPipeError,OSError):return False
        return True
    def poll(self):
        replies=[]
        while True:
            try:generation,value=self.messages.get_nowait()
            except queue.Empty:break
            if generation!=self.generation:continue
            if value.get('ready'):self.ready=True;self.reason='ready';continue
            if self.job and (value.get('id')==self.job['id'] or value.get('error') and value.get('id') is None):
                replies.append(value);self.job=None;self.last_used=time.monotonic()
        if self.proc is not None and (self.proc.poll() is not None or self.job and time.monotonic()-self.job['since']>40):
            if self.job:replies.append({'id':self.job['id'],'error':'classifier_unavailable'})
            self.close('unavailable')
        return replies
    def maintain(self,economy=True,pressure=False):
        if pressure:
            self.close('system_pressure');return
        if not economy:
            self.start();return
        if self.proc is not None and self.job is None and time.monotonic()-self.last_used>=60:self.close('idle')
    def close(self,reason='disabled'):
        proc=self.proc;self.generation+=1;self.proc=None;self.ready=False;self.job=None;self.reason=reason
        if proc is not None:
            try:proc.stdin.close()
            except (OSError,BrokenPipeError):pass
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=2)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=2)
    def status(self):
        return {'state':'busy' if self.ready and self.job else 'ready' if self.ready else 'loading' if self.proc is not None else 'sleeping','pid':self.proc.pid if self.proc else None,'reason':self.reason,'loads':self.loads,'idle_seconds':60}
