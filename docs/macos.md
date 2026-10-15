# macOS — initial diagnostic and experimental route

Status dated **2026-10-15**: the Sony `054c:002d` is visible as `MSAC-US1` on an Apple Silicon Mac running macOS26.2, but no card disk is exposed by the native OS. **No working Mac importer is certified in this source release.** Windows drivers cannot be installed as macOS drivers.

A separate native-userspace investigation with PyUSB1.3.1/libusb-package1.0.30.0 failed to claim the USB interface even after one controlled, owner-approved temporary capture. The native driver was reattached; zero card commands were sent and zero files were copied. This is a failed access test, not a recovery. Do not repeat elevated capture or expand permissions based on the original one-shot approval. A Linux/UTM experiment would be a separate test and is not currently proven.

## Safe first check

With Python3 available:

```sh
python3 macos/diagnose.py
```

This prints only the matching USB count, OS/architecture, available space and external disk identifiers/sizes. It does not claim USB, read sectors, mount a disk, install software or change security. The external disk list is contextual; it does not assert that any listed disk is the Sony. Keep diagnostic output private if it reveals your configuration.

The published diagnostic was successfully run with `/usr/bin/python3` on the test Mac: one matching reader, no external physical disk. A separate Homebrew Python installation on that machine had an unrelated Expat loading error. If your `python3` reports that error, try `/usr/bin/python3 macos/diagnose.py` if available or use a healthy Python3 installation; do not replace system libraries to run this tool.

## Candidate Linux route, not a tested recipe

[UTM's USB documentation](https://docs.getutm.app/guest-support/sharing/usb/) describes USB sharing with its QEMU backend and warns that some devices fail because macOS capture cannot fully reset them. A Linux guest booting successfully does not establish that the Sony USB device was captured successfully.

For macOS26.2, a candidate is an appropriate ARM64 Linux guest on Apple Silicon using UTM's **QEMU** backend, USB sharing enabled, with exactly this reader attached through the USB menu. Intel Macs need a matching supported guest architecture. Check the current UTM/OS documentation before selecting a backend; do not assume Apple Virtualization has the same USB capability on every OS release.

This repository does **not** install UTM, download a multi-GB guest or alter system extensions. Check available space first. If an owner-authorized guest already works, copy the source into it, confirm `054c:002d` with `linux/inspect_reader.py`, then follow [linux.md](linux.md). Share only a dedicated output folder with the guest and independently verify the resulting host backup.

Do not install legacy kernel extensions or disable SIP/Gatekeeper/driver protections to make this old reader appear as a disk. Do not declare success based on USB enumeration, a VM download or synthetic tests. A valid Mac result requires a real exact-device card read, verified delivered files and safe cleanup.
