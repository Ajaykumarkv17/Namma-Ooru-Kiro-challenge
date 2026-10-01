# Namma Ooru infrastructure (AWS CDK v2, Python)

AWS CDK v2 app that provisions Namma Ooru infrastructure. Stacks are split by
concern so the backend can deploy independently:

- **`namma-ooru-data` (`DataStack`)** — the source-document S3 bucket that holds
  the Knowledge Base documents (`data/kb/<id>.md` + `.metadata.json` sidecars).
- **`namma-ooru-ai` (`AiStack`)** — the S3 Vectors bucket + index, the Amazon
  Bedrock Knowledge Base (backed by S3 Vectors), the S3 data source that ingests
  the source documents, and a least-privilege Knowledge Base service role.

- **`namma-ooru-backend` (`BackendStack`)** — independently deployable FastAPI Lambda,
  API Gateway HTTP API, CORS configuration, API URL output, and backend Lambda log group.
- **`namma-ooru-frontend` (`FrontendStack`)** — optional AWS Amplify Hosting. When enabled,
  the Vite build receives `VITE_API_BASE_URL` from the backend API endpoint.
- **`namma-ooru-monitoring` (`MonitoringStack`)** — CloudWatch backend Lambda/API 5xx alarms,
  an operations dashboard, and a backend-log query widget.

## Reusable constructs
- `SourceDataBucket` — hardened S3 bucket (block public access, SSL enforced,
  SSE, versioned).
- `VectorStore` — S3 Vectors bucket + cosine index. Retrieval metadata
  (district, city, category, region, heritage, UNESCO, travel type) stays
  filterable; `AMAZON_BEDROCK_TEXT` is non-filterable.

## Configuration
Non-secret configuration comes from CDK context (`cdk.json`), resolved by
`NammaOoruConfig`: `appName`, `vectorDimension`, `embeddingModelId`,
`primaryGenerationModelId`, `fallbackGenerationModelId`, `frontendEnabled`, `frontendBranch`, and optional
`frontendRepositoryUrl`. Titan Text Embeddings V2 is used only by the Knowledge Base; generation
uses the Nova inference profiles configured by the two generation keys.
chain via `CDK_DEFAULT_ACCOUNT` / `CDK_DEFAULT_REGION`. No credentials are
hardcoded.

Amplify Hosting is disabled by default so backend deployments stay independent.
Enable it with `-c namma-ooru:frontendEnabled=true`; optionally provide the
repository URL with `-c namma-ooru:frontendRepositoryUrl=https://...`. Repository
authorization must be configured through Amplify/AWS deployment mechanisms, never
in CDK context or source control.

## Least-privilege IAM
The Knowledge Base role is scoped to exactly:
- read the source-document bucket (`s3:GetObject`, `s3:ListBucket` on that ARN),
- invoke only the configured Titan embedding model, and
- the backend invokes only the configured Nova inference profiles and their associated
  Nova foundation-model resources; cross-region model ARNs are limited to those two model IDs,
  which is required for system-profile routing,
- access only this vector store's bucket and index.

No statement uses a `*` resource (Req 12.4).

## Commands
```bash
pip install -r requirements-dev.txt
pytest tests            # CDK assertion + synth tests
npx cdk synth           # or: python app.py
```

## Outputs
`DataStack`: `SourceDataBucketName`, `SourceDataBucketArn`.
`AiStack`: `KnowledgeBaseId`, `DataSourceId`, `VectorBucketArn`, `VectorIndexArn`,
`KnowledgeBaseRoleArn`.
`BackendStack`: `BackendApiUrl`.
`FrontendStack` (when enabled): `FrontendHostingUrl`.
`MonitoringStack`: `OperationsDashboardName`.
