# Lucid Storage Re-mount Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | LUCID-STORAGE-REMOUNT-001 |
| Version | 1.0.0 |
| Status | ACTIVE |
| Last Updated | 2025-01-14 |
| Target Platform | Raspberry Pi (Pi Console) |
| Mount Point | `/mnt/myssd/Lucid/Lucid` |

---

## Overview

This guide provides step-by-step instructions for re-mounting storage devices (NVMe drives, SSDs, or other block devices) on the Raspberry Pi console. The guide covers device identification, filesystem checking, repair procedures, and permanent mounting configuration.

### Prerequisites

- SSH access to Raspberry Pi console
- Sudo/root privileges
- Basic understanding of Linux filesystem operations

**⚠️ IMPORTANT:** This guide assumes you want to preserve existing data. Formatting commands are clearly marked and should only be used on empty drives.

---

## Quick Reference

### Standard Re-mount Sequence (Drive with Existing Filesystem)

```bash
# 1. Identify device
lsblk

# 2. Check filesystem status
sudo blkid /dev/sdX
sudo file -s /dev/sdX

# 3. Repair if needed
sudo fsck -y /dev/sdX

# 4. Create mount point
sudo mkdir -p /mnt/myssd/Lucid/Lucid

# 5. Mount device
sudo mount /dev/sdX /mnt/myssd

# 6. Set permissions
sudo chown -R pickme:pickme /mnt/myssd
sudo chmod -R 755 /mnt/myssd

# 7. Verify
df -h /mnt/myssd
ls -la /mnt/myssd
```

---

## Step-by-Step Procedures

### Step 1: Identify the Storage Device

**Terminal DIR:** Raspberry Pi console (SSH session)

```bash
# List all block devices
lsblk

# Look for your device - common patterns:
# - NVMe drives: /dev/nvme0n1, /dev/nvme0n1p1 (with partition)
# - SATA/USB drives: /dev/sda, /dev/sdb, /dev/sdi, etc.
# - SD cards: /dev/mmcblk0, /dev/mmcblk0p1, etc.
```

**Example Output:**
```
NAME        MAJ:MIN RM   SIZE RO TYPE MOUNTPOINTS
sdi           8:128  0 931.5G  0 disk    <-- This is your device
mmcblk0     179:0    0  59.5G  0 disk
├─mmcblk0p1 179:1    0   512M  0 part /boot/firmware
└─mmcblk0p2 179:2    0    59G  0 part /
```

**Note:** In the example above, `/dev/sdi` is the 931.5GB drive with no partitions.

---

### Step 2: Check Current Mount Status

```bash
# Check if device is already mounted
mount | grep sdX    # Replace sdX with your device (e.g., sdi, nvme0n1)
df -h | grep sdX

# Check what's using the device
sudo lsof /dev/sdX 2>/dev/null
sudo fuser -v /dev/sdX 2>/dev/null
```

**If device is mounted:**
```bash
# Unmount first (if needed)
sudo umount /mnt/myssd 2>/dev/null || true
```

---

### Step 3: Check Filesystem Status

```bash
# Check for existing filesystem
sudo blkid /dev/sdX

# Get detailed filesystem information
sudo file -s /dev/sdX

# Check partition table (if applicable)
sudo fdisk -l /dev/sdX
```

**Expected Outputs:**

**A) Device with ext4 filesystem:**
```
/dev/sdi: UUID="7feb1cc6-14fb-49ff-9144-7cade5f6137a" BLOCK_SIZE="4096" TYPE="ext4"
/dev/sdi: Linux rev 1.0 ext4 filesystem data, UUID=7feb1cc6-14fb-49ff-9144-7cade5f6137a (extents) (64bit)
```
→ **Proceed to Step 4 (Repair if needed) or Step 5 (Mount directly)**

**B) Device with filesystem needing repair:**
```
/dev/sdi: Linux rev 1.0 ext4 filesystem data, UUID=... (needs journal recovery)
```
→ **Proceed to Step 4 (Repair required)**

**C) No output from blkid:**
```
(empty output)
```
→ **Device has no filesystem - see "Formatting Empty Drive" section below**

---

### Step 4: Repair Filesystem (If Needed)

**⚠️ SAFE OPERATION:** This repairs filesystem structure and won't remove your data.

```bash
# Run filesystem check and repair
sudo fsck -y /dev/sdX

# The -y flag automatically answers "yes" to repair questions
# This is safe and only fixes filesystem structure issues
```

**What fsck does:**
- Repairs journal inconsistencies
- Fixes directory structure issues
- Recovers orphaned inodes
- Does NOT delete your files

**After repair, verify:**
```bash
sudo blkid /dev/sdX
# Should now show clean filesystem status
```

---

### Step 5: Create Mount Point Directory

```bash
# Create the mount point structure
sudo mkdir -p /mnt/myssd/Lucid/Lucid

# Verify directory was created
ls -la /mnt/myssd
```

---

### Step 6: Mount the Device

```bash
# Mount the device
sudo mount /dev/sdX /mnt/myssd

# OR specify filesystem type explicitly (if auto-detection fails)
sudo mount -t ext4 /dev/sdX /mnt/myssd

# For other filesystem types:
# sudo mount -t xfs /dev/sdX /mnt/myssd
# sudo mount -t ext3 /dev/sdX /mnt/myssd
```

---

### Step 7: Verify Mount

```bash
# Check mount status
df -h /mnt/myssd
mount | grep sdX

# List contents
ls -la /mnt/myssd

# Check directory structure
ls -la /mnt/myssd/Lucid/Lucid
```

**Expected output from `df -h`:**
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/sdi        916G  123G  747G  15% /mnt/myssd
```

---

### Step 8: Set Permissions

```bash
# Set ownership (replace 'pickme' with your username)
sudo chown -R pickme:pickme /mnt/myssd

# Set directory permissions
sudo chmod -R 755 /mnt/myssd

# Verify permissions
ls -ld /mnt/myssd
```

---

### Step 9: Configure Permanent Mounting (Optional but Recommended)

To ensure the drive mounts automatically on boot, add it to `/etc/fstab`.

#### 9.1: Get Device UUID

```bash
# Get UUID (more reliable than device name)
sudo blkid /dev/sdX

# Example output:
# /dev/sdi: UUID="7feb1cc6-14fb-49ff-9144-7cade5f6137a" BLOCK_SIZE="4096" TYPE="ext4"
```

#### 9.2: Backup Current fstab

```bash
# Create backup
sudo cp /etc/fstab /etc/fstab.backup.$(date +%Y%m%d_%H%M%S)
```

#### 9.3: Add Entry to fstab

```bash
# Add entry using UUID (replace YOUR-UUID-HERE with actual UUID)
echo "UUID=YOUR-UUID-HERE /mnt/myssd ext4 defaults,noatime 0 2" | sudo tee -a /etc/fstab

# Example with actual UUID:
# echo "UUID=7feb1cc6-14fb-49ff-9144-7cade5f6137a /mnt/myssd ext4 defaults,noatime 0 2" | sudo tee -a /etc/fstab
```

**fstab Entry Explanation:**
- `UUID=...` - Device identifier (more reliable than /dev/sdX)
- `/mnt/myssd` - Mount point
- `ext4` - Filesystem type
- `defaults,noatime` - Mount options (noatime improves performance)
- `0` - Dump option (0 = don't backup with dump)
- `2` - Filesystem check order (2 = check after root filesystem)

#### 9.4: Test fstab Entry

```bash
# Test fstab configuration (won't remount if already mounted)
sudo mount -a

# If no errors, the entry is valid
# To test full remount:
sudo umount /mnt/myssd
sudo mount -a
df -h /mnt/myssd
```

---

## Special Cases

### Case 1: Device with Partitions

If your device has partitions (e.g., `/dev/nvme0n1p1`, `/dev/sda1`):

```bash
# Mount the partition, not the whole device
sudo mount /dev/nvme0n1p1 /mnt/myssd
# OR
sudo mount /dev/sda1 /mnt/myssd
```

### Case 2: NVMe Drive

NVMe drives typically appear as `/dev/nvme0n1` (whole device) or `/dev/nvme0n1p1` (first partition):

```bash
# Check NVMe device
lsblk | grep nvme
sudo blkid /dev/nvme0n1
sudo blkid /dev/nvme0n1p1  # If partitioned

# Mount accordingly
sudo mount /dev/nvme0n1p1 /mnt/myssd  # If partitioned
# OR
sudo mount /dev/nvme0n1 /mnt/myssd    # If no partitions
```

### Case 3: Empty Drive (No Filesystem)

**⚠️ WARNING: Formatting will ERASE all data on the drive!**

Only format if:
- The drive is new/empty
- You want to erase all existing data
- You've confirmed there's no important data

```bash
# 1. Verify drive is empty (check first!)
sudo file -s /dev/sdX
# Should show: "/dev/sdX: data" (no filesystem)

# 2. Create ext4 filesystem
sudo mkfs.ext4 -F /dev/sdX

# OR for better NVMe performance:
sudo mkfs.ext4 -F -E lazy_itable_init=0,lazy_journal_init=0 /dev/sdX

# 3. Then proceed with mounting (Step 5 onwards)
```

---

## Troubleshooting

### Problem: "mount: /mnt/myssd: mount point does not exist"

**Solution:**
```bash
sudo mkdir -p /mnt/myssd/Lucid/Lucid
```

### Problem: "mount: /mnt/myssd: device is busy"

**Solution:**
```bash
# Find what's using the mount point
sudo lsof /mnt/myssd
sudo fuser -v /mnt/myssd

# Unmount forcefully if needed (use with caution)
sudo umount -l /mnt/myssd
```

### Problem: "mount: wrong fs type, bad option, bad superblock"

**Solution:**
```bash
# Check filesystem type
sudo blkid /dev/sdX
sudo file -s /dev/sdX

# Try mounting with explicit filesystem type
sudo mount -t ext4 /dev/sdX /mnt/myssd

# Or repair filesystem first
sudo fsck -y /dev/sdX
```

### Problem: "Permission denied" after mount

**Solution:**
```bash
# Set ownership
sudo chown -R pickme:pickme /mnt/myssd
sudo chmod -R 755 /mnt/myssd
```

### Problem: Device not mounting on boot (fstab issue)

**Solution:**
```bash
# Check fstab syntax
sudo mount -a

# Verify UUID is correct
sudo blkid /dev/sdX
sudo grep myssd /etc/fstab

# Check system logs
sudo journalctl -b | grep mount
```

### Problem: Filesystem shows "needs journal recovery"

**Solution:**
```bash
# This is normal after unclean shutdown - just repair it
sudo fsck -y /dev/sdX
```

---

## Complete Re-mount Script

For convenience, here's a complete script that handles the standard re-mount procedure:

```bash
#!/bin/bash
# Lucid Storage Re-mount Script
# Usage: ./remount-storage.sh /dev/sdX

set -euo pipefail

DEVICE="${1:-}"
MOUNT_POINT="/mnt/myssd"
USER="${USER:-pickme}"

if [ -z "$DEVICE" ]; then
    echo "Usage: $0 /dev/sdX"
    echo "Example: $0 /dev/sdi"
    exit 1
fi

if [ ! -b "$DEVICE" ]; then
    echo "Error: $DEVICE is not a block device"
    exit 1
fi

echo "=== Lucid Storage Re-mount Procedure ==="
echo "Device: $DEVICE"
echo "Mount Point: $MOUNT_POINT"
echo ""

# Step 1: Check filesystem
echo "Step 1: Checking filesystem status..."
FS_INFO=$(sudo blkid "$DEVICE" || echo "")
if [ -z "$FS_INFO" ]; then
    echo "ERROR: No filesystem detected on $DEVICE"
    echo "Device may need formatting (this will ERASE data!)"
    exit 1
fi
echo "Filesystem detected: $FS_INFO"
echo ""

# Step 2: Check if needs repair
echo "Step 2: Checking filesystem health..."
if echo "$FS_INFO" | grep -q "needs journal recovery"; then
    echo "Filesystem needs repair - running fsck..."
    sudo fsck -y "$DEVICE"
else
    echo "Filesystem appears healthy"
fi
echo ""

# Step 3: Unmount if already mounted
echo "Step 3: Checking for existing mounts..."
if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
    echo "Unmounting existing mount..."
    sudo umount "$MOUNT_POINT"
fi
echo ""

# Step 4: Create mount point
echo "Step 4: Creating mount point..."
sudo mkdir -p "$MOUNT_POINT/Lucid/Lucid"
echo ""

# Step 5: Mount device
echo "Step 5: Mounting device..."
sudo mount "$DEVICE" "$MOUNT_POINT"
echo ""

# Step 6: Set permissions
echo "Step 6: Setting permissions..."
sudo chown -R "$USER:$USER" "$MOUNT_POINT"
sudo chmod -R 755 "$MOUNT_POINT"
echo ""

# Step 7: Verify
echo "Step 7: Verifying mount..."
df -h "$MOUNT_POINT"
echo ""
ls -la "$MOUNT_POINT"
echo ""

echo "=== Re-mount Complete ==="
echo "Device $DEVICE is now mounted at $MOUNT_POINT"
```

**Save and use:**
```bash
# Save script
nano remount-storage.sh
chmod +x remount-storage.sh

# Run it
./remount-storage.sh /dev/sdi
```

---

## Verification Checklist

After completing the re-mount procedure, verify:

- [ ] Device is mounted: `df -h /mnt/myssd` shows the device
- [ ] Mount point exists: `ls -la /mnt/myssd` shows directory
- [ ] Permissions correct: `ls -ld /mnt/myssd` shows correct ownership
- [ ] Directory structure exists: `ls -la /mnt/myssd/Lucid/Lucid`
- [ ] Writable: `touch /mnt/myssd/test && rm /mnt/myssd/test`
- [ ] fstab entry added (if permanent mount desired): `grep myssd /etc/fstab`
- [ ] fstab entry tested: `sudo mount -a` (no errors)

---

## Related Documentation

- [Lucid Deployment Guide](./deployment-guide.md)
- [Backup and Recovery Guide](./backup-recovery-guide.md)
- [Troubleshooting Guide](./troubleshooting-guide.md)

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-01-14 | Initial document creation | System |

---

**Last Updated:** 2025-01-14  
**Status:** ACTIVE

