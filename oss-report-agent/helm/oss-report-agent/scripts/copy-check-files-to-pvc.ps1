param(
  [string]$Namespace = "default",
  [string]$ReleaseName = "oss-report-agent",
  [string]$SourceDir = "..\..\..\check",
  [string]$TargetDir = "/input/checks",
  [string]$AppNameLabel = "oss-report-agent"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ResolvedSourceDir = (Resolve-Path (Join-Path $ScriptDir $SourceDir)).Path

if (-not (Test-Path $ResolvedSourceDir)) {
  throw "Source directory not found: $ResolvedSourceDir"
}

$Files = Get-ChildItem -Path $ResolvedSourceDir -File
if ($Files.Count -eq 0) {
  throw "No check files found in source directory: $ResolvedSourceDir"
}

$PodName = kubectl -n $Namespace get pods `
  -l "app.kubernetes.io/instance=$ReleaseName,app.kubernetes.io/name=$AppNameLabel" `
  --field-selector=status.phase=Running `
  -o jsonpath="{.items[0].metadata.name}"

if (-not $PodName) {
  throw "No running report-agent pod found in namespace=$Namespace, release=$ReleaseName"
}

Write-Host "Using target pod: $PodName"
kubectl -n $Namespace exec $PodName -- mkdir -p $TargetDir

foreach ($file in $Files) {
  kubectl -n $Namespace cp $file.FullName "${PodName}:${TargetDir}/$($file.Name)"
}

kubectl -n $Namespace exec $PodName -- ls -l $TargetDir
Write-Host "Copied $($Files.Count) check files to ${PodName}:${TargetDir}."
