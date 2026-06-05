output "resource_group_name" {
  description = "Azure resource group created for this demo."
  value       = azurerm_resource_group.speech.name
}

output "speech_account_name" {
  description = "Azure Speech account name."
  value       = azurerm_cognitive_account.speech.name
}

output "speech_region" {
  description = "Value to use as SPEECH_REGION."
  value       = var.location
}

output "speech_key" {
  description = "Value to use as SPEECH_KEY."
  value       = azurerm_cognitive_account.speech.primary_access_key
  sensitive   = true
}

output "backend_env" {
  description = "Copy this value into backend/.env."
  value       = local.backend_env
  sensitive   = true
}
