# Sets all install/cache paths to D:\devtools for this PowerShell session.
# Usage: . .\scripts\setup-env.ps1

$ErrorActionPreference = "Stop"

$DevRoot = "D:\devtools"
$dirs = @(
    "$DevRoot\tmp",
    "$DevRoot\uv\bin",
    "$DevRoot\uv\python",
    "$DevRoot\uv\cache",
    "$DevRoot\hf-cache",
    "$DevRoot\torch-cache",
    "$DevRoot\npm-cache",
    "$DevRoot\node",
    "$DevRoot\ffmpeg\bin"
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

$env:DEVTOOLS_ROOT = $DevRoot
$env:TEMP = "$DevRoot\tmp"
$env:TMP = "$DevRoot\tmp"
$env:TMPDIR = "$DevRoot\tmp"

# uv / Python
$env:UV_INSTALL_DIR = "$DevRoot\uv\bin"
$env:UV_PYTHON_INSTALL_DIR = "$DevRoot\uv\python"
$env:UV_CACHE_DIR = "$DevRoot\uv\cache"
$env:UV_LINK_MODE = "copy"

# Hugging Face / torch caches on D:
$env:HF_HOME = "$DevRoot\hf-cache"
$env:HUGGINGFACE_HUB_CACHE = "$DevRoot\hf-cache\hub"
$env:TRANSFORMERS_CACHE = "$DevRoot\hf-cache\transformers"
$env:TORCH_HOME = "$DevRoot\torch-cache"

# Node / npm
$env:NPM_CONFIG_CACHE = "$DevRoot\npm-cache"
$NodeRoot = Get-ChildItem -Path "$DevRoot\node" -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName "node.exe") } |
    Sort-Object Name -Descending |
    Select-Object -First 1
if ($NodeRoot) {
    $env:Path = "$($NodeRoot.FullName);$env:Path"
}

# ffmpeg
$env:FFMPEG_PATH = "$DevRoot\ffmpeg\bin\ffmpeg.exe"
$env:FFPROBE_PATH = "$DevRoot\ffmpeg\bin\ffprobe.exe"
$env:Path = "$DevRoot\ffmpeg\bin;$env:UV_INSTALL_DIR;$env:Path"

Write-Host "Environment pointed to $DevRoot"
Write-Host "  UV_INSTALL_DIR     = $env:UV_INSTALL_DIR"
Write-Host "  HF_HOME            = $env:HF_HOME"
Write-Host "  NPM_CONFIG_CACHE   = $env:NPM_CONFIG_CACHE"
Write-Host "  FFMPEG_PATH        = $env:FFMPEG_PATH"
Write-Host "  TEMP/TMP           = $env:TEMP"
