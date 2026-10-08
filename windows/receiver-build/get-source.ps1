$ErrorActionPreference = 'Stop'
$taskSourceDirectory = Join-Path (Split-Path $PSScriptRoot) 'receiver\source'
$taskArchive = Join-Path $taskSourceDirectory 'uxplay-3dbf7ce-source.zip'
$taskExpectedHash = '0B6E4AA98D1ECFABB7C8D52826A0480E3AA232BECC1AD74368D980DF1125FCFF'
New-Item -ItemType Directory -Force -Path $taskSourceDirectory | Out-Null
if (Test-Path -LiteralPath $taskArchive) {
    if ((Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash -ne $taskExpectedHash) {
        throw 'The existing source archive differs from the pinned archive; it has been retained.'
    }
} else {
    $taskDownload = Join-Path $taskSourceDirectory ('uxplay-' + [Guid]::NewGuid().ToString('N') + '.tmp')
    try {
        Invoke-WebRequest -Uri 'https://codeload.github.com/FDH2/UxPlay/zip/3dbf7ceee65932154e85a2f83963d53520a799fa' -OutFile $taskDownload
        if ((Get-FileHash -LiteralPath $taskDownload -Algorithm SHA256).Hash -ne $taskExpectedHash) {
            throw 'Downloaded source does not match the pinned SHA256.'
        }
        Move-Item -LiteralPath $taskDownload -Destination $taskArchive
    } finally {
        if (Test-Path -LiteralPath $taskDownload) { Remove-Item -LiteralPath $taskDownload }
    }
}
Write-Output 'Verified UxPlay source: 3dbf7ceee65932154e85a2f83963d53520a799fa'
