# How to Restart Docker Desktop on Windows

## Why Restart is Required

After changing Docker's `daemon.json` configuration file, **Docker Desktop MUST be restarted** for the DNS settings to take effect. The configuration changes are only loaded at startup.

## Step-by-Step Restart Instructions

### Method 1: System Tray (Recommended)

1. **Locate Docker Desktop Icon**:

   - Look in the **system tray** (bottom-right corner of screen)

   - Look for the Docker whale icon 🐳

1. **Quit Docker Desktop**:

   - **Right-click** on the Docker whale icon

   - Click **"Quit Docker Desktop"**

   - Wait for the icon to disappear (about 5-10 seconds)

1. **Restart Docker Desktop**:

   - Press **Windows key**

   - Type **"Docker Desktop"**

   - Click **Docker Desktop** from the search results

   - **OR** go to Start Menu → Docker Desktop

1. **Wait for Startup**:

   - Watch the system tray for the Docker whale icon to reappear

   - Wait until the icon turns **solid/green** (not animated)

   - This usually takes 30-60 seconds

### Method 2: Task Manager (If System Tray Method Fails)

1. **Open Task Manager**:

   - Press **Ctrl + Shift + Esc**

   - **OR** Right-click taskbar → Task Manager

1. **End Docker Processes**:

   - Look for **"Docker Desktop"** in the processes

   - **Right-click** → **End Task**

   - Also end any **"dockerd"** or **"docker"** processes

1. **Restart Docker Desktop**:

   - Press **Windows key**

   - Type **"Docker Desktop"**

   - Launch Docker Desktop

1. **Wait for Full Startup**:

   - Monitor system tray for Docker whale icon

   - Wait for solid/green icon (not spinning/animated)

### Method 3: Command Line (Alternative)

```powershell

# Stop Docker Desktop

taskkill /f /im "Docker Desktop.exe"
Start-Sleep -Seconds 10

# Start Docker Desktop

Start-Process "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"

# Wait and verify

Start-Sleep -Seconds 30
docker info

```php

## Verification Steps

After restarting, verify Docker is working:

```powershell

# Test 1: Basic Docker info

docker info

# Test 2: Pull a small image

docker pull hello-world

# Test 3: Run the image

docker run hello-world

```php

## Signs Docker is Ready

✅ **Docker is Ready When**:

- Docker whale icon is visible in system tray

- Icon is solid/green (not animated/spinning)

- `docker info` command runs without errors

- Can pull images without DNS timeouts

❌ **Docker is NOT Ready When**:

- No Docker icon in system tray

- Icon is spinning/animated

- `docker info` shows connection errors

- Cannot pull images (DNS timeout errors)

## Troubleshooting Restart Issues

### If Docker Won't Start:

1. **Check Windows Services**:

   - Press `Windows + R` → type `services.msc`

   - Look for **"Docker Desktop Service"**

   - Right-click → Restart

1. **Check for Updates**:

   - Open Docker Desktop

   - Go to Settings → Software Updates

   - Install any available updates

1. **Reset Docker Desktop** (Last Resort):

   - Open Docker Desktop

   - Go to **Settings → Troubleshoot**

   - Click **"Reset to factory defaults"**

   - **Warning**: This will delete all containers and images

### If DNS Issues Persist After Restart:

1. **Verify Configuration Applied**:

   ```powershell

   Get-Content "$env:USERPROFILE\.docker\daemon.json"

   ```

1. **Check Docker System Info**:

   ```powershell

   docker system info | Select-String "DNS"

   ```

1. **Test DNS Resolution**:

   ```powershell

   Resolve-DnsName registry-1.docker.io

   ```

## Common Mistakes

❌ **Don't Do These**:

- Restart your computer instead of Docker Desktop

- Skip waiting for Docker to fully start

- Assume Docker is ready when the icon first appears

- Run multiple restart attempts rapidly

✅ **Do These Instead**:

- Only restart Docker Desktop application

- Wait for the solid/green whale icon

- Test with `docker info` before proceeding

- Be patient during the 30-60 second startup time

---

**Remember**: The DNS configuration only takes effect after a **complete restart** of Docker Desktop. Simply refreshing or reloading is not sufficient.
