# Cartoon island live wallpaper

This feature is **a full-screen animated desktop wallpaper**, not a panel widget.
The island has a turquoise ocean, palms, a desk, a growing little house and a
cartoon worker. Application windows and desktop icons stay above the scene.
It is a separate optional GNOME 46 extension; AirPlay/Dynamic Island is not
required or changed by its standalone installer.

## Install

From the repository root:

```sh
python3 install_wallpaper.py
```

Log out and back in so GNOME discovers the new extension, then enable it:

```sh
gnome-extensions enable cartoon-island@avalon.local
```

The existing background settings are preserved. Disabling the extension reveals
your previous wallpaper. Each monitor gets its own scene; aspect ratios are
preserved with centered cropping. The screen lock does not show the scene.
GNOME's animation preference is respected. Native GNOME 46 placement, desktop
icon ordering and lifecycle still need testing on a real session.

## React to programs

By default the worker responds to **application focus**:

| Active program | Worker |
| --- | --- |
| Code editor or terminal | Goes to the desk |
| Browser | Reads a little map |
| Other application / desktop | Relaxes with coffee |

This does not inspect screen content or infer whether a program is editing or
running tests. Precise actions need application events. Claude Code is the
first such integration:

```sh
python3 ~/.local/share/cartoon-island/claude_hook.py --install
```

Restart Claude Code to load the hooks. Existing settings and hooks are preserved;
the first existing settings file is backed up as
`~/.claude/settings.json.before-island`. For project-specific hooks, pass
`--settings /path/to/project/.claude/settings.local.json`.

| Claude event | Wallpaper scene |
| --- | --- |
| Prompt submitted | Walks to the desk |
| Edit / Write / MultiEdit / NotebookEdit | Types; another floor grows (up to four) |
| Recognized test command starts | Walks to the house and inspects it |
| Test tool fails | Smoke and «блять…» |
| Permission requested | Walks to the edge of the island and waves |
| Claude stops | Sits down with coffee for 20 seconds |

Claude events temporarily take priority over application focus. Only a fixed
state name crosses the session bus; prompt text, filenames, commands and tool
output never reach the wallpaper. Hooks never approve permissions and fail
silently if the extension is unavailable. Activity expires after three minutes
without another event. With multiple sessions, the most recent event wins.

Test detection covers pytest/Jest/Vitest/Mocha/CTest, package-manager `test`
scripts, Cargo/Go/.NET tests, Python unittest and scripts under `tests/`.
Custom scripts may appear as ordinary work. Failure relies on
`PostToolUseFailure` or a nonzero exit code / error flag in the tool response.

## Preview

Serve the repository locally and open the interactive preview:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
# Open http://127.0.0.1:8000/preview/cartoon-island.html
```

The preview uses the same world model and drawing function as the GNOME
extension. Buttons simulate events; they do not read local application activity.

For a native smoke check:

```sh
gdbus call --session --dest org.gnome.Shell \
  --object-path /org/avalon/CartoonIsland \
  --method org.avalon.CartoonIsland.ClaudeState editing
```

Repeat with `starting`, `testing`, `failed`, `permission`, `done`; check screen
lock, multiple monitors, animations disabled, monitor reconnection, and
extension disable/re-enable.

## Disable / remove

```sh
gnome-extensions disable cartoon-island@avalon.local
```

Delete only hook entries referencing `claude_hook.py` from your Claude settings
if you also want to stop sending events. The wallpaper does not change panel
settings. Existing extension files are backed up under
`~/.local/share/cartoon-island/backups/` when installed over a previous version.
