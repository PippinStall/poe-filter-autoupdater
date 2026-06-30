# ==================== SETTINGS ====================
$repo         = "NeverSinkDev/NeverSink-Filter-for-PoE2"
$poeFilterDir = "$env:USERPROFILE\Documents\My Games\Path of Exile 2"
# ==================================================

$versionFile = Join-Path $PSScriptRoot "current_version.txt"
$apiUrl      = "https://api.github.com/repos/$repo/releases/latest"
$headers     = @{ "User-Agent" = "PoE2-Filter-Updater" }

if (-not (Test-Path $poeFilterDir)) {
    New-Item -ItemType Directory -Path $poeFilterDir | Out-Null
}

Write-Host "Checking for NeverSink filter updates..." -ForegroundColor Cyan

try {
    $release       = Invoke-RestMethod -Uri $apiUrl -Headers $headers
    $latestVersion = $release.tag_name

    $currentVersion = if (Test-Path $versionFile) { (Get-Content $versionFile -Raw).Trim() } else { "" }

    if ($currentVersion -eq $latestVersion) {
        Write-Host "Already up to date: $latestVersion" -ForegroundColor Green
        exit 0
    }

    $fromLabel = if ($currentVersion) { $currentVersion } else { "none" }
    Write-Host "New version found: $latestVersion (installed: $fromLabel)" -ForegroundColor Yellow

    $tempZip     = Join-Path $env:TEMP "poe2_filter.zip"
    $tempExtract = Join-Path $env:TEMP "poe2_filter_extracted"

    if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force }

    Write-Host "Downloading archive..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $release.zipball_url -Headers $headers -OutFile $tempZip -UseBasicParsing

    Write-Host "Extracting .filter files..." -ForegroundColor Cyan
    Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force

    $filters = Get-ChildItem -Path $tempExtract -Filter "*.filter" -Recurse
    if ($filters.Count -eq 0) {
        Write-Host "Warning: no .filter files found in the archive." -ForegroundColor Yellow
    } else {
        $filters | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $poeFilterDir -Force
            Write-Host "  Copied: $($_.Name)" -ForegroundColor Gray
        }
        Write-Host "Copied $($filters.Count) filter(s) to: $poeFilterDir" -ForegroundColor Green
    }

    Remove-Item $tempZip     -Force
    Remove-Item $tempExtract -Recurse -Force

    Set-Content -Path $versionFile -Value $latestVersion -NoNewline

    Write-Host "Filter updated to $latestVersion." -ForegroundColor Green
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}
