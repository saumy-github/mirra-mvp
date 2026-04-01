$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.." )).Path

$candidates = @(
    ".venv\\Scripts\\Activate.ps1",
    ".venv-win312\\Scripts\\Activate.ps1",
    ".venv\\bin\\Activate.ps1",
    ".venv-win312\\bin\\Activate.ps1"
)

foreach ($relativePath in $candidates) {
    $activatePath = Join-Path $repoRoot $relativePath
    if (Test-Path $activatePath) {
        & $activatePath
        return
    }
}

Write-Error "No venv activation script found. Create one with: py -3.12 -m venv .venv"
