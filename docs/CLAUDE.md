# Resort island live wallpaper

This is a full-screen resort wallpaper, behind windows and desktop icons. Its
3D appearance is baked into an image: a Mediterranean bungalow, terrace, palms,
beach and clear sea. A small animated worker reacts to programs on your computer.
It is a separate optional GNOME 46 extension; the panel extension is not required.

## Performance approach

- The background is one decoded image texture, reused on every monitor. It is
  never re-rendered as 3D geometry or processed by a full-screen shader at runtime.
- Character poses, walking directions and smoke are baked into a transparent
  atlas. Water is a separate masked 24-frame, 2-second loop at 12 fps. Runtime
  animation changes texture offsets and actor positions, without video decoding
  or live water shaders.
- A small guest cabana changes its cached construction stage only after edits.
  The main resort bungalow and the rest of the island remain in the background.
- Native animation is capped at approximately 12 frames per second. There is no
  animation timer when water is switched off and the worker is stationary without
  a looping action.
- Lock/greeter and coverage by opaque maximized/fullscreen windows pause animation.
  Window and workspace events wake it again. A single expiration timer still
  returns a Claude event to ordinary application focus when its time expires.
- Water animation is on by default. Two cached PNG banks contain the complete
  masked loop: waves, shore foam and reflections. The island, house, beach, palms
  and rocks are protected by the alpha mask. Switching water off reveals the
  original still sea. The full water plane is composited while visible; it is
  not merely three small glint patches.
- GNOME's animation preference freezes poses and disables water glints.

The background texture is 1536×1024; the character atlas is 1280×2084. Water
uses two 3072×1536 banks (each a 4×3 grid of 768×512 frames). All decoded RGBA
textures total about 53 MiB before compositor buffers and implementation overhead.
The indexed banks share a palette and take about 2.5 MiB on disk together.
Actual CPU/GPU usage on native GNOME remains unmeasured. Screen composition still
costs work whenever something moves, particularly on high-resolution monitors.
This design reduces wallpaper work; it does not guarantee zero system load.

## Install

From the repository root:

```sh
python3 install_wallpaper.py
```

Log out and back in, then enable:

```sh
gnome-extensions enable cartoon-island@avalon.local
```

Existing background settings are preserved. Disabling the extension reveals your
previous wallpaper. Each monitor fits the plate without stretching or clipping
its walkable area. Native GNOME 46 texture loading, desktop-icon ordering, window
coverage, monitor lifecycle and disable/re-enable still need a real-session check.

## Program reactions

| Active program | Worker |
| --- | --- |
| Code editor or terminal | Walks to the outdoor desk |
| Browser | Walks to the back lawn and reads a map |
| Other application / desktop | Relaxes with coffee at the bench |

This observes application focus, not screen contents. Precise editing and test
actions require application events. Claude Code is the first integration:

```sh
python3 ~/.local/share/cartoon-island/claude_hook.py --install
```

Restart Claude Code. Existing settings and hooks are preserved; the first existing
settings file is backed up as `~/.claude/settings.json.before-island`. For project
hooks, pass `--settings /path/to/project/.claude/settings.local.json`.

| Claude event | Scene |
| --- | --- |
| Prompt submitted | Walks to the desk |
| Edit / Write / MultiEdit / NotebookEdit | Types; the guest cabana gains a construction stage |
| Recognized test command starts | Walks over and inspects the bungalow |
| Test tool fails | Smoke and «блять…» |
| Permission requested | Walks to the lookout and waves |
| Claude stops | Sits at the bench with coffee |

Claude events take priority over focus. Only a fixed state name crosses the
session bus, never prompt text, filenames, commands or output. Hooks do not approve
permissions and fail silently when the extension is unavailable. Activity expires
after three minutes without another event; completion expires after 20 seconds.
The latest event wins across multiple Claude sessions. Construction has four
stages and resets at the start of a new task.

Test detection covers pytest/Jest/Vitest/Mocha/CTest, package-manager `test`
scripts, Cargo/Go/.NET tests, Python unittest and scripts under `tests/`.
Custom scripts may appear as ordinary work. Failure relies on
`PostToolUseFailure` or a nonzero exit code / error flag in the tool response.

## Preview and native checks

```sh
python3 -m http.server 8000 --bind 127.0.0.1
# Open http://127.0.0.1:8000/preview/cartoon-island.html
```

The browser preview uses the same atlas, layout and reaction model. Its controls
simulate events. The camera is fixed because the background is pre-rendered.
The preview does not use WebGL or draw a full-screen canvas. It pauses when the
tab is hidden and stops its animation interval in idle/reduced-motion states.

Native smoke check:

```sh
gdbus call --session --dest org.gnome.Shell \
  --object-path /org/avalon/CartoonIsland \
  --method org.avalon.CartoonIsland.ClaudeState editing
```

Repeat with `starting`, `testing`, `failed`, `permission`, `done`. Water control:

```sh
gdbus call --session --dest org.gnome.Shell \
  --object-path /org/avalon/CartoonIsland \
  --method org.avalon.CartoonIsland.WaterAnimation true
```

Use `false` to return to still water. This choice resets to on when the extension
is re-enabled. Check lock, maximized/fullscreen coverage, workspace switches,
multiple monitors, reduced motion, and extension disable/re-enable. The worker
uses registered walkable routes; the baked scenery has no general 3D depth buffer.

## Disable / remove

```sh
gnome-extensions disable cartoon-island@avalon.local
```

Delete only hook entries referencing `claude_hook.py` if you also want to stop
sending events. The wallpaper does not change panel settings. Existing extension
files are backed up under `~/.local/share/cartoon-island/backups/` on reinstall.

## Asset rebuilding

`assets/resort.jpg` is an original AI-generated background exported to JPEG.
`assets/sprites.png` contains 3D character renders plus authored smoke/cabana
frames (the old glint strip is unused). `assets/water-0.png` and `water-1.png`
contain the masked water loop; `water-mask.svg` protects the static scene. The build-time renderer is `scene-3d.js`; it is not loaded by the wallpaper
or its ordinary preview. `preview/bake-atlas.html` produces the atlas in a canvas
for asset authoring. It is not part of runtime animation.

To rebuild water, serve the repository and start Chromium with a local
DevTools endpoint, then run:

```sh
python3 tools/bake_water.py --frames /tmp/resort-water-frames
```

This optional build tool requires `websockets` and Pillow.
`preview/bake-water.html` uses WebGL only during authoring to produce periodic
water displacement/reflections from the plate and mask. The normal preview and
GNOME extension load only its exported PNG frames. The mask and both banks are
validated by portable tests, including fixed scenery, changing sea pixels, a
bounded loop seam and matching palettes.
