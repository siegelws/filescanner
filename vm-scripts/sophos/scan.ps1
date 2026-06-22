# Sophos Intercept X / SAVScan CLI wrapper

param([Parameter(Mandatory = $true)][string]$File)

$ErrorActionPreference = "Stop"

$sav = "C:\Program Files\Sophos\Sophos Anti-Virus\SAVScan.exe"
if (-not (Test-Path $sav)) {
    $sav = (Get-ChildItem "C:\Program Files*\Sophos*" -Recurse -Filter "SAVScan.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty FullName)
}
if (-not $sav) { Write-Error "SAVScan.exe not found"; exit 2 }

# -ss : silent;  -nc : no cleanup;  -di : display info
$out = & $sav -ss -nc -di $File 2>&1 | Out-String
Write-Output $out

# Sophos: ">>> Virus 'Mal/Generic-S' found in file ..."
$detect = $null
foreach ($line in $out -split "`n") {
    if ($line -match "Virus\s+'([^']+)'\s+found") {
        $detect = $Matches[1].Trim()
        break
    }
}

if ($detect) {
    Write-Output "DETECTION_NAME=$detect"
    exit 1
}
exit 0
