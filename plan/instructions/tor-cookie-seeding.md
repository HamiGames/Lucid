# Tor Cookie Seeding Guide

This document describes the manual process to seed Tor cookie files using the `pickme/lucid-tor-proxy:latest-arm64` Docker image. The cookie files are required for Tor control port authentication and must be created before the production tor-proxy container can start.

## Prerequisites

- Docker installed and running
- Docker network `lucid-pi-network` exists
- Project root: `/mnt/myssd/Lucid/Lucid/`
- Directories exist:
  - `/mnt/myssd/Lucid/Lucid/data/tor`
  - `/mnt/myssd/Lucid/Lucid/logs/tor`
  - `/mnt/myssd/Lucid/Lucid/data/tor-run`
  - `/mnt/myssd/Lucid/Lucid/config/tor/`

## Step 1: Discover Container User UID/GID

The `pickme/lucid-tor-proxy:latest-arm64` image runs as the `debian-tor` user. We need to discover its numeric UID/GID to set correct ownership on host directories:

```bash
docker run --rm pickme/lucid-tor-proxy:latest-arm64 /bin/busybox awk -F: '$1=="debian-tor"{print $3":"$4}' /etc/passwd /etc/group
```

Expected output: `100:101` (UID 100, GID 101)

**Note:** On the host, these numeric IDs may appear as `messagebus:_ssh` when viewed with `ls`, but the container will recognize them as the `debian-tor` user.

## Step 2: Set Directory Ownership and Permissions

Set ownership to UID 100, GID 101 (the `debian-tor` user) and apply the correct permissions:

```bash
# Set ownership on all Tor directories
sudo chown -R 100:101 /mnt/myssd/Lucid/Lucid/data/tor
sudo chown -R 100:101 /mnt/myssd/Lucid/Lucid/logs/tor
sudo chown -R 100:101 /mnt/myssd/Lucid/Lucid/data/tor-run

# Set permissions (Tor requires strict permissions)
sudo chmod 700 /mnt/myssd/Lucid/Lucid/data/tor
sudo chmod 755 /mnt/myssd/Lucid/Lucid/logs/tor
sudo chmod 755 /mnt/myssd/Lucid/Lucid/data/tor-run
```

**Critical:** The `data/tor` directory must be `700` (drwx------) for Tor security. The `logs/tor` and `data/tor-run` directories should be `755` (drwxr-xr-x).

## Step 3: Ensure torrc Configuration Exists

The Tor configuration file must exist at `/mnt/myssd/Lucid/Lucid/config/tor/torrc`. This file will be mounted read-only into the container at `/etc/tor/torrc`.

**Important:** The torrc file must be configured for cookie authentication and file-based logging. Ensure it contains at minimum:

```
Log notice file /var/log/tor/notices.log
SafeLogging 1
SocksPort 0.0.0.0:9050
ControlPort 127.0.0.1:9051
CookieAuthentication 1
CookieAuthFile /var/lib/tor/control_auth_cookie
DataDirectory /var/lib/tor
ClientOnly 1
ExitPolicy reject *:*
RunAsDaemon 0
AvoidDiskWrites 0
```

Set appropriate ownership on the torrc file (readable by the container):

```bash
sudo chown pickme:pickme /mnt/myssd/Lucid/Lucid/config/tor/torrc
sudo chmod 664 /mnt/myssd/Lucid/Lucid/config/tor/torrc
```

## Step 4: Clean Up Any Existing Container

Before starting a new seeding run, ensure no previous container is running:

```bash
docker rm -f tor-bootstrap-temp 2>/dev/null
```

## Step 5: Start the Container for Cookie Seeding

Run the container with the correct volume mounts and network configuration:

```bash
docker run -d --rm \
  --name tor-bootstrap-temp \
  --network lucid-pi-network \
  --ip 172.20.0.9 \
  --cap-drop=ALL \
  --security-opt no-new-privileges:true \
  --tmpfs /tmp:noexec,nosuid,size=64m \
  -v /mnt/myssd/Lucid/Lucid/data/tor:/var/lib/tor:rw \
  -v /mnt/myssd/Lucid/Lucid/logs/tor:/var/log/tor:rw \
  -v /mnt/myssd/Lucid/Lucid/data/tor-run:/run:rw \
  -v /mnt/myssd/Lucid/Lucid/config/tor:/etc/tor:ro \
  pickme/lucid-tor-proxy:latest-arm64 /usr/local/bin/entrypoint.sh
```

## Step 6: Monitor Bootstrap Progress

Watch the container logs to verify Tor starts and bootstraps successfully:

```bash
docker logs -f tor-bootstrap-temp
```

You should see:
1. Entrypoint initialization messages
2. Tor starting and opening listeners
3. Bootstrap progress messages: `Bootstrapped 0%`, `5%`, `10%`, etc.
4. Final success: `Bootstrapped 100% (done): Done`

**Expected timeline:** Bootstrap typically completes within 1-2 minutes. The entrypoint script will poll for up to 180 attempts (~6 minutes) before timing out.

## Step 7: Verify Cookie Files Were Created

Once bootstrap reaches 100%, verify the cookie and state files exist on the host:

```bash
sudo ls -lh /mnt/myssd/Lucid/Lucid/data/tor
```

You should see:
- `control_auth_cookie` (32 bytes) - **This is the critical file**
- `state` (several KB)
- `cached-certs`
- `cached-microdesc-consensus`
- `cached-microdescs.new`
- `keys/` directory
- `lock` file
- `tor.pid` file

**Note:** The directory has `700` permissions, so you must use `sudo` to list its contents.

## Step 8: Verify Bootstrap Completion in Logs

Check the Tor notices log for the final bootstrap confirmation:

```bash
sudo tail -n 100 /mnt/myssd/Lucid/Lucid/logs/tor/notices.log | grep -i "Bootstrapped 100%"
```

You should see:
```
Nov XX XX:XX:XX.XXX [notice] Bootstrapped 100% (done): Done
```

## Step 9: Stop the Temporary Container

Once bootstrap is complete and files are verified, stop the seeding container:

```bash
docker rm -f tor-bootstrap-temp
```

The seeded files in `/mnt/myssd/Lucid/Lucid/data/tor` will remain and can be reused by the production tor-proxy container.

## Troubleshooting

### Permission Denied Errors

If you see `Permission denied` errors in the logs:
- Verify ownership is set to `100:101` on all directories
- Verify `data/tor` has `700` permissions
- Verify `logs/tor` has `755` permissions

### Bootstrap Never Reaches 100%

If bootstrap stalls:
- Check the full Tor notices log: `sudo tail -n 200 /mnt/myssd/Lucid/Lucid/logs/tor/notices.log`
- Look for network errors, DNS failures, or clock skew warnings
- Ensure the container has network access to reach Tor directory authorities

### Input/Output Errors

If you see `Input/output error` when running commands:
- The external drive (`/mnt/myssd`) may have disconnected
- Check drive status: `lsblk` and `sudo dmesg | tail -n 40`
- Remount the drive if necessary before continuing

### Container Exits Immediately

If the container exits with status 137 or other errors:
- Check full logs: `docker logs tor-bootstrap-temp`
- Verify all volume mounts are correct
- Verify the torrc file exists and is readable
- Ensure the Docker network `lucid-pi-network` exists

## Production Usage

After seeding is complete, the production `tor-proxy` service in `docker-compose.foundation.yml` will automatically use the seeded cookie files when it mounts:

```yaml
volumes:
  - /mnt/myssd/Lucid/Lucid/data/tor:/var/lib/tor:rw
  - /mnt/myssd/Lucid/Lucid/logs/tor:/var/log/tor:rw
```

The `control_auth_cookie` file will be read by Tor on startup, and the cached consensus/descriptor files will speed up subsequent bootstraps.

## Summary

The successful seeding process requires:
1. ✅ Correct ownership (UID 100, GID 101) on all Tor directories
2. ✅ Correct permissions (700 for data/tor, 755 for logs/tor and data/tor-run)
3. ✅ Valid torrc configuration file
4. ✅ Container running with proper volume mounts
5. ✅ Bootstrap reaching 100% completion
6. ✅ `control_auth_cookie` file created (32 bytes)

Once these steps are complete, the Tor cookie files are ready for production use.

