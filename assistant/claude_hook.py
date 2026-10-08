#!/usr/bin/env python3
"""Optional Claude Code hooks. Only bounded animation state crosses the desktop transport."""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import os
import urllib.request

EVENTS = ('UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'PostToolUseFailure',
          'PermissionRequest', 'Notification', 'Stop', 'SessionEnd')
TEST_COMMAND = re.compile(r'\b(pytest|jest|vitest|mocha|ctest)\b|\b(npm|pnpm|yarn|bun|cargo|go|dotnet|uv)\s+(?:run\s+)?test\b|\bpython[\d.]*\s+(?:-m\s+unittest|\S*tests/)', re.I)


def state_for(data):
    event = data.get('hook_event_name')
    if event == 'UserPromptSubmit':
        return 'starting'
    if event in ('Stop', 'SessionEnd'):
        return 'done'
    if event == 'PermissionRequest' or (event == 'Notification' and data.get('notification_type') == 'permission_prompt'):
        return 'permission'
    tool = data.get('tool_name', '')
    inputs = data.get('tool_input') or {}
    command = inputs.get('command', '') if isinstance(inputs, dict) else ''
    testing = tool == 'Bash' and isinstance(command, str) and bool(TEST_COMMAND.search(command))
    if event == 'PreToolUse':
        if tool in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
            return 'editing'
        return 'testing' if testing else 'working'
    if event == 'PostToolUseFailure':
        return 'failed' if testing else 'working'
    if event == 'PostToolUse':
        response = data.get('tool_response') or {}
        if testing and isinstance(response, dict):
            code = response.get('exit_code', response.get('exitCode'))
            if response.get('is_error') or (code is not None and code != 0):
                return 'failed'
        return 'working'
    return None


def install(settings):
    settings.parent.mkdir(parents=True, exist_ok=True)
    original = settings.read_text(encoding='utf-8') if settings.exists() else None
    data = json.loads(original) if original else {}
    parts = [sys.executable, str(Path(__file__).resolve())]
    command = subprocess.list2cmdline(parts) if sys.platform == 'win32' else ' '.join(map(shlex.quote, parts))
    hooks = data.setdefault('hooks', {})
    for event in EVENTS:
        entries = hooks.setdefault(event, [])
        if any(h.get('command') == command for e in entries for h in e.get('hooks', [])):
            continue
        entry = {'hooks': [{'type': 'command', 'command': command, 'timeout': 3}]}
        if event in ('PreToolUse', 'PostToolUse', 'PostToolUseFailure', 'PermissionRequest', 'Notification'):
            entry['matcher'] = '*'
        entries.append(entry)
    if original is not None:
        backup = settings.with_name(settings.name + '.before-island')
        if not backup.exists():
            backup.write_text(original, encoding='utf-8')
    settings.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print(f'Claude hooks installed: {settings}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--settings', type=Path, default=Path.home() / '.claude/settings.json')
    args = parser.parse_args()
    if args.install:
        install(args.settings)
        return
    try:
        data = json.loads(sys.stdin.read(262145))
        if not isinstance(data, dict):
            return
        state = state_for(data)
        if state:
            if sys.platform == 'win32':
                connection = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ResortIsland/connection.json'
                target = json.loads(connection.read_text(encoding='utf-8'))
                # Never transmit payloads, prompts, filenames or commands.
                if not re.fullmatch(r'http://127\.0\.0\.1:\d+/event', target['url']):
                    return
                request = urllib.request.Request(target['url'], data=json.dumps({'state': state}).encode(),
                    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + target['token']})
                with urllib.request.urlopen(request, timeout=1) as response:
                    response.read(128)
                return
            subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.gnome.Shell',
                            '--object-path', '/org/avalon/CartoonIsland', '--method',
                            'org.avalon.CartoonIsland.ClaudeState', state],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired):
        pass  # An unavailable desktop must never block Claude.


if __name__ == '__main__':
    main()
