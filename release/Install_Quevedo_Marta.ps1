# Quevedo - exclusive custom skin for Marta (Hellish Quart).
# Installs the four skin files and the Marta first-person (FPP) compatibility
# adjustment, which makes Marta's FPP loader use the selected custom skin.
#   Install:     .\Install_Quevedo_Marta.ps1
#   Uninstall:   .\Install_Quevedo_Marta.ps1 -Uninstall          (removes the skin, restores FPP)
#   Skin only:   .\Install_Quevedo_Marta.ps1 -NoFpp
param([string]$GameDirectory = 'C:\Program Files (x86)\Steam\steamapps\common\Hellish Quart',
      [switch]$Uninstall, [switch]$NoFpp)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$game = [IO.Path]::GetFullPath($GameDirectory)
$streaming = Join-Path $game 'Hellish Quart_Data\StreamingAssets'
$assets = Join-Path $game 'Hellish Quart_Data\resources.assets'
if (!(Test-Path -LiteralPath $streaming) -or !(Test-Path -LiteralPath $assets)) { throw "Hellish Quart was not found at: $game" }
if (Get-Process 'Hellish Quart' -ErrorAction SilentlyContinue) { throw 'Close Hellish Quart first.' }
$names = 'skin_marta_quevedo', 'skin_marta_quevedo.manifest', 'pic_marta_quevedo', 'pic_marta_quevedo.manifest'

function Get-RegionHash($fs, $patch) {
  $fs.Position = [Int64]$patch.object_offset
  $buf = New-Object byte[] ([int]$patch.object_length)
  if ($fs.Read($buf, 0, $buf.Length) -ne $buf.Length) { throw 'Could not read the Marta skin loader.' }
  ([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($buf))).Replace('-', '').ToLowerInvariant()
}

function Set-MartaFpp([bool]$enable) {
  $patch = Get-Content -LiteralPath (Join-Path $here 'marta_fpp_patch.json') -Raw | ConvertFrom-Json
  if ((Get-Item -LiteralPath $assets).Length -ne [Int64]$patch.file_size) { Write-Warning 'FPP: unsupported game build (resources.assets size differs). Skin installed without the FPP adjustment.'; return }
  $fs = [IO.File]::Open($assets, 'Open', 'ReadWrite', 'None')
  try {
    $sha = Get-RegionHash $fs $patch
    $target = if ($enable) { [string]$patch.patched_sha256 } else { [string]$patch.original_sha256 }
    $source = if ($enable) { [string]$patch.original_sha256 } else { [string]$patch.patched_sha256 }
    if ($sha -eq $target) { "FPP: already " + $(if ($enable) { 'enabled' } else { 'restored' }) + '.'; return }
    if ($sha -ne $source) { Write-Warning 'FPP: Marta loader does not match the supported build. No changes were made.'; return }
    if ($enable) {
      $backup = Join-Path $here 'marta_loader_backup.bin'
      $fs.Position = [Int64]$patch.object_offset
      $buf = New-Object byte[] ([int]$patch.object_length); [void]$fs.Read($buf, 0, $buf.Length)
      [IO.File]::WriteAllBytes($backup, $buf)
    }
    foreach ($c in $patch.changes) {
      $fs.Position = [Int64]$c.offset
      $fs.WriteByte($(if ($enable) { [byte]$c.after } else { [byte]$c.before }))
    }
    $fs.Flush($true)
    if ((Get-RegionHash $fs $patch) -ne $target) { throw 'FPP verification failed.' }
    "FPP: " + $(if ($enable) { 'enabled for Marta custom skins.' } else { 'original loader restored.' })
  } finally { $fs.Dispose() }
}

if ($Uninstall) {
  foreach ($n in $names) { $t = Join-Path $streaming $n; if (Test-Path -LiteralPath $t) { Remove-Item -LiteralPath $t -Force } }
  $others = Get-ChildItem -LiteralPath $streaming -Filter 'skin_marta_*' -ErrorAction SilentlyContinue | Where-Object { $_.Extension -ne '.manifest' }
  if ($others) { 'FPP: other Marta custom skins remain installed, FPP adjustment kept.' } else { Set-MartaFpp $false }
  'Quevedo uninstalled.'
  exit 0
}
foreach ($n in $names) {
  $src = Join-Path $here $n
  if (!(Test-Path -LiteralPath $src)) { throw "Missing mod file: $n" }
  Copy-Item -LiteralPath $src -Destination (Join-Path $streaming $n) -Force
}
if (-not $NoFpp) { Set-MartaFpp $true }
'Quevedo installed. Start Hellish Quart, select Marta and choose her under Custom Skin.'
