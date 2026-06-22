# ESET NOD32 ecls.exe wrapper

param([Parameter(Mandatory = $true)][string]$File)

$ErrorActionPreference = "Stop"

$ecls = "C:\Program Files\ESET\ESET Security\ecls.exe"
if (-not (Test-Path $ecls)) {
    $ecls = (Get-ChildItem "C:\Program Files*\ESET*" -Recurse -Filter "ecls.exe" -ErrorAction SilentlyContinue |
             Select-Object -First 1 -ExpandProperty FullName)
}
if (-not $ecls) { Write-Error "ecls.exe not found"; exit 2 }

# --no-quarantine: report-only; --clean-mode=NONE: do not delete
$out = & $ecls --no-log-all --no-quarantine --clean-mode=NONE $File 2>&1 | Out-String
Write-Output $out

# ESET output:  "<path> - infected by "<name>" cleaned by deleting"
$detect = $null
foreach ($line in $out -split "`n") {
    if ($line -match 'infected by\s+"([^"]+)"') {
        $detect = $Matches[1].Trim()
        break
    }
    if ($line -match '\-\s+(?:probably a variant of\s+)?(.+?)\s+\-\s+') {
        $detect = $Matches[1].Trim()
    }
}

if ($detect) {
    Write-Output "DETECTION_NAME=$detect"
    exit 1
}

# ecls.exe exit codes: 0 clean, 1 threat found, 10 partial scan, 50 error
if ($LASTEXITCODE -eq 1) {
    Write-Output "DETECTION_NAME=ESET:Heuristic"
    exit 1
}
exit 0
