function Sync-ResortProperties([string]$Source, [string]$Destination) {
    $defaults = Get-Content -LiteralPath $Source -Raw | ConvertFrom-Json
    if (Test-Path -LiteralPath $Destination) {
        $saved = Get-Content -LiteralPath $Destination -Raw | ConvertFrom-Json
        foreach ($property in $defaults.PSObject.Properties) {
            $old = $saved.PSObject.Properties[$property.Name]
            if ($old -and $old.Value.PSObject.Properties['value']) {
                $property.Value.value = $old.Value.value
            }
        }
        # Retain extension settings that are absent from the current schema.
        foreach ($property in $saved.PSObject.Properties) {
            if (-not $defaults.PSObject.Properties[$property.Name]) {
                $defaults | Add-Member -MemberType NoteProperty -Name $property.Name -Value $property.Value
            }
        }
    }
    $json = $defaults | ConvertTo-Json -Depth 20
    [System.IO.File]::WriteAllText($Destination, $json, [System.Text.UTF8Encoding]::new($false))
}
