"""Streaming onset autocorrelation and texture features. No instrument labels."""
from collections import deque
import math
import statistics

class MusicFeatures:
    def __init__(self):
        self.frames=deque(maxlen=480);self.previous=[0]*4;self.last=None
        self.bpm=None;self.confidence=0;self.candidate=None;self.matches=0;self.silent=0
    def add(self,level,bands):
        flux=sum(max(0,bands[i]-self.previous[i])*w for i,w in enumerate((1.4,1,.7,.4)))
        self.previous=list(bands);self.frames.append((level,list(bands),flux))
        self.silent=self.silent+1 if level<.006 else 0
        if self.silent>=80:
            self.frames.clear();self.bpm=None;self.confidence=0;self.candidate=None;self.matches=0
    def analyse(self):
        if len(self.frames)<160:return {'bpm':None,'confidence':0,'drive':.15,'texture':'unknown'}
        frames=list(self.frames);onsets=[f[2] for f in frames];mean=statistics.mean(onsets)
        centered=[x-mean for x in onsets];scores={}
        for lag in range(6,23):
            a=centered[lag:];b=centered[:-lag]
            norm=math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
            scores[lag]=sum(x*y for x,y in zip(a,b))/norm if norm>1e-8 else 0
        best=max(scores,key=scores.get)
        peaks=[lag for lag in range(6,23) if scores[lag]>=scores.get(lag-1,-1) and scores[lag]>=scores.get(lag+1,-1) and scores[lag]>=max(.22,scores[best]*.35)]
        lag=min(peaks) if peaks else best;score=scores[lag]
        if score>.18:
            offset=0
            if lag-1 in scores and lag+1 in scores:
                left,right=scores[lag-1],scores[lag+1];den=left-2*score+right
                if abs(den)>1e-8:offset=max(-.5,min(.5,.5*(left-right)/den))
            candidate=60/((lag+offset)*.05)
            if self.candidate is not None and abs(candidate-self.candidate)<8:self.matches+=1
            else:self.matches=1
            self.candidate=candidate
            if self.matches>=2:
                self.bpm=candidate if self.bpm is None else self.bpm*.7+candidate*.3
                self.confidence=max(0,min(1,(score-.1)/.65))
        else:self.confidence*=.8
        recent=frames[-160:];energy=[sum(f[1][i]**2 for f in recent)/len(recent) for i in range(4)];total=sum(energy)+1e-8
        fractions=[e/total for e in energy];brightness=sum(e*c for e,c in zip(fractions,(95,380,1400,3700)))
        avg=statistics.mean(f[0] for f in recent);percussion=min(1,statistics.mean(f[2] for f in recent)/(avg+.01)*5)
        tempo=self.bpm if self.bpm and self.confidence>.2 else 90
        pace=max(0,min(1,(tempo-80)/75));bright=max(0,min(1,(brightness-500)/1800))
        drive=max(0,min(1,.6*pace+.3*percussion+.1*bright))
        texture='warm_harmonic' if brightness<850 and percussion<.32 else 'percussive' if percussion>.4 else 'mixed'
        self.last={'bpm':round(self.bpm,1) if self.bpm and self.confidence>.2 else None,'confidence':round(self.confidence,3),'drive':round(drive,3),'texture':texture,'brightness_hz':round(brightness),'percussion':round(percussion,3),'band_fractions':[round(x,3) for x in fractions]}
        return self.last
