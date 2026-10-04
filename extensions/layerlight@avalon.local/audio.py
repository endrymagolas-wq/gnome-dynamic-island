#!/usr/bin/python3
"""Four frequency bands from system playback. Never records the microphone."""
import array
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time
from music_features import MusicFeatures

STATE=Path(os.environ.get('XDG_RUNTIME_DIR','/tmp'))/f'layerlight-{os.getuid()}.json'
BANDS=((35,180),(180,700),(700,2400),(2400,5500))
RATE=12000

class Biquad:
    """Butterworth HP/LP; coefficients from the W3C Audio EQ Cookbook."""
    def __init__(self,frequency,highpass):
        omega=2*math.pi*frequency/RATE
        c=math.cos(omega);alpha=math.sin(omega)/math.sqrt(2);a0=1+alpha
        b0=(1+c)/2 if highpass else (1-c)/2
        self.b0=b0/a0;self.b1=(-2*b0 if highpass else 2*b0)/a0;self.b2=b0/a0
        self.a1=-2*c/a0;self.a2=(1-alpha)/a0;self.z1=self.z2=0.0
    def process(self,x):
        y=self.b0*x+self.z1
        self.z1=self.b1*x-self.a1*y+self.z2
        self.z2=self.b2*x-self.a2*y
        return y

class Spectrum:
    def __init__(self):
        self.filters=[(Biquad(low,True),Biquad(high,False)) for low,high in BANDS]
    def analyse(self,samples):
        energies=[0.0]*4;total=0.0
        for x in samples:
            if not math.isfinite(x):x=0.0
            total+=x*x
            for i,(highpass,lowpass) in enumerate(self.filters):
                y=lowpass.process(highpass.process(x));energies[i]+=y*y
        n=max(1,len(samples))
        return math.sqrt(total/n),[math.sqrt(e/n) for e in energies]

def main():
    capture=subprocess.Popen(['pw-cat','--record','--target','@DEFAULT_AUDIO_SINK@','--properties','{ stream.capture.sink = true }','--rate',str(RATE),'--channels','1','--format','f32','-'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    def stop(*_):
        capture.terminate();raise SystemExit
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    spectrum=Spectrum();features=MusicFeatures();frame=0;scene={"bpm":None,"confidence":0,"drive":.15,"texture":"unknown"};last_request=0;request_id=None
    request=STATE.with_name(f"layerlight-scene-request-{os.getuid()}.json");reply=STATE.with_name(f"layerlight-scene-{os.getuid()}.json")
    try:
        while True:
            chunk=capture.stdout.read(2400)
            if not chunk:break
            samples=array.array('f');samples.frombytes(chunk[:len(chunk)//4*4])
            rms,bands=spectrum.analyse(samples)
            levels=[max(0.0,(value-.00035)*7.5) for value in bands]
            level=max(0.0,(rms-.0008)*7.5);features.add(level,levels);frame+=1
            now=time.time()
            if frame%40==0:
                scene=features.analyse();scene['source']='audio_features'
                if level>.006 and features.last and now-last_request>25:
                    last_request=now;request_id=str(round(now*1000));payload={'id':request_id,'time':now,'features':scene}
                    tmp=request.with_suffix('.tmp');tmp.write_text(json.dumps(payload));tmp.chmod(0o600);tmp.replace(request)
                try:
                    decision=json.loads(reply.read_text())
                    if now-decision.get('time',0)<55 and decision.get('source')=='laya' and decision.get('request_id')==request_id and decision.get('confidence',0)>=.65 and decision.get('profile') in ['calm','flow','drive']:
                        scene={**scene,'profile':decision['profile'],'source':'laya','laya_confidence':decision['confidence']}
                except (OSError,ValueError,TypeError):pass
            state={'time':now,'level':level,'bands':levels,'bass':levels[0],'scene':scene}
            tmp=STATE.with_suffix('.tmp');tmp.write_text(json.dumps(state));tmp.chmod(0o600);tmp.replace(STATE)
    finally:
        capture.terminate();capture.wait();STATE.unlink(missing_ok=True);request.unlink(missing_ok=True)

if __name__=='__main__':main()
