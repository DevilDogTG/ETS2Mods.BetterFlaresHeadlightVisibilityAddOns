<#
.SYNOPSIS
    Stages src/ into the folder layout the SCS Workshop Uploader tool expects.

.DESCRIPTION
    Does NOT pack a .scs - the Workshop Uploader tool packs/uploads from a raw folder
    itself. This script only assembles that folder:

        <OutputDir>/
            versions.sii            # package_version_info, catch-all ".latest" block
            <PackageName>/          # copy of Root, with display_name and
                                     # compatible_versions[] stripped from manifest.sii
                manifest.sii
                description.txt
                ...

    Per SCS's docs (modding.scssoft.com/wiki/Documentation/Tools/SCS_Workshop_Uploader/
    versions.sii and .../Difference_between_Workshop_mod_and_the_Standard_mod):
    display_name is configured in the uploader tool's own UI instead of manifest.sii, and
    compatible_versions is expressed via versions.sii instead. This mod has a single
    supported content line, so versions.sii uses the documented ".latest" catch-all block
    (package_name only, no compatible_versions[] - matches everything not claimed by a
    more specific block).

.PARAMETER Root
    Mod source folder to stage (must contain manifest.sii at its top level).

.PARAMETER OutputDir
    Workshop staging root. Recreated on each run.

.PARAMETER PackageName
    Content subfolder name under OutputDir; also the package_name written into versions.sii.

.EXAMPLE
    .\tools\prepare-workshop.ps1
#>
[CmdletBinding()]
param(
    [string]$Root = "src",
    [string]$OutputDir = "output/workshop",
    [string]$PackageName = "latest"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
function Resolve-RepoPath([string]$Path) {
    if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }
    return Join-Path $RepoRoot $Path
}

$RootFull = Resolve-RepoPath $Root
$OutputDirFull = Resolve-RepoPath $OutputDir
$ManifestSrcPath = Join-Path $RootFull "manifest.sii"

if (-not (Test-Path $ManifestSrcPath)) {
    Write-Error "manifest.sii not found at $ManifestSrcPath"
    exit 1
}

# --- Stage: clean/recreate <OutputDir>/<PackageName>/, mirror Root into it ---
$Target = Join-Path $OutputDirFull $PackageName
if (Test-Path $Target) {
    Remove-Item -Recurse -Force $Target
}
New-Item -ItemType Directory -Path $Target -Force | Out-Null

Copy-Item -Path (Join-Path $RootFull "*") -Destination $Target -Recurse -Force

# --- Strip display_name / compatible_versions[] from the copied manifest.sii ---
$ManifestTargetPath = Join-Path $Target "manifest.sii"
$ManifestLines = Get-Content -Path $ManifestTargetPath
$FilteredLines = $ManifestLines | Where-Object {
    $_ -notmatch "^\s*display_name\s*:" -and $_ -notmatch "^\s*compatible_versions\[\]\s*:"
}
Set-Content -Path $ManifestTargetPath -Value $FilteredLines

# --- Write versions.sii (root of OutputDir, sibling of <PackageName>/) ---
$VersionsSiiPath = Join-Path $OutputDirFull "versions.sii"
$VersionsSiiContent = @"
SiiNunit
{
package_version_info : .latest {
	package_name: "$PackageName"
}
}
"@
Set-Content -Path $VersionsSiiPath -Value $VersionsSiiContent

Write-Host "Workshop package staged at $OutputDirFull"
Write-Host "  versions.sii -> package_name: `"$PackageName`""
Write-Host "  content      -> $Target"
