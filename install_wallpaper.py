#!/usr/bin/env python3
"""Install only the cartoon wallpaper; does not change panels or wallpaper settings."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
UUID = 'cartoon-island@avalon.local'


def install(home, files_only=False):
    target = home / '.local/share/gnome-shell/extensions' / UUID
    if target.exists():
        backup = home / '.local/share/cartoon-island/backups' / str(time.time_ns())
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(target, backup)
        print(f'Previous extension backed up: {backup}')
    shutil.copytree(ROOT / 'extensions' / UUID, target, dirs_exist_ok=True)
    hooks = home / '.local/share/cartoon-island/claude_hook.py'
    hooks.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'assistant/claude_hook.py', hooks)
    if not files_only:
        result = subprocess.run(['gnome-extensions', 'enable', UUID], capture_output=True, text=True)
        if result.returncode:
            print('Log out and back in, then run: gnome-extensions enable ' + UUID)
    print(f'Wallpaper extension installed: {target}')
    print(f'Optional Claude hooks: {sys.executable} {hooks} --install')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--files-only', action='store_true', help='Copy files without changing the running GNOME session')
    args = parser.parse_args()
    install(args.home, args.files_only)


if __name__ == '__main__':
    main()
