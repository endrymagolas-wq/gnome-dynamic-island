"""Require matching source, four shipped bundles and real native V6 evidence."""
import hashlib, json
from pathlib import Path
from PIL import Image
root = Path(__file__).resolve().parents[1]
out = root / 'docs/evidence/resort'
assets = root / 'wallpaper/assets'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = json.loads((out / 'source-v6-audit.json').read_text())
assert source['sourceSha256'] == sha(root / source['source'])
assert source['rigBones'] == 43 and source['meshVertices'] == source['weightedVertices'] == 19980
assert not source['invalidConstraints'] and source['gestureSurvivesFrameEvaluation']
assert source['plantedFootMaxDriftMetres'] < .00001 and source['permissionWristHeight'] > 1.8
assert sum(name.startswith('Resort_Pip_') for name in source['actions']) == 15
assert all(item['packed'] for item in source['images'])
reproduction = json.loads((out / 'reproduction-v6.json').read_text())
assert source['sourceSha256'] in json.dumps(reproduction)
meta = json.loads((assets / 'scene.json').read_text())
assert meta['lighting']['fadeSeconds'] == 120
assert [p['minute'] for p in meta['lighting']['schedule']] == [360, 540, 1080, 1260]
for phase, folder in meta['lighting']['phases'].items():
    bundle = assets / folder
    for name, size, rows, frames in [('character.png', (2048, 3200), 19, 16),
                                    ('ambient.png', (2048, 2880), 18, 16)]:
        with Image.open(bundle / name) as atlas:
            assert atlas.size == size, (phase, name)
            for row in range(rows):
                for frame in range(frames):
                    bounds = atlas.crop((frame*128, row*160, (frame+1)*128, (row+1)*160)).getchannel('A').getbbox()
                    assert bounds and bounds[0] > 0 and bounds[1] > 0 and bounds[2] < 128 and bounds[3] < 160, (phase, name, row, frame, bounds)
    encoded = json.loads((out / f'encoded-water-v6-{phase}.json').read_text())
    for name in ('water-1080.mp4', 'water-720.mp4'):
        assert sha(bundle / name) == encoded[name]['sha256']
        assert int(encoded[name]['nb_read_frames']) == 360 and encoded[name]['r_frame_rate'] == '30/1'
        assert float(encoded[name]['duration']) == 12
        assert encoded[name]['seamMAE'] <= max(encoded[name]['firstStepMAE'], encoded[name]['lastStepMAE']) * 1.5 + .1
for name, size in [('character-depth.png', (2048, 3040)), ('ambient-depth.png', (2048, 2880))]:
    with Image.open(assets / name) as depth:
        assert depth.size == size
        assert depth.getchannel('A').getbbox()
native = json.loads((out / 'v6/native-reactions.json').read_text())
expected = ['starting', *[f'editing-{i}' for i in range(1, 5)], 'testing', 'failed', 'permission', 'done', 'browsing', 'working', 'idle']
for event in expected:
    current = native[event]
    assert current['state'] == event.split('-')[0] and not current['transition']
    assert current['actorVisiblePixels'] > 1000
    assert (out / 'v6' / f'{event}.jpg').stat().st_size > 10000
assert native['done']['seated'] and native['idle']['seated']
assert native['failed']['smokeVisiblePixels'] > 100
controls = json.loads((out / 'v6/native-controls.json').read_text())
assert all(k in controls for k in ['manualPause', 'waterOff', '720p', 'qualityOff'])
ambient = json.loads((out / 'v6/native-ambient.json').read_text())
for clip in ('drink', 'nod', 'yawn'):
    before, after = ambient[clip]
    assert before['ambient'] == after['ambient'] == clip and before['actorRect'] != after['actorRect']
    assert after['actorVisiblePixels'] > 1000 and after['restTime'] > before['restTime']
    assert (out / 'v6' / f'ambient-{clip}.jpg').stat().st_size > 10000
lighting = json.loads((out / 'v6/native-lighting.json').read_text())
for phase in ('morning', 'day', 'evening', 'night'):
    assert lighting[phase]['lighting']['a'] == phase
    assert lighting[phase]['lighting']['b'] is None and lighting[phase]['lighting']['decoderCount'] == 1
    assert (out / 'v6' / f'lighting-{phase}.jpg').stat().st_size > 10000
perf = json.loads((out / 'performance-v6.json').read_text())
for report in (native, controls, ambient, lighting, perf):
    for name, digest in report['assets'].items():
        assert sha(assets / name) == digest, name
report = {'source': source['sourceSha256'], 'assets': perf['assets'],
          'mainSpriteFramesPerPhase': 304, 'ambientFramesPerPhase': 288, 'lightingPhases': 4,
          'clippedFrames': 0, 'nativeCases': expected, 'performance': 'performance-v6.json',
          'limitations': 'Physical lock/resume, exclusive fullscreen and multiple monitors remain manual. Yawn is a body/hand gesture without animated jaw or eyelids. Eating is not implemented.'}
(out / 'validation-v6.json').write_text(json.dumps(report, indent=2))
print('PASS V6 source, four coherent lighting bundles, 2368 unclipped actor frames, native reactions, controls and matching performance assets')
