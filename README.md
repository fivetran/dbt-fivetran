# Overview

When you run dbt with this adapter, it will create a local duckdb file named as `<your-database-name>.local.db`. 
It will be placed in `target` folder in your project folder if it exists. Otherwise, it will be placed in
the root of your project folder.


# Example profile

```
testprj:
  target: dev
  outputs:
    dev:
      type: fivetran
      extensions:
        - httpfs
        - iceberg
      threads: 1
      max-memory: 4096
      secrets:
        - type: s3
          region: <aws-region>
          key_id: <aws-client-id>
          secret: <aws-client-secret>
      database: <s3-bucket-name>
      schema: <schema-name>
      polaris_uri: "https://polaris.fivetran.com"
      polaris_credentials: <fivetranPolarisCredentials>
      polaris_scope: "PRINCIPAL_ROLE:ALL"
      polaris_catalog: <fivetran-group-id>
```