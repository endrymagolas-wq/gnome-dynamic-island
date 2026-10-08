"""Fetch pinned public portable runtimes; never reads a user's installed settings."""
import argparse, hashlib, json, urllib.request, zipfile
from pathlib import Path

PYTHON_URL = 'https://www.python.org/ftp/python/3.13.14/python-3.13.14-embed-amd64.zip'
PYTHON_SHA256 = '90b4e5b9898b72d744650524bff92377c367f44bd5fbd09e3148656c080ad907'
LIVELY_URL = 'https://github.com/lively-community/lively/releases/download/v2.0.4.0/lively_command_utility.zip'
LIVELY_SHA256='39b74812b6c736a45eb7ab5037aa953930ba34413e7f2d730e73068bc9b5763d'
LIVELY_SOURCE_SHA256='e0fae158e8909261fbe7267d3de337898c1ec568b6bc3c88f76d7a9d20e43530'

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'IslandDesktop-release/0.4.0'}), timeout=120) as r:
        return r.read()

def download(url, dest, expected=None):
    data = dest.read_bytes() if dest.exists() else get(url)
    sha = hashlib.sha256(data).hexdigest()
    if expected and sha != expected: raise ValueError(f'Hash mismatch: {dest.name}')
    dest.write_bytes(data)
    return {'file':dest.name, 'url':url, 'sha256':sha, 'bytes':len(data)}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True); args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    records=[download(PYTHON_URL,args.out/'python-3.13.14-embed-amd64.zip',PYTHON_SHA256)]
    metadata=json.loads(get('https://pypi.org/pypi/psutil/7.2.2/json'))
    wheels=[f for f in metadata['urls'] if f['filename'].endswith('abi3-win_amd64.whl')]
    assert len(wheels)==1, [f['filename'] for f in wheels]
    wheel=wheels[0]
    records.append(download(wheel['url'],args.out/wheel['filename'],wheel['digests']['sha256']))
    sdist=next(f for f in metadata['urls'] if f['packagetype']=='sdist')
    records.append(download(sdist['url'],args.out/sdist['filename'],sdist['digests']['sha256']))
    records.append(download(LIVELY_URL,args.out/'lively_command_utility.zip',LIVELY_SHA256))
    # Include the exact corresponding utility source, not only a moving repository link.
    records.append(download('https://codeload.github.com/lively-community/lively/zip/refs/tags/v2.0.4.0',args.out/'lively-v2.0.4.0-source.zip',LIVELY_SOURCE_SHA256))
    records.append(download('https://raw.githubusercontent.com/lively-community/lively/v2.0.4.0/LICENSE',args.out/'Lively-GPL-3.0.txt'))
    (args.out/'dependencies.json').write_text(json.dumps({'python':'3.13.14','psutil':'7.2.2','livelyCLI':'2.0.4.0','downloads':records},indent=2)+'\n')
    print(json.dumps({'downloads':len(records),'bytes':sum(f['bytes'] for f in records),'manifest':str(args.out/'dependencies.json')}))

if __name__=='__main__': main()
