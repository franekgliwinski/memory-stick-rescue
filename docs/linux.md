# Linux read-only import

Use a Linux environment with Python 3.9+ and util-linux (`mount`, `umount`, `findmnt`, `blockdev`, `blkid`), and a kernel that supports the exact Sony `054c:002d`. The original Windows/WSL hardware test used this kernel's USB storage support. Native Linux desktop/live-USB combinations require their own check; this repository does not write a boot USB or distribute an OS image.

For a Linux VM on Mac, the **actual USB device must be passed into the guest**. A mounted shared host folder or a Linux shell alone is insufficient.

1. Set the card LOCK switch if available, then connect the reader. Decline any format/repair prompt.
2. Run `python3 linux/inspect_reader.py`. If another desktop tool automatically mounted the card, safely unmount the matching Sony volume first using that desktop's eject/unmount function. The importer refuses already mounted devices; it never steals a mount or guesses a disk name.
3. Make a dedicated backup directory on the computer, not on the card. Run:

```sh
mkdir -p "$HOME/Pictures/MemoryStick-Backups"
sudo python3 linux/import_card.py \
  --output-root "$HOME/Pictures/MemoryStick-Backups" \
  --result-json "$HOME/Pictures/MemoryStick-Backups/result-$(date -u +%Y%m%dT%H%M%SZ).json" \
  --capture-image
```

`--capture-image` is optional and preserves the complete card, including unused space. Treat an image as private, because deleted-data remnants may exist. An image backup is not a deleted-file recovery tool. Use a fresh result path for every invocation. The Linux helper creates root-owned batch files with normal read permissions; it does not grant arbitrary permissions or change system policy.

The helper selects disks by sysfs USB ancestry and refuses ambiguous readers, disks, partitions, unexpected capacity and non-FAT filesystems. It sets all matching block nodes read-only, verifies read-only status and mounts privately. A successful run unmounts only its own mount. It does not detach a VM USB mapping: use the VM's disconnect/eject control after success before unplugging the cable. If cleanup fails, keep the reader connected until the exact mount can be inspected and safely unmounted.

Copy a completed batch to the host if using a guest. Run `python3 tools/verify_backup.py /path/to/batch` **on the delivered host copy**, not just inside the guest. File transfer does not change the camera's recording quality. Reformatting the card, changing permissions globally, or adding it to `/etc/fstab` is unnecessary for this importer.
