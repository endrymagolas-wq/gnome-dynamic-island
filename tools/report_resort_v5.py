"""Fresh V5 native windows; preserve V4 comparison for unchanged water formats."""
import datetime,hashlib,json,statistics
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'docs/evidence/resort'
rows=[]
for label in ['runtime-v5-coffee','runtime-v5-editing','runtime-v5-paused']:
    cpu=json.loads((out/(label+'.json')).read_text())
    gpu=json.loads((out/(label+'-gpu.json')).read_text(encoding='utf-8-sig'))
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
        'playbackFps':cpu['observedPlaybackFps'],
        'droppedFramesDuringInterval':after.get('droppedVideoFrames',0)-before.get('droppedVideoFrames',0)})
restore=json.loads((out/'v5/restored-pause-policy.json').read_text(encoding='utf-8-sig'))
assert restore['restoredFullscreenPause']==0 and restore['observerEnabled']
assets={name:hashlib.sha256((root/'wallpaper/assets'/name).read_bytes()).hexdigest() for name in ['scene.json','character.png','water-1080.mp4','water-720.mp4']}
v4=json.loads((out/'performance-v4.json').read_text())
assert all(assets[n]==v4['assets'][n] for n in ['water-1080.mp4','water-720.mp4'])
report={'recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'hardware':v4['hardware'],'scope':v4['scope'],
    'conditions':'Three fresh 30-second V5 native windows with Blender stopped. Active windows disable coverage/observer temporarily; ordinary policy restored before native CLI pause callback. Physical lock/fullscreen and multi-monitor checks remain manual.',
    'unchangedWaterComparison':'performance-v4.json; water asset hashes match exactly',
    'rows':rows,'restoredPausePolicy':restore,'assets':assets}
(out/'performance-v5.json').write_text(json.dumps(report,indent=2));print(json.dumps(rows,indent=2))
