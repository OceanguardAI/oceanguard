param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Value
)

$ErrorActionPreference = "Stop"
$PROJECT_ID = "oceaneyelabs"
$RUNTIME_SA = "oceanguard-runtime@oceaneyelabs.iam.gserviceaccount.com"

function Ensure-GCloudCommand {
    param(
        [Parameter(Mandatory = $true)][string[]]$Command
    )

    & gcloud @Command
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud command failed: gcloud $($Command -join ' ')"
    }
}

& gcloud secrets describe $Name --project $PROJECT_ID 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating secret $Name"
    Ensure-GCloudCommand @(
        "secrets",
        "create",
        $Name,
        "--replication-policy=automatic",
        "--project",
        $PROJECT_ID
    )
}
else {
    Write-Host "Secret $Name already exists"
}

$tmp = [System.IO.Path]::GetTempFileName()
try {
    Set-Content -LiteralPath $tmp -Value $Value -Encoding UTF8 -NoNewline
    Ensure-GCloudCommand @(
        "secrets",
        "versions",
        "add",
        $Name,
        "--data-file",
        $tmp,
        "--project",
        $PROJECT_ID
    )
}
finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}

Write-Host "Granting Secret Manager access to runtime service account"
Ensure-GCloudCommand @(
    "secrets",
    "add-iam-policy-binding",
    $Name,
    "--member",
    "serviceAccount:$RUNTIME_SA",
    "--role",
    "roles/secretmanager.secretAccessor",
    "--project",
    $PROJECT_ID
)
