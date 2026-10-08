# Windows release package QA

Recorded package gates pass for `windows-v0.4.0-beta.1`. The five product ZIPs were read in full for CRC and safe-path checks, privacy patterns, required license/source-resource presence and exact package-manifest hashes. Live sources and desktop state were not changed.

| Artifact | Bytes | Manifest records verified | SHA-256 |
| --- | ---: | ---: | --- |
| `island-desktop-windows-0.4.0-beta.1.zip` | 87688585 | 524 | `01fd2033afdac15483d6dfeb290b3177ff2ee5af6a11d8a0511537c596c9d004` |
| `fairy-lagoon-v7-wallpaper-windows.zip` | 345900936 | 143 | `d63079c23b36d142cf9cd50e1c6bcc8fab8a7005e7da8a883616a9940d2a5dec` |
| `cortiva-airplay-windows-0.4.0-beta.1.zip` | 80544758 | 463 | `60497a49ebf3a976df04ea8a901ca3556ce76d20c81dd1776ab8a785f99a34d8` |
| `island-desktop-windows-full-0.4.0-beta.1.zip` | 513873593 | 1085 | `8e7a32b617307bc9c66ab496994911fb29777d60576d044e9774b94e272118bf` |
| `fairy-lagoon-v7-blender-sources.zip` | 127918328 | 91 | `8f3aad204e0440a91fe16bd22b6aade8326c2495ef58cef6293dd357b57e553e` |

The corresponding native source ZIP contains 96 exact MSYS2 source archives for 99 package versions owning all 175 shipped dependency binaries. All archives decompress and contain their package recipes. The ZIP is 1245140566 bytes with SHA-256 `81372689243525d1d3486fbca9306ad979d3b2f9b7894a60a612645fa1419f6c`. Its receiver build recipe exactly equals the final frozen recipe.

Both AirPlay-containing packages match all 430 receiver manifest records and close imports/delay imports for 176 native PE files against their included DLLs and declared Windows dependencies. No user pairing key, captured phone media, settings, log, browser profile or build cache is included. Six PEM-pattern constants in one exact GnuTLS DLL were byte-matched to its public upstream cryptographic self-tests; the exception is limited to that DLL hash.

All seven public Blender project copies were reopened after sanitation and compression. Mesh/rig/action/material/camera fingerprints and exact packed-image bytes match, with zero personal paths in uncompressed Blender data. All are below GitHub's 100 MiB per-file limit. The Blender ZIP includes the exact accepted V6 base, V7 organic scene and V7 activity-action files.

The managed runtime, SDK projection, CsWinRT, NAudio, CPython, psutil, Lively CLI, native GNU dependencies and artwork keep their applicable notices and source resources. These are resource/provenance checks, not an independent legal opinion.

Native startup, phone playback, visual UI and performance remain separate evidence. The source-mapped receiver retains the original synthetic local-pause failure; it is not an all-controls pass. This audit does not establish a fresh-machine Lively install, every Windows/DPI arrangement or independent compiler reproduction of every dependency.

Machine-readable receipts: [package QA](package-qa.json), [manifest verification](package-manifests.json), [Blender integrity](blender-integrity.json), [historical evidence sanitation](historical-evidence-privacy.json), [public GnuTLS constants](gnutls-public-key-proof.json), and [native mapping limits](uxplay-mapped-promotion.json).
