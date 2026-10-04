"""Receiver integration uses source-built UxPlay and Ubuntu Shairport Sync."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
UNITS = ['ytmusic-airplay.service', 'airplay-screen.service', 'ytmusic-airplay-auto-pause.service']


def plan(home):
    items = [(ROOT / 'receivers' / name, home / '.config/systemd/user' / name) for name in UNITS]
    items += [(ROOT / 'receivers/shairport-sync.conf', home / '.config/ytmusic-airplay/shairport-sync.conf'),
              (ROOT / 'receivers/auto-pause', home / '.local/share/island-desktop/receivers/auto-pause'),
              (b'# Receiver arguments are defined by the user service.\n', home / '.config/airplay-island/uxplayrc')]
    return items


def preflight(run, home):
    binary = home / '.local/share/island-desktop/receivers/bin/uxplay'
    if not binary.is_file():
        raise RuntimeError('First build the pinned UxPlay receiver: python3 setup_receivers.py')
    version = run('/usr/bin/shairport-sync', '-V')
    if not all(feature in version.split('-') for feature in ['pa', 'metadata', 'dbus', 'mpris']):
        raise RuntimeError('Shairport Sync must provide PulseAudio, metadata, D-Bus and MPRIS support.')
    if run('systemctl', 'show', '--property=ActiveState', '--value', 'shairport-sync.service') == 'active':
        raise RuntimeError('The system Shairport service already uses the receiver port. Disable that service before using the user receiver; see docs/DESKTOP.md.')
    run(str(binary), '-h')
