# LUCID DISTROLESS DEPLOYMENT EXAMPLE
# Example usage of the distroless deployment scripts
# Demonstrates the complete workflow from build to deployment

# Set strict mode and error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Color functions for output
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success { param([string]$Message) Write-ColorOutput "✅ $Message" "Green" }
function Write-Error { param([string]$Message) Write-ColorOutput "❌ $Message" "Red" }
function Write-Warning { param([string]$Message) Write-ColorOutput "⚠️ $Message" "Yellow" }
function Write-Info { param([string]$Message) Write-ColorOutput "ℹ️ $Message" "Cyan" }
function Write-Progress { param([string]$Message) Write-ColorOutput "🔄 $Message" "Blue" }

function Show-ExampleUsage {
    Write-ColorOutput "LUCID DISTROLESS DEPLOYMENT EXAMPLES" "Magenta"
    Write-ColorOutput "="*60 "Magenta"
    
    Write-Info "This script demonstrates how to use the Lucid distroless deployment system."
    Write-Info "Choose an example to run or view the commands:"
    Write-ColorOutput ""
    
    Write-ColorOutput "1. VALIDATION EXAMPLE" "Yellow"
    Write-ColorOutput "   Test the build system before deployment:" "White"
    Write-ColorOutput "   .\scripts\test-distroless-build.ps1" "Cyan"
    Write-ColorOutput ""
    
    Write-ColorOutput "2. BUILD EXAMPLE (Local)" "Yellow"
    Write-ColorOutput "   Build all distroless images locally:" "White"
    Write-ColorOutput "   .\scripts\build-all-distroless-images.ps1 -Verbose" "Cyan"
    Write-ColorOutput ""
    
    Write-ColorOutput "3. BUILD EXAMPLE (With Push)" "Yellow"
    Write-ColorOutput "   Build and push images to Docker Hub:" "White"
    Write-ColorOutput "   .\scripts\build-all-distroless-images.ps1 -Push -Verbose" "Cyan"
    Write-ColorOutput ""
    
    Write-ColorOutput "4. CONFIGURATION EXAMPLE" "Yellow"
    Write-ColorOutput "   Generate environment configurations:" "White"
    Write-ColorOutput "   .\scripts\generate-service-environments.ps1 -Verbose" "Cyan"
    Write-ColorOutput ""
    
    Write-ColorOutput "5. DEPLOYMENT EXAMPLE (Complete)" "Yellow"
    Write-ColorOutput "   Complete deployment (build + config + deploy):" "White"
    Write-ColorOutput "   .\scripts\deploy-distroless-cluster.ps1 -Build -GenerateConfig -Deploy -Push -Verbose" "Cyan"
    Write-ColorOutput ""
    
    Write-ColorOutput "6. DEPLOYMENT EXAMPLE (Deploy Only)" "Yellow"
    Write-ColorOutput "   Deploy existing images:" "White"
    Write-ColorOutput "   .\scripts\deploy-distroless-cluster.ps1 -Deploy -Verbose" "Cyan"
    Write-ColorOutput ""
    
    Write-ColorOutput "7. DEVELOPMENT WORKFLOW" "Yellow"
    Write-ColorOutput "   Complete development workflow:" "White"
    Write-ColorOutput "   # Step 1: Validate system" "Cyan"
    Write-ColorOutput "   .\scripts\test-distroless-build.ps1" "Cyan"
    Write-ColorOutput "   " "White"
    Write-ColorOutput "   # Step 2: Build images locally" "Cyan"
    Write-ColorOutput "   .\scripts\build-all-distroless-images.ps1 -Verbose" "Cyan"
    Write-ColorOutput "   " "White"
    Write-ColorOutput "   # Step 3: Generate configurations" "Cyan"
    Write-ColorOutput "   .\scripts\generate-service-environments.ps1 -Verbose" "Cyan"
    Write-ColorOutput "   " "White"
    Write-ColorOutput "   # Step 4: Deploy cluster" "Cyan"
    Write-ColorOutput "   .\scripts\deploy-distroless-cluster.ps1 -Deploy -Verbose" "Cyan"
    Write-ColorOutput ""
    
    Write-ColorOutput "8. PRODUCTION WORKFLOW" "Yellow"
    Write-ColorOutput "   Complete production workflow:" "White"
    Write-ColorOutput "   # Step 1: Validate system" "Cyan"
    Write-ColorOutput "   .\scripts\test-distroless-build.ps1" "Cyan"
    Write-ColorOutput "   " "White"
    Write-ColorOutput "   # Step 2: Build and push images" "Cyan"
    Write-ColorOutput "   .\scripts\build-all-distroless-images.ps1 -Push -Verbose" "Cyan"
    Write-ColorOutput "   " "White"
    Write-ColorOutput "   # Step 3: Generate configurations" "Cyan"
    Write-ColorOutput "   .\scripts\generate-service-environments.ps1 -Verbose" "Cyan"
    Write-ColorOutput "   " "White"
    Write-ColorOutput "   # Step 4: Deploy cluster" "Cyan"
    Write-ColorOutput "   .\scripts\deploy-distroless-cluster.ps1 -Deploy -Verbose" "Cyan"
    Write-ColorOutput ""
    
    Write-ColorOutput "9. MONITORING COMMANDS" "Yellow"
    Write-ColorOutput "   Monitor the deployed cluster:" "White"
    Write-ColorOutput "   # View running containers" "Cyan"
    Write-ColorOutput "   docker ps --filter \"label=org.lucid.service\"" "Cyan"
    Write-ColorOutput "   " "White"
    Write-ColorOutput "   # View service logs" "Cyan"
    Write-ColorOutput "   docker-compose -f infrastructure/compose/lucid-distroless-complete.yaml logs -f" "Cyan"
    Write-ColorOutput "   " "White"
    Write-ColorOutput "   # Check service health" "Cyan"
    Write-ColorOutput "   curl -f http://localhost:3000/health" "Cyan"
    Write-ColorOutput "   curl -f http://localhost:8084/health" "Cyan"
    Write-ColorOutput ""
    
    Write-ColorOutput "10. CLEANUP COMMANDS" "Yellow"
    Write-ColorOutput "    Clean up the deployment:" "White"
    Write-ColorOutput "    # Stop and remove containers" "Cyan"
    Write-ColorOutput "    docker-compose -f infrastructure/compose/lucid-distroless-complete.yaml down --remove-orphans" "Cyan"
    Write-ColorOutput "    " "White"
    Write-ColorOutput "    # Remove volumes" "Cyan"
    Write-ColorOutput "    docker-compose -f infrastructure/compose/lucid-distroless-complete.yaml down --volumes" "Cyan"
    Write-ColorOutput "    " "White"
    Write-ColorOutput "    # Remove images" "Cyan"
    Write-ColorOutput "    docker images | grep pickme/lucid | awk '{print $3}' | xargs docker rmi" "Cyan"
    Write-ColorOutput ""
}

function Run-Example {
    param([int]$ExampleNumber)
    
    switch ($ExampleNumber) {
        1 {
            Write-Progress "Running validation example..."
            .\scripts\test-distroless-build.ps1
        }
        2 {
            Write-Progress "Running local build example..."
            .\scripts\build-all-distroless-images.ps1 -Verbose
        }
        3 {
            Write-Progress "Running build with push example..."
            .\scripts\build-all-distroless-images.ps1 -Push -Verbose
        }
        4 {
            Write-Progress "Running configuration example..."
            .\scripts\generate-service-environments.ps1 -Verbose
        }
        5 {
            Write-Progress "Running complete deployment example..."
            .\scripts\deploy-distroless-cluster.ps1 -Build -GenerateConfig -Deploy -Push -Verbose
        }
        6 {
            Write-Progress "Running deploy only example..."
            .\scripts\deploy-distroless-cluster.ps1 -Deploy -Verbose
        }
        7 {
            Write-Progress "Running development workflow..."
            Write-Info "Step 1: Validating system..."
            .\scripts\test-distroless-build.ps1
            if ($LASTEXITCODE -eq 0) {
                Write-Info "Step 2: Building images locally..."
                .\scripts\build-all-distroless-images.ps1 -Verbose
                if ($LASTEXITCODE -eq 0) {
                    Write-Info "Step 3: Generating configurations..."
                    .\scripts\generate-service-environments.ps1 -Verbose
                    if ($LASTEXITCODE -eq 0) {
                        Write-Info "Step 4: Deploying cluster..."
                        .\scripts\deploy-distroless-cluster.ps1 -Deploy -Verbose
                    }
                }
            }
        }
        8 {
            Write-Progress "Running production workflow..."
            Write-Info "Step 1: Validating system..."
            .\scripts\test-distroless-build.ps1
            if ($LASTEXITCODE -eq 0) {
                Write-Info "Step 2: Building and pushing images..."
                .\scripts\build-all-distroless-images.ps1 -Push -Verbose
                if ($LASTEXITCODE -eq 0) {
                    Write-Info "Step 3: Generating configurations..."
                    .\scripts\generate-service-environments.ps1 -Verbose
                    if ($LASTEXITCODE -eq 0) {
                        Write-Info "Step 4: Deploying cluster..."
                        .\scripts\deploy-distroless-cluster.ps1 -Deploy -Verbose
                    }
                }
            }
        }
        9 {
            Write-Progress "Running monitoring commands..."
            Write-Info "Viewing running containers..."
            docker ps --filter "label=org.lucid.service"
            Write-Info "Checking service health..."
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:3000/health" -UseBasicParsing -TimeoutSec 5
                Write-Success "Admin UI: Healthy (HTTP $($response.StatusCode))"
            } catch {
                Write-Warning "Admin UI: Not accessible"
            }
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8084/health" -UseBasicParsing -TimeoutSec 5
                Write-Success "Blockchain API: Healthy (HTTP $($response.StatusCode))"
            } catch {
                Write-Warning "Blockchain API: Not accessible"
            }
        }
        10 {
            Write-Progress "Running cleanup commands..."
            Write-Warning "This will stop and remove all Lucid containers and volumes."
            $confirmation = Read-Host "Are you sure you want to continue? (y/N)"
            if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
                docker-compose -f infrastructure/compose/lucid-distroless-complete.yaml down --volumes --remove-orphans
                Write-Success "Cleanup completed"
            } else {
                Write-Info "Cleanup cancelled"
            }
        }
        default {
            Write-Error "Invalid example number: $ExampleNumber"
            return
        }
    }
}

function Main {
    if ($args.Count -eq 0) {
        Show-ExampleUsage
        Write-ColorOutput ""
        Write-Info "To run an example, use: .\scripts\example-usage.ps1 <number>"
        Write-Info "Example: .\scripts\example-usage.ps1 1"
    } else {
        $exampleNumber = [int]$args[0]
        Run-Example $exampleNumber
    }
}

# Run main function
Main $args
