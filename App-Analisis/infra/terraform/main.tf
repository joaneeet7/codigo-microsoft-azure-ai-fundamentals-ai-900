resource "random_string" "suffix" {
  length  = 5
  numeric = true
  special = false
  upper   = false
}

locals {
  unique_name    = "${var.name_prefix}-${random_string.suffix.result}"
  resource_group = "rg-${local.unique_name}"
  language_name  = replace(local.unique_name, "-", "")
  language_key   = azurerm_cognitive_account.language.primary_access_key
  language_url   = azurerm_cognitive_account.language.endpoint
  backend_env    = <<EOT
AZURE_LANGUAGE_ENDPOINT=${local.language_url}
AZURE_LANGUAGE_KEY=${local.language_key}
PORT=${var.backend_port}
ALLOWED_ORIGIN=${var.frontend_origin}
EOT
}

resource "azurerm_resource_group" "language" {
  name     = local.resource_group
  location = var.location
  tags     = var.tags
}

resource "azurerm_cognitive_account" "language" {
  name                = local.language_name
  location            = azurerm_resource_group.language.location
  resource_group_name = azurerm_resource_group.language.name
  kind                = "TextAnalytics"
  sku_name            = var.sku_name

  custom_subdomain_name = local.language_name

  tags = var.tags
}
