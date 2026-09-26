targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary Location for all resources')
param location string

@description('The backend service container image name or reference')
param backendImageName string = ''

@description('The frontend service container image name or reference')
param frontendImageName string = ''

var abbrs = {
  resourceGroups: 'rg-'
  containerAppsEnvironment: 'cae-'
  containerApp: 'ca-'
  containerRegistry: 'cr'
  logAnalyticsWorkspace: 'log-'
}
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: '${abbrs.resourceGroups}${environmentName}'
  location: location
  tags: tags
}

module resources './resources.bicep' = {
  name: 'resources'
  scope: rg
  params: {
    environmentName: environmentName
    location: location
    resourceToken: resourceToken
    tags: tags
    backendImageName: backendImageName
    frontendImageName: frontendImageName
  }
}

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.AZURE_CONTAINER_REGISTRY_ENDPOINT
output BACKEND_URI string = resources.outputs.BACKEND_URI
output FRONTEND_URI string = resources.outputs.FRONTEND_URI
