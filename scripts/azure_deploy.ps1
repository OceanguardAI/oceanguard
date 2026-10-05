<#
.SYNOPSIS
    Deploy OceanGuard (backend API + YOLO service + web UI) to Azure Container Apps.

    - Images are built in the cloud with 'az acr build' (no local Docker engine).
    - Secrets are read from backend\.env and passed as Container Apps secrets;
      nothing is printed. ADMIN_API_KEY is generated into backend\.env if empty.
    - The YOLO service (torch image, built in ACR) scales to zero between checks;
      the backend gets its URL as YOLO_SERVICE_URL.
    - Region must be one the student policy allows (centralindia).
#>
param(
    [string]$RG       = "oceanguard-rg",
    [string]$Location = "centralindia",
    [string]$Acr      = "ogacr901ad",
    [string]$EnvName  = "og-env",
    [string]$Tag      = (Get-Date -Format "yyyyMMddHHmm")
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

Write-Host "[1/7] Providers and extension..."
foreach ($p in "Microsoft.App", "Microsoft.ContainerRegistry", "Microsoft.OperationalInsights") {
    do { $s = az provider show -n $p --query registrationState -o tsv; if ($s -ne "Registered") { az provider register -n $p | Out-Null; Start-Sleep 10 } } while ($s -ne "Registered")
}
az extension show --name containerapp --query name -o tsv 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { az extension add --name containerapp --yes | Out-Null; Assert-Ok "extension" }

Write-Host "[2/7] Container registry '$Acr'..."
$have = az acr show -n $Acr -g $RG --query name -o tsv 2>$null
if (-not $have) { az acr create -n $Acr -g $RG -l $Location --sku Basic --admin-enabled true | Out-Null; Assert-Ok "acr create" }
az acr update -n $Acr --admin-enabled true | Out-Null
$server = az acr show -n $Acr --query loginServer -o tsv
$acrUser = az acr credential show -n $Acr --query username -o tsv
$acrPass = az acr credential show -n $Acr --query "passwords[0].value" -o tsv

Write-Host "[3/7] Container Apps environment '$EnvName'..."
$have = az containerapp env show -n $EnvName -g $RG --query name -o tsv 2>$null
if (-not $have) { az containerapp env create -n $EnvName -g $RG -l $Location | Out-Null; Assert-Ok "env create" }

Write-Host "[4/7] Backend image + app..."
az acr build -r $Acr -t "og-backend:$Tag" -f (Join-Path $repo "backend\Dockerfile") (Join-Path $repo "backend") | Out-Null
Assert-Ok "backend build"

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

$exists = az containerapp show -n og-backend -g $RG --query name -o tsv 2>$null
if (-not $exists) {
    az containerapp create -n og-backend -g $RG --environment $EnvName --image "$server/og-backend:$Tag" `
        --registry-server $server --registry-username $acrUser --registry-password $acrPass `
        --target-port 8080 --ingress external --min-replicas 1 --max-replicas 1 --cpu 1.0 --memory 2.0Gi `
        --secrets $secrets --env-vars $envVars | Out-Null
    Assert-Ok "backend create"
} else {
    az containerapp update -n og-backend -g $RG --image "$server/og-backend:$Tag" | Out-Null
    Assert-Ok "backend update"
}
$backendUrl = "https://" + (az containerapp show -n og-backend -g $RG --query properties.configuration.ingress.fqdn -o tsv)

Write-Host "[5/7] YOLO service (scale-to-zero)..."
az acr build -r $Acr -t "og-yolo:$Tag" -f (Join-Path $repo "yolo-service\Dockerfile") (Join-Path $repo "yolo-service") | Out-Null
Assert-Ok "yolo build"
$exists = az containerapp show -n og-yolo -g $RG --query name -o tsv 2>$null
if (-not $exists) {
    $yoloArgs = @("--env-vars", "PORT=8080") + $sentinelVars
    if ($sentinelSecrets) { $yoloArgs += @("--secrets") + $sentinelSecrets }
    az containerapp create -n og-yolo -g $RG --environment $EnvName --image "$server/og-yolo:$Tag" `
        --registry-server $server --registry-username $acrUser --registry-password $acrPass `
        --target-port 8080 --ingress external --min-replicas 0 --max-replicas 1 --cpu 2.0 --memory 4.0Gi @yoloArgs | Out-Null
    Assert-Ok "yolo create"
} else {
    az containerapp update -n og-yolo -g $RG --image "$server/og-yolo:$Tag" | Out-Null
    Assert-Ok "yolo update"
}
$yoloUrl = "https://" + (az containerapp show -n og-yolo -g $RG --query properties.configuration.ingress.fqdn -o tsv)
az containerapp update -n og-backend -g $RG --set-env-vars "YOLO_SERVICE_URL=$yoloUrl" | Out-Null
Assert-Ok "backend yolo url"

Write-Host "[6/7] Web image + app (API = $backendUrl)..."
az acr build -r $Acr -t "og-web:$Tag" -f (Join-Path $repo "frontend\Dockerfile") `
    --build-arg "VITE_API_BASE_URL=$backendUrl" (Join-Path $repo "frontend") | Out-Null
Assert-Ok "web build"
$exists = az containerapp show -n og-web -g $RG --query name -o tsv 2>$null
if (-not $exists) {
    az containerapp create -n og-web -g $RG --environment $EnvName --image "$server/og-web:$Tag" `
        --registry-server $server --registry-username $acrUser --registry-password $acrPass `
        --target-port 8080 --ingress external --min-replicas 1 --max-replicas 1 --cpu 0.25 --memory 0.5Gi | Out-Null
    Assert-Ok "web create"
} else {
    az containerapp update -n og-web -g $RG --image "$server/og-web:$Tag" | Out-Null
    Assert-Ok "web update"
}
$webUrl = "https://" + (az containerapp show -n og-web -g $RG --query properties.configuration.ingress.fqdn -o tsv)

Write-Host "[7/7] Backend CORS -> $webUrl"
az containerapp update -n og-backend -g $RG --set-env-vars "CORS_ORIGINS=$webUrl" | Out-Null
Assert-Ok "cors update"

Write-Host ""
Write-Host "Web:     $webUrl"
Write-Host "Backend: $backendUrl/health"
Write-Host "Admin key saved in backend\.env (ADMIN_API_KEY); write routes need header X-API-Key."
