param()

$ErrorActionPreference = "Stop"

$PROJECT_ID = "oceaneyelabs"
$PROJECT_NUMBER = "26506540964"
$REGION = "asia-south1"
$GAR_LOCATION = "asia-south1"
$REPOSITORY = "oceanguard"
$SERVICE_NAME = "oceanguard-api"
$POOL_ID = "github-pool"
$PROVIDER_ID = "github-provider"
$RUNTIME_SA = "oceanguard-runtime@oceaneyelabs.iam.gserviceaccount.com"
$DEPLOYER_SA = "github-deployer@oceaneyelabs.iam.gserviceaccount.com"

$GITHUB_OWNER = Read-Host "Enter GITHUB_OWNER"
$GITHUB_REPO = Read-Host "Enter GITHUB_REPO"

if ([string]::IsNullOrWhiteSpace($GITHUB_OWNER) -or [string]::IsNullOrWhiteSpace($GITHUB_REPO)) {
    throw "GITHUB_OWNER and GITHUB_REPO are required."
}

$repoRef = "$GITHUB_OWNER/$GITHUB_REPO"
$poolName = "projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID"
$providerName = "$poolName/providers/$PROVIDER_ID"
$member = "principalSet://iam.googleapis.com/$poolName/attribute.repository/$repoRef"

function Test-GCloudResource {
    param(
        [Parameter(Mandatory = $true)][string[]]$Command
    )

    $ErrorActionPreference = "SilentlyContinue"
    & gcloud @Command 1>$null 2>$null
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    return $exitCode -eq 0
}

function Ensure-GCloudCommand {
    param(
        [Parameter(Mandatory = $true)][string[]]$Command
    )

    & gcloud @Command
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud command failed: gcloud $($Command -join ' ')"
    }
}

Write-Host "Setting active gcloud project to $PROJECT_ID"
Ensure-GCloudCommand @("config", "set", "project", $PROJECT_ID)

Write-Host "Enabling required Google Cloud APIs"
Ensure-GCloudCommand @(
    "services",
    "enable",
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com"
)

if (-not (Test-GCloudResource @("artifacts", "repositories", "describe", $REPOSITORY, "--location", $GAR_LOCATION))) {
    Write-Host "Creating Artifact Registry repository $REPOSITORY"
    Ensure-GCloudCommand @(
        "artifacts",
        "repositories",
        "create",
        $REPOSITORY,
        "--repository-format=docker",
        "--location",
        $GAR_LOCATION,
        "--description",
        "OceanGuard backend images"
    )
}
else {
    Write-Host "Artifact Registry repository already exists"
}

if (-not (Test-GCloudResource @("iam", "service-accounts", "describe", $RUNTIME_SA))) {
    Write-Host "Creating runtime service account"
    Ensure-GCloudCommand @(
        "iam",
        "service-accounts",
        "create",
        "oceanguard-runtime",
        "--display-name",
        "OceanGuard Runtime"
    )
}
else {
    Write-Host "Runtime service account already exists"
}

if (-not (Test-GCloudResource @("iam", "service-accounts", "describe", $DEPLOYER_SA))) {
    Write-Host "Creating deployer service account"
    Ensure-GCloudCommand @(
        "iam",
        "service-accounts",
        "create",
        "github-deployer",
        "--display-name",
        "GitHub Deployer"
    )
}
else {
    Write-Host "Deployer service account already exists"
}

Write-Host "Granting runtime role to runtime service account"
Ensure-GCloudCommand @(
    "projects",
    "add-iam-policy-binding",
    $PROJECT_ID,
    "--member",
    "serviceAccount:$RUNTIME_SA",
    "--role",
    "roles/aiplatform.user"
)

Write-Host "Granting deploy roles to deployer service account"
foreach ($role in @("roles/run.admin", "roles/artifactregistry.writer")) {
    Ensure-GCloudCommand @(
        "projects",
        "add-iam-policy-binding",
        $PROJECT_ID,
        "--member",
        "serviceAccount:$DEPLOYER_SA",
        "--role",
        $role
    )
}

Write-Host "Allowing deployer service account to use runtime service account"
Ensure-GCloudCommand @(
    "iam",
    "service-accounts",
    "add-iam-policy-binding",
    $RUNTIME_SA,
    "--member",
    "serviceAccount:$DEPLOYER_SA",
    "--role",
    "roles/iam.serviceAccountUser"
)

if (-not (Test-GCloudResource @("iam", "workload-identity-pools", "describe", $POOL_ID, "--location", "global"))) {
    Write-Host "Creating workload identity pool"
    Ensure-GCloudCommand @(
        "iam",
        "workload-identity-pools",
        "create",
        $POOL_ID,
        "--location",
        "global",
        "--display-name",
        "GitHub Actions Pool"
    )
}
else {
    Write-Host "Workload identity pool already exists"
}

$condition = "assertion.repository=='$repoRef' && assertion.ref=='refs/heads/main'"

if (-not (Test-GCloudResource @("iam", "workload-identity-pools", "providers", "describe", $PROVIDER_ID, "--location", "global", "--workload-identity-pool", $POOL_ID))) {
    Write-Host "Creating GitHub OIDC provider"
    Ensure-GCloudCommand @(
        "iam",
        "workload-identity-pools",
        "providers",
        "create-oidc",
        $PROVIDER_ID,
        "--location",
        "global",
        "--workload-identity-pool",
        $POOL_ID,
        "--display-name",
        "GitHub Provider",
        "--issuer-uri",
        "https://token.actions.githubusercontent.com/",
        "--attribute-mapping",
        "google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner,attribute.ref=assertion.ref",
        "--attribute-condition",
        $condition
    )
}
else {
    Write-Host "GitHub OIDC provider already exists"
}

Write-Host "Allowing GitHub repo to impersonate deployer service account"
Ensure-GCloudCommand @(
    "iam",
    "service-accounts",
    "add-iam-policy-binding",
    $DEPLOYER_SA,
    "--member",
    $member,
    "--role",
    "roles/iam.workloadIdentityUser"
)

Write-Host ""
Write-Host "Add these GitHub Actions variables in your repository settings:"
Write-Host "WIF_PROVIDER=$providerName"
Write-Host "WIF_SERVICE_ACCOUNT=$DEPLOYER_SA"
Write-Host ""
Write-Host "GitHub repo -> Settings -> Secrets and variables -> Actions -> Variables"
