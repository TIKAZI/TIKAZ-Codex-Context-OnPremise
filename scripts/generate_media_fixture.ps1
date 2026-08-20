param(
    [Parameter(Mandatory = $true)]
    [string]$Ffmpeg
)

$ErrorActionPreference = 'Stop'
$root = Join-Path (Split-Path -Parent $PSScriptRoot) 'benchmarks\acceptance-fixtures'
New-Item -ItemType Directory -Force -Path $root | Out-Null
$wav = Join-Path $root 'speech.wav'
$video = Join-Path $root 'speech-video.mp4'

Add-Type -AssemblyName System.Speech
$voice = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    $voice.SetOutputToWaveFile($wav)
    $voice.Speak('TIKAZ Token Forge benchmark. Media anchor nine four zero. Release version nine point four point zero. Verification date December twenty first, twenty twenty six.')
} finally {
    $voice.Dispose()
}

& $Ffmpeg -y -f lavfi -i 'color=c=#0B1220:s=1280x720:d=8' -f lavfi -i 'color=c=#2563EB:s=1280x720:d=8' -i $wav -filter_complex '[0:v][1:v]concat=n=2:v=1:a=0[v]' -map '[v]' -map '2:a' -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac $video
if ($LASTEXITCODE -ne 0) { throw 'FFmpeg failed to generate the media fixture.' }

$reference = 'TIKAZ Token Forge benchmark Media anchor 940 Release version 9.4.0 Verification date December 21 2026'
[System.IO.File]::WriteAllText(
    (Join-Path $root 'speech-reference.txt'),
    $reference,
    [System.Text.UTF8Encoding]::new($false)
)
