# ============================================================
# CEBD 1261 — Session 08 | Terraform Demo
# outputs.tf
#
# After terraform apply, these values are printed to the terminal.
# Copy them directly into GitHub Secrets.
#
# Replaces manually copying values from the az CLI JSON output.
# ============================================================

# ── GitHub Secret: AZURE_CREDENTIALS ─────────────────────────
# The full JSON block that GitHub Actions uses to authenticate.
# This is the exact format expected by azure/login@v1
output "AZURE_CREDENTIALS" {
  description = "Paste this entire JSON block as the AZURE_CREDENTIALS GitHub Secret"
  sensitive   = true
  value = jsonencode({
    clientId       = azuread_application.github_sp.client_id
    clientSecret   = azuread_service_principal_password.github_sp.value
    subscriptionId = data.azurerm_subscription.current.subscription_id
    tenantId       = data.azurerm_subscription.current.tenant_id
  })
}

# ── GitHub Secret: AZURE_SUBSCRIPTION_ID ─────────────────────
output "AZURE_SUBSCRIPTION_ID" {
  description = "Paste as AZURE_SUBSCRIPTION_ID GitHub Secret"
  value       = data.azurerm_subscription.current.subscription_id
}

# ── GitHub Secret: RESOURCE_GROUP ────────────────────────────
output "RESOURCE_GROUP" {
  description = "Paste as RESOURCE_GROUP GitHub Secret"
  value       = azurerm_resource_group.main.name
}
