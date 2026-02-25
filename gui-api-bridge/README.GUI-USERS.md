# GUI API Bridge - GUI User Setup & Runtime Documentation

**File:** `gui-api-bridge/README.GUI-USERS.md`

## Overview

The Lucid GUI API Bridge provides cross-platform support for GUI applications running on Windows, macOS, and Linux. All GUI commands are automatically routed through a Linux runtime environment (Docker, WSL2, or Raspberry Pi) to ensure consistent behavior across platforms.

---

## Quick Start (5 minutes)

### 1. Initialize GUI User Environment

```bash
# Run full setup
bash gui-api-bridge/scripts/gui-user-setup.sh --full

# This will:
# - Create GUI user profile
# - Setup directories (.lucid/logs, .lucid/cache, etc.)
# - Add shell integration (aliases & PATH)
# - Configure Docker permissions
# - Setup credentials
```

### 2. Verify Setup

```bash
# Check initialization status
bash gui-api-bridge/scripts/gui-user-setup.sh --check
```

### 3. Ensure Linux Runtime

```bash
# Automatically detect and start Linux runtime
bash gui-api-bridge/scripts/os-detector-linux-enforcer.sh
```

### 4. Test API

```bash
# Check API health
gui-exec health

# Or manually:
bash gui-api-bridge/scripts/gui-exec.sh health
```

---

## Operating System Support

### Windows

**Requirements:**
- WSL2 (Windows Subsystem for Linux 2) - **Recommended**
- OR Docker Desktop
- Bash shell (Git Bash, WSL2, or Windows Terminal)

**Setup:**
```bash
# WSL2 will be auto-detected and started if available
bash gui-api-bridge/scripts/os-detector-linux-enforcer.sh

# Or start manually:
wsl.exe -d Ubuntu
```

**Verification:**
```bash
wsl --list --verbose
# Should show "Running" status
```

### macOS

**Requirements:**
- Docker Desktop (Recommended)
- Homebrew (optional, for command-line tools)

**Setup:**
```bash
# Docker will be auto-detected and started if available
bash gui-api-bridge/scripts/os-detector-linux-enforcer.sh

# Or start Docker manually:
open -a Docker
```

**Verification:**
```bash
docker ps
# Should list running containers
```

### Linux / Raspberry Pi

**If running natively on Linux:**
- Docker is optional (but recommended)
- All commands run directly

**If running on Pi:**
- No additional setup needed
- All commands run natively

---

## Available GUI Commands

All commands automatically use the correct Linux runtime.

### Health & Status

```bash
# Check API health
gui-exec health

# Show system status (OS, runtime, API URL)
gui-exec status

# Stream container logs
gui-exec logs

# Show container statistics
gui-exec stats
```

### API Operations

```bash
# GET request
gui-exec api GET /health

# POST request
gui-exec api POST /api/v1/user/profile -H "Content-Type: application/json"

# With data
gui-exec api POST /api/v1/user/profile -d '{"key": "value"}'
```

### Direct Execution

```bash
# Execute command in Linux runtime
gui-exec exec "docker ps"

# Execute multiple commands
gui-exec exec "cd /opt/lucid && ls -la"
```

---

## Shell Integration

After running `gui-user-setup.sh --shell-integration`, the following aliases are available:

```bash
# Shortcuts for common operations
lucid-health          # Check API health
lucid-logs            # Stream logs
lucid-status          # Show status
lucid-api             # Make API calls

# Examples:
lucid-health
lucid-api GET /health
lucid-logs
lucid-status
```

---

## Environment Variables

The following environment variables control behavior:

### User Configuration

```bash
# Enable debug output
export DEBUG=true

# Set API backend URL (auto-detected by default)
export LUCID_GUI_API_BRIDGE_URL=http://localhost:8102

# Enable auto-initialization on shell startup
export LUCID_AUTO_INIT_RUNTIME=true
```

### Raspberry Pi Configuration

```bash
# Set Pi host (default: 192.168.0.75)
export PI_HOST=192.168.0.75

# Set Pi user (default: pickme)
export PI_USER=pickme

# Set SSH port (default: 22)
export PI_SSH_PORT=22
```

### Docker Configuration

```bash
# Docker socket (auto-detected, usually unix:///var/run/docker.sock)
export DOCKER_HOST=unix:///var/run/docker.sock
```

---

## Runtime Types

The system automatically selects the best available runtime:

### Docker (Recommended)

**Platforms:** Windows, macOS, Linux

**Advantages:**
- Fast startup
- Consistent environment
- Easy to scale
- Works across all platforms

**Status Check:**
```bash
docker ps | grep lucid-gui-api-bridge
```

### WSL2 (Windows)

**Platforms:** Windows only

**Advantages:**
- Native Linux kernel
- Fast I/O
- Direct filesystem access

**Status Check:**
```bash
wsl -l -v
```

### Raspberry Pi (Native)

**Platforms:** Raspberry Pi (ARM64)

**Advantages:**
- No overhead
- Native performance
- Direct hardware access

**Status Check:**
```bash
uname -a
# Should show ARM64 architecture
```

---

## Configuration Files

### GUI User Profile

**Location:** `~/.lucid/.gui-user-profile`

Contains:
- Application settings
- Security configuration
- Logging settings
- Cache settings

### Credentials

**Location:** `~/.lucid/gui-auth-token`

Stores:
- JWT authentication token
- Protected with 600 permissions

---

## Troubleshooting

### API Health Check Failed

```bash
# 1. Check if Docker is running
docker ps

# 2. Check if container is running
docker ps -a | grep lucid-gui-api-bridge

# 3. View container logs
docker logs lucid-gui-api-bridge

# 4. Restart container
docker-compose -f gui-api-bridge/docker-compose.yml restart lucid-gui-api-bridge
```

### Runtime Not Detected

```bash
# 1. Check available runtimes
bash gui-api-bridge/scripts/os-detector-linux-enforcer.sh

# 2. Check OS detection
# Run with debug
DEBUG=true bash gui-api-bridge/scripts/os-detector-linux-enforcer.sh

# 3. Check Docker
docker --version
docker ps

# 4. Check WSL2
wsl --list --verbose

# 5. Check SSH to Pi
ssh -v pickme@192.168.0.75
```

### Shell Integration Not Working

```bash
# 1. Check if aliases are loaded
alias | grep lucid

# 2. Reload shell profile
source ~/.bashrc          # Bash
source ~/.zshrc           # Zsh
source ~/.profile         # General

# 3. Verify scripts are executable
ls -la gui-api-bridge/scripts/*.sh
# All should have 'x' permission

# 4. Manually set PATH
export PATH="$(pwd)/gui-api-bridge/scripts:$PATH"
```

### Permission Denied

**For Docker:**
```bash
# User must be in docker group
sudo usermod -aG docker $USER

# Then restart your shell/terminal
exit
# Re-login
```

**For SSH:**
```bash
# Check SSH key permissions
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

# Add SSH key to Pi
ssh-copy-id -i ~/.ssh/id_rsa pickme@192.168.0.75
```

---

## Advanced Usage

### Custom Command Execution

```bash
# Execute arbitrary command in Linux runtime
gui-exec exec "python3 -c 'import sys; print(sys.version)'"

# Run scripts
gui-exec exec "bash /path/to/script.sh"

# Check service status
gui-exec exec "systemctl status lucid-gui-api-bridge"
```

### API Request Examples

```bash
# Get user profile
gui-exec api GET /api/v1/user/profile

# Create session
gui-exec api POST /api/v1/user/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'

# List sessions
gui-exec api GET /api/v1/user/sessions

# Recover session token
gui-exec api POST /api/v1/user/sessions/session-123/recover \
  -H "Content-Type: application/json" \
  -d '{"owner_address": "0x..."}'
```

### Monitoring & Debugging

```bash
# Real-time container stats
gui-exec stats

# View last 100 log lines
docker logs -n 100 lucid-gui-api-bridge

# Follow logs with grep filter
docker logs -f lucid-gui-api-bridge | grep ERROR

# Check network connectivity
gui-exec exec "ping lucid-api-gateway"

# Verify environment variables
gui-exec exec "env | grep LUCID"
```

---

## Automated Initialization

### Auto-Start on Shell Login

Add to `~/.bashrc` (or `~/.zshrc`):

```bash
# Auto-initialize Linux runtime on shell startup
export LUCID_AUTO_INIT_RUNTIME=true
```

Then reload:
```bash
source ~/.bashrc
# or
source ~/.zshrc
```

### Background Initialization

To ensure runtime is always ready:

```bash
# In crontab (runs every minute)
* * * * * bash /path/to/gui-api-bridge/scripts/os-detector-linux-enforcer.sh > /dev/null 2>&1
```

---

## Security

### JWT Token Management

```bash
# Set JWT token
export LUCID_GUI_AUTH_TOKEN="your-jwt-token-here"

# Verify token is loaded
echo $LUCID_GUI_AUTH_TOKEN

# Token is stored in ~/.lucid/gui-auth-token (600 permissions)
ls -la ~/.lucid/gui-auth-token
```

### SSH Key Setup (for Pi)

```bash
# Generate SSH key (if needed)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""

# Copy to Pi
ssh-copy-id -i ~/.ssh/id_rsa pickme@192.168.0.75

# Test connection
ssh -i ~/.ssh/id_rsa pickme@192.168.0.75 "echo 'Connected!'"
```

---

## Logs & Debugging

### View Logs

```bash
# Stream logs
gui-exec logs

# View logs from last 10 minutes
docker logs --since 10m lucid-gui-api-bridge

# Search logs
docker logs lucid-gui-api-bridge | grep "ERROR\|WARNING"
```

### Enable Debug Mode

```bash
# Set environment variable
export DEBUG=true

# Run with debug output
DEBUG=true gui-exec health

# Or re-run setup with debug
DEBUG=true bash gui-api-bridge/scripts/os-detector-linux-enforcer.sh
```

### Debug Files

```bash
# Check log files
tail -f ~/.lucid/logs/gui-app.log

# Check cache
ls -la ~/.lucid/cache

# Check config
cat ~/.lucid/.gui-user-profile
```

---

## Support & References

### Project Files

- **Alignment Report:** `gui-api-bridge/ALIGNMENT_COMPLETION_REPORT.md`
- **README:** `gui-api-bridge/README.md`
- **Configuration:** `gui-api-bridge/config/rate-limit-config.yaml`
- **Routing:** `gui-api-bridge/config/routing-config.yaml`

### Scripts

- **OS Detector:** `gui-api-bridge/scripts/os-detector-linux-enforcer.sh`
- **GUI Executor:** `gui-api-bridge/scripts/gui-exec.sh`
- **User Setup:** `gui-api-bridge/scripts/gui-user-setup.sh`
- **Build:** `gui-api-bridge/scripts/build.sh`
- **Deploy:** `gui-api-bridge/scripts/deploy.sh`

### External Resources

- [WSL2 Documentation](https://docs.microsoft.com/en-us/windows/wsl/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Raspberry Pi SSH](https://www.raspberrypi.org/documentation/remote-access/ssh/)

---

## Frequently Asked Questions

### Q: Can I run this on Windows without WSL2 or Docker?

**A:** No. GUI applications need a Linux runtime to ensure compatibility. Please install either WSL2 or Docker Desktop.

### Q: What's the difference between WSL2 and Docker?

**A:** 
- **WSL2:** Native Linux kernel, better for development
- **Docker:** Better for production, containerized isolation

Both work equally well for GUI API Bridge.

### Q: How do I check which runtime is being used?

**A:** Run `gui-exec status` - it will show the detected runtime.

### Q: Can I use SSH to my Pi instead of Docker?

**A:** Yes. The system will auto-detect SSH if available and Docker is not. Ensure SSH is enabled on your Pi and `PI_HOST` is set.

### Q: Why do I get "Permission denied" with Docker?

**A:** Your user is not in the docker group. Run:
```bash
sudo usermod -aG docker $USER
# Then restart your shell
exit
```

### Q: How do I update the GUI API Bridge?

**A:** Pull the latest changes and rebuild:
```bash
cd gui-api-bridge
git pull
bash scripts/build.sh
bash scripts/deploy.sh
```

---

## Getting Help

1. **Check logs:** `gui-exec logs`
2. **Check status:** `gui-exec status`
3. **Run diagnostics:** `DEBUG=true bash scripts/os-detector-linux-enforcer.sh`
4. **Check documentation:** See above sections

---

**Last Updated:** 2026-02-25
**Version:** 1.0.0
