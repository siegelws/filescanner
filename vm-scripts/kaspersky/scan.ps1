# Kaspersky Endpoint Security CLI wrapper (avp.com)
#
# Called by agent.py inside the AV-Kaspersky VM.

param([Parameter(Mandatory = $true)][string]$File)

$ErrorActionPreference = "Stop"

$avp = "C:\Program Files (x86)\Kaspersky Lab\Kaspersky Endpoint Security for Windows\avp.com"
if (-not (Test-Path $avp)) {
    $avp = (Get-ChildItem "C:\Program Files*\Kaspersky*" -Recurse -Filter "avp.com" -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty FullName)
}
if (-not $avp) { Write-Error "avp.com not found"; exit 2 }

# SCAN /MEMORY=no /STARTUP=no /REMDRIVES=no /FIXEDDRIVES=no /NETWORKDRIVES=no <path>
#   /i0  → skip infected (we just want to report)
$out = & $avp SCAN $File /i0 2>&1 | Out-String
Write-Output $out

# Kaspersky's avp.com line on detection:
#   "<time>  detected   <THREAT_NAME>   <path>"
$detect = $null
foreach ($line in $out -split "`n") {
    if ($line -match 'detected\s+([^\s]+(?:\.[^\s]+)*)') {
        $detect = $Matches[1].Trim()
        break
    }
}

if ($detect) {
    Write-Output "DETECTION_NAME=$detect"
    exit 1
}
exit 0
