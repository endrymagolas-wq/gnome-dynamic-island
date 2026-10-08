#!/usr/bin/env bash
set -euo pipefail
export PATH="/ucrt64/bin:/usr/bin:$PATH"
export PKG_CONFIG_PATH="/ucrt64/lib/pkgconfig:/ucrt64/share/pkgconfig"
task_bundle="$(cd "$(dirname "$0")" && pwd)"
task_workspace="${1:?Pass a dedicated build workspace path}"
mkdir -p "$task_workspace"
task_workspace="$(cd "$task_workspace" && pwd)"
task_source="$task_workspace/UxPlay-3dbf7ceee65932154e85a2f83963d53520a799fa"
task_patch="$task_bundle/island-windows.patch"
task_archive="$task_bundle/../receiver/source/uxplay-3dbf7ce-source.zip"
task_digest="$(sha256sum "$task_patch" | cut -d' ' -f1)"
if [[ -d "$task_source" ]]; then
    if [[ ! -f "$task_source/.island-patch-sha256" ]] || [[ "$(cat "$task_source/.island-patch-sha256")" != "$task_digest" ]]; then
        echo "Existing source has a different patch or no marker. Use a fresh build workspace." >&2
        exit 1
    fi
else
    bsdtar -xf "$task_archive" -C "$task_workspace"
    (cd "$task_source" && patch -p1 --forward -i "$task_patch")
    printf '%s\n' "$task_digest" > "$task_source/.island-patch-sha256"
fi
task_native_source="$(cygpath -m "$task_source")"
task_native_workspace="$(cygpath -m "$task_workspace")"
task_prefix_flags="-ffile-prefix-map=$task_native_workspace=/build/uxplay -fdebug-prefix-map=$task_native_workspace=/build/uxplay -ffile-prefix-map=$task_native_source=/src/uxplay -fdebug-prefix-map=$task_native_source=/src/uxplay"
cmake -S "$task_source" -B "$task_workspace/build-ucrt64" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DNO_MARCH_NATIVE=ON -DUSE_MDNS=ON \
    "-DCMAKE_C_FLAGS=$task_prefix_flags" "-DCMAKE_CXX_FLAGS=$task_prefix_flags"
cmake --build "$task_workspace/build-ucrt64" --parallel 4
