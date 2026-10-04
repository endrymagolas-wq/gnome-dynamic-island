# Contributing

Use GNOME 46 and run `python3 tests/run.py` before proposing changes. Describe the trigger, expected/actual result, distribution, Shell version, Wayland/X11, display scaling and conflicting extensions. Include screenshots only after checking them for private content. Redact local logs and never attach preferences, history, browser profiles or credentials.

The titlebar overlays use explicit profiles in `extensions/island-window-controls@avalon.local/profiles.json`. Verify normal/maximized/fullscreen/resize/drag/minimize/close before adding an application. Do not claim universal compatibility or bump supported Shell versions without native tests.

Keep assistant outputs bounded and template-based, preserve quiet contexts and the full OFF path, and do not add model-controlled process termination or file deletion. Pull requests are welcome.
