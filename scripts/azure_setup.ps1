<#
.SYNOPSIS
    Provision Azure resources for OceanGuard model training.
    Run after: az login --use-device-code
    Subscription: Azure for Students
    Region: centralindia. The student subscription's policy only allows
            malaysiawest, indonesiacentral, centralindia, uaenorth, eastasia;
            centralindia is the one with an unrestricted T4 SKU.
    Budget limit: USD 50 (half the student credit; stop well before $100)
#>
param(
    [string]$Location    = "centralindia",
    [string]$RG          = "oceanguard-rg",
    [string]$Storage     = "oceanguardmldata",
    [string]$Workspace   = "oceanguard-ml",
    [string]$Compute     = "gpu-t4-small",
    [string]$ComputeSku  = "Standard_NC4as_T4_v3",
    [int]   $BudgetUsd   = 50
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-Ok([string]$what) {
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" }
}

Write-Host "=== OceanGuard Azure ML setup ===" -ForegroundColor Cyan
Write-Host "Region       : $Location"
Write-Host "Compute      : $ComputeSku (1x T4 GPU, min=0 nodes -> zero cost when idle)"
Write-Host ""

Write-Host "[0/5] Resource providers..."
foreach ($p in 'Microsoft.MachineLearningServices','Microsoft.Storage','Microsoft.Compute',
               'Microsoft.Insights','Microsoft.KeyVault','Microsoft.ContainerRegistry',
               'Microsoft.OperationalInsights') {
    az provider register --namespace $p | Out-Null
}
foreach ($p in 'Microsoft.MachineLearningServices','Microsoft.Insights','Microsoft.KeyVault') {
    do {
        $state = az provider show --namespace $p --query registrationState -o tsv
        if ($state -ne 'Registered') { Start-Sleep -Seconds 10 }
    } while ($state -ne 'Registered')
}

Write-Host "[1/5] az ml extension..."
az extension show --name ml --query name -o tsv 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { az extension add --name ml --yes; Assert-Ok "az extension add" }

Write-Host "[2/5] Resource group '$RG'..."
az group show --name $RG --query name -o tsv 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { az group create --name $RG --location $Location | Out-Null; Assert-Ok "group create" }

Write-Host "[3/5] Storage '$Storage'..."
az storage account show --name $Storage --resource-group $RG --query name -o tsv 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    az storage account create --name $Storage --resource-group $RG --location $Location `
        --sku Standard_LRS --allow-blob-public-access false | Out-Null
    Assert-Ok "storage create"
}
$storageId = az storage account show --name $Storage --resource-group $RG --query id -o tsv
Assert-Ok "storage show"

Write-Host "[4/5] Workspace '$Workspace'..."
az ml workspace show --name $Workspace --resource-group $RG --query name -o tsv 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    az ml workspace create --name $Workspace --resource-group $RG --location $Location `
        --storage-account $storageId | Out-Null
    Assert-Ok "workspace create"
}

Write-Host "[5/5] Compute '$Compute' ($ComputeSku)..."
az ml compute show --name $Compute --workspace-name $Workspace --resource-group $RG --query name -o tsv 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    az ml compute create --name $Compute --type AmlCompute `
        --workspace-name $Workspace --resource-group $RG `
        --size $ComputeSku --min-instances 0 --max-instances 1 `
        --idle-time-before-scale-down 300 | Out-Null
    Assert-Ok "compute create"
}

Write-Host ""
Write-Host "=== Done. ===" -ForegroundColor Green
Write-Host "Set a budget alert: https://portal.azure.com/#blade/Microsoft_Azure_CostManagement/BudgetBlade"
