"""Standalone wallpaper install leaves panel, wallpaper and Claude settings alone."""
import importlib.util
from pathlib import Path
import tempfile
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wallpaper_install',root/'install_wallpaper.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td:
    home=Path(td)
    settings=home/'.claude/settings.json';settings.parent.mkdir();settings.write_text('{"model":"sonnet"}')
    m.install(home,files_only=True)
    target=home/'.local/share/gnome-shell/extensions'/m.UUID
    assert (target/'world.js').exists()
    assert (home/'.local/share/cartoon-island/claude_hook.py').exists()
    assert settings.read_text()=='{"model":"sonnet"}'
    assert not (home/'.local/share/gnome-shell/extensions/airplay-island@avalon.local').exists()
    (target/'metadata.json').write_text('old metadata')
    m.install(home,files_only=True)
    backups=list((home/'.local/share/cartoon-island/backups').iterdir())
    assert len(backups)==1 and (backups[0]/'metadata.json').read_text()=='old metadata'
print('PASS isolated wallpaper installation, prior version backup and settings preservation')
