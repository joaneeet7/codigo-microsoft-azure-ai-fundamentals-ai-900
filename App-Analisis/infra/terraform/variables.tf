variable "subscription_id" {
  description = "Azure subscription ID where the text analysis resources will be created."
  type        = string
}

variable "location" {
  description = "Azure region for Azure AI Language."
  type        = string
  default     = "eastus2"
}

variable "name_prefix" {
  description = "Short lowercase prefix for resource names."
  type        = string
  default     = "txtdemo"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,16}$", var.name_prefix))
    error_message = "name_prefix must start with a lowercase letter and contain 3-17 lowercase letters, numbers, or hyphens."
  }
}

variable "sku_name" {
  description = "Azure AI Language SKU. Use F0 for demo/free tier when available, or S for standard."
  type        = string
  default     = "F0"
}

variable "backend_port" {
  description = "Local backend port."
  type        = number
  default     = 3010
}

variable "frontend_origin" {
  description = "Allowed frontend origin for CORS."
  type        = string
  default     = "http://localhost:5174"
}

variable "tags" {
  description = "Tags applied to Azure resources."
  type        = map(string)
  default = {
    app = "app-analisis-texto"
    env = "demo"
  }
}
