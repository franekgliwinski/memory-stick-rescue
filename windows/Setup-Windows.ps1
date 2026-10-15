[CmdletBinding(SupportsShouldProcess=$true)]
param([switch]$InstallUsbipd, [switch]$ConfigureReader, [string]$Distro='Ubuntu')
$ErrorActionPreference='Stop'
$cli = Join-Path $env:ProgramFiles 'usbipd-win\usbipd.exe'
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (($InstallUsbipd -or $ConfigureReader) -and -not $admin) { throw 'Open PowerShell as Administrator for explicit setup changes.' }
if ($env:PROCESSOR_ARCHITECTURE -ne 'AMD64') { throw 'This installer is pinned to Windows x64. Other architectures are not validated.' }

& wsl.exe -d $Distro -- uname -r
if ($LASTEXITCODE -ne 0) { throw 'Install and initialize an Ubuntu WSL2 distro first. See docs/windows.md. This script will not reboot or replace WSL.' }
& wsl.exe -d $Distro -- python3 --version
if ($LASTEXITCODE -ne 0) { throw 'Python 3.9+ is required in the selected Linux distro.' }
foreach ($module in @('usb_storage','vhci-hcd')) {
    & wsl.exe -d $Distro -- modinfo $module | Out-Null
    if ($LASTEXITCODE -ne 0) { throw ('Required WSL kernel module unavailable: ' + $module + '. No automatic WSL shutdown/update will be performed.') }
}
$aliases=(& wsl.exe -d $Distro -- modinfo -F alias usb_storage | Out-String)
if ($LASTEXITCODE -ne 0 -or $aliases -notmatch 'usb:v054Cp002D') { throw 'The selected WSL kernel does not report the exact Sony 054c:002d storage alias. Do not guess a driver.' }

if ($InstallUsbipd -and -not (Test-Path -LiteralPath $cli)) {
    $interfaces = @(Get-NetAdapter -IncludeHidden | Where-Object { $_.Name -like 'vEthernet (WSL*' })
    if ($interfaces.Count -ne 1) { throw 'Expected exactly one WSL virtual adapter. Resolve networking before installation; no broad firewall fallback.' }
    if ($PSCmdlet.ShouldProcess('usbipd-win 5.3.0 x64 service and signed drivers', 'Install official pinned MSI without restart')) {
        $temp = Join-Path ([IO.Path]::GetTempPath()) ('memory-stick-rescue-' + [Guid]::NewGuid().ToString('N'))
        $null=New-Item -ItemType Directory -Path $temp
        $msi=Join-Path $temp 'usbipd-win_5.3.0_x64.msi'
        Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/dorssel/usbipd-win/releases/download/v5.3.0/usbipd-win_5.3.0_x64.msi' -OutFile $msi
        $hash=(Get-FileHash -LiteralPath $msi -Algorithm SHA256).Hash
        $sig=Get-AuthenticodeSignature -LiteralPath $msi
        if ($hash -ne '1C984914AEC944DE19B64EFF232421439629699F8138E3DDC29301175BC6D938' -or [string]$sig.Status -ne 'Valid') { throw 'Installer SHA-256 or Authenticode signature is invalid. No installer executed.' }
        $process=Start-Process msiexec.exe -ArgumentList ('/i "'+$msi+'" /passive /norestart /L*v "'+(Join-Path $temp 'install.log')+'"') -Wait -PassThru -WindowStyle Hidden
        # The MSI creates a service-wide rule. Restrict it immediately to the WSL virtual network.
        $rule=Get-NetFirewallRule -Name usbipd -ErrorAction Stop
        $rule | Set-NetFirewallRule -InterfaceAlias $interfaces[0].Name -RemoteAddress LocalSubnet | Out-Null
        if ($process.ExitCode -eq 3010 -or $process.ExitCode -eq 1641) { throw 'Installer reports a restart requirement. No restart performed; stop and review before continuing.' }
        if ($process.ExitCode -ne 0) { throw ('Installer failed, code '+$process.ExitCode+'. Log: '+$temp) }
    }
}
if (-not (Test-Path -LiteralPath $cli)) { throw 'usbipd-win missing. Re-run with -InstallUsbipd to explicitly authorize installation, or see docs/windows.md.' }
& $cli --version
if ($ConfigureReader) {
    $interfaces=@(Get-NetAdapter -IncludeHidden | Where-Object { $_.Name -like 'vEthernet (WSL*' })
    if ($interfaces.Count -ne 1) { throw 'Expected one WSL virtual network adapter; no broad firewall fallback.' }
    $state=(& $cli state | Out-String) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot query USB state.' }
    $sony=@($state.Devices | Where-Object { $_.InstanceId -like 'USB\VID_054C&PID_002D\*' -and $_.BusId })
    if ($sony.Count -ne 1) { throw 'Connect exactly one Sony MSAC-US1 054c:002d before configuring. No device bound.' }
    if ($sony[0].ClientIPAddress) { throw 'Reader is in use. Detach safely before configuring.' }
    $rule=Get-NetFirewallRule -Name usbipd -ErrorAction Stop
    $filter=$rule | Get-NetFirewallApplicationFilter
    if ($filter.Program -ne $cli) { throw 'Unexpected usbipd firewall program. Inspect the existing installation.' }
    if ($PSCmdlet.ShouldProcess('usbipd firewall and Sony 054c:002d at '+$sony[0].BusId, 'Restrict USB/IP to WSL virtual network; bind signed proxy driver to Sony only')) {
        # Save bounded pre-state in the current user's LocalAppData, outside the source repository.
        $stateDir=Join-Path $env:LOCALAPPDATA 'MemoryStickRescue'
        $null=New-Item -ItemType Directory -Path $stateDir -Force
        $pre=[ordered]@{timestamp_utc=(Get-Date).ToUniversalTime().ToString('o');busid=$sony[0].BusId;was_forced=$sony[0].IsForced;persisted_guid=$sony[0].PersistedGuid;firewall_interfaces=@(($rule|Get-NetFirewallInterfaceFilter).InterfaceAlias);firewall_remote=@(($rule|Get-NetFirewallAddressFilter).RemoteAddress)}
        $receipt=Join-Path $stateDir ('setup-'+[Guid]::NewGuid().ToString('N')+'.json')
        $pre | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receipt -Encoding utf8
        $rule | Set-NetFirewallRule -InterfaceAlias $interfaces[0].Name -RemoteAddress LocalSubnet | Out-Null
        $fresh=Get-NetFirewallRule -Name usbipd
        if (@(($fresh|Get-NetFirewallInterfaceFilter).InterfaceAlias).Count -ne 1 -or ($fresh|Get-NetFirewallInterfaceFilter).InterfaceAlias -ne $interfaces[0].Name -or ($fresh|Get-NetFirewallAddressFilter).RemoteAddress -ne 'LocalSubnet') { throw 'Firewall containment readback failed; reader was not bound.' }
        & $cli bind --busid $sony[0].BusId --force
        if ($LASTEXITCODE -ne 0) { throw 'Sony-only proxy binding failed. Reconnect, inspect and retry.' }
        $after=(& $cli state | Out-String) | ConvertFrom-Json
        $matched=@($after.Devices | Where-Object { $_.InstanceId -eq $sony[0].InstanceId -and $_.IsForced -and $_.PersistedGuid })
        if ($matched.Count -ne 1) { throw 'Proxy binding readback failed.' }
        Write-Host ('Configured this Sony USB port. Pre-state receipt: '+$receipt)
    }
}
if (-not $ConfigureReader) { Write-Host 'Prerequisites inspected. Use -ConfigureReader for explicit Sony-only binding; see docs/windows.md.' }
Write-Host 'Daily use: double-click windows\Import Memory Stick.cmd. Keep the original card unchanged until files are checked.'
