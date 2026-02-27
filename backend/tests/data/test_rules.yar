
rule EICAR_Test_File
{
    meta:
        description = "EICAR antivirus test file"
        author = "ForensicStack Tests"
    strings:
        $eicar = "EICAR-STANDARD-ANTIVIRUS-TEST-FILE"
    condition:
        $eicar
}

rule PE_Header_Test
{
    meta:
        description = "Detects PE executable header"
        author = "ForensicStack Tests"
    strings:
        $mz = { 4D 5A }
        $pe = { 50 45 00 00 }
    condition:
        $mz at 0 and $pe
}
