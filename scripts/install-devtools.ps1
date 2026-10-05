# Downloads portable uv, Node.js, and ffmpeg into D:\devtools (never C:).
# Run once: powershell -ExecutionPolicy Bypass -File .\scripts\install-devtools.ps1

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\setup-env.ps1"

$DevRoot = $env:DEVTOOLS_ROOT

function Ensure-File($Url, $OutFile) {
    if (Test-Path $OutFile) {
        Write-Host "Already present: $OutFile"
        return
    }
    Write-Host "Downloading $Url ..."
    Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
}

# --- uv ---
$uvExe = Join-Path $env:UV_INSTALL_DIR "uv.exe"
if (-not (Test-Path $uvExe)) {
    Write-Host "Installing uv to $env:UV_INSTALL_DIR ..."
    $installer = Join-Path $env:TEMP "uv-install.ps1"
    Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -OutFile $installer -UseBasicParsing
    & powershell -ExecutionPolicy Bypass -File $installer
} else {
    Write-Host "uv already installed: $uvExe"
}

# --- Node.js portable (win-x64 zip) ---
$nodeVersion = "v22.14.0"
$nodeZipName = "node-$nodeVersion-win-x64"
$nodeDir = Join-Path $DevRoot "node\$nodeZipName"
$nodeExe = Join-Path $nodeDir "node.exe"
if (-not (Test-Path $nodeExe)) {
    $nodeZip = Join-Path $env:TEMP "$nodeZipName.zip"
    Ensure-File "https://nodejs.org/dist/$nodeVersion/$nodeZipName.zip" $nodeZip
    Write-Host "Extracting Node.js to $DevRoot\node ..."
    Expand-Archive -Path $nodeZip -DestinationPath (Join-Path $DevRoot "node") -Force
} else {
    Write-Host "Node.js already installed: $nodeExe"
}
$env:Path = "$nodeDir;$env:Path"

# --- ffmpeg essentials build (gyan.dev) ---
$ffmpegExe = $env:FFMPEG_PATH
if (-not (Test-Path $ffmpegExe)) {
    $ffmpegZip = Join-Path $env:TEMP "ffmpeg-release-essentials.zip"
    Ensure-File "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" $ffmpegZip
    $extractTo = Join-Path $env:TEMP "ffmpeg-extract"
    if (Test-Path $extractTo) { Remove-Item -Recurse -Force $extractTo }
    Expand-Archive -Path $ffmpegZip -DestinationPath $extractTo -Force
    $binSrc = Get-ChildItem -Path $extractTo -Recurse -Filter "ffmpeg.exe" |
        Select-Object -First 1 |
        ForEach-Object { $_.Directory.FullName }
    if (-not $binSrc) { throw "ffmpeg.exe not found inside archive" }
    Copy-Item -Path (Join-Path $binSrc "*") -Destination (Join-Path $DevRoot "ffmpeg\bin") -Force
    Write-Host "ffmpeg installed to $(Join-Path $DevRoot 'ffmpeg\bin')"
} else {
    Write-Host "ffmpeg already installed: $ffmpegExe"
}

Write-Host ""
Write-Host "Done. Versions:"
& "$env:UV_INSTALL_DIR\uv.exe" --version
& "$nodeDir\node.exe" --version
& "$env:FFMPEG_PATH" -version | Select-Object -First 1
& "$env:FFPROBE_PATH" -version | Select-Object -First 1
Write-Host ""
Write-Host "Next: . .\scripts\setup-env.ps1"
