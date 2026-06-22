rule EICAR_Test_File
{
    meta:
        description = "EICAR antivirus test string"
        author      = "filescanner"
        reference   = "https://www.eicar.org/download-anti-malware-testfile/"
        severity    = "test"

    strings:
        $eicar = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

    condition:
        $eicar
}
