resource "random_string" "suffix" {
  length  = 5
  numeric = true
  special = false
  upper   = false
}

locals {
  unique_name    = "${var.name_prefix}-${random_string.suffix.result}"
  resource_group = "rg-${local.unique_name}"
  speech_name    = replace(local.unique_name, "-", "")
  speech_key     = azurerm_cognitive_account.speech.primary_access_key
  backend_env    = <<EOT
SPEECH_KEY=${local.speech_key}
SPEECH_REGION=${var.location}
SPEECH_VOICE_NAME=${var.speech_voice_name}
SPEECH_RECOGNITION_LANGUAGE=${var.speech_recognition_language}
PORT=${var.backend_port}
ALLOWED_ORIGIN=${var.frontend_origin}
EOT
}

resource "azurerm_resource_group" "speech" {
  name     = local.resource_group
  location = var.location
  tags     = var.tags
}

resource "azurerm_cognitive_account" "speech" {
  name                = local.speech_name
  location            = azurerm_resource_group.speech.location
  resource_group_name = azurerm_resource_group.speech.name
  kind                = "SpeechServices"
  sku_name            = var.sku_name

  custom_subdomain_name = local.speech_name

  tags = var.tags
}
