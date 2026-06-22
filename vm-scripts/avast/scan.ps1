# Avast Antivirus CLI wrapper (ashCmd.exe)

param([Parameter(Mandatory = $true)][string]$File)

$ErrorActionPreference = "Stop"

$ash = "C:\Program Files\AVAST Software\Avast\ashCmd.exe"
if (-not (Test-Path $ash)) {
    $ash = (Get-ChildItem "C:\Program Files*\AVAST*" -Recurse -Filter "ashCmd.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty FullName)
}
if (-not $ash) { Write-Error "ashCmd.exe not found"; exit 2 }

# /_ : no banner; report-only by default
$out = & $ash /_ $File 2>&1 | Out-String
Write-Output $out

# Avast format: "<path>\t[L] <THREAT_NAME>"
$detect = $null
foreach ($line in $out -split "`n") {
    if ($line -match '\[L\]\s+(.+?)\s*$') {
        $detect = $Matches[1].Trim()
        break
    }
}

if ($detect) {
    Write-Output "DETECTION_NAME=$detect"
    exit 1
}
exit 0
