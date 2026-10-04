import importlib.util, json, os, tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', root / 'install.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, HOME=td):
    home = Path(td)
    original = home / '.local/share/gnome-shell/extensions/airplay-island@avalon.local/metadata.json'
    original.parent.mkdir(parents=True); original.write_text('{"original":true}\n')
    untouched = original.parent / 'custom.txt'; untouched.write_text('keep user file')
    m.install(SimpleNamespace(no_activate=True, dry_run=True))
    assert not (home / '.themes').exists(), 'dry run wrote files'
    m.install(SimpleNamespace(no_activate=True, dry_run=False))
    assert json.loads(original.read_text())['version'] == 4
    assert (home / '.local/bin/island-assistant').stat().st_mode & 0o111
    prefs = home / '.local/share/island-desktop/assistant/preferences.json'
    assert json.loads(prefs.read_text())['enabled'] is False
    assert prefs.stat().st_mode & 0o777 == 0o600
    manifest = next((home / '.local/share/island-desktop/install-backups').glob('*/manifest.json'))
    script = home / '.local/share/island-desktop/assistant/monitor.py'
    original_script = script.read_text(); script.write_text('user modification')
    try:
        m.restore(SimpleNamespace(manifest=str(manifest)))
        raise AssertionError('restore overwrote user edits')
    except RuntimeError as e:
        assert 'changed' in str(e)
    script.write_text(original_script)
    prefs.write_text('{"enabled":true,"economy":false,"muted_kinds":["cpu"]}')
    m.restore(SimpleNamespace(manifest=str(manifest)))
    assert original.read_text() == '{"original":true}\n'
    assert untouched.read_text() == 'keep user file'
    assert json.loads(prefs.read_text())['enabled'] is True, 'lost later assistant preference'
    assert not script.exists(), 'new installed files survived restore'
print('PASS installer dry run, backups, install, restore, private default OFF, modified-file guard, later preference preservation')
