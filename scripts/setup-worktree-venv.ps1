#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup virtual environment link for git worktree

.DESCRIPTION
    Creates a symlink or junction point from the worktree to the main venv.
    This allows sharing the virtual environment across multiple worktrees.

.PARAMETER WorktreePath
    Path to the worktree directory

.PARAMETER MainRepoPath
    Path to the main repository (default: auto-detect)

.EXAMPLE
    .\scripts\setup-worktree-venv.ps1 ..\lolstonksrss-feature-auth

.EXAMPLE
    .\scripts\setup-worktree-venv.ps1 -WorktreePath ..\lolstonksrss-feature-x -MainRepoPath D:\lolstonksrss
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$WorktreePath,

    [Parameter(Mandatory = $false)]
    [string]$MainRepoPath = (Get-Location)
)

# Set error action preference
$ErrorActionPreference = "Stop"

function Get-RepositoryRoot {
    <#
    .SYNOPSIS
        Detect git repository root from current directory
    #>
    $result = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not detect git repository root"
    }
    return $result
}

function Test-Administrator {
    <#
    .SYNOPSIS
        Check if running as administrator
    #>
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function New-SymlinkOrJunction {
    <#
    .SYNOPSIS
        Create symlink or junction point with fallback
    #>
    param(
        [string]$Link,
        [string]$Target
    )

    $linkPath = Resolve-Path $Link -ErrorAction SilentlyContinue
    if ($linkPath) {
        Write-Host "✓ Link already exists: $Link"
        return
    }

    # Try creating symlink first
    try {
        New-Item -ItemType SymbolicLink -Path $Link -Target $Target | Out-Null
        Write-Host "✓ Created symlink: $Link -> $Target"
        return
    } catch {
        Write-Verbose "Symlink creation failed: $_"
    }

    # Fallback to junction point (works without admin rights on Windows)
    try {
        & mklink /J $Link $Target 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Created junction: $Link -> $Target"
            return
        }
    } catch {
        Write-Verbose "Junction creation failed: $_"
    }

    # Last resort: copy venv (slow but always works)
    Write-Warning "Could not create symlink or junction, copying venv (slower)"
    Copy-Item -Path $Target -Destination $Link -Recurse -Force
    Write-Host "✓ Copied venv to: $Link"
}

# Main script logic
try {
    # Detect repository root if not specified
    if (-not $MainRepoPath) {
        $MainRepoPath = Get-RepositoryRoot
    }

    # Resolve paths
    $mainRepoPath = Resolve-Path $MainRepoPath
    $worktreePath = Resolve-Path $WorktreePath -ErrorAction SilentlyContinue

    if (-not $worktreePath) {
        $worktreePath = Resolve-Path (Join-Path $MainRepoPath $WorktreePath)
    }

    Write-Host "Setting up venv link for worktree..."
    Write-Host "  Main repo:  $mainRepoPath"
    Write-Host "  Worktree:   $worktreePath"

    # Check main venv exists
    $mainVenv = Join-Path $mainRepoPath ".venv"
    if (-not (Test-Path $mainVenv)) {
        throw "Main venv not found at: $mainVenv"
    }

    # Create venv link in worktree
    $worktreeVenv = Join-Path $worktreePath ".venv"
    New-SymlinkOrJunction -Link $worktreeVenv -Target $mainVenv

    # Check if Python is accessible through the link
    $pythonExe = if ($IsWindows) { "python.exe" } else { "python" }
    $testPython = Join-Path $worktreeVenv "Scripts" $pythonExe

    if (-not (Test-Path $testPython)) {
        Write-Warning "⚠ Python executable not found at: $testPython"
        Write-Warning "The venv link may not be working correctly."
    } else {
        Write-Host "✓ Python accessible at: $testPython"
    }

    Write-Host ""
    Write-Host "Setup complete! Worktree is ready to use."

} catch {
    Write-Error "Setup failed: $_"
    exit 1
}
