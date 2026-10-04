#!/usr/bin/env python3
"""Optional convenience launcher; no phone-remote credentials shipped."""
from pathlib import Path
import subprocess
helper = Path.home() / '.local/share/island-desktop/mediactl.py'
if helper.is_file():
    subprocess.run(['/usr/bin/python3', str(helper), 'netflix'], check=True)
else:
    subprocess.run(['xdg-open', 'https://www.netflix.com/'], check=True)
