# Beta validation

Date: 2026-10-04. Release: 0.1.0-beta.1.

## Checks completed for the packaged source

- Six deterministic Python suites: network debounce/loss/recovery/unknown state; preference permissions/muting; asynchronous expired and muted results; noise caps/quiet contexts; process CPU normalization/PID reuse/role protection; long nested tasks/service failure episodes; disk hysteresis/dedup/history corruption/bounds.
- Install/restore round trip in a temporary home: dry run writes nothing, original files backed up and restored, new files removed, unrelated files retained, fresh assistant defaults OFF with private preferences, edited source blocks destructive restoration, later preferences survive restore.
- Pure JavaScript pointer-intent regressions for ceiling/titlebar/island/Shift/pressure, button/grab/fullscreen/lock guards and monitor passage geometry.
- Python compilation and JavaScript syntax checks.
- The packaged worker performed seven actual offline Laya classifications: connection, completed download, sustained resource pressure, brief routine spike, task end, low disk and network loss. The existing tested Python 3.11 runtime and cached pinned model were reused. This is actual inference, not the older interactive browser simulation.
- Separate native GNOME 46 Wayland compositor, installed via the package's copy-only installer in a temporary home: smart-edge mode and two barriers, titlebar hover remains hidden, ceiling above island opens, desktop ceiling opens, emitted native window-grab signal immediately hides the bar, an actual fullscreen fixture removes barriers and hides the bar. Missing receiver services hide the Cast toggle. No extension JavaScript errors were found.

The compositor fixtures simulate pointer coordinates and emit the grab signal. They do not prove physical pointer feel or hardware sleep/resume. Unsafe evaluation was enabled only in the disposable copied test extension, not in the distributed or user's extension.

## Existing implementation evidence

The local prototype was exercised with real phone AirPlay artwork, phone-volume feedback, track changes and reconnections during development. Per-app mixer adjustments were checked with two owned silent audio streams, preserving receiver audio. Actual lazy model unload/reload and full service OFF were checked earlier. Native popup and notice bounds, long-text ellipses, reduced motion and cleanup were examined in isolated GNOME fixtures.

The user's current prototype reports smart-edge and modelBridge enabled after relogin. These observations apply to this workstation/prototype; they are not a broad compatibility certification of the renamed public package.

## Not verified / open beta work

- A completely fresh online setup of all model dependencies on a separate user's computer. The optional setup pins the main SDK/runtime versions and warms tokenizer/config caches; future package-index availability may change.
- Public CI completion until GitHub runs the workflow.
- Reliable physical lock/unlock, suspend/resume and long sessions after previous crashes.
- Hardware game/video fullscreen behavior, multi-monitor scaling/layout combinations and physical gesture feel across devices.
- Authenticated custom titlebars across all releases of each configured application, unknown applications, and all GNOME versions outside 46.
- New users' receiver configuration, phone artwork/remote-control support and firewall/LAN setup. Receivers are not bundled.

Please report reproducible beta issues with Shell version, display scaling and extension conflicts. Do not attach private runtime state or unredacted system logs.
