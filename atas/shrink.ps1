# Trim recorded CSVs to the cash session and gzip them.
#
# A 1-tick recording is enormous -- 375 MB for one day -- because at 1 tick the
# top ten levels span 2.5 points, so price walks through the whole ladder
# constantly and every level changes on nearly every snapshot. Nothing about
# that is wrong; the data is simply large. This makes it movable without
# re-recording anything and without discarding anything from the cash session.
#
# Two passes, both lossless for analysis:
#   RTH only   the overnight session is not analysed and is most of the file
#   gzip       CSV of this shape compresses about 18x, measured on real tape
#
# Times are matched as text against the PLATFORM clock written into the file,
# which on this install is UTC, so the cash session is 13:30 to 20:00 there.
#
#   .\shrink.ps1
#   .\shrink.ps1 -Folder "D:\somewhere" -Start "13:30:00" -End "20:00:00"
#   .\shrink.ps1 -KeepAll          leave the overnight session in, gzip only

param(
    [string]$Folder = "$env:USERPROFILE\Desktop\ATAS_Export",
    [string]$Start  = "13:30:00",
    [string]$End    = "20:00:00",
    [string]$OutDir = "",
    [switch]$KeepAll
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Folder)) {
    Write-Host ""
    Write-Host "  Folder not found: $Folder" -ForegroundColor Red
    Write-Host "  Pass the right one:  .\shrink.ps1 -Folder ""C:\path\to\ATAS_Export"""
    exit 1
}

if ([string]::IsNullOrEmpty($OutDir)) { $OutDir = Join-Path $Folder "small" }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# The filtering runs in C# rather than a PowerShell loop: these files hold
# millions of lines and per-line PowerShell overhead would turn seconds into
# many minutes.
$cs = @'
using System;
using System.IO;
using System.IO.Compression;

public static class AtasShrink
{
    public static long[] Run(string src, string dst, string start, string end,
                             bool keepAll)
    {
        long total = 0, kept = 0;
        using (var fin = File.OpenRead(src))
        using (var sr = new StreamReader(fin))
        using (var fout = File.Create(dst))
        using (var gz = new GZipStream(fout, CompressionLevel.Optimal))
        using (var sw = new StreamWriter(gz))
        {
            string line = sr.ReadLine();
            if (line != null) sw.WriteLine(line);

            while ((line = sr.ReadLine()) != null)
            {
                total++;
                if (line.Length < 19) continue;
                if (!keepAll)
                {
                    string t = line.Substring(11, 8);
                    if (string.CompareOrdinal(t, start) < 0) continue;
                    if (string.CompareOrdinal(t, end) >= 0) continue;
                }
                sw.WriteLine(line);
                kept++;
            }
        }
        return new long[] { total, kept };
    }
}
'@

if (-not ("AtasShrink" -as [type])) { Add-Type -TypeDefinition $cs }

$files = @(Get-ChildItem -LiteralPath $Folder -Filter *.csv -File |
           Where-Object { $_.Name -notlike "_*" })

if ($files.Count -eq 0) {
    Write-Host ""
    Write-Host "  No .csv files in $Folder" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "  Shrinking $($files.Count) file(s) from $Folder"
if ($KeepAll) { Write-Host "  keeping all hours, compressing only" }
else          { Write-Host "  keeping $Start to $End (platform clock)" }
Write-Host ""

$inTotal = 0L
$outTotal = 0L

foreach ($f in $files) {
    $dst = Join-Path $OutDir ($f.BaseName + ".csv.gz")
    Write-Host ("  {0,-34}" -f $f.Name) -NoNewline
    try {
        $r = [AtasShrink]::Run($f.FullName, $dst, $Start, $End, [bool]$KeepAll)
        $outSize = (Get-Item -LiteralPath $dst).Length
        $inTotal += $f.Length
        $outTotal += $outSize
        $ratio = if ($outSize -gt 0) { $f.Length / $outSize } else { 0 }
        Write-Host ("{0,8:N1} MB -> {1,7:N1} MB  ({2,4:N0}x)  {3:N0} of {4:N0} rows" -f `
            ($f.Length / 1MB), ($outSize / 1MB), $ratio, $r[1], $r[0])
    }
    catch {
        Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "  ============================================================"
Write-Host ("   {0:N1} MB  ->  {1:N1} MB" -f ($inTotal / 1MB), ($outTotal / 1MB))
Write-Host "   written to $OutDir"
Write-Host ""
Write-Host "   Send the .csv.gz files. Do not unzip them -- they are read"
Write-Host "   compressed and unzipping only makes them large again."
Write-Host "  ============================================================"
