# V6: fairy lagoon, seated Pip and local time

All four final lighting bundles have been rendered, checked and promoted together.
The ordinary Windows wallpaper now uses V6. Review:
`http://127.0.0.1:18765/wallpaper/fairy-review.html`.

## Art direction and layers

The camera and dry-land geometry are retained. Painted coral/mint/lavender
surfaces replace photographic base color and normal detail. Original leaf alpha
is retained. The submerged drop is shallower, with a height-based sand-to-lagoon
transition. Cycles renders actual periodic geometric waves, reflection,
refraction and shoreline foam. A restrained compositor glow is baked offline.

The static plate uses RGB from the full beauty frame, including its glow, and
alpha from the water holdout/shore mask. This avoids combining a differently lit
holdout RGB with the full water beauty. Ground/foreground depth, animated Pip
depth and cabana depth are separate data renders with neutral color transforms.

Each lighting preset has its own beauty/transparent plate, water videos,
character, ambient and smoke atlases. Geometry, projection and depth are shared.
Morning/day/evening/night start at 06:00/09:00/18:00/21:00 in the PC's local time.
The fade lasts two minutes. A second video decoder is used only during a fade;
the old source is unloaded afterwards. This is a fixed local-clock schedule,
not an astronomical sunrise calculation. A fixed phase can be selected in
Lively or the preview controls. Pausing stops both videos and actor animation;
lighting assets are not refreshed while paused.

## Furniture regression

V5 routed through the cafe furniture and applied a sitting pose at ground level.
Navigation now uses measured Blender bounds expanded by a 0.30m actor clearance.
The actor walks to a clear approach point, then uses a separate 0.9s sit/stand
transition. The rig origin on the cushion is 0.64m; cushion top is 0.95m. Walking
continues on the measured beach surface. New events during the transition are
retained and routed after standing. The larger actor's stride is 0.5952m/s.

The regression first failed with `walks inside coffee seating`; the corrected
model passes 81 state pairs and 18,100 walking samples outside measured furniture.
Per-pixel animated depth replaces the old upright actor plane. The source retains
the generated V5 mesh, Quaternius rig and original actions; no model is relabeled
CC0. Existing provenance remains in `art/ASSET_SOURCES.md`.

Idle no longer freezes its first frame. Three six-second clips (16fps) cycle
through drinking, nodding and a hand-cover yawn gesture. The mesh has no facial
rig, so these clips do not animate the jaw or eyelids. Eating is not implemented.
Task events interrupt the rest cycle via standing and normal navigation.

## Offline reproduction

Blender 4.5.9, Cycles OptiX on RTX 3080; Python/Pillow and FFmpeg for packaging.
No Blender process is launched by the wallpaper. The following are offline
commands, run from the repository. Use the actual local Blender executable.

1. Inspect/edit `art/island/resort-v6.blend`, or rebuild from retained V5 with
   `blender --background --python tools/build_resort_v6.py -- C:/scratch/resort-v6.blend`.
   The builder refuses to overwrite an existing destination.
2. Run the sequential renderer:
   `python tools/render_resort_v6_batch.py --blender <absolute Blender.exe>`.
   It stages outputs in ignored `wallpaper/assets/v6-stage/`, skips complete
   stages and records progress/logs. Defaults to the shipped V6 source. Use
   `--source C:/scratch/resort-v6.blend` for a fresh protected rebuild, with a
   fresh staging directory so completion reports from another source are not reused.
3. Record the three editable ambient rig actions if rebuilding source:
   `blender --background C:/scratch/resort-v6.blend --python tools/render_resort_v6.py -- ambient-actions day`.
4. Package only after all stages complete:
   `python tools/package_resort_v6.py`.
   The packer checks sprite bounds and fully decoded water seams for every phase.
   `--preview` stages only a draft day bundle and cannot promote it.
5. Run the scene/navigation/depth checks against staged assets. After review,
   `python tools/package_resort_v6.py --promote` backs up V5 outside Git and
   promotes the coherent layer set. Reload through `wallpaper/launch.ps1`.
6. Prepare the format comparison with `python tools/prepare_resort_atlas.py`.
   Stop owned Blender workers, then run `tools/run_resort_v6_native.ps1`.
   It checks the real hook transport/native player and properties, compares
   video/atlas/still, measures coffee/editing/two-decoder fade/native pause,
   and restores ordinary pause policy and observer. Synthetic hooks execute
   no paid Claude tasks or test commands.
   Use `-MeasurementsOnly` to resume measurements after the matching native
   reaction/control evidence exists. Python failures retain their full traceback
   in the named evidence log; they still fail the run.
   `-TransitionOnly` checks the native two-decoder fade and initialized-player
   pause when repairing those paths; `-PauseOnly` repeats just the pause window.
   The pause gate requires previously decoded frames, then frozen water, actor
   cell, rest time and position. A byte-range HTTP regression first failed
   with `Video seeking requires HTTP byte ranges`; streaming 206/416 responses
   fixed actual loop synchronization in WebView2. Counter sampling waits for
   its first valid GPU sample before beginning the CPU/RAM interval, avoiding
   a startup-related `TimeoutExpired` without dropping validity checks.

The source lighting recipes are in `art/island/resort_time_of_day.py`; the
palette is in `fairy_palette.py`, poses in `pip_v6_poses.py`, and ambient gestures
in `bake_pip_ambient.py`. Source rig actions remain editable in Blender.

Fast checks: `node tests/resort-lighting.mjs`,
`node tests/resort-lighting-runtime.mjs`, and
`powershell -NoProfile -File tests/resort-properties.ps1`.
For staged navigation/depth tests set `RESORT_TEST_ASSETS` to
`wallpaper/assets/v6-stage`. The native run also captures each rest gesture and
requires advancing atlas cells. Work/rest benchmarks wait for the actual desk
or seated target before measuring.

`launch.ps1` migrates both the library schema and this wallpaper's saved
per-monitor Lively properties. Existing water, quality and fixed-time values
are retained. Other wallpapers' properties are not touched.

Environment shadows/reflections are baked. The moving actor uses animated
per-pixel depth and a small contact shadow; arbitrary-position cast shadows and
reflections of the moving actor are not rendered at runtime.

## Final native verification

All four 12-second water videos contain 360 playback frames at 30fps. The raw
endpoint frame is excluded; encoded last-to-first differences passed the seam
gate for both 1080p and 720p in every phase. The source audit, independently
rebuilt day frame, 2,368 unclipped actor cells, 12 native event cases, three
advancing rest clips, four native lighting presets and controls passed.
Evidence: `docs/evidence/resort/validation-v6.json`, `performance-v6.json` and
`v6/`. Screenshots are actual Lively captures, not composited proof images.

Fresh 30-second windows on Windows 11, i9-9900K/32GB/RTX3080 10GB, with Blender
stopped. CPU includes the owned Lively/WebView2 tree, Lively core and local host.
RSS sums process mappings and can count shared pages more than once. GPU 3D and
video decode are separate Windows engine counters, not whole-board utilization.

| Mode | CPU, whole PC | RSS MiB | Dedicated GPU MiB | GPU 3D | Video decode | FPS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 720p video comparison | 1.94% | 666 | 53 | 0.31% | 3.90% | 29.97 |
| Same 720p frames as atlas | 3.56% | 841 | 334 | 0.57% | 0% | 23.41 |
| Still comparison | 0.16% | 605 | 71 | 0% | 0% | — |
| Full 1080p, coffee | 2.29% | 929 | 142 | 1.29% | 8.56% | 29.97 |
| Full 1080p, editing | 3.38% | 943 | 122 | 1.50% | 7.96% | 29.97 |
| Two-video lighting fade | 4.02% | 993 | 197 | 3.82% | 29.27% | 29.93 |
| Native pause | 0.30% | 882 | 172 | 0% | 0% | 0 |

Video was selected for water because this PC decoded it more smoothly with
less CPU and dedicated GPU memory than the atlas. Actor clips remain atlases.
All measured video intervals had zero new dropped frames; FPS describes decoded
frames, while atlas FPS describes draw submissions, not physical display presents.
The fade finished the measured window with 0.0214s circular clock difference.
Pause froze the already decoded water count (37 frames), actor cell, rest time
and position, with zero active decoders. Assets remain resident during pause.
Ordinary fullscreen-pause policy and foreground observer were restored, and the
ordinary V6 wallpaper was launched with automatic local-time lighting.

No After Effects composition was needed: Blender, Pillow and FFmpeg produced
the shipped layers. The render resource guard is optional; it was stopped when
the user chose parallel rendering with CS2. No game process was stopped.

Physical lock/resume, exclusive fullscreen and multiple monitors remain manual
checks; callback and observer tests are not physical lock/fullscreen proof.
