# Re-download third-party frontend assets into static/vendor and static/fonts.
# Run from the backend directory: powershell -File scripts/download_vendor_assets.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$vendor = Join-Path $root "static\vendor"
$fonts = Join-Path $root "static\fonts"
New-Item -ItemType Directory -Force -Path $vendor, $fonts | Out-Null

$assets = @(
    @{ Url = "https://cdn.tailwindcss.com/3.4.17"; Out = Join-Path $vendor "tailwindcss.js" },
    @{ Url = "https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"; Out = Join-Path $vendor "marked.min.js" },
    @{ Url = "https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.18/files/inter-latin-400-normal.woff2"; Out = Join-Path $fonts "inter-latin-400.woff2" },
    @{ Url = "https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.18/files/inter-latin-600-normal.woff2"; Out = Join-Path $fonts "inter-latin-600.woff2" },
    @{ Url = "https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.18/files/inter-latin-700-normal.woff2"; Out = Join-Path $fonts "inter-latin-700.woff2" }
)

foreach ($asset in $assets) {
    Write-Host "Downloading $($asset.Url)"
    Invoke-WebRequest -Uri $asset.Url -OutFile $asset.Out
}

Write-Host "Done."
