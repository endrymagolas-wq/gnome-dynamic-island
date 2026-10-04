#!/usr/bin/env python3
"""Build a pinned UxPlay with the tested local HLS fixes; never enables services."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent
REVISION = 'df67c212a433cf6dda3676dd40c097900d24e645'
UPSTREAM = 'https://github.com/FDH2/UxPlay.git'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    base = Path.home() / '.local/share/island-desktop/receivers'
    if args.dry_run:
        print(f'Build UxPlay {REVISION} with receivers/uxplay.patch into {base}/bin/uxplay. No services or firewall changes.')
        return 0
    try:
        for name in ['git', 'cmake', 'make', 'g++', 'pkg-config']:
            if not shutil.which(name):
                raise RuntimeError('Missing build dependency: ' + name + '. See docs/DESKTOP.md.')
        subprocess.run(['pkg-config', '--exists', 'gstreamer-1.0', 'gstreamer-video-1.0', 'gstreamer-app-1.0', 'libplist-2.0', 'openssl'], check=True)
        base.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.TemporaryDirectory(prefix='uxplay-build-', dir=base) as td:
            work = Path(td)
            subprocess.run(['git', 'init', str(work / 'source')], check=True, stdout=subprocess.DEVNULL)
            subprocess.run(['git', '-C', str(work / 'source'), 'fetch', '--depth=1', UPSTREAM, REVISION], check=True)
            subprocess.run(['git', '-C', str(work / 'source'), 'checkout', '--detach', 'FETCH_HEAD'], check=True)
            actual = subprocess.check_output(['git', '-C', str(work / 'source'), 'rev-parse', 'HEAD'], text=True).strip()
            if actual != REVISION:
                raise RuntimeError('UxPlay source revision mismatch.')
            subprocess.run(['git', '-C', str(work / 'source'), 'apply', str(SOURCE / 'receivers/uxplay.patch')], check=True)
            subprocess.run(['cmake', '-S', str(work / 'source'), '-B', str(work / 'build'), '-DCMAKE_BUILD_TYPE=Release'], check=True)
            subprocess.run(['cmake', '--build', str(work / 'build'), '--parallel', str(min(4, os.cpu_count() or 1))], check=True)
            dest = base / 'bin/uxplay'
            dest.parent.mkdir(exist_ok=True)
            if dest.is_symlink():
                raise RuntimeError('Refusing symlink receiver binary.')
            shutil.copy2(work / 'build/uxplay', dest.with_suffix('.new'))
            dest.with_suffix('.new').chmod(0o755)
            dest.with_suffix('.new').replace(dest)
        print('Built UxPlay. Next: python3 install.py install --desktop --receivers')
        print('This build step did not enable receivers or modify firewall rules.')
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
