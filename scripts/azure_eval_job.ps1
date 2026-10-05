<#
.SYNOPSIS
    Submit the baseline Sentinel-1 evaluation (run A0) to Azure ML on the CPU cluster.

    Expects the xView3 validation scenes (<scene_id>.tar.gz) already uploaded to
    blob container 'xview3' under val/, and the filtered label CSV under labels/.
    Nothing is downloaded from xView3 inside Azure (the xView3 licence forbids it).

.NOTES
    Evaluation is inference only, so the CPU cluster is enough. The student
    subscription has no GPU quota. Cluster scales to 0 nodes when idle.
#>
param(
    [string]$RG         = "oceanguard-rg",
    [string]$Workspace  = "oceanguard-ml",
    [string]$Compute    = "cpu-eval",
    [string]$Storage    = "oceanguardmldata",
    [string]$Container  = "xview3",
    [string]$ModelPath  = ".\ml\models\best.pt",
    [string]$LabelsPath = "D:\Main\OceanGuard\crop\crop_labels.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Assert-Ok([string]$what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" } }

foreach ($f in $ModelPath, $LabelsPath) { if (-not (Test-Path $f)) { throw "Missing $f" } }

$key = az storage account keys list -n $Storage -g $RG --query "[0].value" -o tsv; Assert-Ok "storage key"

Write-Host "[1/4] Uploading labels to blob..."
az storage blob upload --account-name $Storage --account-key $key --container-name $Container `
    --name "labels/crop_labels.csv" --file $LabelsPath --overwrite --no-progress | Out-Null
Assert-Ok "labels upload"

Write-Host "[2/4] Registering datastore and model..."
$dsFile = Join-Path $env:TEMP "xview3_ds.yml"
@"
`$schema: https://azuremlschemas.azureedge.net/latest/azureBlob.schema.json
name: xview3_store
type: azure_blob
account_name: $Storage
container_name: $Container
credentials:
  account_key: $key
"@ | Set-Content $dsFile -Encoding UTF8
az ml datastore create --file $dsFile -w $Workspace -g $RG | Out-Null; Assert-Ok "datastore"
Remove-Item $dsFile -ErrorAction SilentlyContinue

$have = az ml data show --name yolo11n-best --version 2 -w $Workspace -g $RG --query name -o tsv 2>$null
if (-not $have) {
    az ml data create --name yolo11n-best --version 2 --path $ModelPath --type uri_file `
        -w $Workspace -g $RG | Out-Null; Assert-Ok "model asset"
}

Write-Host "[3/4] Building job..."
$jobYaml = @'
$schema: https://azuremlschemas.azureedge.net/latest/commandJob.schema.json
display_name: oceanguard-baseline-eval-A0
description: Size-binned recall of the current best.pt on xView3 validation scenes (CPU inference).
compute: azureml:__COMPUTE__
environment:
  image: mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04
  conda_file:
    name: oceanguard-eval
    channels: [conda-forge]
    dependencies:
      - python=3.11
      - pip
      - pip:
        - --extra-index-url https://download.pytorch.org/whl/cpu
        - torch
        - torchvision
        - ultralytics>=8.2
        - rasterio>=1.3
        - shapely>=2.0
        - pyproj>=3.5
        - numpy>=1.26
        - pillow>=10.0
inputs:
  scenes:
    type: uri_folder
    path: azureml://datastores/xview3_store/paths/crop/
  labels:
    type: uri_file
    path: azureml://datastores/xview3_store/paths/labels/crop_labels.csv
  model_weights:
    type: uri_file
    path: azureml:yolo11n-best:2
outputs:
  results:
    type: uri_folder
code: ./ml
command: >-
  pip uninstall -y opencv-python &&
  pip install --force-reinstall --no-deps opencv-python-headless &&
  python -m evaluation.detection_by_size
  --scenes-dir ${{inputs.scenes}}
  --labels ${{inputs.labels}}
  --model ${{inputs.model_weights}}
  --out ${{outputs.results}}/eval_report.json
  --conf 0.25
'@
$mlSrc = (Resolve-Path (Join-Path $PSScriptRoot "..\ml")).Path
$stage = Join-Path $env:TEMP "oceanguard_code"
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory $stage | Out-Null
foreach ($pkg in "evaluation", "pipeline") {
    Copy-Item (Join-Path $mlSrc $pkg) (Join-Path $stage $pkg) -Recurse
    Get-ChildItem (Join-Path $stage $pkg) -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
}
$mlDir = $stage.Replace('\', '/')
$jobYaml = $jobYaml.Replace("__COMPUTE__", $Compute).Replace("code: ./ml", "code: $mlDir")
$jobFile = Join-Path $env:TEMP "oceanguard_eval_job.yml"
$jobYaml | Set-Content $jobFile -Encoding UTF8

Write-Host "[4/4] Submitting job..."
$job = az ml job create --file $jobFile -w $Workspace -g $RG -o json | ConvertFrom-Json; Assert-Ok "job create"
Remove-Item $jobFile -ErrorAction SilentlyContinue
Write-Host "Job: $($job.name)"
Write-Host "Stream:   az ml job stream -n $($job.name) -w $Workspace -g $RG"
Write-Host "Download: az ml job download -n $($job.name) -w $Workspace -g $RG --output-name results --download-path .\ml\outputs"
