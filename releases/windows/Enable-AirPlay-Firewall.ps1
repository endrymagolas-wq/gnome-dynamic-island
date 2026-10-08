param([switch]$Remove,[switch]$Diagnose)
$ErrorActionPreference='Stop'
$exe=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'receiver/bin/uxplay.exe'))
if(-not(Test-Path -LiteralPath $exe)){throw 'The receiver binary is missing.'}
$sha=[Security.Cryptography.SHA256]::Create()
try{$id=([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($exe.ToLowerInvariant())))).Replace('-','').Substring(0,12)}finally{$sha.Dispose()}
$group='Cortiva AirPlay '+$id
if($Diagnose){@{component='airplay-firewall';scope='LocalSubnet';tcp='7100-7102';udp='5353,7100-7102';automatic=$false;administratorRequired=$true}|ConvertTo-Json -Compress;exit 0}
$admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if(-not $admin){throw 'Run this optional script in an administrator PowerShell. It only manages rules for this extracted receiver path.'}
if($Remove){Get-NetFirewallRule -Group $group -ErrorAction SilentlyContinue | Remove-NetFirewallRule;Write-Host 'This package AirPlay firewall rules were removed.';exit 0}
foreach($rule in @(@{Protocol='TCP';Ports='7100-7102'},@{Protocol='UDP';Ports='5353,7100-7102'})){
    $name=$group+' '+$rule.Protocol
    if(-not(Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue)){New-NetFirewallRule -Name $name -DisplayName $name -Group $group -Direction Inbound -Action Allow -Program $exe -Protocol $rule.Protocol -LocalPort $rule.Ports.Split(',') -RemoteAddress LocalSubnet -Profile Any | Out-Null}
}
Write-Host 'AirPlay is allowed from the local subnet for this receiver only.'
