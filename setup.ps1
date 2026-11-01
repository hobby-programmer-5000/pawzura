param([string]$Python = "")
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv-standard\Scripts\python.exe')) {
    if ($Python) {
        & $Python -m venv .venv-standard
    } elseif (Get-Command uv -ErrorAction SilentlyContinue) {
        uv venv --python-preference only-managed --python 3.14 .venv-standard
    } else {
        py -3.14 -m venv .venv-standard
    }
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create environment. Use setup.ps1 -Python C:\path\to\python.exe (standard CPython 3.12+).' }
}
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv pip install --python .venv-standard\Scripts\python.exe -r requirements.txt
} else {
    & .venv-standard\Scripts\python.exe -m pip install -r requirements.txt
}
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& .venv-standard\Scripts\python.exe -c 'from PySide6.QtCore import qVersion; print("Qt", qVersion())'
if ($LASTEXITCODE -ne 0) { throw 'Qt failed to load. Use a standard CPython installation instead of Conda.' }
Write-Host 'Ready. Double-click run.bat or run .venv-standard\Scripts\python.exe -m pawzura --settings'
