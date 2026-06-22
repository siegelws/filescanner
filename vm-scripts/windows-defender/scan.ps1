# Windows Defender / MpCmdRun.exe scan wrapper
#
# Called by agent.py inside the AV-Defender VM.
# Usage:  powershell -ExecutionPolicy Bypass -File scan.ps1 <file>
# Contract:
#   - Print  DETECTION_NAME=<exact threat name>  on stdout if detected.
#   - Exit 1 on detection, 0 on clean, 2 on error.

param([Parameter(Mandatory = $true)][string]$File)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $File)) {
    Write-Error "File not found: $File"
    exit 2
}

# Defender ships with MpCmdRun.exe under the Platform versioned folder.
$mpcmd = Get-ChildItem "C:\ProgramData\Microsoft\Windows Defender\Platform\*\MpCmdRun.exe" `
         -ErrorAction SilentlyContinue |
         Sort-Object FullName -Descending |
         Select-Object -First 1

if (-not $mpcmd) {
    Write-Error "MpCmdRun.exe not found"
    exit 2
}

# Make sure signatures are reasonably fresh — comment out if your snapshot
# already has the desired definitions baked in.
try { & $mpcmd.FullName -SignatureUpdate | Out-Null } catch {}

# -Scan -ScanType 3 -File <path>  → custom path scan (static + behaviour heuristics).
$out = & $mpcmd.FullName -Scan -ScanType 3 -File $File 2>&1 | Out-String
Write-Output $out

# Defender's stdout when it detects is like:
#   "found 1 threats."  + "Threat               : Trojan:Win32/Wacatac.B!ml"
$detect = $null
foreach ($line in $out -split "`n") {
    if ($line -match 'Threat\s*:\s*(.+?)\s*$') {
        $detect = $Matches[1].Trim()
        break
    }
    if ($line -match 'Threat information:\s*(.+?)\s*$') {
        $detect = $Matches[1].Trim()
        break
    }
}

# Defender exits 2 on detection; we also use the parsed name as a tie-breaker.
if ($detect) {
    Write-Output "DETECTION_NAME=$detect"
    exit 1
}

# Some clean scans exit non-zero on engine warnings — only flag detection if
# we actually pulled a name out.
exit 0
