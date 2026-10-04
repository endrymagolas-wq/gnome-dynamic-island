"""Frequency separation and owned-monitor cleanup without recording real audio."""
import importlib.util
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'extensions/layerlight@avalon.local'
sys.path.insert(0, str(LAYER))
spec = importlib.util.spec_from_file_location('wave_audio', LAYER / 'audio.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
for index, frequency in enumerate([90, 350, 1200, 3500]):
    spectrum = m.Spectrum()
    samples = [.1 * math.sin(2 * math.pi * frequency * n / m.RATE) for n in range(m.RATE)]
    rms, bands = spectrum.analyse(samples)
    assert .06 < rms < .08 and max(range(4), key=lambda i: bands[i]) == index, (frequency, bands)
assert all(math.isfinite(x) for x in m.Spectrum().analyse([float('nan'), float('inf'), 0])[1])
with tempfile.TemporaryDirectory() as td:
    path = Path(td)
    monitor = path / 'pw-cat'
    monitor.write_text('#!/usr/bin/python3\nimport os,time\nfrom pathlib import Path\nPath(os.environ["XDG_RUNTIME_DIR"]+"/child.pid").write_text(str(os.getpid()))\nwhile True:\n os.write(1,b"\\0"*2400);time.sleep(.05)\n')
    monitor.chmod(0o755)
    env = dict(os.environ, PATH=td + ':' + os.environ['PATH'], XDG_RUNTIME_DIR=td)
    producer = subprocess.Popen([sys.executable, str(LAYER / 'audio.py')], env=env, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic()+5
        while not (path / f'layerlight-{os.getuid()}.json').exists() and time.monotonic()<deadline: time.sleep(.05)
        assert (path / f'layerlight-{os.getuid()}.json').exists()
        child = int((path / 'child.pid').read_text())
        producer.send_signal(signal.SIGTERM); producer.wait(timeout=3)
        assert not Path(f'/proc/{child}').exists(), 'owned audio monitor survived disable'
        assert not (path / f'layerlight-{os.getuid()}.json').exists()
    finally:
        if producer.poll() is None: producer.kill(); producer.wait()
print('PASS waves: four-band frequency separation, malformed samples and SIGTERM cleanup of owned monitor')
