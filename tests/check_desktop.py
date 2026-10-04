"""Exercise full install/restore in a temporary home and a fake settings bus."""
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
import desktop_profile
spec = importlib.util.spec_from_file_location('desktop_installer', ROOT / 'install.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

with tempfile.TemporaryDirectory(prefix='island-profile-test-') as td, patch.dict(os.environ, HOME=td):
    home = Path(td)
    gtk = home / '.config/gtk-4.0/gtk.css'; gtk.parent.mkdir(parents=True); gtk.write_text('/* original custom GTK */')
    private = home / '.local/share/netflix-remote/remote-key'; private.parent.mkdir(parents=True); private.write_text('fixture, never an actual credential')
    calls = []
    store = {name: "'original'" for name in desktop_profile.desired(home)}
    store.update({'org.gnome.shell/enabled-extensions': "['existing-extension']",
                  'org.gnome.shell/disabled-extensions': '[]',
                  'org.gnome.shell.extensions.user-theme/name': "'original-shell'"})
    def run(*args):
        calls.append(args)
        if args == ('gnome-shell', '--version'): return 'GNOME Shell 46.0'
        if args == ('gnome-extensions', 'list'):
            return '\n'.join(['user-theme@gnome-shell-extensions.gcampax.github.com', desktop_profile.DOCK_UUID])
        if args[:2] == ('gsettings', 'get'): return store['/'.join(args[2:4])]
        if args[:2] == ('gsettings', 'set'):
            store['/'.join(args[2:4])] = args[4]; return ''
        if args[:3] == ('systemctl', '--user', 'show'): return 'UnitFileState=disabled\nActiveState=inactive'
        return ''
    original = dict(store)
    with patch.object(m, 'run', run), patch.object(m.subprocess, 'run'), patch('shutil.which', return_value='/usr/bin/fixture'), contextlib.redirect_stdout(io.StringIO()):
        m.install(SimpleNamespace(desktop=True, no_activate=False, dry_run=True))
        assert not (home / '.themes').exists()
        assert store == original
        m.install(SimpleNamespace(desktop=True, no_activate=False, dry_run=False))
        manifest = next((home / '.local/share/island-desktop/install-backups').glob('*/manifest.json'))
        assert gtk.read_text().startswith('@import url("file://') and str(home) in gtk.read_text()
        assert (home / '.themes/Island-WhiteSur/gtk-3.0/gtk.css').exists()
        assert (home / '.local/share/icons/Island-WhiteSur/index.theme').exists()
        assert (home / '.local/share/gnome-shell/extensions/layerlight@avalon.local/wave.glsl').exists()
        assert (home / '.local/share/applications/island-youtube.desktop').exists()
        assert private.read_text() == 'fixture, never an actual credential'
        assert not any('enable' in call and 'netflix-remote.service' in call for call in calls)
        assert store['org.gnome.shell.extensions.dash-to-dock/dock-position'] == "'BOTTOM'"
        # A later user preference must survive restore, while other keys revert.
        store['org.gnome.desktop.interface/font-name'] = "'User font 12'"
        m.restore(SimpleNamespace(manifest=str(manifest)))
        assert gtk.read_text() == '/* original custom GTK */'
        assert private.exists()
        assert store['org.gnome.desktop.interface/font-name'] == "'User font 12'"
        for name, value in original.items():
            if name != 'org.gnome.desktop.interface/font-name': assert store[name] == value, name
        assert not (home / '.local/share/island-desktop/wallpaper/WhiteSur-light.jpg').exists()
print('PASS full desktop install/restore, original GTK backup, portable paths, private media state preservation, remote OFF and per-key later-choice preservation')
