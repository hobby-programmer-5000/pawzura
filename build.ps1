param([switch]$OneFile)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv-standard\Scripts\python.exe')) { & .\setup.ps1 }
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv pip install --python .venv-standard\Scripts\python.exe 'PyInstaller==6.22.3'
} else {
    & .venv-standard\Scripts\python.exe -m pip install 'PyInstaller==6.22.3'
}
if ($LASTEXITCODE -ne 0) { throw 'Build dependency installation failed.' }
if ($OneFile) {
    & .venv-standard\Scripts\python.exe scripts\build.py --onefile
} else {
    & .venv-standard\Scripts\python.exe scripts\build.py
}
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
