# Windows setup and rollback

## Requirements

- Windows x64; original workflow verified on Windows 10 Pro build 19045. Windows 11 support in this toolkit has not received a hardware test.
- Windows PowerShell 5.1; a local extracted source folder and local destination drive with free space.
- An initialized **Ubuntu WSL2**, Python 3.9+, util-linux and kernel `usb_storage` / `vhci-hcd` support. Original workflow used WSL kernel `6.18.54.1-microsoft-standard-WSL2`. Kernel modules must include the Sony alias. A version number alone is not proof of that alias.
- A visible WSL virtual network adapter. Mirrored/other networking without that adapter is deliberately rejected rather than opening a broad firewall rule.
- Exactly one Sony MSAC-US1 `054c:002d`, with an original 32 MB FAT card. On a different port, configure that port again.
- Owner-authorized Administrator access for installation, firewall narrowing and Sony-only proxy binding. Ordinary recurring imports do not require an elevated Windows shell.

Use Microsoft's [WSL installation instructions](https://learn.microsoft.com/en-us/windows/wsl/install) if necessary. **WSL installation may require a reboot and several GB**; this toolkit does not initiate it automatically. On a machine with active WSL work, arrange any update/shutdown separately. Inspect with `wsl --list --verbose` and `wsl -d Ubuntu -- uname -r`.

## Setup

From the extracted repository, run the commands in README.md. Setup without switches is a prerequisite inspection. Explicit `-InstallUsbipd` downloads version5.3.0 x64 only if absent; SHA-256 must equal:

```text
1C984914AEC944DE19B64EFF232421439629699F8138E3DDC29301175BC6D938
```

Authenticode must also be valid. Do not substitute an unknown binary. The process uses `/norestart`; if MSI reports that a restart is needed, setup stops and reports it.

`-ConfigureReader` records bounded firewall/binding pre-state under `%LOCALAPPDATA%\MemoryStickRescue`, restricts the existing usbipd program rule to the WSL virtual interface and `LocalSubnet`, reads that restriction back, then uses `usbipd bind --busid <discovered Sony bus> --force`. The forced binding installs the signed USB proxy for this device; it does not disable Windows driver signature enforcement. No other USB device is bound by this toolkit. The firewall rule is service-wide; narrowing an existing shared installation affects its other users.

If attachment fails, unplug the reader, wait about ten seconds and reconnect to the same configured port. Do not repeatedly reset a card with a running import. Do not accept a Windows format prompt.

## Daily import

Use `windows/Import Memory Stick.cmd`. The helper refuses a reader already attached elsewhere and does not steal another operation. Use `-Distro` if your initialized compatible distro has a different name. Use `-OutputRoot` for another local drive. Network/UNC paths and custom WSL automount roots are not supported. Windows-side copies are independently hashed after Linux unmount and before USB/IP detach.

Receipts are in `<OutputRoot>/.state/`. They may contain local paths and filenames: keep them private. A failed run can retain a `.partial` folder. `-NoPause -NoOpen` supports unattended *invocation*, but this project does not install an unattended service, scheduler or auto-import hook.

## Rollback

Finish the import and confirm unmount first. Detach **only the discovered Sony bus** with `usbipd detach --busid <Sony bus>` if still attached. Then, as Administrator, run `usbipd unbind --busid <Sony bus>` to remove the persistent Sony proxy binding. Verify with `usbipd state`/Device Manager. Do not unbind all USB devices.

If usbipd-win was installed solely for this toolkit and has no other users, uninstall it from Windows Installed apps; verify its service/firewall rule removal. If usbipd already existed, retain it and review the saved firewall pre-state before restoring a wider rule. Do not automatically widen the firewall. Keep backups. No global PowerShell execution-policy setting is changed: `-ExecutionPolicy Bypass` applies only to that launched process.
