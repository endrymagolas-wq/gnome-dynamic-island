function Find-ResortLively {
    $installed = Get-AppxPackage '*LivelyWallpaper*' | Select-Object -First 1
    if ($installed) { return $installed }
    # Some PowerShell sessions cannot enumerate Store registrations. Verify
    # the running official Store binary and its existing cache instead.
    $running = @(Get-Process Lively -ErrorAction SilentlyContinue)
    if ($running.Count -ne 1) { return $null }
    $exe = $running[0].Path
    if (-not $exe -or -not (Test-Path -LiteralPath $exe)) { return $null }
    $install = Split-Path (Split-Path $exe -Parent) -Parent
    $parts = (Split-Path $install -Leaf).Split('_')
    if ($parts.Count -lt 5 -or $parts[0] -notlike '*LivelyWallpaper') { return $null }
    $family = $parts[0] + '_' + $parts[-1]
    if (-not (Test-Path -LiteralPath (Join-Path $env:LOCALAPPDATA ('Packages/'+$family+'/LocalCache/Local/Lively Wallpaper')))) { return $null }
    return [pscustomobject]@{ InstallLocation=$install; PackageFamilyName=$family }
}
