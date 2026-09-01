param(
    [string]$Runtime = 'G:\CodexTools\token-forge\runtimes\ollama\ollama.exe',
    [string]$ModelRoot = 'G:\CodexTools\models\token-forge\ollama',
    [string]$ListenAddress = '127.0.0.1:11434'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Runtime -PathType Leaf)) {
    throw "Ollama runtime not found: $Runtime"
}

try {
    $version = Invoke-RestMethod 'http://127.0.0.1:11434/api/version' -TimeoutSec 2
    Write-Output "Ollama is already ready: $($version.version)"
    exit 0
} catch {
    # Continue with a local project-scoped process.
}

New-Item -ItemType Directory -Force -Path $ModelRoot | Out-Null
$env:OLLAMA_MODELS = $ModelRoot
$env:OLLAMA_HOST = $ListenAddress
$env:OLLAMA_FLASH_ATTENTION = '1'
Start-Process -FilePath $Runtime -ArgumentList 'serve' -WindowStyle Hidden

for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Seconds 1
    try {
        $version = Invoke-RestMethod 'http://127.0.0.1:11434/api/version' -TimeoutSec 2
        Write-Output "Ollama ready: $($version.version)"
        exit 0
    } catch {
        # Retry during the bounded startup window.
    }
}

throw 'Ollama did not become ready within 20 seconds.'
