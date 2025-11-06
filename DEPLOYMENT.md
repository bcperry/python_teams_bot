# Azure Developer CLI (azd) Deployment Guide

This project is configured to deploy to Azure App Service using Azure Developer CLI (azd).

## Prerequisites

1. Install Azure Developer CLI (azd):
   ```powershell
   winget install microsoft.azd
   ```
   Or visit: https://aka.ms/azure-dev/install

2. Install Azure CLI (if not already installed):
   ```powershell
   winget install microsoft.azurecli
   ```

3. You need a Microsoft Entra ID (formerly Azure AD) app registration for your Teams bot:
   - App ID (Client ID)
   - App Secret (Client Secret)
   - Tenant ID

## Setup Steps

### 1. Login to Azure

```powershell
azd auth login
```

### 2. Set Environment Variables

Before running `azd up`, you need to set your bot's Azure AD credentials:

```powershell
# Initialize the environment (first time only)
azd env new <environment-name>

# Set the required bot credentials
azd env set BOT_AAD_APP_CLIENT_ID "your-bot-app-id"
azd env set BOT_AAD_APP_CLIENT_SECRET "your-bot-app-secret"
azd env set BOT_AAD_APP_TENANT_ID "your-tenant-id"
```

Replace `<environment-name>` with a name for your environment (e.g., "dev", "prod").

### 3. Deploy Everything

Run the following command to provision all Azure resources and deploy your application:

```powershell
azd up
```

This single command will:
- Create a resource group
- Provision an App Service Plan
- Create an App Service (Web App)
- Register the Azure Bot Service
- Configure the Teams channel
- Deploy your Python code to the App Service

### 4. Verify Deployment

After deployment completes, `azd` will output the URLs and resource information. You can verify:

```powershell
# Show environment variables
azd env get-values

# Show deployment outputs
azd env get-values
```

## What Gets Deployed

The infrastructure includes:
- **Resource Group**: `rg-<environment-name>`
- **App Service Plan**: Linux-based B1 tier (can be changed)
- **App Service**: Python 3.11 runtime
- **Bot Service**: Free tier (F0)
- **Teams Channel**: Automatically configured

## Configuration Files

- `azure.yaml` - Main azd configuration file
- `infra/azure.bicep` - Main infrastructure as code (subscription-level)
- `infra/resources.bicep` - Resource definitions
- `infra/azure.parameters.json` - Parameter mappings
- `requirements.txt` - Python dependencies

## Environment Variables

The following environment variables are automatically configured in App Service:
- `MicrosoftAppId` - From BOT_AAD_APP_CLIENT_ID
- `MicrosoftAppPassword` - From BOT_AAD_APP_CLIENT_SECRET
- `MicrosoftAppType` - Set to "SingleTenant"
- `MicrosoftAppTenantId` - From BOT_AAD_APP_TENANT_ID

## Useful Commands

```powershell
# Deploy only (after infrastructure is provisioned)
azd deploy

# Provision only (without deploying code)
azd provision

# View logs
azd monitor

# Clean up all resources
azd down
```

## Customization

### Change App Service SKU

To use a different pricing tier:

```powershell
azd env set APP_SERVICE_PLAN_SKU "F1"  # Free tier
# or
azd env set APP_SERVICE_PLAN_SKU "S1"  # Standard tier
```

### Change Azure Region

```powershell
azd env set AZURE_LOCATION "westus2"
```

## Troubleshooting

### View App Service Logs

```powershell
# Via Azure CLI
az webapp log tail --name app-<environment-name> --resource-group rg-<environment-name>
```

### Check Bot Configuration

Make sure your bot's messaging endpoint in the Azure Portal matches:
```
https://app-<environment-name>.azurewebsites.net/api/messages
```

### Update Environment Variables

If you need to update bot credentials:

```powershell
azd env set BOT_AAD_APP_CLIENT_SECRET "new-secret"
azd deploy  # Re-deploy to update the App Service settings
```

## Additional Resources

- [Azure Developer CLI Documentation](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [Bot Framework Documentation](https://docs.microsoft.com/azure/bot-service/)
- [Teams Bot Documentation](https://learn.microsoft.com/microsoftteams/platform/bots/what-are-bots)
