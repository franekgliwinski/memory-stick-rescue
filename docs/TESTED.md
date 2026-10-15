# Validation record — 2026-10-15

This is a sanitized record, not a claim that every computer is supported.

| Check | Result |
| --- | --- |
| Original machine-specific Windows10 x64 + WSL2 setup, real MSAC-US1/original32MB FAT12 card | Verified14 files/572391 bytes, including independent native Windows hash readback and a user-confirmed physical reconnect. |
| Public portable version: Python tests on Linux/WSL | 26/26 passed; temporary synthetic files and mocked USB discovery. No card or mount used. |
| Public portable version: Python tests on Windows | 15 passed;11 platform-dependent tests skipped. |
| Public offline verifier against the existing real14-file backup | VERIFIED;14 files/572391 bytes. This reads the saved copy, not the current card. |
| Public Windows scripts, Windows PowerShell5.1 parser | Both scripts parsed with zero errors. |
| Public Windows importer without a connected reader | Correctly refused before creating a destination or attaching anything. |
| Public Windows setup without mutation switches | Existing WSL/Python/modules/usbipd prerequisites inspected. |
| Public portable installer/binding on a fresh computer | Not tested. Existing working PC setup deliberately retained. |
| Public macOS card importer | Not certified in this initial release. USB visibility is confirmed; see macos.md. |

Regression coverage includes wrong IDs/capacities, duplicate readers, mounted-device aliases, refusal to overwrite an existing destination, mismatched copy sizes, bad destination hashes, corrupted/truncated/missing files, incomplete imports, failed cleanup, manifest count/total mismatches, duplicate paths, traversal, extra files, symlinks, optional raw-image integrity and empty cards.

No private card image, personal media or raw local logs are included. Device tests for alternate capacities, reboot recovery, different ports and macOS remain distinct work.
