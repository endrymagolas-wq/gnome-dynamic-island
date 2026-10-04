# Claude Code construction scene

The island can show a tiny worker reacting to Claude Code hooks:

| Event | Scene |
| --- | --- |
| Prompt submitted | Walks to the desk |
| Edit / Write / MultiEdit / NotebookEdit | Types; another storey grows (up to four) |
| Recognized test command starts | Walks over and inspects the building |
| Test tool fails | Smoke and «блять…» |
| Permission requested | Walks to the edge and waves |
| Claude stops | Sits down with coffee for 15 seconds |

Install/update the extension using the normal repository installer and log out
and back in. Then opt in to hooks:

```sh
python3 ~/.local/share/island-desktop/assistant/claude_hook.py --install
```

Restart Claude Code so it loads the updated hook settings. Existing hooks and
other settings are preserved. The first existing settings file is backed up as
`~/.claude/settings.json.before-island`. For project-specific hooks, pass
`--settings /path/to/project/.claude/settings.local.json`.

To remove this integration, delete just the hook entries whose command references
`claude_hook.py` from that settings file. The regular extension restore removes
its installed files but does not modify Claude settings.

No prompt, file contents, command text or tool output is sent to the desktop;
only a fixed state name crosses the session bus. Hooks never approve permissions
and fail silently when the extension or session bus is unavailable. Animation
respects GNOME's animation setting. Volume/connection notices and focus timers
have priority. Activity expires after three minutes without another hook event;
permission requests also expire, but remain pending in Claude. With multiple
Claude sessions, the most recent event controls the scene.

Test detection covers common pytest/Jest/Vitest/Mocha/CTest commands, package
manager `test` scripts, Cargo/Go/.NET tests, Python unittest and scripts under
`tests/`. Custom scripts may appear as ordinary work. Test failure relies on
`PostToolUseFailure` or a nonzero exit code / error flag in the tool response.

For a desktop smoke check, call the scene directly:

```sh
gdbus call --session --dest org.gnome.Shell \
  --object-path /org/avalon/AirplayIsland \
  --method org.avalon.AirplayIsland.ClaudeState editing
```

Replace `editing` with `starting`, `testing`, `failed`, `permission`, or `done`.
Check these on GNOME 46, also with animations disabled, focus/volume notices,
screen lock and extension disable/re-enable. Portable tests cannot verify native
Cairo rendering or compositor behavior.
