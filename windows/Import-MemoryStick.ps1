[CmdletBinding()]
param(
    [string]$OutputRoot = (Join-Path ([Environment]::GetFolderPath('MyPictures')) 'MemoryStick-Backups'),
    [string]$Distro = 'Ubuntu',
    [switch]$CaptureImage,
    [switch]$NoOpen,
    [switch]$NoPause
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$attachedHere = $false
$busId = $null
$exitCode = 1
$mutex = New-Object Threading.Mutex($false, 'Local\SonyMemoryStickRescueImport')
$ownsMutex = $false
$receipt = [ordered]@{status='STARTED'; started_at_utc=(Get-Date).ToUniversalTime().ToString('o'); card_erasure=$false}
$receiptPath = $null

function Convert-ToLinuxPath([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if ($full -notmatch '^([A-Za-z]):\\') { throw 'Use a local Windows drive path. Network/UNC destinations are not supported.' }
    return '/mnt/' + $Matches[1].ToLowerInvariant() + '/' + $full.Substring(3).Replace('\','/')
}
function Convert-ToWindowsPath([string]$Path) {
    if ($Path -notmatch '^/mnt/([a-z])/(.+)$') { throw 'Unexpected Linux backup destination.' }
    return $Matches[1].ToUpperInvariant() + ':\' + $Matches[2].Replace('/','\')
}
function Invoke-Usbipd([string[]]$Arguments) {
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $output = & $script:cli @Arguments 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $old
    if ($code -ne 0) { throw ('usbipd failed: ' + ($output | Out-String).Trim()) }
    return ($output | Out-String).Trim()
}

try {
    $ownsMutex = $mutex.WaitOne(0)
    if (-not $ownsMutex) { throw 'Another import is running. Wait for it to finish.' }
    $cli = Join-Path $env:ProgramFiles 'usbipd-win\usbipd.exe'
    if (-not (Test-Path -LiteralPath $cli)) { throw 'Run windows\Setup-Windows.ps1 first. usbipd-win is missing.' }
    $state = (Invoke-Usbipd -Arguments @('state')) | ConvertFrom-Json
    $sony = @($state.Devices | Where-Object { $_.InstanceId -like 'USB\VID_054C&PID_002D\*' -and $_.BusId })
    if ($sony.Count -ne 1) { throw 'Connect exactly one Sony MSAC-US1 (054c:002d) with its original 32 MB card.' }
    $sony = $sony[0]
    $busId = $sony.BusId
    if (-not $sony.PersistedGuid -or -not $sony.IsForced) { throw 'Reader is not configured for this USB port. Run Setup-Windows.ps1 -ConfigureReader as Administrator.' }
    if ($sony.ClientIPAddress) { throw 'Reader is already attached to another operation. Finish and detach it first.' }
    $linuxOutput = Convert-ToLinuxPath $OutputRoot
    $helper = Convert-ToLinuxPath (Join-Path $repo 'linux\import_card.py')
    $probe = Convert-ToLinuxPath (Join-Path $repo 'linux\inspect_reader.py')
    $null = New-Item -ItemType Directory -Path $OutputRoot -Force
    $stateDir = Join-Path $OutputRoot '.state'
    $null = New-Item -ItemType Directory -Path $stateDir -Force
    $runId = [Guid]::NewGuid().ToString('N')
    $resultPath = Join-Path $stateDir ($runId + '-result.json')
    $receiptPath = Join-Path $stateDir ($runId + '-windows.json')
    $linuxResult = Convert-ToLinuxPath $resultPath
    foreach ($module in @('usb_storage','vhci-hcd')) {
        & wsl.exe -d $Distro -u root -- modprobe $module
        if ($LASTEXITCODE -ne 0) { throw ('WSL kernel module unavailable: ' + $module + '. See docs/windows.md.') }
    }
    $receipt.attach_output = Invoke-Usbipd -Arguments @('attach','--wsl',$Distro,'--busid',$busId)
    $attachedHere = $true
    $ready = $false
    for ($attempt=0; $attempt -lt 20; $attempt++) {
        & wsl.exe -d $Distro -- python3 $probe --ready | Out-Null
        if ($LASTEXITCODE -eq 0) { $ready=$true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'The reader did not expose its card. Reconnect it and retry. Do not format or repair.' }
    $arguments = @('-d',$Distro,'-u','root','--','python3',$helper,'--output-root',$linuxOutput,'--result-json',$linuxResult)
    if ($CaptureImage) { $arguments += '--capture-image' }
    Write-Host 'Copying Memory Stick read-only; verifying every file with SHA-256...'
    & wsl.exe @arguments
    $importCode = $LASTEXITCODE
    if (-not (Test-Path -LiteralPath $resultPath)) { throw 'No result receipt. Keep the original card unchanged.' }
    $result = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
    if ($importCode -ne 0 -or $result.status -ne 'VERIFIED_COPY' -or -not $result.cleanup_complete) {
        throw ('Import incomplete. Keep the card unchanged. ' + $result.error)
    }
    $backup = Convert-ToWindowsPath $result.backup_path_linux
    # Independent Windows-side readback catches cross-filesystem delivery errors.
    foreach ($file in $result.files) {
        $full = [IO.Path]::GetFullPath((Join-Path (Join-Path $backup 'Files') $file.path.Replace('/','\')))
        $prefix = [IO.Path]::GetFullPath((Join-Path $backup 'Files')) + '\'
        if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid manifest path.' }
        if ((Get-Item -LiteralPath $full).Length -ne $file.bytes -or (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256_copy) {
            throw 'Windows readback failed. Keep the card unchanged.'
        }
    }
    $receipt.detach_output = Invoke-Usbipd -Arguments @('detach','--busid',$busId)
    $attachedHere = $false
    $receipt.status = 'VERIFIED_COPY_AND_DETACHED'
    $receipt.backup_path = $backup
    $receipt.files_copied = $result.files_copied
    Write-Host ('Verified ' + $result.files_copied + ' files. Safe to unplug the reader. Folder: ' + $backup) -ForegroundColor Green
    Write-Host 'Open the copied media before considering any later cleanup in the camera.'
    if (-not $NoOpen) { Start-Process explorer.exe -ArgumentList ('"' + (Join-Path $backup 'Files') + '"') | Out-Null }
    $exitCode = 0
} catch {
    $receipt.status = 'FAILED_OR_INCOMPLETE'
    $receipt.error = $_.Exception.Message
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($attachedHere -and $busId) {
        & wsl.exe -d $Distro -- python3 $probe --safe-detach | Out-Null
        if ($LASTEXITCODE -eq 0) {
            try { $receipt.detach_output = Invoke-Usbipd -Arguments @('detach','--busid',$busId); $attachedHere=$false } catch { $receipt.detach_error=$_.Exception.Message }
        }
        if ($attachedHere) { Write-Host 'Cleanup not confirmed: leave the reader connected for inspection.' -ForegroundColor Yellow }
    }
} finally {
    if ($receiptPath) {
        $receipt.finished_at_utc=(Get-Date).ToUniversalTime().ToString('o')
        $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding utf8
    }
    if ($ownsMutex) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
    if ($exitCode -ne 0 -and -not $NoPause) { $null = Read-Host 'Press Enter to close' }
}
exit $exitCode
