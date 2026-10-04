#!/usr/bin/env python3
"""Desktop web-player launchers and explicit Netflix phone-remote setup."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE = Path.home() / '.local/share/netflix-remote'
CONFIG = Path.home() / '.config/island-desktop/media.env'


def browser():
    for name in ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']:
        if path := shutil.which(name):
            return path
    raise RuntimeError('Install Google Chrome or Chromium first. Netflix also needs browser DRM support.')


def launch(app):
    executable = browser()
    profile = BASE / 'chrome' if app == 'netflix' else Path.home() / '.local/share/island-desktop/youtube-browser'
    profile.mkdir(parents=True, exist_ok=True, mode=0o700)
    preferences = profile / 'Default/Preferences'
    if not preferences.exists():
        preferences.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        preferences.write_text(json.dumps({'browser': {'custom_chrome_frame': False},
                                           'extensions': {'theme': {'system_theme': 1, 'id': ''}}}))
        preferences.chmod(0o600)
    args = [executable, f'--user-data-dir={profile}', '--no-first-run', '--no-default-browser-check',
            '--class=NetflixRemote' if app == 'netflix' else '--class=IslandYouTube',
            '--app=https://www.netflix.com/browse' if app == 'netflix' else '--app=https://www.youtube.com/']
    if app == 'netflix':
        args += ['--remote-debugging-address=127.0.0.1', '--remote-debugging-port=9327']
    subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def remote_on(lan=False):
    node = shutil.which('node')
    if not node or int(subprocess.check_output([node, '-p', 'process.versions.node.split(".")[0]'], text=True).strip()) < 22:
        raise RuntimeError('Netflix remote requires Node.js 22 or newer on PATH.')
    browser()
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if any(c in node for c in '\r\n'):
        raise RuntimeError('Unsupported Node executable path.')
    escaped = node.replace('\\', '\\\\').replace('"', '\\"')
    CONFIG.write_text(f'REMOTE_LAN={int(lan)}\nISLAND_NODE="{escaped}"\n')
    CONFIG.chmod(0o600)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'enable', '--now', 'netflix-remote.service'], check=True)
    # A running unit must reload its explicit LAN setting.
    subprocess.run(['systemctl', '--user', 'restart', 'netflix-remote.service'], check=True)
    print('Netflix remote enabled for the local LAN.' if lan else 'Netflix remote enabled for this PC only.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['netflix', 'youtube', 'pair', 'remote-on', 'remote-off', 'status'])
    parser.add_argument('--lan', action='store_true', help='Allow authenticated phones on the same private IPv4 subnet')
    args = parser.parse_args()
    try:
        if args.command in ('netflix', 'youtube'):
            launch(args.command)
        elif args.command == 'remote-on':
            remote_on(args.lan)
        elif args.command == 'remote-off':
            subprocess.run(['systemctl', '--user', 'disable', '--now', 'netflix-remote.service'], check=True)
        elif args.command == 'pair':
            if not CONFIG.exists() or 'REMOTE_LAN=1' not in CONFIG.read_text().splitlines():
                raise RuntimeError('First enable phone access: island-media remote-on --lan')
            subprocess.run(['/usr/bin/python3', str(BASE / 'show-pairing.py')], check=True)
        else:
            subprocess.run(['systemctl', '--user', 'status', 'netflix-remote.service'], check=False)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
