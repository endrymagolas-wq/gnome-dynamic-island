import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import receiver_profile
spec = importlib.util.spec_from_file_location('receiver_installer', ROOT / 'install.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, HOME=td), contextlib.redirect_stdout(io.StringIO()):
    home = Path(td)
    m.install(SimpleNamespace(receivers=True, desktop=False, no_activate=True, dry_run=False))
    config = home / '.config/ytmusic-airplay/shairport-sync.conf'
    assert 'interface =' not in config.read_text()
    assert 'mpris_service_bus = "session"' in config.read_text()
    assert 'include_cover_art = "yes"' in config.read_text()
    screen = (home / '.config/systemd/user/airplay-screen.service').read_text()
    assert '-hls 2' in screen and 'xvimagesink' not in screen and '1920x1080' not in screen
    manifest = next((home / '.local/share/island-desktop/install-backups').glob('*/manifest.json'))
    m.restore(SimpleNamespace(manifest=str(manifest)))
    assert not config.exists()
    # Refuse a competing system receiver, without stopping it.
    binary = home / '.local/share/island-desktop/receivers/bin/uxplay'; binary.parent.mkdir(parents=True); binary.touch()
    calls=[]
    def run(*args):
        calls.append(args)
        if args[0] == '/usr/bin/shairport-sync': return '3.3.8-pa-metadata-dbus-mpris'
        return 'active'
    try:
        receiver_profile.preflight(run, home)
        raise AssertionError('competing receiver was accepted')
    except RuntimeError as error:
        assert 'system Shairport' in str(error)
    assert not any('stop' in call or 'disable' in call for call in calls)
print('PASS receiver install/restore, portable interfaces, session artwork/MPRIS, HLS settings and conflict preflight')
