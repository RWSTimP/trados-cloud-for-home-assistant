# Start Home Assistant in Docker for Trados Cloud Development

Write-Host "🐳 Starting Home Assistant in Docker..." -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
$dockerRunning = docker ps 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Docker is not running. Starting Docker Desktop..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Write-Host "   Waiting for Docker to start (30 seconds)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
}

# Check if container already exists
$containerExists = docker ps -a --filter "name=homeassistant" --format "{{.Names}}" 2>$null

if ($containerExists -eq "homeassistant") {
    Write-Host "📦 Home Assistant container exists" -ForegroundColor Green
    
    # Check if it's running
    $containerRunning = docker ps --filter "name=homeassistant" --format "{{.Names}}" 2>$null
    
    if ($containerRunning -eq "homeassistant") {
        Write-Host "✅ Container is already running" -ForegroundColor Green
    }
    else {
        Write-Host "🔄 Starting existing container..." -ForegroundColor Yellow
        docker start homeassistant
    }
}
else {
    Write-Host "🆕 Creating new Home Assistant container..." -ForegroundColor Green
    
    # Make sure integration is copied
    Write-Host "📋 Copying Trados integration to config..." -ForegroundColor Cyan
    Copy-Item -Path "custom_components" -Destination "config\" -Recurse -Force
    
    # Create and start container
    docker run -d `
        --name homeassistant `
        --restart=unless-stopped `
        -e TZ=America/New_York `
        -v "${PWD}/config:/config" `
        -p 8123:8123 `
        ghcr.io/home-assistant/home-assistant:stable
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Container created successfully!" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Failed to create container" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "🎉 Home Assistant is starting..." -ForegroundColor Green
Write-Host ""
Write-Host "📍 URL: " -NoNewline -ForegroundColor Yellow
Write-Host "http://localhost:8123" -ForegroundColor White
Write-Host ""
Write-Host "⏱️  First startup takes 2-3 minutes" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Magenta
Write-Host "   1. Wait for startup to complete" -ForegroundColor White
Write-Host "   2. Open http://localhost:8123 in your browser" -ForegroundColor White
Write-Host "   3. Complete onboarding wizard" -ForegroundColor White
Write-Host "   4. Go to Settings → Devices & Services" -ForegroundColor White
Write-Host "   5. Click '+ ADD INTEGRATION'" -ForegroundColor White
Write-Host "   6. Search for 'Trados Cloud'" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Useful commands:" -ForegroundColor Magenta
Write-Host "   View logs:    " -NoNewline -ForegroundColor White
Write-Host "docker logs -f homeassistant" -ForegroundColor Cyan
Write-Host "   Stop:         " -NoNewline -ForegroundColor White
Write-Host "docker stop homeassistant" -ForegroundColor Cyan
Write-Host "   Restart:      " -NoNewline -ForegroundColor White
Write-Host "docker restart homeassistant" -ForegroundColor Cyan
Write-Host "   Remove:       " -NoNewline -ForegroundColor White
Write-Host "docker rm -f homeassistant" -ForegroundColor Cyan
Write-Host ""

# Offer to watch logs
$response = Read-Host "Watch startup logs? (y/n)"
if ($response -eq 'y') {
    Write-Host ""
    Write-Host "📜 Watching logs (Ctrl+C to exit)..." -ForegroundColor Cyan
    docker logs -f homeassistant
}
