#!/usr/bin/env python3
"""Generate a private phone-pairing QR from actual private LAN interfaces."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import shutil
import subprocess


def private_addresses(interfaces):
    networks = [ipaddress.ip_network(cidr) for cidr in ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']]
    result = []
    for interface in interfaces:
        if 'UP' not in interface.get('flags', []) or interface.get('ifname') == 'lo':
            continue
        for item in interface.get('addr_info', []):
            try:
                address = ipaddress.ip_address(item['local'])
            except (KeyError, ValueError):
                continue
            if address.version == 4 and any(address in network for network in networks):
                result.append(str(address))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-open', action='store_true')
    parser.add_argument('--address', help='Select a local private IPv4 address if several interfaces exist')
    args = parser.parse_args()
    base = Path(os.environ.get('REMOTE_DATA', str(Path.home() / '.local/share/netflix-remote')))
    config = Path.home() / '.config/island-desktop/media.env'
    if os.environ.get('REMOTE_LAN') != '1' and (not config.exists() or 'REMOTE_LAN=1' not in config.read_text().splitlines()):
        raise SystemExit('Спочатку: island-media remote-on --lan')
    addresses = private_addresses(json.loads(subprocess.check_output(['ip', '-j', '-4', 'address'], text=True)))
    if args.address and args.address not in addresses:
        raise SystemExit('Адреса має належати активному локальному мережевому інтерфейсу.')
    if not addresses:
        raise SystemExit('Не знайдено домашню IPv4 мережу. Підключи ПК до Wi-Fi або Ethernet.')
    if len(addresses) > 1 and not args.address:
        raise SystemExit('Кілька мереж: повтори з --address та адресою Wi-Fi/Ethernet з команди ip -4 address.')
    encoder = shutil.which('qrencode')
    if not encoder:
        raise SystemExit('Встанови qrencode: sudo apt install qrencode')
    try:
        key = (base / 'remote-key').read_text().strip()
    except OSError:
        raise SystemExit('Пульт ще не запущено: island-media remote-on --lan')
    if not key:
        raise SystemExit('Порожній ключ підключення.')
    address = args.address or addresses[0]
    port = int(os.environ.get('REMOTE_PORT', '8765'))
    url = f'http://{address}:{port}/#key={key}'
    qr = subprocess.check_output([encoder, '-t', 'PNG', '-s', '8', '-m', '3', '-o', '-'], input=url.encode())
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = base / 'connect.png'
    path.write_bytes(qr); path.chmod(0o600)
    if not args.no_open:
        subprocess.Popen(['/usr/bin/python3', str(base / 'pairing-window.py'), str(path)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    print('QR saved locally. Keep it private.')


if __name__ == '__main__':
    main()
