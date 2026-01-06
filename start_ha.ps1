# Start Home Assistant for Trados Cloud Development
# Run this script from the HomeAssistant directory

Write-Host "🏠 Starting Home Assistant for Trados Cloud Development..." -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv/Scripts/Activate.ps1")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "   Run: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment
Write-Host "📦 Activating virtual environment..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1

# Check if Home Assistant is installed
$haVersion = & E:/HomeAssistant/.venv/Scripts/python.exe -m homeassistant --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Home Assistant not installed!" -ForegroundColor Red
    Write-Host "   Run: pip install homeassistant" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Home Assistant version: $haVersion" -ForegroundColor Green
Write-Host ""

# Check if integration exists
if (-not (Test-Path "custom_components/trados_cloud/__init__.py")) {
    Write-Host "⚠️  Trados Cloud integration not found!" -ForegroundColor Yellow
    Write-Host "   Expected location: custom_components/trados_cloud/" -ForegroundColor Yellow
}
else {
    Write-Host "✅ Trados Cloud integration found" -ForegroundColor Green
}

Write-Host ""
Write-Host "🚀 Starting Home Assistant..." -ForegroundColor Cyan
Write-Host "   URL: http://localhost:8123" -ForegroundColor Yellow
Write-Host "   Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""
Write-Host "📝 After onboarding:" -ForegroundColor Magenta
Write-Host "   1. Go to Settings → Devices & Services" -ForegroundColor White
Write-Host "   2. Click '+ ADD INTEGRATION'" -ForegroundColor White
Write-Host "   3. Search for 'Trados Cloud'" -ForegroundColor White
Write-Host "   4. Enter your Trados credentials" -ForegroundColor White
Write-Host ""

# Start Home Assistant
& E:/HomeAssistant/.venv/Scripts/python.exe -m homeassistant --config "$PSScriptRoot\config" --verbose
