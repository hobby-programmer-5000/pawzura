# Install only into the explicitly selected per-user runtime directory.
param([Parameter(Mandatory=$true)][string]$RuntimeRoot)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::Error.WriteLine('PAWZURA_PROGRESS {"stage":"art_runtime_tool"}')
$RuntimeRoot = [IO.Path]::GetFullPath($RuntimeRoot)
New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
$uvPath = Join-Path $RuntimeRoot 'uv.exe'
if (-not (Test-Path -LiteralPath $uvPath)) {
    $archive = Join-Path $RuntimeRoot 'uv-download.zip'
    Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/astral-sh/uv/releases/download/0.13.6/uv-x86_64-pc-windows-msvc.zip' -OutFile $archive
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'a2a8820d5eea32f08ef467ef3b7f66883a9b076d5737a2fc2fbb5f458d1bb50f') { throw 'Runtime download checksum mismatch' }
    Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $RuntimeRoot 'uv-unpack') -Force
    $candidate = Get-ChildItem -LiteralPath (Join-Path $RuntimeRoot 'uv-unpack') -Filter uv.exe -Recurse | Select-Object -First 1
    if (-not $candidate) { throw 'Runtime tool missing' }
    Copy-Item -LiteralPath $candidate.FullName -Destination $uvPath
    Remove-Item -LiteralPath $archive
}
$env:UV_CACHE_DIR = Join-Path $RuntimeRoot 'package-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $RuntimeRoot 'python'
[Console]::Error.WriteLine('PAWZURA_PROGRESS {"stage":"art_runtime_python"}')
& $uvPath python install 3.12.14
if ($LASTEXITCODE -ne 0) { throw 'Python installation failed' }
$venv = Join-Path $RuntimeRoot 'venv'
if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts/python.exe'))) {
    & $uvPath venv --python 3.12.14 $venv
    if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed' }
}
$python = Join-Path $venv 'Scripts/python.exe'
[Console]::Error.WriteLine('PAWZURA_PROGRESS {"stage":"art_runtime_torch"}')
& $uvPath pip install --python $python torch==2.7.1 --index-url https://download.pytorch.org/whl/cu118
if ($LASTEXITCODE -ne 0) { throw 'CUDA runtime installation failed' }
[Console]::Error.WriteLine('PAWZURA_PROGRESS {"stage":"art_runtime_packages"}')
& $uvPath pip install --python $python --index-url https://pypi.org/simple -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Image runtime installation failed' }
[Console]::Error.WriteLine('PAWZURA_PROGRESS {"stage":"art_runtime_notices"}')
& $python (Join-Path $PSScriptRoot 'inventory.py') $RuntimeRoot
if ($LASTEXITCODE -ne 0) { throw 'Runtime notices inventory failed' }
Write-Output 'READY'
