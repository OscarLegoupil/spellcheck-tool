$ErrorActionPreference = 'Stop'
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows 64-bit is required.' }
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeRoot = Join-Path $ProjectRoot '.runtime'
$CacheRoot = Join-Path $RuntimeRoot 'downloads'
New-Item -ItemType Directory -Force $CacheRoot | Out-Null
$Manifest = Get-Content (Join-Path $ProjectRoot 'src\spellcheck_tool\resources\downloads.lock.json') -Raw | ConvertFrom-Json
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Get-CheckedFile($Asset) {
    $Destination = Join-Path $CacheRoot $Asset.name
    if ((Test-Path $Destination) -and (Get-FileHash $Destination -Algorithm SHA256).Hash.ToLower() -eq $Asset.sha256) { return $Destination }
    Write-Host ('Downloading ' + $Asset.name)
    $Temporary = $Destination + '.part'
    Invoke-WebRequest -UseBasicParsing -Uri $Asset.url -OutFile $Temporary
    if ((Get-FileHash $Temporary -Algorithm SHA256).Hash.ToLower() -ne $Asset.sha256) {
        Remove-Item $Temporary -Force
        throw ('Checksum mismatch for ' + $Asset.name + '. No files from this download were executed.')
    }
    Move-Item -Force $Temporary $Destination
    return $Destination
}

Write-Host 'Spellcheck Tool - setting up private runtimes in this folder'
Write-Host 'No system installation, administrator access, or machine settings changes.'
$PythonArchive = Get-CheckedFile $Manifest.python
$PythonRoot = Join-Path $RuntimeRoot 'python'
if (-not (Test-Path (Join-Path $PythonRoot 'python.exe'))) { Expand-Archive -LiteralPath $PythonArchive -DestinationPath $PythonRoot -Force }
$PathFile = Join-Path $PythonRoot 'python312._pth'
@('python312.zip', '.', 'Lib\site-packages', '..\..\src', 'import site') | Set-Content $PathFile -Encoding ASCII
$PythonExe = Join-Path $PythonRoot 'python.exe'
$PipWheel = Get-CheckedFile $Manifest.pip
& $PythonExe (Join-Path $PSScriptRoot 'bootstrap_pip.py') $PipWheel (Join-Path $PythonRoot 'Lib\site-packages') (Join-Path $ProjectRoot 'requirements-windows.lock')
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed. Check network/proxy access to PyPI.' }
& $PythonExe (Join-Path $PSScriptRoot 'setup_runtime.py') --windows
if ($LASTEXITCODE -ne 0) { throw 'Engine installation failed.' }
& $PythonExe -m spellcheck_tool doctor
if ($LASTEXITCODE -ne 0) { throw 'An engine failed its startup check. Run Setup.cmd again after resolving the error.' }
