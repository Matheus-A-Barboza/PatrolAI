param([Parameter(Mandatory=$true)][string]$GtaPath)
$ErrorActionPreference = 'Stop'
$env:RPH_DIR = (Resolve-Path $GtaPath).Path
if (!(Test-Path (Join-Path $env:RPH_DIR 'RagePluginHook.dll'))) { throw "RagePluginHook.dll nao encontrada em $env:RPH_DIR" }
if (!(Get-Command dotnet -ErrorAction SilentlyContinue)) { throw 'Instale o .NET SDK 8 ou mais recente e abra novo terminal.' }
dotnet build (Join-Path $PSScriptRoot 'PatrolAI.csproj') -c Release
if ($LASTEXITCODE -ne 0) { throw 'Falha na compilacao.' }
Write-Host "DLL pronta: $PSScriptRoot\bin\Release\net48\PatrolAI.dll"
