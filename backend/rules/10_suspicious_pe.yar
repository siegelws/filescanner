// Generic suspicion rules for Windows PE files.
// Trips on indicators commonly associated with droppers, packers, and stealers.
// These are *heuristic*, not high-confidence on their own.

rule PE_UPX_Packed
{
    meta:
        description = "PE file packed with UPX"
        severity    = "low"
    strings:
        $upx0 = "UPX0"
        $upx1 = "UPX1"
        $upx2 = "UPX!"
    condition:
        uint16(0) == 0x5A4D and ($upx0 or $upx1 or $upx2)
}

rule PE_Suspicious_API_Imports
{
    meta:
        description = "PE imports a high concentration of process-injection / persistence APIs"
        severity    = "medium"
    strings:
        $a1 = "VirtualAllocEx"
        $a2 = "WriteProcessMemory"
        $a3 = "CreateRemoteThread"
        $a4 = "NtUnmapViewOfSection"
        $a5 = "SetWindowsHookEx"
        $b1 = "RegSetValueExA"
        $b2 = "RegCreateKeyExA"
        $c1 = "InternetOpenA"
        $c2 = "InternetReadFile"
        $c3 = "WinHttpOpen"
    condition:
        uint16(0) == 0x5A4D and
        3 of ($a*) and
        1 of ($b*) and
        1 of ($c*)
}

rule PE_Likely_Stealer_Strings
{
    meta:
        description = "PE contains strings typical of info-stealers (browser/wallet paths)"
        severity    = "high"
    strings:
        $s1 = "\\Google\\Chrome\\User Data\\Default\\Login Data" ascii wide
        $s2 = "\\Microsoft\\Edge\\User Data\\" ascii wide
        $s3 = "\\Mozilla\\Firefox\\Profiles\\" ascii wide
        $s4 = "wallet.dat" ascii wide
        $s5 = "\\Telegram Desktop\\tdata" ascii wide
        $s6 = "\\Discord\\Local Storage\\leveldb" ascii wide
    condition:
        uint16(0) == 0x5A4D and 3 of them
}
