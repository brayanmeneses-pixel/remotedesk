<#
.SYNOPSIS
  Fase 1a: genera el .exe portable apuntando a NUESTRO servidor, sin compilar.
  Descarga el cliente oficial de RustDesk (versión fijada), verifica su SHA-256
  contra el digest publicado por GitHub y lo renombra con la configuración
  incrustada en el nombre (mecanismo documentado de RustDesk OSS:
  "rustdesk-host=<servidor>,key=<clave>.exe").
  La versión con nombre/íconos propios (Fase 1b) se compila en GitHub Actions.

.EXAMPLE
  .\tools\make-portable.ps1 -ServerHost remotedesk.duckdns.org -PubKey "AbC...="
#>
param(
  [Parameter(Mandatory)] [string] $ServerHost,
  [Parameter(Mandatory)] [string] $PubKey,
  [string] $Version = '1.5.3',
  [string] $Sha256  = '523ba0efbf62a21739961b62c7daaffb44d3da86139c546b364fd4e1333ed249',
  [string] $OutDir  = (Join-Path $PSScriptRoot '..\dist')
)
$ErrorActionPreference = 'Stop'

if ($PubKey -match '[\\/:*?"<>|]') {
  throw "La clave contiene caracteres no válidos para un nombre de archivo. Vuelve a ejecutar infra/setup.sh en una VM nueva o regenera la clave."
}
if ($ServerHost -match '[\\/:*?"<>|,]') { throw "ServerHost inválido: usa solo el dominio o IP, sin puerto ni http://" }

New-Item -ItemType Directory -Force $OutDir | Out-Null
$src = Join-Path $OutDir "rustdesk-$Version-x86_64.exe"
if (-not (Test-Path $src)) {
  $url = "https://github.com/rustdesk/rustdesk/releases/download/$Version/rustdesk-$Version-x86_64.exe"
  Write-Host "Descargando $url"
  Invoke-WebRequest $url -OutFile $src -UseBasicParsing
}
$hash = (Get-FileHash $src -Algorithm SHA256).Hash.ToLower()
if ($hash -ne $Sha256) { Remove-Item $src; throw "SHA-256 no coincide ($hash). Descarga corrupta o alterada." }
Write-Host "SHA-256 verificado."

$name = "rustdesk-host=$ServerHost,key=$PubKey.exe"
$dst = Join-Path $OutDir $name
Copy-Item $src $dst -Force
Write-Host "`nListo: $dst"
Write-Host "Cópialo tal cual (sin renombrar) a cada PC. Al abrirlo ya usa tu servidor."
