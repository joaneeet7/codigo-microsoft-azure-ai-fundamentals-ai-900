variable "subscription_id" {
  description = "Azure subscription ID where Foundry resources will be created."
  type        = string
}

variable "location" {
  description = "Azure region for the Foundry resource."
  type        = string
  default     = "eastus2"
}

variable "name_prefix" {
  description = "Short lowercase prefix for resource names."
  type        = string
  default     = "fdchat"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,16}$", var.name_prefix))
    error_message = "name_prefix must start with a lowercase letter and contain 3-17 lowercase letters, numbers, or hyphens."
  }
}

variable "project_name" {
  description = "Foundry project name."
  type        = string
  default     = "chat-demo"
}

variable "model_deployment_name" {
  description = "Deployment name used by the chat backend."
  type        = string
  default     = "gpt-4o"
}

variable "model_name" {
  description = "OpenAI model name to deploy."
  type        = string
  default     = "gpt-4o"
}

variable "model_version" {
  description = "OpenAI model version to deploy."
  type        = string
  default     = "2024-11-20"
}

variable "deployment_sku_name" {
  description = "SKU for the model deployment."
  type        = string
  default     = "GlobalStandard"
}

variable "deployment_capacity" {
  description = "Capacity for the model deployment."
  type        = number
  default     = 1
}

variable "tags" {
  description = "Tags applied to Azure resources."
  type        = map(string)
  default = {
    app = "foundry-chat-demo"
    env = "demo"
  }
}
