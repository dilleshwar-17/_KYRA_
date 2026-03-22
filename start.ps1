# ============================================================
#  KYRA Silent Launcher
#  All helper processes run hidden. Only the Electron window
#  is visible. No console/terminal is ever shown to the user.
# ============================================================

$ErrorActionPreference = "SilentlyContinue"

# -- Paths ----------------------------------------------------
$root        = $PSScriptRoot
$frontendDir = Join-Path $root "frontend"
$electronExe = Join-Path $frontendDir "node_modules\electron\dist\electron.exe"
$mainJs      = Join-Path $frontendDir "electron\main.js"


# -- Clean up old instances silently --------------------------
Get-Process -Name "electron" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

5173..5180 + 8080..8090 | ForEach-Object {
    $procId = (Get-NetTCPConnection -LocalPort $_ -ErrorAction SilentlyContinue).OwningProcess
    if ($procId) { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue }
}

Add-Type -AssemblyName System.Windows.Forms

# -- Validate required files -----------------------------------
# -- Validate required files -----------------------------------
if (-not (Test-Path $electronExe)) {
    [System.Windows.Forms.MessageBox]::Show("Electron not found. Please run:`n  cd frontend && npm install", "KYRA AI - Setup Required", 0, 16) | Out-Null
    exit 1
}
if (-not (Test-Path $mainJs)) {
    [System.Windows.Forms.MessageBox]::Show("electron\main.js not found at:`n$mainJs", "KYRA AI - Error", 0, 16) | Out-Null
    exit 1
}

# -- Build a clean environment (strip ELECTRON_RUN_AS_NODE) ---
$cleanEnv = @{}
[System.Environment]::GetEnvironmentVariables().GetEnumerator() | ForEach-Object {
    if ($_.Key -ne 'ELECTRON_RUN_AS_NODE') {
        $cleanEnv[$_.Key] = $_.Value
    }
}
$cleanEnv['PYTHONIOENCODING'] = 'utf-8'

# -- Helper: start a hidden process ----------------------------
function Start-Hidden {
    param(
        [string]$Exe,
        [string]$Arguments,
        [string]$WorkDir,
        [hashtable]$Env = @{}
    )
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName               = $Exe
    $info.Arguments              = $Arguments
    $info.WorkingDirectory       = $WorkDir
    $info.UseShellExecute        = $false
    $info.CreateNoWindow         = $true          # No console window
    $info.WindowStyle            = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $info.RedirectStandardOutput = $false
    $info.RedirectStandardError  = $false

    # Merge environment
    $cleanEnv.GetEnumerator() | ForEach-Object { $info.EnvironmentVariables[$_.Key] = $_.Value }
    $Env.GetEnumerator()      | ForEach-Object { $info.EnvironmentVariables[$_.Key] = $_.Value }
    $info.EnvironmentVariables.Remove('ELECTRON_RUN_AS_NODE')

    return [System.Diagnostics.Process]::Start($info)
}

# -- 1. Start Vite dev server (hidden) ------------------------
$viteProc = Start-Hidden -Exe "cmd.exe" `
    -Arguments "/c npm run dev > vite_log.txt 2>&1" `
    -WorkDir $frontendDir

# -- 1b. Start KYRA Backend (hidden) --------------------------
$pythonExe = Join-Path $root "python-portable\python.exe"
$backendDir = Join-Path $root "backend"
$backendProc = Start-Hidden -Exe "cmd.exe" `
    -Arguments "/c `"$pythonExe`" main.py > backend_log.txt 2>&1" `
    -WorkDir $backendDir

# -- 2. Wait for Vite to respond (up to 90 s) -----------------
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    try {
        Invoke-WebRequest "http://localhost:5173" -UseBasicParsing -TimeoutSec 1 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep 1
    }
}

if (-not $ready) {
    [System.Windows.Forms.MessageBox]::Show("Startup timed out at 90s.`nCheck vite_log.txt and backend_log.txt.", "KYRA AI - Error", 0, 16) | Out-Null
    if ($viteProc -and !$viteProc.HasExited) { $viteProc.Kill() }
    if ($backendProc -and !$backendProc.HasExited) { $backendProc.Kill() }
    exit 1
}

# -- 3. Launch Electron (the ONLY visible window) --------------
$electronInfo = New-Object System.Diagnostics.ProcessStartInfo
$electronInfo.FileName         = $electronExe
$electronInfo.Arguments        = "`"$mainJs`""
$electronInfo.WorkingDirectory = $frontendDir
$electronInfo.UseShellExecute  = $false
$electronInfo.CreateNoWindow   = $true

# Apply clean env to Electron too
$cleanEnv.GetEnumerator() | ForEach-Object { $electronInfo.EnvironmentVariables[$_.Key] = $_.Value }
$electronInfo.EnvironmentVariables.Remove('ELECTRON_RUN_AS_NODE')

$electronProc = [System.Diagnostics.Process]::Start($electronInfo)

# -- 4. Wait for Electron to exit, then clean up ---------------
$electronProc.WaitForExit()

# Kill the hidden processes when Electron closes
if ($viteProc -and !$viteProc.HasExited) {
    $viteProc.Kill()
}
if ($backendProc -and !$backendProc.HasExited) {
    $backendProc.Kill()
}
# Kill any leftover electron / node processes on Vite port
Get-Process -Name "electron" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
5173..5180 | ForEach-Object {
    $procId = (Get-NetTCPConnection -LocalPort $_ -ErrorAction SilentlyContinue).OwningProcess
    if ($procId) { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue }
}

