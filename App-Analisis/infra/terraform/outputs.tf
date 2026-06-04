output "resource_group_name" {
  description = "Azure resource group created for this demo."
  value       = azurerm_resource_group.language.name
}

output "language_account_name" {
  description = "Azure AI Language account name."
  value       = azurerm_cognitive_account.language.name
}

output "azure_language_endpoint" {
  description = "Value to use as AZURE_LANGUAGE_ENDPOINT."
  value       = azurerm_cognitive_account.language.endpoint
}

output "azure_language_key" {
  description = "Value to use as AZURE_LANGUAGE_KEY."
  value       = azurerm_cognitive_account.language.primary_access_key
  sensitive   = true
}

output "backend_env" {
  description = "Copy this value into backend/.env."
  value       = local.backend_env
  sensitive   = true
}
