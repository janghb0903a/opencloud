param(
  [string]$Tag = "oss-report-agent:0.1.0"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

# Build context must be repository root because app/ and requirements.txt are there.
docker build -t $Tag -f "$ScriptDir/Dockerfile" "$RepoRoot"
