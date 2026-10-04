#!/usr/bin/env python3
"""Deterministic tests without modifying the real desktop or loading the model."""
import os, subprocess, sys, tempfile
from pathlib import Path
root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ, ISLAND_ASSISTANT_DATA_DIR=td, XDG_RUNTIME_DIR=td)
    for test in sorted((root / 'tests/policy').glob('*.py')):
        subprocess.run([sys.executable, str(test)], check=True, env=env)
    subprocess.run([sys.executable, str(root / 'tests/check_install.py')], check=True, env=env, stdout=subprocess.DEVNULL)
    subprocess.run(['node', str(root / 'tests/panel-intent.js')], check=True, env=env)
print('PASS 6 assistant suites, installer round trip and panel-intent regression suite')
