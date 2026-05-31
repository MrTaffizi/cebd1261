# ============================================================
# CEBD 1261 — Session 08 | Terraform Demo
# main.tf
#
# What this replaces (manual az CLI commands):
#
#   az group create \
#     --name cebd1261-rg \
#     --location eastus
#
#   az ad sp create-for-rbac \
#     --name cebd1261-github-sp \
#     --role Contributor \
#     --scopes /subscriptions/.../resourceGroups/cebd1261-rg \
#     --sdk-auth
#
# With Terraform, we declare WHAT we want.
# Terraform figures out HOW to create it.
# ============================================================

# ── Providers ─────────────────────────────────────────────────
# Tell Terraform which cloud APIs to use.
# azurerm = Azure Resource Manager (infrastructure)
# azuread = Azure Active Directory (identities)
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
  }
}

provider "azurerm" {
  features {}
}

provider "azuread" {}

# ── Variables ─────────────────────────────────────────────────
# Values you can change without touching the main code.
variable "resource_group_name" {
  default = "cebd1261-rg"
}

variable "location" {
  default = "eastus"
}

variable "sp_name" {
  default = "cebd1261-github-sp"
}

# ── Data Sources ───────────────────────────────────────────────
# Read existing data from Azure — we need the subscription ID
# to scope the role assignment.
data "azurerm_subscription" "current" {}

# ── Resource 1: Resource Group ────────────────────────────────
# Replaces: az group create --name cebd1261-rg --location eastus
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

# ── Resource 2: Azure AD Application ─────────────────────────
# An Application is the identity object in Azure AD.
# The Service Principal is created from it in the next step.
# Together they replace: az ad sp create-for-rbac
resource "azuread_application" "github_sp" {
  display_name = var.sp_name
}

# ── Resource 3: Service Principal ─────────────────────────────
# The Service Principal is the actual identity that
# GitHub Actions authenticates as.
resource "azuread_service_principal" "github_sp" {
  client_id = azuread_application.github_sp.client_id
}

# ── Resource 4: Service Principal Password ────────────────────
# Generates the client_secret — equivalent to the
# clientSecret value in the AZURE_CREDENTIALS JSON.
resource "azuread_service_principal_password" "github_sp" {
  service_principal_id = azuread_service_principal.github_sp.id
}

# ── Resource 5: Role Assignment ───────────────────────────────
# Grants the Service Principal Contributor access to
# the Resource Group — so it can create/delete ACI groups.
# Replaces: az role assignment create --role Contributor
resource "azurerm_role_assignment" "github_sp_contributor" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.github_sp.object_id
}
