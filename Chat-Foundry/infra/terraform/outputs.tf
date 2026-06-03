output "resource_group_name" {
  description = "Azure resource group created for the demo."
  value       = azurerm_resource_group.foundry.name
}

output "foundry_account_name" {
  description = "Microsoft Foundry account name."
  value       = azurerm_cognitive_account.foundry.name
}

output "foundry_project_name" {
  description = "Microsoft Foundry project name."
  value       = azurerm_cognitive_account_project.chat.name
}

output "foundry_account_endpoint" {
  description = "Base endpoint for the Foundry account."
  value       = azurerm_cognitive_account.foundry.endpoint
}

output "project_endpoint" {
  description = "Value to copy into backend/.env as PROJECT_ENDPOINT."
  value       = local.project_endpoint
}

output "model_deployment_name" {
  description = "Value to copy into backend/.env as MODEL_DEPLOYMENT_NAME."
  value       = azurerm_cognitive_deployment.chat_model.name
}

output "backend_env" {
  description = "Environment values for backend/.env."
  value       = <<EOT
PROJECT_ENDPOINT=${local.project_endpoint}
MODEL_DEPLOYMENT_NAME=${azurerm_cognitive_deployment.chat_model.name}
PORT=3001
ALLOWED_ORIGIN=http://localhost:5173
EOT
}
