$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RootDir

if (Test-Path ".\wheels") {
    Remove-Item -Recurse -Force ".\wheels"
}
New-Item -ItemType Directory -Path ".\wheels" | Out-Null

docker run --rm `
  -v "${RootDir}:/work" `
  -w /work `
  python:3.11-slim `
  sh -c "pip install --no-cache-dir -U pip && pip download --only-binary=:all: -r requirements.txt -d wheels"

Write-Output "Wheelhouse created: $RootDir\wheels"
