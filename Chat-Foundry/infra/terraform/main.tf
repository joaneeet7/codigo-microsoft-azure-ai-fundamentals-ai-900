resource "random_string" "suffix" {
  length  = 5
  numeric = true
  special = false
  upper   = false
}

locals {
  unique_name      = "${var.name_prefix}-${random_string.suffix.result}"
  foundry_account  = replace(local.unique_name, "-", "")
  resource_group   = "rg-${local.unique_name}"
  project_endpoint = "${trimsuffix(azurerm_cognitive_account.foundry.endpoint, "/")}/api/projects/${azurerm_cognitive_account_project.chat.name}"
}

resource "azurerm_resource_group" "foundry" {
  name     = local.resource_group
  location = var.location
  tags     = var.tags
}

resource "azurerm_cognitive_account" "foundry" {
  name                = local.foundry_account
  location            = azurerm_resource_group.foundry.location
  resource_group_name = azurerm_resource_group.foundry.name
  kind                = "AIServices"
  sku_name            = "S0"

  custom_subdomain_name      = local.foundry_account
  project_management_enabled = true

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_cognitive_account_project" "chat" {
  name                 = var.project_name
  cognitive_account_id = azurerm_cognitive_account.foundry.id
  location             = azurerm_resource_group.foundry.location

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_cognitive_deployment" "chat_model" {
  name                 = var.model_deployment_name
  cognitive_account_id = azurerm_cognitive_account.foundry.id

  sku {
    name     = var.deployment_sku_name
    capacity = var.deployment_capacity
  }

  model {
    format  = "OpenAI"
    name    = var.model_name
    version = var.model_version
  }
}
