# ✨ Sparkling Water - Windows Installation Script

$ErrorActionPreference = "Stop"

Write-Host "✨ Initializing Sparkling Water: The Breakthrough AI Coding Agent..." -ForegroundColor Cyan

# Check for Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "❌ Python is required but not found. Please install Python 3.10 or higher."
}

$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([double]$pythonVersion -lt 3.10) {
    Write-Error "❌ Sparkling Water requires Python 3.10 or higher. Found $pythonVersion"
}

# Create a temporary directory for cloning
$tempDir = [System.IO.Path]::GetTempPath()
$swDir = Join-Path $tempDir "sparkling-water-install-$(Get-Random)"

Write-Host "📦 Downloading Sparkling Water..." -ForegroundColor Cyan
git clone https://github.com/deviprasadshetty-dev/sparkling-water.git $swDir

Write-Host "📦 Installing and optimizing system..." -ForegroundColor Cyan
Set-Location $swDir
pip install -e .

Write-Host "`n✅ Installation Complete!" -ForegroundColor Green
Write-Host "🚀 Run 'sw' to start the breakthrough terminal UI." -ForegroundColor Cyan
Write-Host "💡 Context: Use '@filename' in chat to link files instantly." -ForegroundColor Gray

# Go back to original location
Pop-Location
