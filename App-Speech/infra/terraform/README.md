# Terraform - Azure Speech

Esta infraestructura crea:

- Resource Group
- Azure Speech Services
- Output con las variables listas para `backend/.env`

## Manual

```bash
cd infra/terraform
copy terraform.tfvars.example terraform.tfvars
terraform init -upgrade
terraform plan -out main.tfplan
terraform apply main.tfplan
terraform output -raw backend_env
```

## Limpiar

```bash
terraform plan -destroy -out main.destroy.tfplan
terraform apply main.destroy.tfplan
```
