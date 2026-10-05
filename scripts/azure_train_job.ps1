<#
.SYNOPSIS
    Submit the xView3 fine-tune (with HRSID replay) to Azure ML on the CPU cluster.

    Prerequisites (all in blob container 'xview3', datastore 'xview3_store'):
      train_crops/<scene>_<k>/VH_dB.tif + train_crops/train_crop_labels.csv
      hrsid/train|test/{images,labels}
      crop/590dd08f71056cacv/VH_dB.tif + labels/crop_labels.csv   (held-out eval scene)
    Model asset yolo11n-best:2 (the current best.pt).

    The job scores the base and fine-tuned weights on the same held-out xView3
    scene and the same HRSID test images, and writes summary.json with an
    'accept' flag. Nothing is deployed automatically.
#>
param(
    [string]$RG        = "oceanguard-rg",
    [string]$Workspace = "oceanguard-ml",
    [string]$Compute   = "cpu-eval",
    [int]   $Epochs    = 20,
    [int]   $Replay    = 250,
    [double]$Lr0       = 0.002,
    [int]   $Freeze    = 10,
    [string]$Name      = "oceanguard-finetune-xview3"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Assert-Ok([string]$what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" } }

$mlSrc = (Resolve-Path (Join-Path $PSScriptRoot "..\ml")).Path
$stage = Join-Path $env:TEMP "oceanguard_code_train"
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory $stage | Out-Null
foreach ($pkg in "evaluation", "pipeline", "training") {
    Copy-Item (Join-Path $mlSrc $pkg) (Join-Path $stage $pkg) -Recurse
    Get-ChildItem (Join-Path $stage $pkg) -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
}
$mlDir = $stage.Replace('\', '/')

$jobYaml = @'
$schema: https://azuremlschemas.azureedge.net/latest/commandJob.schema.json
display_name: __NAME__
compute: azureml:__COMPUTE__
environment:
  image: mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04
  conda_file:
    name: oceanguard-train
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
  train_crops:
    type: uri_folder
    path: azureml://datastores/xview3_store/paths/train_crops/
  hrsid:
    type: uri_folder
    path: azureml://datastores/xview3_store/paths/hrsid/
  eval_scenes:
    type: uri_folder
    path: azureml://datastores/xview3_store/paths/crop/
  eval_labels:
    type: uri_file
    path: azureml://datastores/xview3_store/paths/labels/crop_labels.csv
  model_weights:
    type: uri_file
    path: azureml:yolo11n-best:2
outputs:
  results:
    type: uri_folder
code: __CODE__
command: >-
  pip uninstall -y opencv-python &&
  pip install --force-reinstall --no-deps opencv-python-headless &&
  python -m training.finetune_xview3
  --train-crops ${{inputs.train_crops}}
  --train-labels ${{inputs.train_crops}}/train_crop_labels.csv
  --hrsid ${{inputs.hrsid}}
  --eval-scenes ${{inputs.eval_scenes}}
  --eval-labels ${{inputs.eval_labels}}
  --base-model ${{inputs.model_weights}}
  --out ${{outputs.results}}
  --epochs __EPOCHS__
  --hrsid-replay __REPLAY__
  --lr0 __LR0__
  --freeze __FREEZE__
'@
$jobYaml = $jobYaml.Replace("__COMPUTE__", $Compute).Replace("__CODE__", $mlDir).Replace("__EPOCHS__", "$Epochs").
    Replace("__REPLAY__", "$Replay").Replace("__LR0__", $Lr0.ToString([cultureinfo]::InvariantCulture)).
    Replace("__FREEZE__", "$Freeze").Replace("__NAME__", $Name)
$jobFile = Join-Path $env:TEMP "oceanguard_train_job.yml"
$jobYaml | Set-Content $jobFile -Encoding UTF8

$job = az ml job create --file $jobFile -w $Workspace -g $RG -o json | ConvertFrom-Json; Assert-Ok "job create"
Remove-Item $jobFile -ErrorAction SilentlyContinue
Write-Host "Job: $($job.name)"
Write-Host "Download: az ml job download -n $($job.name) -w $Workspace -g $RG --output-name results --download-path D:\Main\OceanGuard\train_out"
