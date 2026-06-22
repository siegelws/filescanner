# BitDefender Endpoint CLI wrapper (bdscan / product_console)

param([Parameter(Mandatory = $true)][string]$File)

$ErrorActionPreference = "Stop"

# product_console.exe is BitDefender's modern CLI; bdscan.exe is the legacy one.
$candidates = @(
    "C:\Program Files\Bitdefender\Endpoint Security\product_console.exe",
    "C:\Program Files\Bitdefender\AntiVirus Free Edition\bdscan.exe",
    "C:\Program Files\Bitdefender\Bitdefender Security\bdscan.exe"
)
$bd = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $bd) { Write-Error "BitDefender CLI not found"; exit 2 }

$out = & $bd /scan="$File" 2>&1 | Out-String
Write-Output $out

# BitDefender output line:
#   "<path>  infected: Trojan.Generic.12345"
$detect = $null
foreach ($line in $out -split "`n") {
    if ($line -match 'infected:\s*(.+?)\s*$') {
        $detect = $Matches[1].Trim()
        break
    }
}

if ($detect) {
    Write-Output "DETECTION_NAME=$detect"
    exit 1
}
exit 0
