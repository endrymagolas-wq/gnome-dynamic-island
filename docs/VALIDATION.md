# Beta validation

Date: 2026-10-04. Current release: 0.2.0-beta.1. Previous core beta: 0.1.0-beta.1.

## Checks completed for the packaged source

- Six deterministic Python suites: network debounce/loss/recovery/unknown state; preference permissions/muting; asynchronous expired and muted results; noise caps/quiet contexts; process CPU normalization/PID reuse/role protection; long nested tasks/service failure episodes; disk hysteresis/dedup/history corruption/bounds.
- Install/restore round trip in a temporary home: dry run writes nothing, original files backed up and restored, new files removed, unrelated files retained, fresh assistant defaults OFF with private preferences, edited source blocks destructive restoration, later preferences survive restore.
- Pure JavaScript pointer-intent regressions for ceiling/titlebar/island/Shift/pressure, button/grab/fullscreen/lock guards and monitor passage geometry.
- Python compilation and JavaScript syntax checks.
- The packaged worker performed seven actual offline Laya classifications: connection, completed download, sustained resource pressure, brief routine spike, task end, low disk and network loss. The existing tested Python 3.11 runtime and cached pinned model were reused. This is actual inference, not the older interactive browser simulation.
- Separate native GNOME 46 Wayland compositor, installed via the package's copy-only installer in a temporary home: smart-edge mode and two barriers, titlebar hover remains hidden, ceiling above island opens, desktop ceiling opens, emitted native window-grab signal immediately hides the bar, an actual fullscreen fixture removes barriers and hides the bar. Missing receiver services hide the Cast toggle. No extension JavaScript errors were found.

The compositor fixtures simulate pointer coordinates and emit the grab signal. They do not prove physical pointer feel or hardware sleep/resume. Unsafe evaluation was enabled only in the disposable copied test extension, not in the distributed or user's extension.

## Full desktop profile checks

- Full install/restore in a temporary home with a mocked settings bus: GTK4 CSS backup restored, all bundled files installed/removed, private remote state retained, fresh remote not enabled, later font choice preserved while other appearance keys reverted.
- Isolated native GNOME 46 Wayland render: island, compatibility controls, Layerlight and Ubuntu Dock all state=enabled; actual GTK traffic-light buttons, wallpaper, floating dock and Inter rendered. One live shader attached. Injected numeric audio features exercised the shader; no JavaScript/GLSL errors found. Wave disable removed effects and released its owned audio subprocess. Missing DBusMenu typelib in the minimal fixture left dock quicklists unavailable; the actual Ubuntu dependency environment differs.
- Numeric frequency-separation checks for four audio bands and malformed samples; a fake PipeWire monitor verified SIGTERM also stops the owned child and removes state, without capturing real sound.
- Netflix remote test server bound to loopback in a private temporary directory: fresh key/file permissions, authenticated state, denied unauthenticated/origin/unknown-action/credential-file requests, same-subnet LAN policy across multiple address ranges and failure rate limit passed. No personal browser was driven and no commercial account was used.
- Receiver config/units install/restore passed in a temporary home, session MPRIS/artwork and HLS options verified, competing active system receiver rejected without stopping it.
- The exact published UxPlay setup fetched pinned upstream revision, applied the included patch and built successfully against an existing extracted Ubuntu SDK in a disposable home. Two preparatory SDK failures (missing cmake on PATH, missing multiarch OpenSSL include path) were resolved in the test environment. This proves the recipe's pinned source/patch build, not a fresh apt dependency installation or physical phone video playback. No live receiver or firewall was changed.

## Existing implementation evidence

The local prototype was exercised with real phone AirPlay artwork, phone-volume feedback, track changes and reconnections during development. Per-app mixer adjustments were checked with two owned silent audio streams, preserving receiver audio. Actual lazy model unload/reload and full service OFF were checked earlier. Native popup and notice bounds, long-text ellipses, reduced motion and cleanup were examined in isolated GNOME fixtures.

The user's current prototype reports smart-edge and modelBridge enabled after relogin. These observations apply to this workstation/prototype; they are not a broad compatibility certification of the renamed public package.

## Public release verification

The public prerelease `v0.1.0-beta.1` is published from commit `d81fb71baa79d82d89fe9c7e880bbed665ae307b`. GitHub CI passed on both main and the version tag. Its ZIP and SHA256SUMS were downloaded from the public release URLs and compared with the local artifacts. ZIP SHA-256: `f634a72fc666558845d478778183b228cc3b70294797668d536d8b5d3870588e`. Tests also passed after extracting that ZIP. The validation notes inside the immutable release ZIP predate the public CI run; the release page records the final CI result.

## Not verified / open beta work

- A completely fresh online setup of all model dependencies on a separate user's computer. The optional setup pins the main SDK/runtime versions and warms tokenizer/config caches; future package-index availability may change.
- Reliable physical lock/unlock, suspend/resume and long sessions after previous crashes.
- Hardware game/video fullscreen behavior, multi-monitor scaling/layout combinations and physical gesture feel across devices.
- Authenticated custom titlebars across all releases of each configured application, unknown applications, and all GNOME versions outside 46.
- New users' receiver configuration, phone artwork/remote-control support and firewall/LAN setup. User receiver configuration and pinned-source setup are included; upstream binaries/dependencies are installed separately.

Please report reproducible beta issues with Shell version, display scaling and extension conflicts. Do not attach private runtime state or unredacted system logs.
