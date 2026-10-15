# Safety, evidence and limitations

## Data preservation

- No card write, erase, format, repair or partition command is provided. Use the physical card LOCK switch when possible, especially before connecting to an OS that might automount it. The importer cannot undo anything the OS did before it started.
- Exact USB identification, current mount checks and read-only block protection are required before mounting. Ambiguity fails closed. The importer reads the mounted filesystem and optionally a raw image; it does not recover deleted files.
- A `.partial` batch is not a completed backup. Do not remove the original because some files appeared in a folder. A successful copy and successful USB cleanup are separate checks.
- SHA-256 verifies copy integrity against the bytes read. It does not authenticate a modified manifest or prove that the camera originally recorded valid media. Open the copied files too.
- Nothing is uploaded by the importer. Public source excludes images, card dumps, runtime receipts, personal host paths and credentials. `.gitignore` helps prevent mistakes but is not a substitute for checking staged files.

## Changes on Windows

Only explicit setup switches authorize installer/firewall/binding mutations. Setup can install usbipd-win5.3.0, its service and signed drivers. The Sony proxy binding is persistent and may be specific to a USB port. The service's firewall rule is narrowed to the WSL adapter and LocalSubnet; this can affect other usbipd users. The importer starts/uses the selected existing WSL distro; it does not reboot, shut down WSL, install a scheduler or change global PowerShell policy. Rollback is documented in windows.md.

## What has been tested

The original machine-specific Windows workflow read a real Sony MSAC-US1/original32MB FAT12 card, copied and independently verified14 files, preserved a raw image and passed physical unplug/replug plus desktop-launch use. Private file names, image hashes and raw run logs are deliberately omitted from public source.

This **portable adaptation** changes paths, receipts, checks and setup packaging. Its regression suite uses only synthetic temporary files: correct copying, wrong sizes, interrupted/corrupt destinations, incomplete manifests, traversal, duplicate paths and other safety cases. The Linux tests do not mount a disk or require the Sony. PowerShell syntax can be checked without executing setup. A negative no-reader run checks a refusal path only. These checks do not prove a fresh-machine installation, every USB port, reboot recovery, a macOS importer, other capacities or all OS versions.

No guarantee is made that this legacy hardware works on any arbitrary computer. Initial setup needs compatible hardware/software and the computer owner's permission. A public source ZIP is a preparation aid, not a driver compatibility guarantee.

## Report a problem

Use a GitHub issue if desired. Include OS/architecture, tool versions, exact USB ID and a short sanitized error. **Do not upload card images, photos, original manifests, private paths, tokens or complete system logs.** No program submits an issue or diagnostic automatically.
