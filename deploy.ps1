# Azure Container Apps Deployment Script
# Prerequisites: az cli installed + logged in (`az login`)
# Run: .\deploy.ps1

$RG         = "rg-fdrates"
$LOCATION   = "eastus"
$ACR_NAME   = "fdratescr"          # must be globally unique, lowercase
$IMAGE      = "fdrates-app"
$ENV_NAME   = "fdrates-env"
$APP_NAME   = "fdrates-app"

Write-Host "=== 1. Create Resource Group ===" -ForegroundColor Cyan
az group create --name $RG --location $LOCATION

Write-Host "=== 2. Create Azure Container Registry ===" -ForegroundColor Cyan
az acr create --resource-group $RG --name $ACR_NAME --sku Basic --admin-enabled true

Write-Host "=== 3. Build & Push Docker Image to ACR ===" -ForegroundColor Cyan
az acr build --registry $ACR_NAME --image "${IMAGE}:latest" .

Write-Host "=== 4. Get ACR credentials ===" -ForegroundColor Cyan
$ACR_SERVER   = az acr show --name $ACR_NAME --query loginServer -o tsv
$ACR_USER     = az acr credential show --name $ACR_NAME --query username -o tsv
$ACR_PASSWORD = az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv

Write-Host "=== 5. Create Container Apps Environment ===" -ForegroundColor Cyan
az containerapp env create `
  --name $ENV_NAME `
  --resource-group $RG `
  --location $LOCATION

Write-Host "=== 6. Deploy Container App ===" -ForegroundColor Cyan
az containerapp create `
  --name $APP_NAME `
  --resource-group $RG `
  --environment $ENV_NAME `
  --image "${ACR_SERVER}/${IMAGE}:latest" `
  --registry-server $ACR_SERVER `
  --registry-username $ACR_USER `
  --registry-password $ACR_PASSWORD `
  --target-port 8501 `
  --ingress external `
  --cpu 1.0 `
  --memory 2.0Gi `
  --min-replicas 0 `
  --max-replicas 1

Write-Host "=== Done! Your app URL: ===" -ForegroundColor Green
az containerapp show --name $APP_NAME --resource-group $RG --query properties.configuration.ingress.fqdn -o tsv
