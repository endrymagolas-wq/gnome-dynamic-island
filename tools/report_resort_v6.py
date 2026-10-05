"""Summarize fresh native V6 measurements, including the two-decoder fade."""
import datetime, hashlib, json, statistics
from pathlib import Path
root = Path(__file__).resolve().parents[1]
out = root / 'docs/evidence/resort'
assets = root / 'wallpaper/assets'
labels = ['video-v6-720', 'atlas-v6-720', 'still-v6', 'runtime-v6-coffee',
          'runtime-v6-editing', 'runtime-v6-transition', 'runtime-v6-paused']
rows = []
for label in labels:
    cpu = json.loads((out / (label + '.json')).read_text())
    gpu = json.loads((out / (label + '-gpu.json')).read_text(encoding='utf-8-sig'))
    samples = gpu['samples']
    assert len(samples) >= 29 and all(s.get('invalidTargetSamples', 0) == 0 for s in samples)
    before, after = cpu['playbackBefore'], cpu['playback']
    if label.endswith('-paused'):
        assert before['totalVideoFrames'] > 30 and before['videoWidth'] == 1920
        assert before['paused'] and after['paused'] and before['videoPaused'] and after['videoPaused']
        assert before['totalVideoFrames'] == after['totalVideoFrames']
        assert all(before.get(key)==after.get(key) for key in ('actorRect','restTime','position'))
        assert after['lighting']['decoderCount'] == 0
    if label.endswith('-transition'):
        assert after['lighting']['decoderCount'] == 2 and after['lighting']['clockDelta'] < .1, after
        assert after['lighting']['a'] == 'morning' and after['lighting']['b'] == 'day'
    rows.append({'label': label, 'cpuPercentWholePC': cpu['cpuPercentWholePC'],
                 'meanRssMiB': cpu['meanRssMiB'],
                 'gpu3DPercent': statistics.mean(s['engines'].get('3d', 0) for s in samples),
                 'gpuVideoDecodePercent': statistics.mean(s['engines'].get('videodecode', 0) for s in samples),
                 'meanDedicatedMiB': statistics.mean(s['dedicatedMiB'] for s in samples),
                 'meanSharedMiB': statistics.mean(s['sharedMiB'] for s in samples),
                 'playbackFps': cpu['observedPlaybackFps'],
                 'droppedFramesDuringInterval': after.get('droppedVideoFrames', 0) - before.get('droppedVideoFrames', 0)})
restore = json.loads((out / 'v6/restored-pause-policy.json').read_text(encoding='utf-8-sig'))
assert restore['restoredFullscreenPause'] == 0 and restore['observerEnabled']
files = ['scene.json', 'character.png', 'character-depth.png', 'ambient.png', 'ambient-depth.png', 'water-1080.mp4', 'water-720.mp4']
files += [str(p.relative_to(assets)).replace('\\', '/') for p in sorted((assets / 'phases').rglob('*')) if p.is_file()]
report = {'recordedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'hardware': 'Windows 11 Pro 10.0.26200, i9-9900K (16 logical CPUs), 32GB RAM, RTX3080 10GB, 1920x1080 primary display',
          'conditions': 'Seven fresh 30-second native windows with Blender stopped. CPU sampling begins after the first GPU counter sample. Coverage/observer are temporarily disabled during measurements, including native CLI pause of an initialized player; ordinary policy and observer are restored afterwards. Video/atlas use the same new 720p frames. Physical lock/fullscreen/multi-monitor checks remain manual.',
          'scope': 'Lively core, owned WebView2 process tree and loopback host. RSS sums shared mappings; GPU engines are separate Windows counters, not board power. Video fps counts decoded frames; atlas fps counts submitted draws, not monitor presents.',
          'rows': rows, 'restoredPausePolicy': restore,
          'assets': {name: hashlib.sha256((assets / name).read_bytes()).hexdigest() for name in files}}
(out / 'performance-v6.json').write_text(json.dumps(report, indent=2))
print(json.dumps(rows, indent=2))
