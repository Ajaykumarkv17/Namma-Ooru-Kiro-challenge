# Namma Ooru infrastructure (AWS CDK v2, Python)

AWS CDK v2 app that provisions Namma Ooru infrastructure. Stacks are split by
concern so the backend can deploy independently:

- **`namma-ooru-data` (`DataStack`)** — the source-document S3 bucket that holds
  the Knowledge Base documents (`data/kb/<id>.md` + `.metadata.json` sidecars).
- **`namma-ooru-ai` (`AiStack`)** — the S3 Vectors bucket + index, the Amazon
  Bedrock Knowledge Base (backed by S3 Vectors), the S3 data source that ingests
  the source documents, and a least-privilege Knowledge Base service role.

`BackendStack`, `FrontendStack`, and `MonitoringStack` are added in later tasks.

## Reusable constructs
- `SourceDataBucket` — hardened S3 bucket (block public access, SSL enforced,
  SSE, versioned).
- `VectorStore` — S3 Vectors bucket + cosine index. Retrieval metadata
  (district, city, category, region, heritage, UNESCO, travel type) stays
  filterable; `AMAZON_BEDROCK_TEXT` is non-filterable.

## Configuration
Non-secret configuration comes from CDK context (`cdk.json`), resolved by
`NammaOoruConfig`: `appName`, `vectorDimension`, `embeddingModelId`,
`knowledgeBaseModelId`. Account/region come from the standard AWS credential
chain via `CDK_DEFAULT_ACCOUNT` / `CDK_DEFAULT_REGION`. No credentials are
hardcoded.

## Least-privilege IAM
The Knowledge Base role is scoped to exactly:
- read the source-document bucket (`s3:GetObject`, `s3:ListBucket` on that ARN),
- invoke only the configured Titan embedding model, and
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
