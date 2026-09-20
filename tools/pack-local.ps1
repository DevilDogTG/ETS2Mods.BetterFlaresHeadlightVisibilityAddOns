<#
.SYNOPSIS
    Packs src/ into a versioned .scs archive for local/manual installation.

.DESCRIPTION
    Wraps scs_packer's "create" command. The output archive's base name comes from
    tools/pack.config.json (if present), falling back to src/manifest.sii's display_name.
    The version always comes from src/manifest.sii's package_version - manifest.sii is the
    single source of truth for version, never overridable via config.

    pack.config.json shape (field optional):
        {
          "packageName": "<slug used as the .scs base filename>"
        }
    A missing config file, or a missing/empty packageName, falls back to a slugified
    display_name from manifest.sii.

.PARAMETER Root
    Mod source folder to pack (must contain manifest.sii at its top level).

.PARAMETER OutputDir
    Folder the .scs is written into. Created if missing.

.PARAMETER ConfigPath
    Path to pack.config.json. Silently ignored if it doesn't exist.

.EXAMPLE
    .\tools\pack-local.ps1
#>
[CmdletBinding()]
param(
    [string]$Root = "src",
    [string]$OutputDir = "output/local",
    [string]$ConfigPath = "tools/pack.config.json"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
function Resolve-RepoPath([string]$Path) {
    if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }
    return Join-Path $RepoRoot $Path
}

$RootFull = Resolve-RepoPath $Root
$OutputDirFull = Resolve-RepoPath $OutputDir
$ConfigPathFull = Resolve-RepoPath $ConfigPath
$ManifestPath = Join-Path $RootFull "manifest.sii"

# --- Preflight: scs_packer must resolve on PATH ---
if (-not (Get-Command "scs_packer" -ErrorAction SilentlyContinue) -and
    -not (Get-Command "scs_packer.exe" -ErrorAction SilentlyContinue)) {
    Write-Error "scs_packer not found on PATH. Run the ets2-mod-developer 'tool-preflight' skill to set up this host's tools_dir."
    exit 1
}

if (-not (Test-Path $ManifestPath)) {
    Write-Error "manifest.sii not found at $ManifestPath"
    exit 1
}

# --- Slugify a display name into a filename-safe package name ---
function ConvertTo-Slug([string]$Text) {
    $slug = $Text.ToLowerInvariant()
    $slug = [regex]::Replace($slug, "[^a-z0-9]+", "_")
    $slug = $slug.Trim("_")
    return $slug
}

function Get-ManifestField([string]$Content, [string]$Field) {
    $m = [regex]::Match($Content, "(?m)^\s*$Field\s*:\s*""([^""]*)""")
    if ($m.Success) { return $m.Groups[1].Value }
    return $null
}

$ManifestContent = Get-Content -Raw -Path $ManifestPath

# --- Resolve packageName: config.json first, manifest.sii fallback ---
$Config = $null
if (Test-Path $ConfigPathFull) {
    $Config = Get-Content -Raw -Path $ConfigPathFull | ConvertFrom-Json
}

$PackageName = $null
if ($Config -and ($Config.PSObject.Properties.Name -contains "packageName") -and $Config.packageName) {
    $PackageName = $Config.packageName
}

if (-not $PackageName) {
    $DisplayName = Get-ManifestField $ManifestContent "display_name"
    if (-not $DisplayName) {
        Write-Error "Could not resolve packageName: not set in $ConfigPath and no display_name in manifest.sii"
        exit 1
    }
    $PackageName = ConvertTo-Slug $DisplayName
}

# --- Resolve version: always from manifest.sii, never overridable via config ---
$Version = Get-ManifestField $ManifestContent "package_version"
if (-not $Version) {
    Write-Error "Could not resolve version: no package_version in manifest.sii"
    exit 1
}

# --- Pack ---
if (-not (Test-Path $OutputDirFull)) {
    New-Item -ItemType Directory -Path $OutputDirFull -Force | Out-Null
}

$OutputFileName = "${PackageName}_v${Version}.scs"
$OutputPath = Join-Path $OutputDirFull $OutputFileName

& scs_packer create $OutputPath -root $RootFull
if ($LASTEXITCODE -ne 0) {
    Write-Error "scs_packer exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}

if (-not (Test-Path $OutputPath)) {
    Write-Error "scs_packer reported success but $OutputPath was not created"
    exit 1
}

$SizeKB = [math]::Round((Get-Item $OutputPath).Length / 1KB, 1)
Write-Host "Packed $OutputPath ($SizeKB KB)"
