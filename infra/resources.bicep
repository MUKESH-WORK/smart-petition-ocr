@description('Environment name for resource naming')
param environmentName string

@description('Azure Region for resource placement')
param location string

@description('Unique resource token')
param resourceToken string

@description('Resource Tags')
param tags object

param backendImageName string = ''
param frontendImageName string = ''

// 1. Log Analytics Workspace for Container Apps
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// 2. Azure Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: 'cr${resourceToken}'
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// 3. Azure Container Apps Managed Environment
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'cae-${resourceToken}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// 4. Backend Container App (FastAPI + Embeddings)
resource backendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-backend-${resourceToken}'
  location: location
  tags: union(tags, { 'azd-service-name': 'backend' })
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
      ]
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'registry-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: !empty(backendImageName) ? backendImageName : 'mcr.microsoft.com/azuredocs/aci-helloworld:latest'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            {
              name: 'PORT'
              value: '8000'
            }
            {
              name: 'USE_SQLITE'
              value: 'true'
            }
            {
              name: 'SEMANTIC_CACHE_ENABLED'
              value: 'true'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

// 5. Frontend Container App (React + Nginx)
resource frontendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-frontend-${resourceToken}'
  location: location
  tags: union(tags, { 'azd-service-name': 'frontend' })
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
      }
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
      ]
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'registry-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: !empty(frontendImageName) ? frontendImageName : 'mcr.microsoft.com/azuredocs/aci-helloworld:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.properties.loginServer
output BACKEND_URI string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
output FRONTEND_URI string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
