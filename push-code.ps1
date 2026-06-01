# Push local code to the current Git remote.
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\push-code.ps1 "commit message"
#
# Note: This script disables SSL verification only for the git network commands
# it runs. Use this only on a trusted network.

param(
    [string]$Message = ""
)

$ErrorActionPreference = "Stop"

function Run-Git {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$GitArgs
    )

    git @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed: git $($GitArgs -join ' ')"
    }
}

$repoRoot = git rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "This folder is not a git repository."
}

Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($Message)) {
    $Message = Read-Host "Nhap commit message"
}

if ([string]::IsNullOrWhiteSpace($Message)) {
    throw "Commit message is required."
}

Run-Git add -A

$status = git status --porcelain
if (-not [string]::IsNullOrWhiteSpace($status)) {
    Run-Git commit -m $Message
}
else {
    Write-Host "No local changes to commit."
}

$branch = git branch --show-current
if ([string]::IsNullOrWhiteSpace($branch)) {
    throw "Cannot detect current branch."
}

Write-Host "Pushing branch '$branch' to origin..."
Run-Git -c http.sslVerify=false push origin $branch

Write-Host "Done."
