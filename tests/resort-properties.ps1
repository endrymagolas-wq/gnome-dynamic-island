$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../wallpaper/sync-properties.ps1')
$folder = Join-Path ([System.IO.Path]::GetTempPath()) ('resort-properties-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $folder | Out-Null
$source = Join-Path $PSScriptRoot '../wallpaper/LivelyProperties.json'
$destination = Join-Path $folder 'LivelyProperties.json'
try {
    '{"water":{"value":false},"quality":{"value":1},"extension":{"value":"keep"}}' | Set-Content -LiteralPath $destination
    Sync-ResortProperties $source $destination
    $merged = Get-Content -LiteralPath $destination -Raw | ConvertFrom-Json
    if ($merged.water.value -ne $false -or $merged.quality.value -ne 1 -or $merged.extension.value -ne 'keep' -or $merged.timeOfDay.value -ne 0) { throw 'Saved choices or new time control lost' }
    $merged.timeOfDay.value = 4
    $merged | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $destination
    Sync-ResortProperties $source $destination
    $again = Get-Content -LiteralPath $destination -Raw | ConvertFrom-Json
    if ($again.timeOfDay.value -ne 4 -or $again.quality.value -ne 1) { throw 'Repeated migration reset choices' }
    Write-Host 'PASS properties migration adds local-time control and retains user values'
} finally {
    Remove-Item -LiteralPath $destination -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $folder -ErrorAction SilentlyContinue
}
