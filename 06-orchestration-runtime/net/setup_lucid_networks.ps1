# Lucid RDP Network Setup Script for Windows 11
# Creates and manages Docker networks for inter-container communications
# Based on LUCID-STRICT requirements for Raspberry Pi 5 deployment target

param(
    [Parameter()]
    [ValidateSet("create", "remove", "status", "test", "reset")]
    [string]$Action = "create",
    
    [Parameter()]
    [ValidateSet("dev", "prod")]
    [string]$Environment = "dev",
    
    [Parameter()]
    [switch]$VerboseOutput
)

# Runtime variables aligned for Windows 11 and Raspberry Pi 5
$LUCID_NETWORKS = @{
    "lucid_internal" = @{
        subnet = "172.20.0.0/24"
        gateway = "172.20.0.1"
        purpose = "inter-container-communications"
        internal = $true
    }
    "lucid_external" = @{
        subnet = "172.21.0.0/24"  
        gateway = "172.21.0.1"
        purpose = "user-portals"
        internal = $false
    }
    "lucid_blockchain" = @{
        subnet = "172.22.0.0/24"
        gateway = "172.22.0.1" 
        purpose = "ledger-only"
        internal = $true
    }
    "lucid_tor" = @{
        subnet = "172.23.0.0/24"
        gateway = "172.23.0.1"
        purpose = "onion-services"
        internal = $false
    }
    "lucid_dev" = @{
        subnet = "172.24.0.0/24"
        gateway = "172.24.0.1"
        purpose = "local-dev-access"
        internal = $false
    }
}

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent (Split-Path -Parent $SCRIPT_DIR)

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$ForegroundColor = "White"
    )
    Write-Host $Message -ForegroundColor $ForegroundColor
}

function Test-Docker {
    try {
        docker info *>$null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

function Create-LucidNetwork {
    param(
        [string]$NetworkName,
        [hashtable]$NetworkConfig
    )
    
    Write-ColorOutput "Creating network: $NetworkName" "Yellow"
    
    try {
        # Check if network already exists
        docker network inspect $NetworkName *>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "[+] Network $NetworkName already exists" "Green"
            return $true
        }
        
        # Create network arguments
        $createArgs = @(
            "network", "create"
            "--driver", "bridge"
            "--subnet", $NetworkConfig.subnet
            "--gateway", $NetworkConfig.gateway
            "--label", "lucid.network.purpose=$($NetworkConfig.purpose)"
        )
        
        if ($NetworkConfig.internal) {
            $createArgs += "--internal"
        }
        
        # Driver options for proper container communication
        $createArgs += "--opt"
        $createArgs += "com.docker.network.bridge.enable_icc=true"
        
        if (-not $NetworkConfig.internal) {
            $createArgs += "--opt"
            $createArgs += "com.docker.network.bridge.enable_ip_masquerade=true"
        } else {
            $createArgs += "--opt" 
            $createArgs += "com.docker.network.bridge.enable_ip_masquerade=false"
        }
        
        $createArgs += $NetworkName
        
        & docker @createArgs
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "[+] Successfully created network: $NetworkName" "Green"
            return $true
        } else {
            Write-ColorOutput "[-] Failed to create network: $NetworkName" "Red"
            return $false
        }
        
    } catch {
        Write-ColorOutput "[-] Error creating network $NetworkName : $_" "Red"
        return $false
    }
}

function Remove-LucidNetwork {
    param(
        [string]$NetworkName
    )
    
    Write-ColorOutput "Removing network: $NetworkName" "Yellow"
    
    try {
        docker network inspect $NetworkName *>$null
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "[+] Network $NetworkName doesn't exist" "Green"
            return $true
        }
        
        docker network rm $NetworkName
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "[+] Successfully removed network: $NetworkName" "Green"
            return $true
        } else {
            Write-ColorOutput "[-] Failed to remove network: $NetworkName" "Red"
            return $false
        }
        
    } catch {
        Write-ColorOutput "[-] Error removing network $NetworkName : $_" "Red"
        return $false
    }
}

function Test-NetworkConnectivity {
    param(
        [string]$NetworkName,
        [hashtable]$NetworkConfig
    )
    
    Write-ColorOutput "Testing connectivity for network: $NetworkName" "Yellow"
    
    try {
        # Create test containers on the network
        $testContainer1 = docker run -d --network $NetworkName --name "test-${NetworkName}-1" alpine:3.22.1 sleep 30
        $testContainer2 = docker run -d --network $NetworkName --name "test-${NetworkName}-2" alpine:3.22.1 sleep 30
        
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "[-] Failed to create test containers for $NetworkName" "Red"
            return $false
        }
        
        Start-Sleep -Seconds 3
        
        # Test inter-container connectivity
        $pingResult = docker exec "test-${NetworkName}-1" ping -c 2 "test-${NetworkName}-2" 2>$null
        
        # Cleanup test containers
        docker stop "test-${NetworkName}-1" "test-${NetworkName}-2" *>$null
        docker rm "test-${NetworkName}-1" "test-${NetworkName}-2" *>$null
        
        if ($pingResult -and ($pingResult -match "2 packets transmitted, 2 received")) {
            Write-ColorOutput "[+] Network connectivity test passed for: $NetworkName" "Green"
            return $true
        } else {
            Write-ColorOutput "[-] Network connectivity test failed for: $NetworkName" "Red"
            return $false
        }
        
    } catch {
        # Cleanup on error
        docker stop "test-${NetworkName}-1" "test-${NetworkName}-2" *>$null 2>$null
        docker rm "test-${NetworkName}-1" "test-${NetworkName}-2" *>$null 2>$null
        Write-ColorOutput "[-] Error testing network $NetworkName : $_" "Red"
        return $false
    }
}

function Show-NetworkStatus {
    Write-ColorOutput "===== Lucid Network Status =====" "Cyan"
    
    foreach ($networkName in $LUCID_NETWORKS.Keys) {
        $config = $LUCID_NETWORKS[$networkName]
        
        docker network inspect $networkName *>$null
        if ($LASTEXITCODE -eq 0) {
            $networkInfo = docker network inspect $networkName | ConvertFrom-Json
            $containers = $networkInfo.Containers.Count
            Write-ColorOutput "[+] $networkName" "Green"
            Write-ColorOutput "    Subnet: $($config.subnet)" "White"
            Write-ColorOutput "    Purpose: $($config.purpose)" "White"
            Write-ColorOutput "    Internal: $($config.internal)" "White"
            Write-ColorOutput "    Containers: $containers" "White"
        } else {
            Write-ColorOutput "[-] $networkName (not found)" "Red"
        }
        Write-Host ""
    }
}

# Main execution based on action
Write-ColorOutput "===== Lucid Network Management Script =====" "Cyan"
Write-ColorOutput "Environment: $Environment" "Yellow"
Write-ColorOutput "Action: $Action" "Yellow"
Write-Host ""

if (-not (Test-Docker)) {
    Write-ColorOutput "[-] Docker is not running or not accessible" "Red"
    exit 1
}

Write-ColorOutput "[+] Docker is running" "Green"

switch ($Action) {
    "create" {
        Write-ColorOutput "Creating Lucid networks..." "Blue"
        
        $success = $true
        foreach ($networkName in $LUCID_NETWORKS.Keys) {
            $config = $LUCID_NETWORKS[$networkName]
            
            # Skip dev network in production
            if ($networkName -eq "lucid_dev" -and $Environment -eq "prod") {
                Write-ColorOutput "[-] Skipping dev network in production environment" "Yellow"
                continue
            }
            
            if (-not (Create-LucidNetwork -NetworkName $networkName -NetworkConfig $config)) {
                $success = $false
            }
        }
        
        if ($success) {
            Write-ColorOutput "[+] All networks created successfully" "Green"
        } else {
            Write-ColorOutput "[-] Some networks failed to create" "Red"
            exit 1
        }
    }
    
    "remove" {
        Write-ColorOutput "Removing Lucid networks..." "Blue"
        
        foreach ($networkName in $LUCID_NETWORKS.Keys) {
            Remove-LucidNetwork -NetworkName $networkName
        }
    }
    
    "status" {
        Show-NetworkStatus
    }
    
    "test" {
        Write-ColorOutput "Testing network connectivity..." "Blue"
        
        foreach ($networkName in $LUCID_NETWORKS.Keys) {
            $config = $LUCID_NETWORKS[$networkName]
            
            # Skip internal networks for connectivity test (no external routing)
            if ($config.internal) {
                Write-ColorOutput "[!] Skipping internal network test: $networkName" "Yellow"
                continue
            }
            
            docker network inspect $networkName *>$null
            if ($LASTEXITCODE -eq 0) {
                Test-NetworkConnectivity -NetworkName $networkName -NetworkConfig $config
            } else {
                Write-ColorOutput "[-] Network $networkName not found" "Red"
            }
        }
    }
    
    "reset" {
        Write-ColorOutput "Resetting all Lucid networks..." "Blue"
        
        # Remove all networks
        foreach ($networkName in $LUCID_NETWORKS.Keys) {
            Remove-LucidNetwork -NetworkName $networkName
        }
        
        Start-Sleep -Seconds 2
        
        # Recreate all networks
        foreach ($networkName in $LUCID_NETWORKS.Keys) {
            $config = $LUCID_NETWORKS[$networkName]
            
            if ($networkName -eq "lucid_dev" -and $Environment -eq "prod") {
                continue
            }
            
            Create-LucidNetwork -NetworkName $networkName -NetworkConfig $config
        }
    }
}

Write-Host ""
Write-ColorOutput "===== Network Management Complete =====" "Cyan"