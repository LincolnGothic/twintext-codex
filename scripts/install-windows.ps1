param(
    [ValidateSet('chat', 'desktop')][string]$Workflow,
    [switch]$DownloadModels,
    [switch]$SkipModels,
    [switch]$WithoutEngine,
    [string]$Python
)
$ErrorActionPreference = 'Stop'
$taskInstaller = Join-Path $PSScriptRoot 'install.py'
$taskArguments = @($taskInstaller)
if ($Workflow) { $taskArguments += @('--workflow', $Workflow) }
if ($DownloadModels) { $taskArguments += '--download-models' }
if ($SkipModels) { $taskArguments += '--skip-models' }
if ($WithoutEngine) { $taskArguments += '--without-engine' }
if (-not $Python) {
    foreach ($taskCandidate in @('python', 'python3')) {
        $taskCommand = Get-Command $taskCandidate -ErrorAction SilentlyContinue
        if ($taskCommand) {
            & $taskCommand.Source -c "import sys; sys.exit(not ((3,10) <= sys.version_info[:2] < (3,14)))" 2>$null
            if ($LASTEXITCODE -eq 0) { $Python = $taskCommand.Source; break }
        }
    }
    if (-not $Python -and (Get-Command py -ErrorAction SilentlyContinue)) {
        foreach ($taskVersion in @('3.12', '3.13', '3.11', '3.10')) {
            $taskResolved = & py "-$taskVersion" -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0) { $Python = $taskResolved; break }
        }
    }
}
if (-not $Python) { throw 'Install 64-bit Python 3.12 from python.org with pip and venv, or pass -Python with its path.' }
& $Python @taskArguments
if ($LASTEXITCODE -ne 0) { throw "TwinText installation failed (exit $LASTEXITCODE)." }
