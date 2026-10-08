# Release verification boundaries

This beta has several kinds of evidence. They establish different things and should not be combined into one release-wide test count. The table records the local installed/source checks; final archive inventory, checksums, privacy and dependency-source checks identify the packaged artifact separately.

| Area | Observed evidence | What it does not establish |
| --- | --- | --- |
| **Windows media APIs** | An independent, quiet native player was controlled through Windows SMTC and its actual state read back; Core Audio readbacks were checked. | Every browser/site/player's metadata or action support. |
| **Dock and background icons** | Native launch/focus/window grouping; repeated real Explorer overflow opening/closing; taskbar style and recovery readback. | Every installed application's tray menu or every Windows/DPI arrangement. |
| **AirPlay protocol/runtime** | Receiver startup, pairing/protocol, UDP/HLS and control checks, with source/build/runtime provenance. | A physical iPhone result by themselves. Some shared logic tests overlap other suites. |
| **Physical iPhone** | User confirmed audible music, music after PIN and moving YouTube video with sound on the PC. | All iOS releases/apps, DRM video, general mirroring compatibility or fixed latency. |
| **V7 terrain** | 77 Blender raycast samples; maximum analytic-versus-mesh height difference about 0.01539 m with a 0.02 m bound. | Native player performance. |
| **V7 installed coordination** | Exact installed metadata: 876,493 physical/event assertions over 67,144 simulated frames. All three actors reach their actions and return without wet/furniture shortcuts or body overlap. | A visual/natively rendered proof by itself. |
| **V7 activity atlas** | 3,456 checks over the rendered frame set; 704 color and 176 depth frames; drinking pose reopened/rendered from the editable source. | Facial mouth/eyelid or eating animation, which are absent. |
| **V7 package layers** | 69 render/package checks for final scene provenance, four lighting phases and color/alpha/depth/shore consistency. | Universal performance or lock/suspend behavior. |
| **Wallpaper local host** | 278 bounded-field, origin and telemetry checks, retaining earlier authorization/range checks. | Complete fresh-machine installation or every Lively version. |
| **Native Lively player** | Installed WebView2 at 1920×1080 decoded about 29.94fps in a short post-initialization run, with three distinct character channels. | Sustained frame rate on every PC, all lighting transitions or exclusive fullscreen. |
| **Product media** | Clean scene preview and island/panel captures; the video may stage panel/media states for demonstration and labels that use. | Physical AirPlay or an unstaged daily-use session. |
| **GNOME** | Existing Ubuntu 24.04.5 / GNOME 46 / Wayland validation and installer/restore evidence are retained. | A native port of the Windows V7 player or a newly repeated Linux run for this Windows release. |

The V7 native resource sample lasted roughly 12 seconds after initialization: about 5.22% whole-PC CPU and 0.90 GB summed player-tree RSS on the test machine. These are short-run measurements, not minimum requirements or a prediction for other hardware. The normal desktop-occlusion handling was restored after the measurement.

## Frozen release checks, 8 October 2026

The release source was built with .NET 10 in Release mode and compiler source-path mapping. Its deterministic application checks pass **29/29**, and dock grouping checks pass **12/12**. The exact packaged V7 metadata repeats **876,493** physical/event assertions over **67,144** simulated frames; the local HTTP host repeats **278** checks.

The mapped UxPlay binary has zero personal source-path matches, unchanged DLL imports and **9/9** startup checks. Its HLS fixture passes **13** relay/decode checks. The synthetic local-pause assertion fails identically on the original and mapped binaries; the assertion and deadline were retained. This is a known unresolved fixture/control limitation, **not an all-controls pass**. Earlier physical iPhone playback observations are separate from this comparison. See the [native receipt](evidence/windows-release/uxplay-mapped-promotion.json).

The portable launcher/restore contracts pass **21** isolated cases, the actual packaged Python/host passes **16**, and the standalone receiver owner passes **4** with a synthetic child. Those tests leave the native desktop untouched and do not establish a fresh-machine Lively install.

The seven public Blender files were reopened after privacy sanitation and compression. Meshes, rigs, actions, materials, cameras and exact packed-image bytes retain their semantic fingerprints. Their file hashes changed; the original source hashes in render metadata identify the inputs used before metadata sanitation. See [Blender integrity](evidence/windows-release/blender-integrity.json), [source and media verification](evidence/windows-release/verification.json), and [capture segments](evidence/windows-release/media-capture.json).

## Remaining beta checks

Physical sleep/resume/lock, exclusive fullscreen, broad DPI/multi-monitor configurations, Windows 10/ARM64, protected streaming services and all third-party players need separate validation. The optional native GNOME cartoon wallpaper also has its own runtime and unmeasured native performance; it is not the Windows V7 implementation.

A player/app publishes the available media actions. Task/process activity inference does not prove a real tool task succeeded. The focus timer does not enable Windows Do Not Disturb automatically. Local flyout changes on the development PC are not a general Windows popup-suppression feature.

## Reading the evidence

Release source and binary/archive checksums identify the delivered artifacts. Source tests, native application captures and physical device observations are reported separately. WPF visual captures show the application's own surface; a clean browser scene preview shows matching assets, not the installed desktop.

Windows test methods and build provenance are described in [the component documentation](../windows/README.md). V7 evidence filenames include `installed-physical-gate.json`, `native-playback.json`, `package-render-audit.json`, `frame-validation.json` and `ground-probes.json`. A raw local development report can contain private paths; only sanitized evidence should be published. Local development-output paths are not public download links.
