targetScope = 'subscription'

@maxLength(20)
@minLength(4)
@description('Used to generate names for all resources in this file')
param resourceBaseName string

@description('Required when create Azure Bot service')
param botAadAppClientId string

@secure()
@description('Required when create Azure Bot service')
param botAadAppClientSecret string

@minLength(36)
@maxLength(36)
@description('Tenant that owns the Bot AAD app')
param botAadAppTenantId string

@maxLength(42)
param botDisplayName string

param location string = 'eastus'

param botServiceName string = resourceBaseName
param botServiceSku string = 'F0'

@description('App Service SKU')
param appServicePlanSku string = 'B1'

@secure()
@description('Azure OpenAI API Key')
param azureOpenAiApiKey string

@description('Azure OpenAI Endpoint')
param azureOpenAiEndpoint string

@description('Azure OpenAI Model Deployment Name')
param azureOpenAiModel string

// Variables
var resourceGroupName = 'rg-${resourceBaseName}'
var appServicePlanName = 'plan-${resourceBaseName}'
var appServiceName = 'app-${resourceBaseName}'
var appServiceDomainSuffix = environment().suffixes.storage == 'core.usgovcloudapi.net' ? 'azurewebsites.us' : 'azurewebsites.net'
var botAppDomain = '${appServiceName}.${appServiceDomainSuffix}'

// Resource Group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
}

// Deploy resources into the resource group
module resources 'resources.bicep' = {
  name: 'resources-deployment'
  scope: resourceGroup
  params: {
    location: location
    resourceBaseName: resourceBaseName
    appServicePlanName: appServicePlanName
    appServicePlanSku: appServicePlanSku
    appServiceName: appServiceName
    botServiceName: botServiceName
    botServiceSku: botServiceSku
    botDisplayName: botDisplayName
    botAadAppClientId: botAadAppClientId
    botAadAppClientSecret: botAadAppClientSecret
    botAadAppTenantId: botAadAppTenantId
    botAppDomain: botAppDomain
    azureOpenAiApiKey: azureOpenAiApiKey
    azureOpenAiEndpoint: azureOpenAiEndpoint
    azureOpenAiModel: azureOpenAiModel
  }
}

// Outputs
output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = resourceGroupName
output APP_SERVICE_NAME string = appServiceName
output BOT_DOMAIN string = botAppDomain
output BOT_ENDPOINT string = 'https://${botAppDomain}/api/messages'
