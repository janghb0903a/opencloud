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
  registry.access.redhat.com/ubi9/python-311:latest `
  sh -c "python -m pip install --no-cache-dir -U pip && python -m pip download --only-binary=:all: -r requirements.txt -d wheels"

$pkgFiles = Get-ChildItem .\wheels -File -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "*.whl" -or $_.Name -like "*.tar.gz" -or $_.Name -like "*.zip"
}
if (-not $pkgFiles) {
    throw "Wheelhouse is empty. Dependency download failed."
}

$required = Get-ChildItem .\wheels -File -Filter "python_openstackclient-7.2.1-*.whl" -ErrorAction SilentlyContinue
if (-not $required) {
    throw "Required wheel missing: python_openstackclient-7.2.1"
}

Write-Output "Wheelhouse created: $RootDir\wheels"
