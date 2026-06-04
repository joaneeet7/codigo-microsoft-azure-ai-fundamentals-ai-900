# Terraform - Azure AI Language

Esta infraestructura crea:

- Resource Group
- Azure AI Language / Text Analytics
- Output con las variables listas para `backend/.env`

## Ejecucion manual

```bash
cd infra/terraform
copy terraform.tfvars.example terraform.tfvars
```

Edita `terraform.tfvars` con tu `subscription_id` y ejecuta:

```bash
az login
terraform init -upgrade
terraform plan -out main.tfplan
terraform apply main.tfplan
terraform output -raw backend_env
```

Copia el resultado en `backend/.env`.

## Limpiar recursos

```bash
terraform plan -destroy -out main.destroy.tfplan
terraform apply main.destroy.tfplan
```
