$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }

$AppHome = Join-Path $Root "jobtracker\Home.py"
$Req     = Join-Path $Root "jobtracker\requirements.txt"
$Venv    = Join-Path $Root ".venv"
$Py      = "py"

if (!(Test-Path $AppHome)) { throw "Missing: $AppHome" }
if (!(Test-Path (Join-Path $Root "jobs.db"))) { throw "Missing: $(Join-Path $Root 'jobs.db')" }

if (!(Test-Path $Venv)) {
    & $Py -m venv $Venv
}

$VenvPy  = Join-Path $Venv "Scripts\python.exe"
$VenvPip = Join-Path $Venv "Scripts\pip.exe"

if (Test-Path $Req) {
    & $VenvPip install -r $Req
} else {
    & $VenvPip install streamlit reportlab
}

# Optional: kill old streamlit sessions using this venv
Get-Process python -ErrorAction SilentlyContinue |
  Where-Object { $_.Path -eq $VenvPy } |
  ForEach-Object { try { $_.Kill() } catch {} }

& $VenvPy -m streamlit run $AppHome
