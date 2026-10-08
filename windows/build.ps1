param([string]$Dotnet = 'dotnet')
$ErrorActionPreference = 'Stop'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_NOLOGO = '1'
$sourceRoot = Split-Path $PSScriptRoot
& $Dotnet publish (Join-Path $PSScriptRoot 'src\Island.Windows.csproj') -c Release -r win-x64 --self-contained false -o (Join-Path $PSScriptRoot 'app') -p:PublishSingleFile=false -p:DebugType=None -p:DebugSymbols=false -p:ContinuousIntegrationBuild=true ('-p:PathMap=' + $sourceRoot + '=/src')
if ($LASTEXITCODE -ne 0) { throw 'Windows build failed.' }
$sdkRoot = Split-Path (Get-Command $Dotnet).Source
$runtimeRoot = Join-Path $PSScriptRoot 'runtime'
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $sdkRoot 'dotnet.exe'),(Join-Path $sdkRoot 'LICENSE.txt'),(Join-Path $sdkRoot 'ThirdPartyNotices.txt') -Destination $runtimeRoot
$fxr = Get-ChildItem (Join-Path $sdkRoot 'host\fxr') -Directory | Where-Object Name -like '10.*' | Sort-Object { [version]$_.Name } | Select-Object -Last 1
New-Item -ItemType Directory -Force -Path (Join-Path $runtimeRoot 'host\fxr') | Out-Null
Copy-Item -LiteralPath $fxr.FullName -Destination (Join-Path $runtimeRoot 'host\fxr') -Recurse -Force
foreach ($framework in @('Microsoft.NETCore.App','Microsoft.WindowsDesktop.App')) {
    $version = Get-ChildItem (Join-Path $sdkRoot ('shared\' + $framework)) -Directory | Where-Object Name -like '10.*' | Sort-Object { [version]$_.Name } | Select-Object -Last 1
    $destination = Join-Path $runtimeRoot ('shared\' + $framework)
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Copy-Item -LiteralPath $version.FullName -Destination $destination -Recurse -Force
}
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
& $compiler /nologo /target:winexe /reference:System.Windows.Forms.dll ('/out:' + (Join-Path $PSScriptRoot 'IslandDesktop.exe')) (Join-Path $PSScriptRoot 'src\Launcher.cs')
if ($LASTEXITCODE -ne 0) { throw 'Portable launcher build failed.' }
