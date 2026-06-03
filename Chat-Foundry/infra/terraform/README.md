# Terraform para Microsoft Foundry

Esta carpeta crea:

- Resource Group
- Microsoft Foundry resource usando `azurerm_cognitive_account`
- Foundry Project usando `azurerm_cognitive_account_project`
- Deployment de modelo OpenAI
- Outputs para copiar `PROJECT_ENDPOINT` y `MODEL_DEPLOYMENT_NAME`

## Ejecutar

1. Entra a la carpeta:

```bash
cd infra/terraform
```

2. Inicia sesion en Azure:

```bash
az login
az account set --subscription "<subscription-id>"
```

3. Crea tu archivo de variables:

```bash
copy terraform.tfvars.example terraform.tfvars
```

4. Edita `terraform.tfvars` y cambia:

```hcl
subscription_id = "<tu-subscription-id>"
location        = "eastus2"
```

5. Inicializa Terraform:

```bash
terraform init -upgrade
```

6. Revisa el plan:

```bash
terraform plan -out main.tfplan
```

7. Aplica:

```bash
terraform apply main.tfplan
```

8. Copia los valores para el backend:

```bash
terraform output backend_env
```

Pega ese bloque en `backend/.env`.

## Limpiar recursos

```bash
terraform plan -destroy -out main.destroy.tfplan
terraform apply main.destroy.tfplan
```
