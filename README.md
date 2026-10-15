# Memory Stick Rescue — Sony MSAC-US1

Read-only file import for the legacy **Sony MSAC-US1 USB reader, VID:PID `054c:002d`**, with verified copies and no card erasure. Built from a working Windows/WSL recovery workflow for an original **32 MB Memory Stick**.

[Instrukcja po polsku](docs/START-PL.md) · [Windows setup](docs/windows.md) · [Linux](docs/linux.md) · [macOS status](docs/macos.md) · [Safety and verification](docs/SAFETY.md)

This is a small source toolkit, **not a new universal Sony driver**. It contains no proprietary drivers, personal media or card images. It does not transfer MiniDV tapes or improve image quality; it copies the bytes already on a card.

## Choose a computer

| Host | Route | Evidence and limits |
| --- | --- | --- |
| Windows 10/11 **x64** | usbipd-win → Ubuntu WSL2 → Linux USB storage driver | Original workflow tested on Windows 10 x64 with the real Sony reader and a 32 MB FAT12 card, including physical reconnect. Public portable adaptation has separate synthetic checks; fresh-machine setup is not yet hardware-tested. |
| Linux | Kernel USB storage support → read-only importer | Same importer design; public adaptation tested with synthetic data. Native Linux hardware combinations are not certified. |
| Current macOS, Intel/Apple Silicon | Start with USB diagnosis; native userspace or Linux guest route requires validation | USB enumeration alone is not card access. No working macOS importer is claimed in this initial release. See the dated status in docs/macos.md. |

Only the exact reader ID and original 32 MB cards are in scope. A 16–40 million byte guard rejects other capacities. Memory Stick PRO/Duo, other Sony readers, Windows ARM, Windows x86, other ports, reboots and future OS versions need separate validation.

## Windows quick start

Download this repository with **Code → Download ZIP**, extract it to a local drive and read [windows.md](docs/windows.md). No GitHub account or Git installation is needed to download a public ZIP.

Install/initialize Ubuntu **WSL2** first if missing. Check the prerequisites without changing USB configuration:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows\Setup-Windows.ps1
```

When ready to explicitly install the pinned signed usbipd-win package and configure this reader, run **as Administrator**:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows\Setup-Windows.ps1 -InstallUsbipd -ConfigureReader
```

Setup installs a USB/IP service and signed proxy driver, and restricts its firewall rule to the WSL virtual interface and `LocalSubnet`. It binds **only** `054c:002d`. This service-wide firewall restriction may affect other existing usbipd users; inspect a shared installation first. Setup does not reboot or shut down WSL. `-WhatIf` previews setup mutations.

For daily use, insert the card, plug the reader into the configured USB port and double-click:

**`windows/Import Memory Stick.cmd`**

The default destination is `Pictures/MemoryStick-Backups`. A successful run opens the copied files. To choose another local drive or also preserve a full card image:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows\Import-MemoryStick.ps1 -OutputRoot 'D:\MemoryStick-Backups' -CaptureImage
```

## What a successful import means

1. Exactly one matching Sony reader and one card are identified; device names are discovered dynamically.
2. Already mounted cards are rejected. Linux block devices are made read-only and FAT is mounted with `ro,nosuid,nodev,noexec,noatime`.
3. Files are copied to a fresh timestamped batch. Each source stream and an independent destination reread must have matching SHA-256 hashes and sizes. Windows also performs a native destination readback.
4. The importer unmounts its volume; Windows detaches its USB/IP attachment. A final folder and `VERIFIED_COPY` receipt are produced only after successful copying and unmounting. A Windows cleanup failure is reported separately.

Each batch contains `Files/`, `manifest.json`, `SHA256SUMS.txt` and, if requested, `CARD.img`. Failures preserve a `.partial` folder when one was created. Never use an incomplete batch as your only copy.

Verify a completed batch offline on any computer with Python 3.9+:

```text
python tools/verify_backup.py "/path/to/timestamped-batch"
```

Keep the original card until you have opened the copied materials. **This toolkit has no erase/format command.** If you later choose to reuse the card, clear it in its original camera after checking your backups.

## Travel preparation

Keep a downloaded source ZIP, these instructions and any official installers you need available offline before leaving. Initial setup may require admin rights, Internet, several GB for WSL/Linux, and a compatible USB adapter. A managed, locked-down or public computer may not permit it. This repository cannot make this old reader plug-and-play on every computer. Do not bypass someone else's computer policy.

## Development

No Python dependencies are needed for the Linux importer, offline verifier or Mac diagnostic. Run `python -m unittest discover -s tests -v`; Linux-specific tests are skipped on non-Linux hosts. These are synthetic tests and do not certify USB hardware. PowerShell scripts should also pass the Windows PowerShell 5.1 parser. See [verification scope](docs/SAFETY.md).

## Sources and licensing

- [Microsoft: connect USB devices to WSL](https://learn.microsoft.com/en-us/windows/wsl/connect-usb)
- [usbipd-win WSL documentation](https://github.com/dorssel/usbipd-win/wiki/WSL-support) and [pinned 5.3.0 release](https://github.com/dorssel/usbipd-win/releases/tag/v5.3.0)
- [Linux kernel USB storage device table](https://github.com/torvalds/linux/blob/master/drivers/usb/storage/unusual_devs.h)
- [UTM USB sharing requirements and limitations](https://docs.getutm.app/guest-support/sharing/usb/)

Project code is MIT-licensed. Third-party software retains its own license and is downloaded from its official distributor. This project is independent of Sony, Microsoft, Apple and UTM.
