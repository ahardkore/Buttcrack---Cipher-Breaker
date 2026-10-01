<#
.SYNOPSIS
    Build Buttcrack.exe, buttcrack.exe and buttcrack-setup-<version>.exe.

.DESCRIPTION
    One command, from a clean checkout, on a Windows machine:

        powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1

    It makes an isolated build virtualenv, freezes the app with PyInstaller,
    smoke-tests the result by actually breaking a cipher with it, then wraps
    the whole thing in an Inno Setup installer and prints the SHA-256 you
    should publish next to the download.

    The output is self-contained: the person who runs the installer needs no
    Python, no git and no GitHub account.

.PARAMETER SkipInstaller
    Stop after PyInstaller. Useful when you only want dist\Buttcrack\ to poke at.

.PARAMETER Clean
    Delete dist\, build\ and the build virtualenv first.

.PARAMETER CertThumbprint
    Thumbprint of a code-signing certificate in your certificate store. When
    given, both executables and the installer are signed, which is what stops
    SmartScreen shouting at everyone who downloads it. Optional: an unsigned
    build works, it just gets a scarier first-run dialog.

.PARAMETER TimestampUrl
    RFC 3161 timestamp server used when signing. Default: DigiCert's.

.EXAMPLE
    .\build.ps1

.EXAMPLE
    .\build.ps1 -Clean -CertThumbprint ABCD1234567890ABCDEF1234567890ABCDEF1234
#>
[CmdletBinding()]
param(
    [switch]$SkipInstaller,
    [switch]$Clean,
    [string]$CertThumbprint = '',
    [string]$TimestampUrl = 'http://timestamp.digicert.com'
)

$ErrorActionPreference = 'Stop'

$Here = $PSScriptRoot
$Root = Split-Path (Split-Path $Here -Parent) -Parent
$VenvDir = Join-Path $Root '.venv-build'
$DistDir = Join-Path $Root 'dist'
$AppDir = Join-Path $DistDir 'Buttcrack'
$InstallerDir = Join-Path $DistDir 'installer'

function Write-Step { param([string]$Text) Write-Host "`n==> $Text" -ForegroundColor Cyan }
function Write-Note { param([string]$Text) Write-Host "    $Text" -ForegroundColor DarkGray }
function Fail { param([string]$Text) Write-Host "`nX  $Text`n" -ForegroundColor Red; exit 1 }

function Find-SignTool {
    $found = Get-Command 'signtool.exe' -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    $kit = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin' -Recurse -Filter 'signtool.exe' `
        -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match '\\x64\\' } |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if ($kit) { return $kit.FullName }
    return $null
}

function Invoke-Sign {
    param([string]$Path, [string]$Thumbprint, [string]$Timestamp, [string]$SignTool)
    & $SignTool sign /sha1 $Thumbprint /fd SHA256 /tr $Timestamp /td SHA256 $Path
    if ($LASTEXITCODE -ne 0) { Fail "Signing $Path failed." }
    Write-Note "signed $(Split-Path $Path -Leaf)"
}

Push-Location $Root
try {
    # ----------------------------------------------------------------- #
    # 0. clean
    # ----------------------------------------------------------------- #
    if ($Clean) {
        Write-Step 'Cleaning previous build output'
        foreach ($path in @($DistDir, (Join-Path $Root 'build'), $VenvDir)) {
            if (Test-Path $path) { Remove-Item $path -Recurse -Force; Write-Note "removed $path" }
        }
    }

    # ----------------------------------------------------------------- #
    # 1. interpreter
    # ----------------------------------------------------------------- #
    Write-Step 'Locating Python'
    # `py -3` first: on a machine without a real Python, bare `python` is often
    # the Microsoft Store stub, which "succeeds" by opening the Store.
    $pythonExe = $null
    $pythonArgs = @()
    foreach ($candidate in @(@('py', '-3'), @('python'), @('python3'))) {
        $cmd = Get-Command $candidate[0] -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -notmatch 'WindowsApps') {
            $pythonExe = $cmd.Source
            $pythonArgs = @($candidate | Select-Object -Skip 1)
            break
        }
    }
    if (-not $pythonExe) {
        Fail 'No Python found. Install Python 3.9 or newer from python.org (tick "Add python.exe to PATH").'
    }

    $pyVersion = (& $pythonExe @($pythonArgs + @('-c', 'import sys; print("%d.%d" % sys.version_info[:2])'))).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $pyVersion) { Fail "Could not run $pythonExe." }
    Write-Note "$pythonExe $($pythonArgs -join ' ')  ->  Python $pyVersion"
    if ([version]$pyVersion -lt [version]'3.9') { Fail "Python $pyVersion is too old; 3.9 or newer is required." }

    # The desktop window is Tk. A Python installed without the "tcl/tk and IDLE"
    # component builds happily and then ships an app with no window at all,
    # which is a miserable thing to learn from a user's bug report.
    & $pythonExe @($pythonArgs + @('-c', 'import tkinter')) 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Fail 'This Python has no tkinter, so the desktop window cannot be built. Re-run the python.org installer, choose Modify, and tick "tcl/tk and IDLE".'
    }
    Write-Note 'tkinter: present'

    # ----------------------------------------------------------------- #
    # 2. build virtualenv  (kept out of whatever environment you are in)
    # ----------------------------------------------------------------- #
    Write-Step 'Preparing the build virtualenv'
    $VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
    if (-not (Test-Path $VenvPython)) {
        & $pythonExe @($pythonArgs + @('-m', 'venv', $VenvDir))
        if ($LASTEXITCODE -ne 0) { Fail 'Could not create the build virtualenv.' }
    }
    & $VenvPython -m pip install --quiet --upgrade pip
    # Pinned to a major series: this spec is written against PyInstaller 6
    # (contents_directory, Analysis(optimize=...)).
    & $VenvPython -m pip install --quiet --upgrade 'pyinstaller~=6.10'
    if ($LASTEXITCODE -ne 0) { Fail 'pip could not install PyInstaller.' }
    Write-Note "PyInstaller $((& $VenvPython -m PyInstaller --version).Trim())"

    $AppVersion = (& $VenvPython -c "import sys; sys.path.insert(0, sys.argv[1]); import buttcrack; print(buttcrack.__version__)" $Root).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $AppVersion) { Fail 'Could not read buttcrack.__version__.' }
    Write-Note "buttcrack $AppVersion"

    # ----------------------------------------------------------------- #
    # 3. freeze
    # ----------------------------------------------------------------- #
    Write-Step 'Freezing the application (PyInstaller)'
    & $VenvPython -m PyInstaller --clean --noconfirm (Join-Path $Here 'buttcrack.spec')
    if ($LASTEXITCODE -ne 0) { Fail 'PyInstaller failed.' }

    $GuiExe = Join-Path $AppDir 'Buttcrack.exe'
    $CliExe = Join-Path $AppDir 'buttcrack.exe'
    foreach ($exe in @($GuiExe, $CliExe)) {
        if (-not (Test-Path $exe)) { Fail "Expected $exe, which PyInstaller did not produce." }
    }
    $appSize = [math]::Round((Get-ChildItem $AppDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    Write-Note "dist\Buttcrack\  ($appSize MB)"

    # ----------------------------------------------------------------- #
    # 4. smoke test
    # ----------------------------------------------------------------- #
    # Not just "does it start": a frozen build whose n-gram tables failed to
    # come along starts perfectly and then cannot break anything, which is
    # precisely the bug you do not want to ship. So make it break a cipher.
    Write-Step 'Smoke-testing the frozen build'
    $report = (& $CliExe 'Wkh txlfn eurzq ira mxpsv ryhu wkh odcb grj.' '--json' | Out-String) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { Fail 'buttcrack.exe did not run. The build is broken.' }
    if (-not $report.solved -or $report.best.cipher -ne 'caesar') {
        Fail ("The frozen CLI ran but did not solve the Caesar sample (got '" + $report.best.cipher +
              "'). The language model probably did not get bundled.")
    }
    Write-Note "solved: $($report.best.cipher), key $($report.best.key) -- $($report.best.notes.formatted)"

    # And that the web UI the shortcut opens is actually in there.
    foreach ($asset in @('_internal\buttcrack\static\index.html',
                         '_internal\buttcrack\data\english_quadgrams.txt.gz')) {
        if (-not (Test-Path (Join-Path $AppDir $asset))) { Fail "Missing from the bundle: $asset" }
    }
    Write-Note 'web UI and language model: bundled'

    # ----------------------------------------------------------------- #
    # 5. sign the executables (optional -- see docs/windows-installer.md)
    # ----------------------------------------------------------------- #
    $SignTool = $null
    if ($CertThumbprint) {
        $SignTool = Find-SignTool
        if (-not $SignTool) { Fail 'signtool.exe not found. Install the Windows SDK, or drop -CertThumbprint.' }
        Write-Step 'Signing the executables'
        Write-Note $SignTool
        foreach ($exe in @($GuiExe, $CliExe)) {
            Invoke-Sign -Path $exe -Thumbprint $CertThumbprint -Timestamp $TimestampUrl -SignTool $SignTool
        }
    }

    # ----------------------------------------------------------------- #
    # 6. installer
    # ----------------------------------------------------------------- #
    if ($SkipInstaller) {
        Write-Step 'Done (installer skipped)'
        Write-Host "`nApplication: $AppDir`n" -ForegroundColor Green
        exit 0
    }

    Write-Step 'Building the installer (Inno Setup)'
    $iscc = $null
    $isccCmd = Get-Command 'iscc.exe' -ErrorAction SilentlyContinue
    if ($isccCmd) {
        $iscc = $isccCmd.Source
    }
    else {
        foreach ($candidate in @('C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
                                 'C:\Program Files\Inno Setup 6\ISCC.exe')) {
            if (Test-Path $candidate) { $iscc = $candidate; break }
        }
    }
    if (-not $iscc) {
        Fail 'Inno Setup 6.3 or newer not found. Install it with:  winget install --id JRSoftware.InnoSetup  (or from https://jrsoftware.org/isdl.php), then re-run. Pass -SkipInstaller to stop after the executables instead.'
    }
    Write-Note $iscc

    New-Item -ItemType Directory -Force -Path $InstallerDir | Out-Null
    & $iscc "/DAppVersion=$AppVersion" (Join-Path $Here 'buttcrack.iss')
    if ($LASTEXITCODE -ne 0) { Fail 'Inno Setup failed.' }

    $Setup = Join-Path $InstallerDir "buttcrack-setup-$AppVersion.exe"
    if (-not (Test-Path $Setup)) { Fail "Inno Setup reported success but $Setup is missing." }

    if ($CertThumbprint) {
        Write-Step 'Signing the installer'
        Invoke-Sign -Path $Setup -Thumbprint $CertThumbprint -Timestamp $TimestampUrl -SignTool $SignTool
    }

    # ----------------------------------------------------------------- #
    # 7. what to publish
    # ----------------------------------------------------------------- #
    $hash = (Get-FileHash $Setup -Algorithm SHA256).Hash.ToLower()
    $size = [math]::Round((Get-Item $Setup).Length / 1MB, 1)
    Set-Content -Path "$Setup.sha256" -Value "$hash  buttcrack-setup-$AppVersion.exe" -NoNewline

    $signed = if ($CertThumbprint) { 'yes' } else { 'no (SmartScreen will warn on first run)' }
    Write-Host "`n------------------------------------------------------------" -ForegroundColor Green
    Write-Host " Installer: $Setup" -ForegroundColor Green
    Write-Host " Size:      $size MB"
    Write-Host " SHA-256:   $hash"
    Write-Host " Signed:    $signed"
    Write-Host "------------------------------------------------------------`n" -ForegroundColor Green
    Write-Host 'Upload that one file anywhere that serves static files and you are done.'
    Write-Host 'See docs/windows-installer.md for hosting that does not involve GitHub,'
    Write-Host 'and publish the SHA-256 beside the link so people can verify what they got.'
    Write-Host ''
}
finally {
    Pop-Location
}
