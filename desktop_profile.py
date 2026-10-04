"""Optional, reversible GNOME desktop profile; no personal account data."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parent
LAYER_UUID = 'layerlight@avalon.local'
DOCK_UUID = 'ubuntu-dock@ubuntu.com'


def plan(home):
    """Read a checksummed, deduplicated asset bundle without extracting paths."""
    archive = ROOT / 'desktop/assets.zip'
    index = json.loads((ROOT / 'desktop/ASSETS.json').read_text())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != index['sha256']:
        raise RuntimeError('Desktop asset checksum mismatch.')
    roots = {'gtk': home / '.themes/Island-WhiteSur',
             'icons': home / '.local/share/icons/Island-WhiteSur',
             'fonts': home / '.local/share/fonts/island-desktop',
             'wallpaper': home / '.local/share/island-desktop/wallpaper'}
    items, cache = [], {}
    with zipfile.ZipFile(archive) as bundle:
        for name, sha in sorted(index['files'].items()):
            relative = PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or len(relative.parts) < 2 or relative.parts[0] not in roots:
                raise RuntimeError('Invalid desktop asset path.')
            if sha not in cache:
                info = bundle.getinfo(sha)
                if info.file_size > 12 * 1024 * 1024:
                    raise RuntimeError('Oversized desktop asset.')
                cache[sha] = bundle.read(info)
                if hashlib.sha256(cache[sha]).hexdigest() != sha:
                    raise RuntimeError('Desktop asset content mismatch.')
            data = cache[sha]
            if name == 'gtk/index.theme':
                data = data.replace(b'WhiteSur-Light-solid-blue', b'Island-WhiteSur').replace(b'IconTheme=WhiteSur\n', b'IconTheme=Island-WhiteSur\n').replace(b'CursorTheme=WhiteSur-cursors', b'CursorTheme=Yaru').replace(b'ButtonLayout=close,minimize,maximize:menu', b'ButtonLayout=:minimize,maximize,close')
            items.append((data, roots[relative.parts[0]].joinpath(*relative.parts[1:])))
    layer = ROOT / 'extensions' / LAYER_UUID
    items += [(p, home / '.local/share/gnome-shell/extensions' / LAYER_UUID / p.relative_to(layer))
              for p in sorted(layer.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    media = ROOT / 'desktop/netflix-remote'
    items += [(p, home / '.local/share/netflix-remote' / p.relative_to(media))
              for p in sorted(media.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    items += [(ROOT / 'desktop/mediactl.py', home / '.local/share/island-desktop/mediactl.py'),
              (ROOT / 'bin/island-media', home / '.local/bin/island-media'),
              (ROOT / 'systemd/netflix-remote.service', home / '.config/systemd/user/netflix-remote.service')]
    css = f'@import url("{(home / ".themes/Island-WhiteSur/gtk-4.0/gtk.css").as_uri()}");\n'.encode()
    items.append((css, home / '.config/gtk-4.0/gtk.css'))
    for app, name, icon in [('netflix', 'Netflix · desktop player', 'video-x-generic'),
                            ('youtube', 'YouTube · desktop player', 'video-x-generic'),
                            ('pair', 'Netflix · phone remote', 'input-gaming')]:
        # Desktop-entry quoting: never interpolate a path as shell code.
        script = str(home / '.local/share/island-desktop/mediactl.py').replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
        entry = f'[Desktop Entry]\nType=Application\nName={name}\nExec=/usr/bin/python3 "{script}" {app}\nIcon={icon}\nCategories=AudioVideo;Player;\nTerminal=false\n'
        items.append((entry.encode(), home / '.local/share/applications' / f'island-{app}.desktop'))
    return items


def desired(home):
    wallpaper = (home / '.local/share/island-desktop/wallpaper/WhiteSur-light.jpg').as_uri()
    values = {
        'org.gnome.desktop.interface': {'gtk-theme': "'Island-WhiteSur'", 'icon-theme': "'Island-WhiteSur'", 'font-name': "'Inter 10'"},
        'org.gnome.desktop.wm.preferences': {'theme': "'Island-WhiteSur'", 'button-layout': "':minimize,maximize,close'"},
        'org.gnome.desktop.background': {'picture-uri': repr(wallpaper), 'picture-uri-dark': repr(wallpaper), 'picture-options': "'zoom'"},
        'org.gnome.shell.extensions.dash-to-dock': {
            'dock-position': "'BOTTOM'", 'dock-fixed': 'false', 'extend-height': 'false',
            'dash-max-icon-size': '30', 'icon-size-fixed': 'true', 'height-fraction': '0.9',
            'autohide': 'true', 'intellihide': 'true', 'require-pressure-to-show': 'true',
            'pressure-threshold': '100.0', 'transparency-mode': "'FIXED'",
            'background-opacity': '0.75', 'custom-background-color': 'true', 'background-color': "'#b9bec7'",
            'click-action': "'minimize-or-previews'", 'running-indicator-style': "'DOTS'",
            'show-mounts': 'false', 'show-trash': 'false'},
    }
    return {f'{schema}/{key}': value for schema, rows in values.items() for key, value in rows.items()}


def read_settings(run, home):
    return {name: run('gsettings', 'get', *name.split('/')) for name in desired(home)}


def apply_settings(run, values):
    for name, value in values.items():
        run('gsettings', 'set', *name.split('/'), value)


def restore_settings(run, before, after):
    """Restore each setting independently, retaining later user choices."""
    for name, old in before.items():
        if run('gsettings', 'get', *name.split('/')) == after.get(name):
            run('gsettings', 'set', *name.split('/'), old)
