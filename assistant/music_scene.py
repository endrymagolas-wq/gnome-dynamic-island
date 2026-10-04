"""Wallpaper profile selection using the existing offline Laya pool, without notices."""
import json
import math
import os
from pathlib import Path
import time

QUESTIONS={'category':{'type':'choice','instructions':'Classify the described music character. Select the single best matching category based only on the provided observation.','criteria':{
'gentle':'Quiet relaxed slow mellow music.',
'balanced':'Moderate paced music with steady balanced sound.',
'energetic':'Fast intense upbeat rhythmic music.'}}}

class MusicScene:
    def __init__(self):
        root=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))
        self.request=root/f'layerlight-scene-request-{os.getuid()}.json';self.reply=root/f'layerlight-scene-{os.getuid()}.json'
        self.last_id=None;self.current=None;self.fallback="flow";self.last_result=None;self.next_allowed=0
    def submit(self,pool):
        if time.monotonic()<self.next_allowed or pool.job is not None:return False
        try:
            if self.request.stat().st_size>4096:return False
            payload=json.loads(self.request.read_text());key=payload.get('id');f=payload.get('features',{})
            if not isinstance(key,str) or not key.isdigit() or key==self.last_id or time.time()-float(payload.get('time',0))>35:return False
            bpm=f.get('bpm');bpm=float(bpm) if isinstance(bpm,(float,int)) and math.isfinite(bpm) and 40<=bpm<=220 else None
            percussion=float(f.get('percussion',0));brightness=float(f.get('brightness_hz',0))
            if not all(math.isfinite(x) for x in [percussion,brightness]):return False
            percussion=max(0,min(1,percussion));brightness=max(0,min(6000,brightness))
            texture={'warm_harmonic':'warm mellow harmonic texture','percussive':'strong rhythmic percussive texture','mixed':'mixed harmonic and rhythmic texture'}.get(f.get('texture'),'uncertain texture')
            tempo='unknown tempo' if bpm is None else ('slow' if bpm<95 else 'moderate' if bpm<125 else 'fast')+f' tempo estimated at {bpm:.0f} BPM'
            attacks='many sharp rhythmic attacks' if percussion>.5 else 'few sharp attacks' if percussion<.2 else 'moderate rhythmic attacks'
            state={'event':f'Music playing with {tempo}, {texture}, and {attacks}. Spectral brightness {brightness:.0f} Hz.'}
        except (OSError,ValueError,TypeError,AttributeError):return False
        self.fallback='calm' if (bpm is not None and bpm<100 and percussion<.3 or bpm is None and f.get('texture')=='warm_harmonic') else 'drive' if (bpm is not None and bpm>=125 and percussion>.35 or percussion>.65) else 'flow'
        job='music:'+key
        if not pool.submit(job,state,QUESTIONS):return False
        self.last_id=key;self.current=job;self.next_allowed=time.monotonic()+20
        return True
    def accept(self,response):
        if not self.current or response.get('id') not in [self.current,None]:return False
        key=self.current;self.current=None;answer=response.get('answer') or {}
        choice=answer.get('choice')
        profile={'gentle':'calm','balanced':'flow','energetic':'drive'}.get(choice);confidence=answer.get('answer_confidence',0)
        if not isinstance(confidence,(int,float)) or not math.isfinite(confidence):confidence=0
        conflict={profile,self.fallback}=={'calm','drive'}
        accepted=profile in ['calm','flow','drive'] and confidence>=.65 and not conflict
        result={'time':time.time(),'request_id':key.split(':',1)[1],'profile':profile if accepted else self.fallback,'confidence':round(confidence,4),'source':'laya' if accepted else 'audio_features','model_choice':choice,'status':'accepted' if accepted else 'contradiction' if conflict else 'uncertain'}
        try:
            tmp=self.reply.with_suffix('.tmp');tmp.write_text(json.dumps(result));tmp.chmod(0o600);tmp.replace(self.reply);self.last_result=result
        except OSError:pass
        return True
    def cancel(self):self.current=None
    def status(self):return {'pending':self.current is not None,'last_result':self.last_result,'purpose':'wallpaper_profile_only'}
