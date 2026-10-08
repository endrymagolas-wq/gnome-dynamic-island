param([Parameter(Mandatory=$true)][string]$Command,[string]$Path,[double]$Value,[int]$Seconds,[string]$Id,[double]$Position,[int]$PidValue,[switch]$Boolean,[string]$Property,[bool]$Fullscreen,[bool]$KeepAspect,[int]$BufferSeconds)
$ErrorActionPreference = 'Stop'
$message = @{ command = $Command }
if ($PSBoundParameters.ContainsKey('Path')) { $message.path = $Path }
if ($PSBoundParameters.ContainsKey('Value')) { $message.value = $Value }
if ($PSBoundParameters.ContainsKey('Seconds')) { $message.seconds = $Seconds }
if ($PSBoundParameters.ContainsKey('Id')) { $message.id = $Id }
if ($PSBoundParameters.ContainsKey('Position')) { $message.position = $Position }
if ($PSBoundParameters.ContainsKey('PidValue')) { $message.pid = $PidValue }
if ($PSBoundParameters.ContainsKey('Property')) { $message.property = $Property }
if ($PSBoundParameters.ContainsKey('Fullscreen')) { $message.fullscreen = $Fullscreen }
if ($PSBoundParameters.ContainsKey('KeepAspect')) { $message.keepAspect = $KeepAspect }
if ($PSBoundParameters.ContainsKey('BufferSeconds')) { $message.bufferSeconds = $BufferSeconds }
if ($Command -in @('mute','reactive','airplay-pin')) { $message.value = [bool]$Boolean }
$pipe = [System.IO.Pipes.NamedPipeClientStream]::new('.', 'IslandDesktopWindows', [System.IO.Pipes.PipeDirection]::InOut)
try {
    $pipe.Connect(5000)
    $writer = [System.IO.StreamWriter]::new($pipe); $writer.AutoFlush = $true
    $reader = [System.IO.StreamReader]::new($pipe)
    $writer.WriteLine(($message | ConvertTo-Json -Compress))
    $read = $reader.ReadLineAsync()
    if (-not $read.Wait(15000)) { throw 'Island response timed out.' }
    $read.Result
} finally { $pipe.Dispose() }
