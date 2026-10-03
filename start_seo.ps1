# AI-SEO Station one-click launcher (Windows double-click).
# 8 anti-crash rules from IMA "Highest-level automated deployment" benchmark:
#  - full-path powershell in .bat + if errorlevel 1 pause
#  - PATH-independent python discovery (managed WorkBuddy python first)
#  - release port 8000/8011 before start (kill zombie uvicorn)
#  - run from project root, package style: waitress-serve backend.app:app
#  - tunnel keep-alive via Wait-Process (NEVER Read-Host)
#  - readiness = "Registered tunnel connection" in log (NEVER probe public URL locally)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

$port = 8011

# [Rule] release ports 8000 / 8011 (zombie processes from previous failed runs)
foreach ($p in @(8000, $port)) {
    $occ = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
    if ($occ) { $occ | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }
}

# [Rule] locate python (PATH-independent). Managed WorkBuddy python first.
$pythonCandidates = @(
    "C:\Users\86198\.workbuddy\binaries\python\versions\3.13.12\python.exe",
    "C:\Users\86198\.workbuddy\binaries\python\versions\3.13.14\python.exe",
    "py", "python"
)
$py = $null
foreach ($c in $pythonCandidates) { if (Test-Path $c -PathType Leaf) { $py = $c; break } }
if (-not $py) {
    foreach ($c in @("py", "python")) { if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break } }
}
if (-not $py) { Write-Error "Python not found. Install Python or check managed path."; exit 1 }
Write-Host "[1/6] Python: $py"

# [venv] create if missing, install deps (Tsinghua mirror)
$venv = Join-Path $root "venv"
$venvPy = Join-Path $venv "Scripts/python.exe"
if (-not (Test-Path $venvPy)) {
    & $py -m venv $venv
    & $venvPy -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
    & $venvPy -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
}
Write-Host "[2/6] venv ready: $venvPy"

# [Rule] start server from root, package style (Flask via waitress WSGI)
# NOTE: PowerShell 5.1 Start-Process has no -Environment; set PYTHONPATH in session
# scope so the child waitress inherits it (imports backend package from root).
$waitress = Join-Path $venv "Scripts/waitress-serve.exe"
$env:PYTHONPATH = $root
$uvProc = Start-Process -FilePath $waitress `
    -ArgumentList "--listen=127.0.0.1:$port", "backend.app:app" `
    -WorkingDirectory $root -WindowStyle Minimized -PassThru

# wait for local /api/health (local loopback only, NOT public URL)
$ok = $false
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $t = Invoke-WebRequest -Uri "http://127.0.0.1:$port/api/health" -UseBasicParsing -TimeoutSec 2
        if ($t.StatusCode -eq 200) { $ok = $true; break }
    } catch { }
}
if (-not $ok) { Write-Error "Local service not ready in 30s. Check error above."; exit 1 }
Write-Host "[3/6] Local service ready: http://127.0.0.1:$port"

# [cloudflared] download if missing, then quick tunnel
$cfExe = Join-Path $root "cloudflared.exe"
if (-not (Test-Path $cfExe)) {
    Write-Host "cloudflared.exe not found, downloading (CN mirror)..."
    try {
        $url = "https://ghfast.top/https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        Invoke-WebRequest -Uri $url -OutFile $cfExe -TimeoutSec 180
    } catch { Write-Warning "cloudflared download failed. Local only, skip tunnel." }
}

if (Test-Path $cfExe) {
    $cfProc = Start-Process -FilePath $cfExe `
        -ArgumentList "tunnel", "--no-autoupdate", "--loglevel", "info", "--url", "http://127.0.0.1:$port" `
        -WorkingDirectory $root -WindowStyle Minimized -PassThru `
        -RedirectStandardOutput "cloudflared.log" -RedirectStandardError "cloudflared.err.log"

    $publicUrl = $null
    for ($i = 1; $i -le 60; $i++) {
        Start-Sleep -Seconds 1
        $log = ""
        if (Test-Path "cloudflared.log") { $log += (Get-Content "cloudflared.log" -Raw -ErrorAction SilentlyContinue) }
        if (Test-Path "cloudflared.err.log") { $log += (Get-Content "cloudflared.err.log" -Raw -ErrorAction SilentlyContinue) }
        if ($log -match "https://[a-z0-9-]+\.trycloudflare\.com") { $publicUrl = $matches[0] }
        if ($log -match "Registered tunnel connection") { break }   # readiness signal; never kill prematurely
    }
    if ($publicUrl) {
        Set-Content "PUBLIC_URL.txt" $publicUrl
        try { $publicUrl | Set-Clipboard } catch { }
        Write-Host "[6/6] PUBLIC URL: $publicUrl  (copied to clipboard; keep this window open)"
        try { Start-Process $publicUrl } catch { }
    } else {
        Write-Warning "No public URL yet, but local works: http://127.0.0.1:$port"
    }
    Wait-Process -Id $cfProc.Id   # [Rule] keep-alive by process handle
} else {
    Write-Host "Local service available: http://127.0.0.1:$port (no public tunnel configured)"
    Wait-Process -Id $uvProc.Id
}
