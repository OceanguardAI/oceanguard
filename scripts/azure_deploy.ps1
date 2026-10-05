<#
.SYNOPSIS
    Deploy OceanGuard (backend API + YOLO service + web UI) to Azure Container Apps.

    - Creates the registry, environment and the three Container Apps (infrastructure
      only). Images are built and pushed by the GitHub Actions workflows, because
      Azure for Students blocks ACR Tasks ('az acr build').
    - Secrets are read from backend\.env and passed as Container Apps secrets;
      nothing is printed. ADMIN_API_KEY is generated into backend\.env if empty.
    - The YOLO service (torch image) scales to zero between checks;
      the backend gets its URL as YOLO_SERVICE_URL.
    - Region must be one the student policy allows (centralindia).
#>
param(
    [string]$RG       = "oceanguard-rg",
    [string]$Location = "centralindia",
    [string]$Acr      = "ogacr901ad",
    [string]$EnvName  = "og-env"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Assert-Ok([string]$what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" } }

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $repo "backend\.env"

function Get-EnvValue([string]$name) {
    if (-not (Test-Path $envFile)) { return "" }
    $line = Get-Content $envFile | Where-Object { $_ -match "^$name=" } | Select-Object -First 1
    if (-not $line) { return "" }
    return ($line -split "=", 2)[1].Trim()
}

$admin = Get-EnvValue "ADMIN_API_KEY"
if (-not $admin) {
    $admin = -join ((48..57) + (97..122) | Get-Random -Count 40 | ForEach-Object { [char]$_ })
    Add-Content $envFile "`nADMIN_API_KEY=$admin"
}
$gfw  = Get-EnvValue "GFW_API_TOKEN"
$ais  = Get-EnvValue "AISSTREAM_API_KEY"
$groq = Get-EnvValue "GROQ_API_KEY"
$shId = Get-EnvValue "SENTINELHUB_CLIENT_ID"
$shSecret = Get-EnvValue "SENTINELHUB_CLIENT_SECRET"

Write-Host "[1/6] Providers and extension..."
foreach ($p in "Microsoft.App", "Microsoft.ContainerRegistry", "Microsoft.OperationalInsights") {
    do { $s = az provider show -n $p --query registrationState -o tsv; if ($s -ne "Registered") { az provider register -n $p | Out-Null; Start-Sleep 10 } } while ($s -ne "Registered")
}
az extension show --name containerapp --query name -o tsv 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { az extension add --name containerapp --yes | Out-Null; Assert-Ok "extension" }

Write-Host "[2/6] Container registry '$Acr'..."
$have = az acr show -n $Acr -g $RG --query name -o tsv 2>$null
if (-not $have) { az acr create -n $Acr -g $RG -l $Location --sku Basic --admin-enabled true | Out-Null; Assert-Ok "acr create" }
az acr update -n $Acr --admin-enabled true | Out-Null
$server = az acr show -n $Acr --query loginServer -o tsv
$acrUser = az acr credential show -n $Acr --query username -o tsv
$acrPass = az acr credential show -n $Acr --query "passwords[0].value" -o tsv

Write-Host "[3/6] Container Apps environment '$EnvName'..."
$have = az containerapp env show -n $EnvName -g $RG --query name -o tsv 2>$null
if (-not $have) { az containerapp env create -n $EnvName -g $RG -l $Location | Out-Null; Assert-Ok "env create" }

Write-Host "[4/6] Backend app..."
$secrets = @("admin-key=$admin")
$envVars = @("PORT=8080", "ADMIN_API_KEY=secretref:admin-key", "GFW_SAR_DATASET=public-global-sar-presence:v4.0",
             "GFW_REGION_BBOX=[78.0,5.5,82.5,10.0]", "GFW_LOOKBACK_DAYS=120", "GFW_MAX_EVENTS=600",
             "GFW_INGEST_ON_STARTUP=true")
if ($gfw) { $secrets += "gfw-token=$gfw"; $envVars += "GFW_API_TOKEN=secretref:gfw-token" }
if ($ais) { $secrets += "ais-key=$ais";   $envVars += "AISSTREAM_API_KEY=secretref:ais-key" }
if ($groq) { $secrets += "groq-key=$groq"; $envVars += "GROQ_API_KEY=secretref:groq-key" }
$sentinelSecrets = @(); $sentinelVars = @()
if ($shId -and $shSecret) {
    $sentinelSecrets = @("sh-id=$shId", "sh-secret=$shSecret")
    $sentinelVars = @("SENTINELHUB_CLIENT_ID=secretref:sh-id", "SENTINELHUB_CLIENT_SECRET=secretref:sh-secret")
}
$secrets += $sentinelSecrets; $envVars += $sentinelVars

# Azure for Students blocks ACR Tasks (`az acr build`), so images are built by the
# GitHub Actions workflows and pushed to the registry. Apps are created here with a
# public placeholder image (port 80); the first workflow run swaps in the real image
# and moves ingress to port 8080. Existing apps are left alone so a re-run never
# overwrites a deployed revision.
$placeholder = "mcr.microsoft.com/k8se/quickstart:latest"

function New-App([string]$name, [string[]]$extra) {
    if (az containerapp show -n $name -g $RG --query name -o tsv 2>$null) { Write-Host "  $name exists, left unchanged"; return }
    az containerapp create -n $name -g $RG --environment $EnvName --image $placeholder `
        --registry-server $server --registry-username $acrUser --registry-password $acrPass `
        --target-port 80 --ingress external @extra | Out-Null
    Assert-Ok "$name create"
}
function Get-Url([string]$name) {
    "https://" + (az containerapp show -n $name -g $RG --query properties.configuration.ingress.fqdn -o tsv)
}

New-App "og-backend" (@("--min-replicas", "1", "--max-replicas", "1", "--cpu", "1.0", "--memory", "2.0Gi",
                        "--secrets") + $secrets + @("--env-vars") + $envVars)
$backendUrl = Get-Url "og-backend"

Write-Host "[5/6] YOLO service (scale-to-zero)..."
$yoloExtra = @("--min-replicas", "0", "--max-replicas", "1", "--cpu", "2.0", "--memory", "4.0Gi", "--env-vars", "PORT=8080") + $sentinelVars
if ($sentinelSecrets) { $yoloExtra += @("--secrets") + $sentinelSecrets }
New-App "og-yolo" $yoloExtra
$yoloUrl = Get-Url "og-yolo"
az containerapp update -n og-backend -g $RG --set-env-vars "YOLO_SERVICE_URL=$yoloUrl" | Out-Null
Assert-Ok "backend yolo url"

Write-Host "[6/6] Web app and CORS..."
New-App "og-web" @("--min-replicas", "1", "--max-replicas", "1", "--cpu", "0.25", "--memory", "0.5Gi")
$webUrl = Get-Url "og-web"
az containerapp update -n og-backend -g $RG --set-env-vars "CORS_ORIGINS=$webUrl" | Out-Null
Assert-Ok "cors update"

Write-Host ""
Write-Host "Web:     $webUrl"
Write-Host "Backend: $backendUrl/health"
Write-Host "YOLO:    $yoloUrl"
Write-Host ""
Write-Host "Next: set repo variable VITE_API_BASE_URL=$backendUrl and run the three deploy workflows"
Write-Host "(see docs/modules/deployment-and-runtime.md). Admin key is in backend\.env (ADMIN_API_KEY)."
