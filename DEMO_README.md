Set to commercial cloud
```bash
az cloud set --name AzureCloud 
azd config set cloud.name AzureCloud
```

Login with fdpo tenant:
```bash
az login --tenant fdpo.onmicrosoft.com
 azd auth login --tenant-id fdpo.onmicrosoft.com

```

Deploy resources:
```bash
