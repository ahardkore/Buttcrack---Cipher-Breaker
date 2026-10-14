<#
.SYNOPSIS
    Install the built installer, prove the product works, uninstall it, and
    prove it went away cleanly.

.DESCRIPTION
    build.ps1 proves the *executables* work.  This proves the *installer* does:
    that the wizard's silent path completes, that the shortcuts, the PATH entry
    and the file tree land where the script says they do, that the installed
    program still breaks ciphers once it is running out of %LOCALAPPDATA% rather
    than out of a checkout, and that an uninstall leaves nothing behind.

    That last part is the one people skip.  A wizard is easy to get right on the
    way in and easy to get wrong on the way out -- a stale directory left on
    PATH slows down every command the user types for the rest of the machine's
    life, and nobody reports it as a bug.

    It is deliberately runnable on a developer's own machine:

        .\test-installer.ps1 -Installer ..\..\dist\installer\buttcrack-setup-1.2.0.exe

    Two things it touches outside a temp directory, both on purpose and both
    undone by the uninstall step it also tests: the per-user PATH value
    (HKCU\Environment) and the Start-menu and desktop shortcuts.  Pass
    -NoPathTask to leave PATH alone.

.PARAMETER Installer
    Path to buttcrack-setup-<version>.exe, as produced by build.ps1.

.PARAMETER SkipSelftest
    Skip the 142-puzzle self-test of the installed build.  It is the strongest
    single check here -- it is the difference between "the exe starts" and "the
    shipped product solves puzzles" -- but it takes a couple of minutes.

.PARAMETER NoPathTask
    Do not select the "add the command line to my PATH" task.  The check that it
    is added and removed is skipped; everything else still runs.

.PARAMETER KeepInstalled
    Leave the product installed at the end, for poking at by hand.  The
    uninstall checks are skipped, and the install directory is printed.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\windows\test-installer.ps1 `
        -Installer dist\installer\buttcrack-setup-1.2.0.exe
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Installer,
    [switch]$SkipSelftest,
    [switch]$NoPathTask,
    [switch]$KeepInstalled
)

$ErrorActionPreference = 'Stop'

$Script:Log = $null
$Script:InstallDir = $null
$Script:Progress = New-Object System.Collections.Generic.List[string]

function Write-Step { param([string]$Text) Write-Host "`n==> $Text" -ForegroundColor Cyan; Record-Progress "STEP $Text" }
function Write-Note { param([string]$Text) Write-Host "    $Text" -ForegroundColor DarkGray }
function Write-Pass { param([string]$Text) Write-Host "    OK   $Text" -ForegroundColor Green; Record-Progress "ok   $Text" }

function Record-Progress {
    param([string]$Text)
    $Script:Progress.Add($Text)
    if ($Script:Progress.Count -gt 40) { $Script:Progress.RemoveAt(0) }
}

function Show-Diagnosis {
    <#
        Write a compact account of how far the run got to a file in %TEMP%, and
        print it.

        The CI job turns this file into a check-run annotation, because the job
        log archive lives on a host that is not always reachable from a sandbox
        or a phone.  It is just as useful on a developer's own machine, where it
        saves scrolling back through a quarter of an hour of installer output.
    #>
    param([string]$Text)
    $report = @("FAILED: $Text", '--- where it got to ---') + $Script:Progress
    if ($Script:InstallDir) { $report += "install dir: $Script:InstallDir" }
    if ($Script:Log -and (Test-Path -LiteralPath $Script:Log)) {
        $report += '--- last lines of the installer''s own log ---'
        $report += @(Get-Content -LiteralPath $Script:Log -Tail 25 -ErrorAction SilentlyContinue)
    }
    Write-Host ($report -join "`n") -ForegroundColor Yellow
    try {
        Set-Content -Path (Join-Path $env:TEMP 'buttcrack-installer-failure.txt') `
            -Value ($report -join "`n") -Encoding utf8
    }
    catch {
        Write-Host "   (could not write the failure summary: $_)" -ForegroundColor DarkGray
    }
}

function Fail {
    param([string]$Text)
    # Failing early and loudly beats listing every downstream symptom: the first
    # failure in an installer test is almost always the cause of the rest.
    Write-Host "`nX  $Text`n" -ForegroundColor Red
    Show-Diagnosis $Text
    if ($Script:InstallDir -and (Test-Path -LiteralPath (Join-Path $Script:InstallDir 'unins000.exe'))) {
        Write-Host "   The product is still installed at $Script:InstallDir" -ForegroundColor Yellow
        Write-Host "   Remove it with: & '$Script:InstallDir\unins000.exe' /VERYSILENT" -ForegroundColor Yellow
        Write-Host ''
    }
    exit 1
}

function Assert-True {
    param([bool]$Condition, [string]$Text, [string]$Detail = '')
    if ($Condition) { Write-Pass $Text; return }
    Fail ($(if ($Detail) { "$Text -- $Detail" } else { $Text }))
}

function Convert-ToLongPath {
    <#
        Expand an 8.3 short path to its long form.

        %TEMP% on Windows is usually C:\Users\RUNNER~1\AppData\Local\Temp while
        the installer records the long name it resolved the directory to
        (C:\Users\runneradmin\...).  Those are the same folder spelled two ways,
        so comparing them as strings calls a perfectly good install a failure --
        which is what this script did the first time it ran on a real runner.
        Normalising once, here, keeps every later comparison honest.

        Path.GetFullPath does not do this; only Win32 expands short names.
    #>
    param([string]$Path)
    if (-not ('Win32PathHelper' -as [type])) {
        Add-Type -Namespace Win32 -Name PathHelper -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("kernel32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
public static extern uint GetLongPathName(string shortPath, System.Text.StringBuilder longPath, uint size);
'@
    }
    $buffer = New-Object System.Text.StringBuilder 1024
    $length = [Win32.PathHelper]::GetLongPathName($Path, $buffer, 1024)
    if ($length -gt 0 -and $length -le 1024) { return $buffer.ToString() }
    return $Path
}

function Get-InstalledLocation {
    <#
        Where the product says it installed itself.

        Inno Setup records this under the AppId from buttcrack.iss, so it is the
        authoritative answer and a far better diagnostic than "the directory I
        asked for does not exist" -- the two disagreeing means /DIR was ignored.
    #>
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{4D7F05D7-7C77-50B8-B538-219DED0C01B5}_is1'
    $entry = Get-ItemProperty -Path $key -ErrorAction SilentlyContinue
    if ($entry -and $entry.InstallLocation) { return $entry.InstallLocation }
    return $null
}

function Get-UserPath {
    $value = (Get-ItemProperty -Path 'HKCU:\Environment' -Name 'Path' -ErrorAction SilentlyContinue).Path
    if ($null -eq $value) { return '' }
    return [string]$value
}

function Test-PathEntry {
    <#
        Whether $Directory is one of the entries on the user's PATH.

        Parsed entry by entry and compared in long form rather than as a
        substring.  Two reasons: the installer writes the folder the way /DIR
        spelled it, which under %TEMP% is the 8.3 short name, while this script
        may be holding the long one; and "C:\Foo" must not match inside
        "C:\FooBar", which a plain substring search would allow.
    #>
    param([string]$Directory)
    $wanted = (Convert-ToLongPath $Directory).TrimEnd('\')
    foreach ($entry in ((Get-UserPath) -split ';')) {
        $candidate = $entry.Trim().TrimEnd('\')
        if (-not $candidate) { continue }
        if ((Convert-ToLongPath $candidate) -ieq $wanted) { return $true }
    }
    return $false
}

function Invoke-InstalledCli {
    <#
        Run an installed executable and return @{ Output; Error; ExitCode }.

        Arguments are quoted here rather than at each call site: Start-Process
        flattens the array into one command line, so an argument containing
        spaces -- and the Caesar sample this script exists to crack is ten words
        long -- would otherwise arrive as ten separate arguments.

        stdout and stderr go to files rather than through a pipeline because
        buttcrack emits a very large JSON document for some commands, and
        redirection through PowerShell has been known to mangle it.
    #>
    param([string]$Exe, [string[]]$Arguments)
    $quoted = @($Arguments | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
    $out = Join-Path $Script:WorkDir 'cli-out.txt'
    $err = Join-Path $Script:WorkDir 'cli-err.txt'
    $process = Start-Process -FilePath $Exe -ArgumentList $quoted -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $out -RedirectStandardError $err
    return @{
        Output   = (Get-Content -Raw -Path $out -ErrorAction SilentlyContinue)
        Error    = (Get-Content -Raw -Path $err -ErrorAction SilentlyContinue)
        ExitCode = $process.ExitCode
    }
}

# --------------------------------------------------------------------------- #
# 0. the installer is there, and is the one that was published
# --------------------------------------------------------------------------- #

if (-not (Test-Path -LiteralPath $Installer)) {
    Fail "No installer at $Installer. Build it first: packaging\windows\build.ps1"
}
$Installer = (Resolve-Path -LiteralPath $Installer).Path
Write-Pass "installer found"

Write-Step 'Inspecting the installer'
$setupInfo = Get-Item -LiteralPath $Installer
Write-Note "$($setupInfo.Name)  ($([math]::Round($setupInfo.Length / 1MB, 1)) MB)"

$sidecar = "$Installer.sha256"
if (Test-Path -LiteralPath $sidecar) {
    $expected = ((Get-Content -Raw -Path $sidecar) -split '\s+')[0].Trim().ToLowerInvariant()
    $actual = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
    Assert-True ($expected -eq $actual) 'the SHA-256 sidecar matches the file it ships with'
}
else {
    Write-Note "no .sha256 beside the installer; skipping the checksum check"
}

# The version is in the filename because that is how it is published, so take it
# from there rather than inventing a second place for it to disagree.
if ($setupInfo.Name -match '^buttcrack-setup-(?<version>.+)\.exe$') {
    $Version = $Matches['version']
    Write-Note "version $Version (from the filename)"
}
else {
    Fail "The installer is not named buttcrack-setup-<version>.exe: $($setupInfo.Name)"
}

# --------------------------------------------------------------------------- #
# 1. install
# --------------------------------------------------------------------------- #

$Script:WorkDir = Join-Path $env:TEMP ("buttcrack-install-test-" + [guid]::NewGuid().ToString('N'))
$InstallDir = Join-Path $Script:WorkDir 'app'
$Script:InstallDir = $InstallDir
New-Item -ItemType Directory -Force -Path $Script:WorkDir | Out-Null
$Script:Log = Join-Path $Script:WorkDir 'install.log'

Write-Step 'Running the installer silently'
Write-Note "/DIR=$InstallDir"

$tasks = if ($NoPathTask) { 'desktopicon' } else { 'desktopicon,addtopath' }
$arguments = @(
    '/VERYSILENT',
    '/SUPPRESSMSGBOXES',
    '/NORESTART',
    '/NOCANCEL',
    "/DIR=`"$InstallDir`"",
    "/TASKS=`"$tasks`"",
    "/LOG=`"$($Script:Log)`""
) -join ' '

try {
    $setup = Start-Process -FilePath $Installer -ArgumentList $arguments -Wait -PassThru
}
catch {
    Fail "The installer did not run: $_"
}

Assert-True ($setup.ExitCode -eq 0) 'the installer exited 0' "exit code $($setup.ExitCode)"

if (-not (Test-Path -LiteralPath $InstallDir)) {
    $registered = Get-InstalledLocation
    if ($registered) {
        Fail ("The installer ignored /DIR. It registered itself as installed to " +
              "'$registered' rather than '$InstallDir'.")
    }
    Fail ("The install directory was not created and the installer registered " +
          "nothing, so it did not complete: $InstallDir")
}
Write-Pass 'the install directory exists'

# From here on, compare like with like: the installer writes the long form of
# every path it records, and %TEMP% is usually the 8.3 spelling of the same
# place.  See Convert-ToLongPath.
$InstallDir = Convert-ToLongPath $InstallDir
$Script:InstallDir = $InstallDir

# Now that both spellings are long, the two can be compared, which checks that
# the installer honoured /DIR rather than quietly using its default location.
$registered = Get-InstalledLocation
Assert-True ($registered -and (Convert-ToLongPath $registered.TrimEnd('\')) -ieq $InstallDir.TrimEnd('\')) `
    'the installer used the directory it was asked for' "registered '$registered'"

# --------------------------------------------------------------------------- #
# 2. what landed on disk
# --------------------------------------------------------------------------- #

Write-Step 'Checking the installed file tree'

# Every one of these is something a user would notice the absence of: the two
# entry points, the language model (nothing solves without it), the web UI the
# shortcut opens, the prompt helper, and the uninstaller.
$missing = @()
$required = @(
    'Buttcrack Desktop.exe',
    'buttcrack.exe',
    'buttcrack-prompt.cmd',
    'unins000.exe',
    '_internal\buttcrack\data\english_quadgrams.txt.gz',
    '_internal\buttcrack\data\english_words.json.gz',
    '_internal\buttcrack\static\index.html',
    '_internal\buttcrack\static\app.js',
    '_internal\buttcrack\static\style.css'
)
foreach ($relative in $required) {
    if (Test-Path -LiteralPath (Join-Path $InstallDir $relative)) {
        Write-Pass "installed $relative"
    }
    else {
        $missing += $relative
    }
}
if ($missing) {
    # "Expected X, found Y" is answerable; "X is missing" is not.
    Write-Host '    the install directory actually contains:' -ForegroundColor DarkGray
    Get-ChildItem -LiteralPath $InstallDir -Recurse -Depth 2 -ErrorAction SilentlyContinue |
        Select-Object -First 40 |
        ForEach-Object { Write-Host "      $($_.FullName.Substring($InstallDir.Length))" -ForegroundColor DarkGray }
    Fail "missing from the install: $($missing -join ', ')"
}

$installedBytes = (Get-ChildItem $InstallDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
Write-Note "$([math]::Round($installedBytes / 1MB, 1)) MB installed"

# Two names is not the same as two programs, and this is the check that caught
# it: the first Windows build named them Buttcrack.exe and buttcrack.exe, which
# on a case-insensitive filesystem is one file, so PyInstaller kept whichever it
# wrote last and the Start-menu shortcut launched the command line.  Comparing
# the contents is the property that actually matters.
$guiHash = (Get-FileHash -LiteralPath (Join-Path $InstallDir 'Buttcrack Desktop.exe') -Algorithm SHA256).Hash
$cliHash = (Get-FileHash -LiteralPath (Join-Path $InstallDir 'buttcrack.exe') -Algorithm SHA256).Hash
Assert-True ($guiHash -ne $cliHash) `
    'the windowed and console programs are different binaries, not one file under two names'

# --------------------------------------------------------------------------- #
# 3. shortcuts and the PATH entry
# --------------------------------------------------------------------------- #

Write-Step 'Checking shortcuts and the PATH entry'

$programs = [Environment]::GetFolderPath('Programs')
$groupDir = Join-Path $programs 'Buttcrack'
Assert-True (Test-Path -LiteralPath $groupDir) 'the Start-menu group was created'

# 'Buttcrack' plus 'Buttcrack command line' plus 'Uninstall Buttcrack'.
$groupLinks = @(Get-ChildItem -LiteralPath $groupDir -Filter '*.lnk' -ErrorAction SilentlyContinue)
Assert-True ($groupLinks.Count -ge 3) 'the Start-menu group has its shortcuts' "found $($groupLinks.Count)"

# A shortcut that exists but points at nothing is a classic installer defect and
# is invisible to a test that only counts files.
$shell = New-Object -ComObject WScript.Shell
$launcher = Join-Path $groupDir 'Buttcrack.lnk'
Assert-True (Test-Path -LiteralPath $launcher) 'the Start-menu launcher exists'
$shortcut = $shell.CreateShortcut($launcher)
$target = $shortcut.TargetPath
Assert-True ((Convert-ToLongPath $target) -ieq (Join-Path $InstallDir 'Buttcrack Desktop.exe')) `
    'the launcher points at the installed executable' "points at '$target'"
Assert-True (Test-Path -LiteralPath $target) 'the launcher target exists on disk' $target
$workingDir = $shortcut.WorkingDirectory
Assert-True ((Convert-ToLongPath $workingDir).TrimEnd('\') -ieq $InstallDir.TrimEnd('\')) `
    'the launcher sets a working directory inside the install' "'$workingDir'"

# Two places, because OneDrive redirects the desktop on some machines and the
# shell's answer and the plain path can disagree.  Guarded against an empty
# result: Join-Path throws rather than returning nothing.
$desktopFolders = @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:USERPROFILE 'Desktop')) |
    Where-Object { $_ } | Select-Object -Unique
$desktopCandidates = @($desktopFolders | ForEach-Object { Join-Path $_ 'Buttcrack.lnk' })
Assert-True (@($desktopCandidates | Where-Object { Test-Path -LiteralPath $_ }).Count -ge 1) `
    'the desktop shortcut was created'

if ($NoPathTask) {
    Write-Note '-NoPathTask given; skipping the PATH checks'
    Assert-True (-not (Test-PathEntry $InstallDir)) 'PATH was left alone, as asked'
}
else {
    Assert-True (Test-PathEntry $InstallDir) 'the install directory was appended to the user PATH'
}

# --------------------------------------------------------------------------- #
# 4. does the installed product actually work?
# --------------------------------------------------------------------------- #

Write-Step 'Breaking a cipher with the installed CLI'

$sample = 'Wkh txlfn eurzq ira mxpsv ryhu wkh odcb grj.'
$run = Invoke-InstalledCli -Exe (Join-Path $InstallDir 'buttcrack.exe') -Arguments @($sample, '--json')
Assert-True ($run.ExitCode -eq 0) 'buttcrack.exe ran' "exit $($run.ExitCode): $($run.Error)"

try {
    $report = $run.Output | ConvertFrom-Json
}
catch {
    Fail "The installed CLI did not produce JSON: $_"
}

Assert-True ($report.solved) 'it solved the sample'
Assert-True ($report.best.cipher -eq 'caesar') 'it identified the cipher as Caesar' "got '$($report.best.cipher)'"
Assert-True ($report.best.notes.formatted -eq 'The quick brown fox jumps over the lazy dog.') `
    'the plaintext is exactly right' "got '$($report.best.notes.formatted)'"

# The language model is the thing most likely to be left behind by a bad build,
# and it is invisible until the solver is asked to score something.
Assert-True ($report.stats.quadgram_fitness -lt 0) 'the bundled language model scored the result'
Write-Note "confidence $($report.confidence); $($report.attacks.Count) attack(s) tried in $($report.elapsed)s"

Write-Step 'Checking AES in the installed CLI'
$aesInput = Join-Path $Script:WorkDir 'aes-smoke.json'
'{"operation":"decrypt","mode":"ECB","key":"00000000000000000000000000000000","data":"66e94bd4ef8a2c3b884cfa59ca342b2e"}' | Set-Content -Encoding ASCII $aesInput
$aesRun = Invoke-InstalledCli -Exe (Join-Path $InstallDir 'buttcrack.exe') -Arguments @('modern', 'aes', '--input', $aesInput)
Assert-True ($aesRun.ExitCode -eq 0) 'installed AES provider ran' $aesRun.Error
$aesReport = $aesRun.Output | ConvertFrom-Json
Assert-True ($aesReport.output.hex -eq '00000000000000000000000000000000') 'AES known-answer output matches'

Write-Step 'Booting the windowed executable'
# The desktop program is a different binary from buttcrack.exe and fails
# it has no console, so anything printing to a stream PyInstaller left as None
# raises AttributeError, and Tk has to be inside the bundle or there is no window
# at all.  --help walks through every one of those and exits; actually opening
# the window is not something a runner can be asked to do.
$windowed = Start-Process -FilePath (Join-Path $InstallDir 'Buttcrack Desktop.exe') -ArgumentList '--help' `
    -NoNewWindow -Wait -PassThru
Assert-True ($windowed.ExitCode -eq 0) 'the desktop program boots and parses arguments' "exit $($windowed.ExitCode)"

# The desktop program's own files go here rather than into the runner's user
# profile: what is under test is the product, not the machine.
$env:BUTTCRACK_DATA_DIR = Join-Path $Script:WorkDir 'data'
New-Item -ItemType Directory -Force -Path $env:BUTTCRACK_DATA_DIR | Out-Null

Write-Step 'Asking the installed build what it is (doctor)'
$run = Invoke-InstalledCli -Exe (Join-Path $InstallDir 'buttcrack.exe') -Arguments @('doctor')
$diagnosis = ($run.Output -join "`n")
Assert-True ($run.ExitCode -eq 0) 'doctor reports a healthy install' "exit $($run.ExitCode): $($run.Error)"
Assert-True ($diagnosis -match 'no problems found') 'doctor says so in words' $diagnosis
Assert-True ($diagnosis -match 'frozen executable') 'it knows it is the installed build' $diagnosis
Assert-True ($diagnosis -match [regex]::Escape($env:BUTTCRACK_DATA_DIR)) `
    'doctor names the data directory in use' $diagnosis

Write-Step 'Booting the installed desktop program for real (no window)'
# The windowed binary is what the shortcut runs, and in a windowed build stdout
# is a file rather than a console -- which makes this the only place the log file
# (docs/desktop-app-audit.md, E1) and the single-instance handover (A2) can be
# watched from outside.  --console keeps Tk out of it, so a runner needs no
# desktop session.
$desktopExe = Join-Path $InstallDir 'Buttcrack Desktop.exe'
$log = Join-Path $env:BUTTCRACK_DATA_DIR 'logs\buttcrack.log'
if (Test-Path -LiteralPath $log) { Remove-Item -LiteralPath $log -Force }
$first = Start-Process -FilePath $desktopExe -ArgumentList '--console', '--no-browser' -PassThru
try {
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline -and -not (Test-Path -LiteralPath $log)) { Start-Sleep -Seconds 1 }
    Assert-True (Test-Path -LiteralPath $log) 'the windowed build wrote its log file' $log
    $banner = [string](Get-Content -LiteralPath $log -Raw -ErrorAction SilentlyContinue)
    Assert-True ($banner -match 'buttcrack \d+\.\d+') 'the log begins with the version banner' $banner
    $match = [regex]::Match($banner, 'http://127\.0\.0\.1:(\d+)/')
    Assert-True $match.Success 'the log names the address it is serving' $banner
    if ($match.Success) {
        $port = [int]$match.Groups[1].Value
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$port/api/health" -TimeoutSec 30
        Assert-True ($health.name -eq 'buttcrack') "the installed desktop program serves on port $port" "$health"
    }

    # The marker is what the second launch reads, and on Windows it has to be
    # readable while the first copy holds its lock: a byte-range lock is
    # mandatory there, so a marker that carried the lock was unreadable and the
    # second copy started a server of its own.  That is what this asserts.
    $marker = Join-Path $env:BUTTCRACK_DATA_DIR 'desktop-instance.json'
    $markerText = if (Test-Path -LiteralPath $marker) { (Get-Content -LiteralPath $marker -Raw).Trim() } else { '(no marker)' }
    Assert-True ($markerText -match '"url"') 'the running app leaves a mark a second launch can read' $markerText

    Write-Step 'Starting it a second time (it has to hand over, not pile up)'
    $second = Start-Process -FilePath $desktopExe -ArgumentList '--console', '--no-browser' -PassThru
    $handedOver = $second.WaitForExit(60000)
    if (-not $handedOver) { try { $second.Kill() } catch { } }
    Assert-True $handedOver 'the second launch exits instead of starting a second server' `
        "exit $($second.ExitCode); marker: $markerText"
    Assert-True (-not $first.HasExited) 'the first copy is still running'
}
finally {
    if (-not $first.HasExited) {
        try { $first.Kill() } catch { }
        $first.WaitForExit(15000) | Out-Null
    }
}

Write-Step 'Exercising the SQLite-backed results store'
$database = Join-Path $Script:WorkDir 'results.sqlite3'
$run = Invoke-InstalledCli -Exe (Join-Path $InstallDir 'buttcrack.exe') -Arguments @('results', $database, '--limit', '5')
# results_db imports sqlite3, which the spec used to exclude from the bundle.
# That made this command -- and the PK9 Campaign panel in the window -- fail with
# ModuleNotFoundError in the shipped app while every other screen worked.
Assert-True ($run.ExitCode -eq 0) 'the results store opened (sqlite3 is bundled)' "exit $($run.ExitCode): $($run.Error)"

if ($SkipSelftest) {
    Write-Note '-SkipSelftest given; skipping the 142-check self-test'
}
else {
    Write-Step 'Running the installed self-test (142 checks, a couple of minutes)'
    $run = Invoke-InstalledCli -Exe (Join-Path $InstallDir 'buttcrack.exe') -Arguments @('selftest')
    # The summary lines *and* the failing checks under them: without the second
    # half an annotation says "2 of 47 failed" and nothing about which.
    $tail = ($run.Output -split "`r?`n" |
        Where-Object { $_ -match 'checks passed|FAIL|^\s+x\s' } |
        Select-Object -First 4) -join ' / '
    Assert-True ($run.ExitCode -eq 0) 'the installed build passes every self-test' "$tail"
    if ($tail) { Write-Note $tail }
}

# --------------------------------------------------------------------------- #
# 5. uninstall, and leave no trace
# --------------------------------------------------------------------------- #

if ($KeepInstalled) {
    Write-Step 'Done (-KeepInstalled): the product is still installed'
    Write-Host "`nInstalled at: $InstallDir`n" -ForegroundColor Green
    exit 0
}

Write-Step 'Uninstalling silently'

$uninstaller = Join-Path $InstallDir 'unins000.exe'
try {
    Start-Process -FilePath $uninstaller -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -Wait | Out-Null
}
catch {
    Fail "The uninstaller did not run: $_"
}

# The uninstaller copies itself into %TEMP% and the original process returns
# immediately, so the process exiting is not the same as the product being gone.
$deadline = (Get-Date).AddSeconds(120)
while ((Test-Path -LiteralPath (Join-Path $InstallDir 'Buttcrack Desktop.exe')) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
}
Start-Sleep -Milliseconds 500  # let the last of the file deletions settle

Write-Step 'Checking nothing was left behind'

foreach ($relative in @('Buttcrack Desktop.exe', 'buttcrack.exe', 'buttcrack-prompt.cmd', 'unins000.exe', '_internal')) {
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $InstallDir $relative))) "removed $relative"
}

if (Test-Path -LiteralPath $InstallDir) {
    $leftovers = @(Get-ChildItem -LiteralPath $InstallDir -Recurse -Force -ErrorAction SilentlyContinue)
    Assert-True ($leftovers.Count -eq 0) 'the install directory is empty' "$($leftovers.Count) item(s) left"
}
else {
    Write-Pass 'the install directory is gone'
}

Assert-True (-not (Test-PathEntry $InstallDir)) 'the install directory was removed from PATH'
Assert-True (-not (Get-InstalledLocation)) 'the uninstall registration is gone' (Get-InstalledLocation)

Assert-True (-not (Test-Path -LiteralPath $groupDir)) 'the Start-menu group was removed'
Assert-True (@($desktopCandidates | Where-Object { Test-Path -LiteralPath $_ }).Count -eq 0) `
    'the desktop shortcut was removed'

Write-Host "`n------------------------------------------------------------" -ForegroundColor Green
Write-Host " The installer works: it installs, runs, solves and uninstalls." -ForegroundColor Green
Write-Host " Installer: $Installer" -ForegroundColor Green
Write-Host " Version:   $Version" -ForegroundColor Green
Write-Host "------------------------------------------------------------`n" -ForegroundColor Green
