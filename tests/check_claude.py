"""Claude event mapping, nonblocking delivery and settings preservation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('claude_hook', root / 'assistant/claude_hook.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
assert m.state_for({'hook_event_name':'UserPromptSubmit'}) == 'starting'
for tool in ('Edit','Write','MultiEdit','NotebookEdit'):
    assert m.state_for({'hook_event_name':'PreToolUse','tool_name':tool}) == 'editing'
for command in ('npm test','pnpm run test','pytest -q','cargo test','python3 tests/run.py','uv run pytest'):
    event = {'hook_event_name':'PreToolUse','tool_name':'Bash','tool_input':{'command':command}}
    assert m.state_for(event) == 'testing', command
    event['hook_event_name'] = 'PostToolUseFailure'
    assert m.state_for(event) == 'failed'
    event.update(hook_event_name='PostToolUse', tool_response={'exit_code':1})
    assert m.state_for(event) == 'failed'
assert m.state_for({'hook_event_name':'PreToolUse','tool_name':'Bash','tool_input':{'command':'ls'}}) == 'working'
assert m.state_for({'hook_event_name':'PermissionRequest'}) == 'permission'
assert m.state_for({'hook_event_name':'Notification','notification_type':'permission_prompt'}) == 'permission'
assert m.state_for({'hook_event_name':'Notification','notification_type':'idle_prompt'}) is None
assert m.state_for({'hook_event_name':'Stop'}) == 'done'
with tempfile.TemporaryDirectory() as td:
    settings = Path(td) / 'settings.json'
    original = {'model':'sonnet', 'hooks':{'Stop':[{'hooks':[{'type':'command','command':'echo existing'}]}]}}
    settings.write_text(json.dumps(original))
    m.install(settings)
    once = settings.read_text()
    m.install(settings)
    assert settings.read_text() == once
    data = json.loads(once)
    assert data['model'] == 'sonnet' and data['hooks']['Stop'][0] == original['hooks']['Stop'][0]
    assert json.loads(settings.with_name('settings.json.before-island').read_text()) == original
with patch.object(sys,'argv',['claude_hook.py']), patch('sys.stdin') as stdin, patch.object(m.subprocess,'run',side_effect=FileNotFoundError):
    stdin.read.return_value = '{"hook_event_name":"Stop"}'
    m.main()
for payload in ('not JSON','[]','null'):
    subprocess.run([sys.executable,str(root/'assistant/claude_hook.py')],input=payload,text=True,check=True)
print('PASS Claude hook events, test failures, settings merge/idempotency and unavailable desktop')
