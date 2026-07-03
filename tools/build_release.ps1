param(
    [string]$Python = ".\.venv-build\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $ProjectRoot $Python

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python runtime not found: $PythonPath"
}

& $PythonPath -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Ebee Conquest release builds require Python 3.10 or newer."
}

Push-Location $ProjectRoot
try {
    & $PythonPath -m PyInstaller `
        --clean `
        --noconfirm `
        --distpath build `
        --workpath .pyinstaller `
        ebeeconquest.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }

    $ExecutablePath = Join-Path $ProjectRoot "build\ebeeconquest.exe"
    if (-not (Test-Path -LiteralPath $ExecutablePath)) {
        throw "Expected executable was not created: $ExecutablePath"
    }

    Get-Item -LiteralPath $ExecutablePath
}
finally {
    Pop-Location
}
