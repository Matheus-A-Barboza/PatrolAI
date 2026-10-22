param([string]$GtaDir = 'D:\SteamLibrary\steamapps\common\Grand Theft Auto V')
$ErrorActionPreference='Stop'
$proj=Join-Path $PSScriptRoot 'PatrolAI.csproj'
if (!(Test-Path $proj)) {throw "Nao achei PatrolAI.csproj. Copie este script para a pasta plugin."}
$dll=Get-ChildItem -LiteralPath (Join-Path $GtaDir 'Plugins') -Recurse -File -Filter 'LSPD First Response.dll' -ErrorAction SilentlyContinue | Select-Object -First 1
if (!$dll) {throw "Nao achei LSPD First Response.dll em $GtaDir\Plugins. Confirme a instalacao do LSPDFR."}
[xml]$xml=Get-Content -LiteralPath $proj -Raw
$existing=$xml.Project.ItemGroup.Reference | Where-Object { $_.Include -eq 'LSPD First Response' }
if ($existing) {
    $existing.HintPath=$dll.FullName
} else {
    $group=$xml.Project.ItemGroup | Where-Object {$_.Reference} | Select-Object -First 1
    if (!$group) {$group=$xml.CreateElement('ItemGroup');[void]$xml.Project.AppendChild($group)}
    $node=$xml.CreateElement('Reference');$node.SetAttribute('Include','LSPD First Response')
    $h=$xml.CreateElement('HintPath');$h.InnerText=$dll.FullName
    $private=$xml.CreateElement('Private');$private.InnerText='False'
    [void]$node.AppendChild($h);[void]$node.AppendChild($private);[void]$group.AppendChild($node)
}
$xml.Save($proj)
Write-Host "Referencia adicionada: $($dll.FullName)"
