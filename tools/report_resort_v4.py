"""Summarize the six recorded native measurement windows without inventing data."""
import datetime, hashlib, json, statistics
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'docs/evidence/resort'
labels=['video-v4-720','atlas-v4-720','still-v4','runtime-v4-coffee','runtime-v4-editing','runtime-v4-paused']
rows=[]
for label in labels:
    cpu=json.loads((out/(label+'.json')).read_text());gpu=json.loads((out/(label+'-gpu.json')).read_text(encoding='utf-8-sig'))
    samples=gpu['samples'];assert len(samples)>=29 and all(s.get('invalidTargetSamples',0)==0 for s in samples)
    before=cpu['playbackBefore'];after=cpu['playback']
    if label.endswith('-paused'):
        assert before['paused'] and after['paused'] and before['videoPaused'] and after['videoPaused']
        assert before['totalVideoFrames']==after['totalVideoFrames']
    rows.append({'label':label,'cpuPercentWholePC':cpu['cpuPercentWholePC'],'meanRssMiB':cpu['meanRssMiB'],
        'gpu3DPercent':statistics.mean(s['engines'].get('3d',0) for s in samples),
        'gpuVideoDecodePercent':statistics.mean(s['engines'].get('videodecode',0) for s in samples),
        'meanDedicatedMiB':statistics.mean(s['dedicatedMiB'] for s in samples),
        'meanSharedMiB':statistics.mean(s['sharedMiB'] for s in samples),
        'playbackFps':cpu['observedPlaybackFps'],'droppedFramesDuringInterval':after.get('droppedVideoFrames',0)-before.get('droppedVideoFrames',0)})
restore=json.loads((out/'v4/restored-pause-policy.json').read_text(encoding='utf-8-sig'))
assert restore['restoredFullscreenPause']==0 and restore['observerEnabled']
report={'recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'hardware':'Windows 11 Pro 10.0.26200, i9-9900K (16 logical CPUs), 32GB RAM, RTX3080 10GB, 1920x1080 primary display',
    'conditions':'Six 30-second CPU/GPU windows, all Blender processes stopped. Active runs temporarily disabled the observer and ignored fullscreen coverage; ordinary pause policy and observation restored before the Lively native pause callback measurement. Desktop was not fully covered; this is not a current coverage-pause measurement. Video and atlas use the same decoded 720p loop.',
    'scope':'Lively core, owned WebView2 process tree and loopback host. RSS sums shared mappings; GPU engines are separate Windows counters, not board power. Video fps counts decoded frames; atlas fps counts submitted draws, not monitor presents.',
    'rows':rows,'restoredPausePolicy':restore,
    'assets':{name:hashlib.sha256((root/'wallpaper/assets'/name).read_bytes()).hexdigest() for name in ['scene.json','character.png','water-1080.mp4','water-720.mp4']}}
(out/'performance-v4.json').write_text(json.dumps(report,indent=2))
print(json.dumps(rows,indent=2))
