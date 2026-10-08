# Isolated HLS regression

Generate the silent synthetic test media with a local FFmpeg build supporting
libx264, then test the packaged receiver:

```powershell
python .\receiver-build\tests\generate-hls-fixture.py --ffmpeg C:\msys64\ucrt64\bin\ffmpeg.exe
python .\receiver-build\tests\test-hls.py --relay --controls --visual
python .\receiver-build\tests\test-startup.py
```

The script starts its own receiver at port 17500, uses loopback-only synthetic
playlists/segments, exercises the reused reverse HTTP channel and reads actual
decoded state and video-sink properties. It closes its owned child at the end.
The normal receiver at port 7100 remains running. The test briefly opens its own
video window and toggles fullscreen. No real phone, account or PIN is needed.

`--https` separately tests real HTTPS HLS using Apple's public streaming example.
It requires Internet access. Without `--visual`, a clocked fake video sink is used;
the fullscreen/aspect checks require D3D11 and use the actual WASAPI sink with silent
media. Generated media, plugin caches and test results stay in this test directory.

These are native protocol/renderer checks. They do not replace physical iPhone
confirmation or Windows SMTC/WPF tests.

The startup test starts three fresh HLS receiver processes at port 17600: with
missing POSIX locale variables, empty variables, and an explicit language choice.
Each must reach ready, stay alive and exit cleanly. This catches Windows startup
failures hidden by a development shell's Linux-style environment variables.
