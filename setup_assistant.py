#!/usr/bin/env python3
"""Explicit optional CPU model download. Does not enable monitoring."""
import argparse, os, subprocess, sys
from pathlib import Path

REVISION = '55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851'
BASE = Path.home() / '.local/share/island-desktop/assistant'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', default=sys.executable, help='Python 3.10 or newer with venv support')
    args = parser.parse_args()
    if not (BASE / 'monitor.py').is_file():
        parser.error('Run install.py install first.')
    subprocess.run([args.python, '-m', 'venv', str(BASE / 'venv')], check=True)
    python = str(BASE / 'venv/bin/python')
    subprocess.run([python, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
    subprocess.run([python, '-m', 'pip', 'install', 'torch==2.14.1+cpu', '--index-url', 'https://download.pytorch.org/whl/cpu'], check=True)
    subprocess.run([python, '-m', 'pip', 'install', 'laya==0.3.20', 'transformers==5.18.0', 'huggingface-hub==1.33.0'], check=True)
    env = dict(os.environ)
    env.pop('HF_HUB_OFFLINE', None)
    script = f"from huggingface_hub import snapshot_download; snapshot_download('convaiinnovations/laya', revision={REVISION!r}, allow_patterns=['multilingual/*'], local_dir={str(BASE / 'model')!r})"
    subprocess.run([python, '-c', script], check=True, env=env)
    # Populate tokenizer/encoder configuration caches during explicit online setup.
    subprocess.run([python, '-c', f"import torch,laya; torch.set_num_threads(2); laya.load({str(BASE / 'model/multilingual')!r}, device='cpu')"], check=True, env=env)
    if not (BASE / 'model/multilingual/model.safetensors').is_file():
        raise RuntimeError('Model download incomplete.')
    print('CPU model installed. Monitoring remains OFF until you run: island-assistant on')

if __name__ == '__main__':
    main()
