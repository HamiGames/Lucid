# run-lucid-dev.ps1
# Manually run the lucid dev container without using DevContainer CLI

# Define values
$ContainerName = "lucid-run"
$ImageName = "pickme/lucid-dev-fixed:latest"
$WorkDir = "/workspaces/Lucid"
$HostDir = ${PWD}.Path.Replace('\', '/')  # Escape colon issue

Write-Host "🚀 Starting container '$ContainerName' from image '$ImageName'..." -ForegroundColor Cyan

# Kill any old container with same name
docker rm -f $ContainerName > $null 2>&1

# Run the container (keep alive with sleep)
docker run -dit `
  --name $ContainerName `
  -v "$HostDir:$WorkDir" `
  -v "/var/run/docker.sock:/var/run/docker.sock" `
  -p 8080:8080 `
  -p 8081:8081 `
  -p 9050:9050 `
  -p 9051:9051 `
  -p 27017:27017 `
  $ImageName `
  sh -c "while true; do sleep 3600; done"

Start-Sleep -Seconds 2

# Check if running
$Status = docker inspect -f '{{.State.Running}}' $ContainerName 2>$null

if ($Status -eq "true") {
    Write-Host "✅ Container is running and ready!" -ForegroundColor Green
    Write-Host "💡 Enter with: docker exec -it $ContainerName sh" -ForegroundColor Yellow
    Write-Host "📁 Your code is mounted at: $WorkDir"
} else {
    Write-Host "❌ Failed to start container. Check your image and system setup." -ForegroundColor Red
    exit 1
}
