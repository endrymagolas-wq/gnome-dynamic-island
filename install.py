#!/usr/bin/env python3
"""User-local installation with a file manifest and reversible settings."""
import argparse, ast, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
UUIDS = ['airplay-island@avalon.local', 'island-window-controls@avalon.local']
THEME = 'Island-Ink'

def run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=15).stdout.strip()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def settings():
    return {
        'enabled': ast.literal_eval(run('gsettings', 'get', 'org.gnome.shell', 'enabled-extensions').removeprefix('@as ')),
        'disabled': ast.literal_eval(run('gsettings', 'get', 'org.gnome.shell', 'disabled-extensions').removeprefix('@as ')),
        'theme': run('gsettings', 'get', 'org.gnome.shell.extensions.user-theme', 'name'),
    }

def apply_settings(value):
    run('gsettings', 'set', 'org.gnome.shell', 'disabled-extensions', repr(value['disabled']))
    run('gsettings', 'set', 'org.gnome.shell', 'enabled-extensions', repr(value['enabled']))
    run('gsettings', 'set', 'org.gnome.shell.extensions.user-theme', 'name', value['theme'])

def plan(home):
    items = []
    for uuid in UUIDS:
        root = SOURCE / 'extensions' / uuid
        for source in sorted(root.rglob('*')):
            if source.is_file():
                items.append((source, home / '.local/share/gnome-shell/extensions' / uuid / source.relative_to(root)))
    root = SOURCE / 'theme' / THEME
    for source in sorted(root.rglob('*')):
        if source.is_file():
            items.append((source, home / '.themes' / THEME / source.relative_to(root)))
    base = home / '.local/share/island-desktop/assistant'
    for source in sorted((SOURCE / 'assistant').glob('*.py')):
        items.append((source, base / source.name))
    items += [(SOURCE / 'bin/island-assistant', home / '.local/bin/island-assistant'),
              (SOURCE / 'systemd/island-assistant.service', home / '.config/systemd/user/island-assistant.service')]
    return items

def install(args):
    home = Path.home()
    items = plan(home)
    if not args.no_activate:
        if 'GNOME Shell 46.' not in run('gnome-shell', '--version'):
            raise RuntimeError('This beta supports GNOME Shell 46 only.')
        before = settings()  # Preflight before writing any files.
        if 'user-theme@gnome-shell-extensions.gcampax.github.com' not in run('gnome-extensions', 'list'):
            raise RuntimeError('Install GNOME User Themes first; see README.')
    else:
        before = None
    if args.dry_run:
        print('\n'.join(str(target) for _, target in items))
        print('Dry run: no files, settings or services changed.')
        return
    root = home / '.local/share/island-desktop/install-backups' / str(time.time_ns())
    root.mkdir(parents=True, mode=0o700)
    manifest = {'version': (SOURCE / 'VERSION').read_text().strip(), 'home': str(home),
                'files': [], 'before': before, 'after': None, 'unit_before': None}
    if before:
        unit = run('systemctl', '--user', 'show', '--property=UnitFileState,ActiveState', 'island-assistant.service')
        manifest['unit_before'] = dict(line.split('=', 1) for line in unit.splitlines() if '=' in line)
    def copy(source, target, contents=None):
        if target.is_symlink() or any(parent.is_symlink() for parent in target.parents if parent != home):
            raise RuntimeError(f'Refusing symlink target: {target}')
        index = str(len(manifest['files']))
        backup = root / index if target.exists() else None
        if backup:
            shutil.copy2(target, backup)
        target.parent.mkdir(parents=True, exist_ok=True)
        if contents is None:
            shutil.copy2(source, target)
        else:
            target.write_text(contents)
            target.chmod(0o600)
        manifest['files'].append({'target': str(target), 'backup': str(backup) if backup else None,
                                  'installed_sha256': digest(target)})
        (root / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    try:
        for source, target in items:
            copy(source, target)
        (home / '.local/bin/island-assistant').chmod(0o755)
        prefs = home / '.local/share/island-desktop/assistant/preferences.json'
        if not prefs.exists():
            copy(None, prefs, '{"enabled": false, "economy": true, "muted_kinds": []}\n')
        if before:
            theme_uuid = 'user-theme@gnome-shell-extensions.gcampax.github.com'
            required = UUIDS + [theme_uuid]
            after = {'enabled': list(dict.fromkeys([x for x in before['enabled'] if x != 'cortiva-window-controls@avalon.local'] + required)),
                     'disabled': list(dict.fromkeys([x for x in before['disabled'] if x not in required] + (['cortiva-window-controls@avalon.local'] if 'cortiva-window-controls@avalon.local' in before['enabled'] else []))),
                     'theme': repr(THEME)}
            manifest['after'] = after
            (root / 'manifest.json').write_text(json.dumps(manifest, indent=2))
            apply_settings(after)
            run('systemctl', '--user', 'daemon-reload')
    except Exception:
        print(f'Installation interrupted. Recovery manifest: {root / "manifest.json"}', file=sys.stderr)
        raise
    print(f'Installed. Recovery manifest: {root / "manifest.json"}')
    print('Save work, then log out and back in. No automatic logout.')
    print('Assistant starts OFF. Optional setup: python3 setup_assistant.py, then island-assistant on')

def restore(args):
    path = Path(args.manifest).resolve()
    manifest = json.loads(path.read_text())
    home = Path.home().resolve()
    if manifest['home'] != str(home):
        raise RuntimeError('Manifest belongs to a different home directory.')
    allowed = {str(target) for _, target in plan(home)}
    allowed.add(str(home / '.local/share/island-desktop/assistant/preferences.json'))
    for item in manifest['files']:
        target = Path(item['target'])
        if str(target) not in allowed or target.is_symlink() or any(parent.is_symlink() for parent in target.parents if parent != home):
            raise RuntimeError('Invalid restore target.')
        if target.exists() and digest(target) != item['installed_sha256'] and target.name != 'preferences.json':
            raise RuntimeError(f'File changed since installation; preserve it before restoring: {target}')
        if item['backup'] and (Path(item['backup']).parent != path.parent or not Path(item['backup']).is_file()):
            raise RuntimeError('Invalid or missing backup.')
    current = settings() if manifest['before'] else None
    # Only the package-owned service is stopped; state/history/model files are retained.
    if current:
        subprocess.run(['systemctl', '--user', 'disable', '--now', 'island-assistant.service'], capture_output=True, timeout=15)
    for item in reversed(manifest['files']):
        target = Path(item['target'])
        if target.name == 'preferences.json' and target.exists() and digest(target) != item['installed_sha256']:
            continue  # Preserve subsequent explicit assistant choices.
        if item['backup']:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item['backup'], target)
        else:
            target.unlink(missing_ok=True)
    if current and current == manifest['after']:
        apply_settings(manifest['before'])
    elif current:
        print('Desktop settings changed since install; kept current settings.')
    if current:
        run('systemctl', '--user', 'daemon-reload')
    if current and manifest.get('unit_before'):
        unit = manifest['unit_before']
        if unit.get('UnitFileState') == 'enabled':
            run('systemctl', '--user', 'enable', 'island-assistant.service')
        if unit.get('ActiveState') == 'active':
            run('systemctl', '--user', 'start', 'island-assistant.service')
    print('Original files restored. Personal history and model cache retained. Log out and back in.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('install')
    add.add_argument('--dry-run', action='store_true')
    add.add_argument('--no-activate', action='store_true', help='Copy only; do not change desktop settings or services')
    commands.add_parser('restore').add_argument('manifest')
    args = parser.parse_args()
    try:
        (install if args.command == 'install' else restore)(args)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
