// Office documents that look like maldoc droppers.

rule Office_VBA_AutoExec
{
    meta:
        description = "Office macro with auto-exec entry point"
        severity    = "medium"
    strings:
        $a1 = "AutoOpen"     nocase
        $a2 = "Auto_Open"    nocase
        $a3 = "Document_Open" nocase
        $a4 = "Workbook_Open" nocase
        $a5 = "AutoClose"    nocase
        $b1 = "Shell"        nocase
        $b2 = "WScript.Shell" nocase
        $b3 = "powershell"   nocase
        $b4 = "CreateObject" nocase
    condition:
        1 of ($a*) and 1 of ($b*)
}

rule Office_PowerShell_Dropper
{
    meta:
        description = "Office document with embedded PowerShell that pulls a remote payload"
        severity    = "high"
    strings:
        $p1 = "powershell" nocase
        $p2 = "-EncodedCommand" nocase
        $p3 = "DownloadString" nocase
        $p4 = "Invoke-Expression" nocase
        $p5 = "FromBase64String" nocase
    condition:
        $p1 and 2 of ($p2, $p3, $p4, $p5)
}
