# Blender resort wallpaper on Windows

This is a full-screen wallpaper, independent of the GNOME Dynamic Island panel.
The original GNOME extension remains available; it cannot run natively on Windows.

## Start on this PC

```powershell
pwsh -NoProfile -File wallpaper/launch.ps1 -InstallHooks
```

Requires Python 3.10+ and Lively Wallpaper. The launcher starts a small loopback
server, preserves existing Claude hooks, installs a Lively library entry and
checks Lively's persisted layout before reporting success. Restart Claude Code
after adding its hooks. No Blender, After Effects or live 3D renderer is needed
while the wallpaper is running. The host is not added to Windows startup.

The installed Microsoft Store version redirects its library to LocalCache.
The launcher handles that mapping. It downloads the official Lively command
utility v2.0.4.0 into `%LOCALAPPDATA%/ResortIsland/lively-cli`, because the tested
v2.2.1.0 utility throws an immutable-constructor exception on `setwp` here.
It does not downgrade Lively itself. The prior wallpaper layout is backed up
to `%LOCALAPPDATA%/ResortIsland/previous-layout.json`.

Use Lively's Customize controls to turn water off or choose 720p. Closing the
wallpaper in Lively reveals the ordinary desktop wallpaper. To restore the
previous Lively wallpaper, select its entry in the library; the backup records
its exact library path. To remove our hooks, remove only entries whose command
references this repository's `assistant/claude_hook.py`; keep unrelated hooks.

Open `http://127.0.0.1:18765/wallpaper/index.html?preview=1` for manual reaction
controls. The actual desktop URL omits those controls.
The preview ignores desktop coverage so it can animate inside an application
window; hidden-page and reduced-motion pause still apply. The ordinary desktop
continues to honor coverage pause.

## Events and privacy

The existing `state_for()` Claude event mapping is reused. Windows delivery uses
an authenticated HTTP POST to `127.0.0.1:18765`, while Linux keeps its existing
D-Bus transport. Prompt text, paths, tool commands and tool output never leave
the hook. The host exposes bounded state names and scene playback diagnostics.
Its token stays in the current user's LocalAppData and is regenerated at launch.
Claude events take priority over ordinary focus for 180 seconds (20 for done).
Latest event wins across sessions, matching the existing behavior.

| Trigger | Scene |
| --- | --- |
| Task starts | Walk to outdoor laptop |
| Edit / Write tools | Type and increase guest-cabana stage (up to four) |
| Recognized test command starts | Walk to inspect the guest cabana |
| Test failure | Smoke and `блять…` |
| Permission request | Walk to front beach and wave |
| Task finishes | Sit at coffee bench |
| Editor / terminal focus | Work at desk |
| Browser focus | Visit the back of the island |
| Other program / desktop | Coffee |

Other applications can send explicit states with `python wallpaper/emit.py
testing` (or any documented state). Focus detection observes executable names,
not file contents or keystrokes; it does not infer that arbitrary applications
have edited files or passed tests.

## Layers and registration

- `poster.png`: still complete scene, used when water is off.
- `water-1080.mp4` / `water-720.mp4`: 12-second, 360-frame H.264 loops at 30 fps,
  rendered from displaced Blender water geometry. Transmission, shoreline,
  shading and reflections are evaluated together offline.
- `static.png`: the fixed island environment, rendered with a water holdout.
  It locks the interior land pixels over the compressed video. A height-based
  feathered shore mask exposes the baked moving shoreline and foam; the plate
  cannot freeze the beach/water intersection. Both retain the same camera.
- `character.png`: transparent Blender-rendered rig poses, eight walk headings,
  nine reactions and four construction stages.
- `construction-depth.png`: the cabana's real per-pixel depth offsets, one tile
  per stage. Its wide footprint is not treated as an upright sprite plane.
- `depth.png`: camera-space depth matte from the same scene. The player compares
  scene depth with the projected vertical character plane per pixel. It handles
  palms, rocks, furniture and the cottage rather than using screen-space guesses.
- `scene.json`: camera matrix, real ground targets, anchors and sprite scale.

Pip, a friendly turquoise fantasy creature in yellow swim shorts, moves along the elevated plateau and the organically
perturbed beach slope. Perspective position
and scale come from the Blender camera. Routes use clear beach corridors around
the cottage. The depth comparison approximates the character as a vertical
sprite plane; it is not a full animated per-pixel 3D depth volume. Dynamic character
reflections are not baked into the ocean, because the walkable paths are on land.
The soft contact shadow is composited at the projected ground point.

Seven-frame cyclic temporal filtering softens Cycles sampling grain while
preserving 30 rendered frames per second. Padding comes from the end of the same
cycle, so the filter does not reset at the seam. Geometry and foam use exact
12-second sine/cosine periods, with one normal 1/30-second step from last to first.
This is geometric water rendering, not deformation of a background photograph.
The shipped H.264 uses intra-only frames: the original predicted-frame encode
introduced a compression-quality jump at the loop boundary despite continuous
PNG inputs. `tools/check_resort_water.py` verifies the decoded shipped boundary
and all 360 frames, rather than checking only the raw render.

Lively's pause event stops video playback and actor scheduling. The Windows host
also checks lock/input-desktop availability and union coverage by opaque windows
over the primary work area. Page visibility and reduced motion stop animation.
Multi-monitor per-display lock/coverage and physical lock/resume require separate
manual validation; the observer currently targets this PC's primary display.

## Reproduce the render

Current source: `art/island/resort-v5.blend`, with Resort_Island, Mascot_Pip,
Construction_Bake and Smoke_Bake scenes and packed image textures. V5 replaces
the rejected BlueDemon-shaped mascot with a generated mesh based directly on the
accepted cute turquoise reference. Antigravity obtained the textured GLB from
the official free Stable Fast 3D Space, including an improved 2048px export.
The working mesh has 19,980 vertices and 39,956 triangular faces after welding
UV seam duplicates. Its large soft ears and face stay attached to Head.
The retained Quaternius 43-bone skeleton is adapted from T-pose to the new A-pose,
then skinned; 14 original motions and ten editable task actions are saved.
The generated mesh has different provenance from the CC0 rig; see
[sources and credits](../art/ASSET_SOURCES.md). `resort-v4.blend` preserves the
previous mascot and approved sunny environment; `resort-v2.blend` preserves Snow/V3.

V5 reuses V4's unchanged water, static plate, depth, construction and smoke.
Only its 272 character sprites and metadata are rebuilt. Open V5 and execute
this through Blender MCP (the child is an offline render, never a wallpaper process):

```python
import bpy, subprocess
from pathlib import Path
root = Path(bpy.data.filepath).parents[2]
with open(root/'wallpaper/offline-render.log', 'w') as log:
    subprocess.run([bpy.app.binary_path, '--background', str(root/'art/island/resort-v5.blend'),
        '--python', str(root/'tools/render_resort_v5.py')], stdout=log, stderr=log,
        check=True, creationflags=subprocess.CREATE_NO_WINDOW)
```

Then `python tools/package_resort_v5.py --promote`. It checks all 272 alpha bounds
before replacing character/metadata and preserves V4 in
`../runtime-backups/v4-before-pip-v5/`. Reopen the saved source to restore the
editable rig/actions. For a full local mesh rebuild from the retained original
HQ GLB, start from V4 and execute `tools/build_pip_v5.py`; it saves a separate V5.

The following retained V4 pipeline reproduces the shared environment and water.

The packed source is reproducible with Blender 4.5.9. The offline worker
regenerates static/transparent plates, depth with leaf alpha, 272 worker sprites,
construction, smoke and 361 water frames. Launch it through Blender MCP with
the current saved source (Windows example):

```python
import bpy, subprocess
from pathlib import Path
root = Path(bpy.data.filepath).parents[2]
log = open(root/'wallpaper/offline-render.log', 'w')
for mode in ('sprites', 'layers', 'water'):
    subprocess.run([
        bpy.app.binary_path, '--background', '--threads', '8',
        str(root/'art/island/resort-v4.blend'), '--python',
        str(root/'tools/render_resort_v4.py'), '--', mode
    ], stdout=log, stderr=log, check=True,
       creationflags=subprocess.CREATE_NO_WINDOW)
```

Then, with FFmpeg and Pillow installed:

```powershell
python tools/package_resort_v4.py --promote
```

Frame 361 is the audit endpoint; it is excluded from the 360-frame video.
The packager rejects an incomplete render and checks all frame dimensions before
replacing the runtime bundle. Raw PNG sequences are retained locally but ignored
by Git in `wallpaper/assets/v4-stage/`. Runtime files and the editable `.blend`
are versioned. Run `draft` instead of `water` for a 480p look-development loop;
after `sprites` and `layers`, `package_resort_v4.py --preview` prepares the isolated
candidate at `index.html?preview=1&assets=v4`. It cannot promote a draft. Do not
run the source-saving `sprites` and `layers` workers together. The water worker
is read-only. `mascot-review` renders a larger transparent character proof.
Promotion preserves the former live bundle in `../runtime-backups/v3-before-pip/`;
reload Lively with `wallpaper/launch.ps1` after promotion.
Antigravity assisted licensed asset discovery/downloads. The current Pip reference
was generated with GPT; older art-direction references were generated in Flow.
References are not the animated water layer.
After Effects was not required; its exposed
MCP did not receive a reply from the local bridge panel during this run.

## Validation

V5's 272 offline sprites rendered in 40.64 seconds on this PC after excluding
archived meshes from viewport pose evaluation. Saved mesh/rig audit:
`docs/evidence/resort/source-v5-audit.json`. All nine reaction states, four edit
growth stages, smoke visibility, water-off, 720p and native pause controls were
verified in Lively using synthetic payloads through the real Claude hook transport;
screenshots and reports are under `docs/evidence/resort/v5/`. These checks do not
claim a paid Claude task or test command was actually executed.

Fresh V5 1080p measurements (`performance-v5.json`, three 30-second windows):

| State | CPU whole PC | Mean RSS | GPU 3D / decode | Dedicated GPU memory | Decoded fps |
| --- | ---: | ---: | ---: | ---: | ---: |
| Coffee | 1.52% | 806 MiB | 3.56% / 16.66% | 133 MiB | 29.97 |
| Editing | 1.64% | 820 MiB | 3.57% / 14.21% | 122 MiB | 29.97 |
| Native pause callback | 0.35% | 761 MiB | 0% / 0% | 156 MiB | 0 |

Two decoded frame drops occurred during the coffee window; none during editing.
CPU covers Lively core, its owned WebView2 processes and local host on 16 logical
CPUs. RSS sums shared mappings; GPU engine counters are not board power and
decoded fps is not physical monitor presentation. All Blender processes were
stopped. Benchmark overrides were restored. Physical lock/resume, exclusive
fullscreen applications and per-display multi-monitor behavior remain manual
checks. This run verified the native pause callback, not full desktop coverage.
The V4 video/atlas/still comparison below remains relevant because both water
file hashes are unchanged; it has not been relabeled as a new V5 measurement.

`tools/run_resort_v5_native.ps1` reproduces the fresh reaction/control/runtime
measurements and restores the ordinary policy, and `tools/report_resort_v5.py`
validates the measurement counters and unchanged water hashes.

```powershell
python tests/check_claude.py
python tests/check_resort_host.py
node tests/resort-scene.mjs
python tests/check_resort_depth.py
python tests/check_resort_construction_depth.py
python tools/check_resort_water.py
node tests/cartoon-island.mjs
python tools/validate_resort_v5.py
# V4's unchanged water/environment evidence remains under docs/evidence/resort.
# Run tools/audit_resort_v5.py inside Blender after reopening the V5 source.
```

The original full `tests/run.py` fails on Windows at `os.getuid()` in
`assistant/music_scene.py`. The same failure was reproduced on the untouched
PR baseline `14a163d37c7bb06d2455bd024383ac8b810effe1`; it is not a new regression.
See `docs/evidence/resort/` for measured results and remaining native checks.

`tools/audit_resort_v5.py`, run inside Blender after reopening the saved source,
checks packed textures, retained actions, the planted stride and that permission
gestures survive frame evaluation. The source action is detached before sprite
rendering so it cannot overwrite adjusted poses. The runtime's 0.4992 m/s travel
matches the retimed stance phase of the weighted leg IK.

For optional native remeasurement, first stop your owned Blender workers, then
run `tools/prepare_resort_atlas.py` and `tools/run_resort_v4_native.ps1`. This tool
requires exactly one active Resort wallpaper. It temporarily restarts Lively and
the owned host for active measurements, restores the fullscreen pause policy and
coverage observer, checks the native Lively pause callback, then reinstalls the ordinary entry.
It refuses to replace another active wallpaper or measure with Blender running.

Water uses offline Cycles/OptiX rendering: geometric periodic waves, periodically
advected fine bump normals, IOR 1.333, transmission, volume absorption and a
Nishita sky with a sun reflection. No runtime 3D shader is required.

## Measurements on this PC

Windows 11 Pro 10.0.26200, i9-9900K (16 logical CPUs), 32 GB RAM, RTX 3080
10 GB, primary display 1920×1080. Each CPU/GPU window lasted 30 seconds with
all owned Blender processes stopped. Scope includes the Lively core, the owned
WebView2 player and descendants, and the loopback event host.

| Mode | CPU % of whole PC | Mean summed RSS MiB | GPU 3D % | GPU decode % | Dedicated GPU MiB | Playback fps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Same 720p water as video | 2.49 | 680 | 0.65 | 8.02 | 71 | 29.98 |
| Same 720p water as atlas | 4.17 | 862 | 0.53 | 0.00 | 334 | 20.77 |
| Still image only | 0.15 | 602 | 0.00 | 0.00 | 53 | 0 |
| Full 1080p scene, coffee | 2.47 | 811 | 1.94 | 16.03 | 132 | 29.97 |
| Full 1080p scene, typing | 2.80 | 824 | 3.37 | 13.73 | 122 | 29.97 |
| Full scene, Lively pause callback | 0.36 | 784 | 0.00 | 0.00 | 156 | 0 |

Video is selected because it kept 30 decoded fps and used less CPU and memory
than the atlas. The atlas averaged about 48 ms between draws, with p95 about
192 ms. The decoded atlas occupies substantially more memory than its PNG files;
the browser's actual residency is reported above, rather than its theoretical
allocation. Shared GPU memory means were 11–25 MiB across these runs.

Active measurements temporarily used `--no-observer` and Lively's fullscreen
ignore setting because Codex covered the desktop. Both were restored before the
paused measurement and ordinary launch. The current desktop was not fully covered:
that initial measurement is retained as `v4/uncovered-run.json` and explicitly
excluded from pause evidence. The successful repeat used Lively's native pause
callback via its CLI. It held the decoded frame counter at 22 throughout the
interval, with video and actor scheduling paused. Earlier V3 coverage evidence
remains archived; it is not relabeled as a new V4 coverage run.
Pause reduces processing; it retains loaded assets and GPU allocations.

RSS can double-count shared mappings. GPU columns are separate Windows engine
counters at the current clock, not total board utilization or power. Video fps
counts decoded frames; atlas fps counts draw submissions. Neither proves physical
monitor presentation. The standalone video reported one dropped frame during its
interval; both full-scene intervals reported zero additional drops. These are short measurements
on this PC, not a promise of zero load or all-day performance.

Evidence: [performance](evidence/resort/performance-v4.json),
[native reactions](evidence/resort/v4/native-reactions.json),
[native controls](evidence/resort/v4/native-controls.json),
[encoded seam](evidence/resort/encoded-water-v4.json),
[delivery hashes](evidence/resort/delivery-v4-manifest.json),
[source audit](evidence/resort/source-v4-audit.json),
[verification commands](evidence/resort/validation-v4.json).
The geometry checks cover 104 beach samples, opaque/transparent palm leaves,
and 517 cabana depth samples against the unchanged coast/cabana geometry. Pip's
43-bone weighted rig, 14 original actions and ten editable task actions were
retained. Native tests used synthetic hook payloads through the real transport;
they did not execute paid Claude tasks or real test commands.

Physical Win+L/resume, exclusive fullscreen games and per-display pause/resume
on multiple monitors remain manual checks. Native computer input was unavailable
in this session. The native Lively pause callback was verified in V4. Primary
coverage was observed in the earlier V3 delivery; current coverage geometry is
tested with fixtures, and the desktop was not fully covered during the new run.
Do not extend that evidence to those untested cases.

![Current native Lively coffee scene](evidence/resort/v4/done.jpg)
