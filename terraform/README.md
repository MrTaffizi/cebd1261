# CEBD 1261 — Session 08 | Take-Home Assignment
## Terraform: Infrastructure as Code

## What this does

Replaces the manual `az` CLI setup commands with Infrastructure as Code.

| Manual CLI command | Terraform resource |
|---|---|
| `az group create` | `azurerm_resource_group` |
| `az ad sp create-for-rbac` | `azuread_application` + `azuread_service_principal` |
| `az role assignment create` | `azurerm_role_assignment` |

---

## ⚠️ Important — Where to Run Terraform

**Do NOT run Terraform from your local machine for this demo.**

Terraform requires Azure AD permissions to create Service Principals and App
Registrations. Concordia university accounts do not have these permissions —
the same restriction we hit with the `az ad sp create-for-rbac` CLI command.

**Use your personal Microsoft account in one of these two ways:**

---

### Option A — Azure Cloud Shell (recommended, no install needed)

Terraform is pre-installed in Azure Cloud Shell.

1. Go to portal.azure.com and sign in with your **personal Microsoft account**
2. Click the **>_** icon in the top navigation bar → choose **Bash**
3. Click the **Upload** button (📁 icon) in the Cloud Shell toolbar
4. Upload both `main.tf` and `outputs.tf`
5. Run the commands below

---

### Option B — Local machine (requires installation)

If you prefer to run Terraform locally, install it first:

**Windows:**
```powershell
# Using winget (built into Windows 11)
winget install HashiCorp.Terraform

# Or using Chocolatey
choco install terraform
```

**macOS:**
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

**Verify installation:**
```bash
terraform version
```

Then login to Azure with your **personal account** before running:
```bash
az login
az account set --subscription YOUR_PERSONAL_SUBSCRIPTION_ID
```

---

## Commands (run in order)

```bash
# 1. Initialize — downloads the Azure provider plugins (~30 seconds)
terraform init

# 2. Preview — shows what will be created (nothing runs yet)
#    You should see: 5 resources to add
terraform plan

# 3. Apply — creates all resources in Azure (~30 seconds)
#    Type 'yes' when prompted
terraform apply

# 4. Get your GitHub Secrets values
terraform output AZURE_SUBSCRIPTION_ID
terraform output RESOURCE_GROUP

# AZURE_CREDENTIALS is sensitive — use -raw to print the JSON:
terraform output -raw AZURE_CREDENTIALS

# 5. Destroy everything when done (after M4 demo)
#    Type 'yes' when prompted
terraform destroy
```

---

## Expected output from terraform plan

```
Plan: 5 to add, 0 to change, 0 to destroy.

  + azurerm_resource_group.main
  + azuread_application.github_sp
  + azuread_service_principal.github_sp
  + azuread_service_principal_password.github_sp
  + azurerm_role_assignment.github_sp_contributor
```

---

## Files

- `main.tf` — declares all Azure resources
- `outputs.tf` — prints the values needed for GitHub Secrets

---

## After terraform apply

Copy these values into GitHub Secrets:

| GitHub Secret | Terraform command |
|---|---|
| `AZURE_CREDENTIALS` | `terraform output -raw AZURE_CREDENTIALS` |
| `AZURE_SUBSCRIPTION_ID` | `terraform output AZURE_SUBSCRIPTION_ID` |
| `RESOURCE_GROUP` | `terraform output RESOURCE_GROUP` |
