# Namma Ooru: AWS backend + local frontend quickstart

## 1. Overview

This guide deploys the Namma Ooru **data, AI/RAG, and FastAPI backend** to AWS, then runs the Vite/React frontend locally against the deployed API. It intentionally **does not deploy `namma-ooru-frontend` or Amplify**.

The supported sequence is:

```text
Data stack → validate/build KB files → upload KB files → AI stack → KB ingestion → backend stack → local frontend
```

### Current readiness and scope

The repository implements catalog browsing, details and filters, search, map markers, recommendations, itineraries, reviews, chat, and CDK infrastructure. The audited local quality checks passed except for one infrastructure assertion test; see [Feature-readiness audit](#8-feature-readiness-audit).

Do not present the deployment as a statewide production catalog yet:

- The checked-in catalog and KB source currently contain **one destination**: `madurai-meenakshi-amman-temple`.
- The Lambda packages and loads `backend/data/destinations.json`; it does **not** read the S3 source bucket at runtime. No catalog S3 seed is required.
- Bedrock chat needs an uploaded, successfully ingested KB before it can return grounded deployed answers.
- Reviews and generated itineraries are in-memory. Lambda cold starts/recycles lose them; they are not persistent multi-session records.
- In deployed Bedrock mode, natural-language search-intent extraction and itinerary-edit parsing are intentionally unavailable. The local mock supports deterministic versions of those flows.

## 2. Prerequisites

Run every command in **Windows PowerShell**. The examples assume this repository root:

```powershell
Set-Location "C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\Namma_Ooru"
```

Install/configure the following:

| Requirement | Notes |
| --- | --- |
| Python **3.11** | Backend tooling and the Lambda runtime target Python 3.11. |
| Node.js and npm | Use npm because `frontend/package-lock.json` is committed. |
| AWS CLI v2 | Authenticate with a named profile, AWS IAM role, or AWS IAM Identity Center/SSO. |
| AWS CDK v2 | Use the project-local invocation `npx cdk` from `infra`; a global CDK install is not required. |
| AWS account and deployment region | The account must support Bedrock Knowledge Bases with S3 Vectors and the configured Bedrock models/inference profiles, and must have the required model access. These conditions were not live-tested by the audit. |

The repository template one directory above the project root is `..\.env.example`. It lists a non-secret `AWS_REGION=ap-south-1`, but the actual CDK target comes from your AWS/CDK environment—not from that file. Never put AWS access keys in `.env` files.

Set your actual profile and region once for this session, then confirm the account identity:

```powershell
$profile = "<PROFILE>"
$region = "<AWS_REGION>"
$env:AWS_PROFILE = $profile
$env:AWS_DEFAULT_REGION = $region
$env:CDK_DEFAULT_REGION = $region

aws sts get-caller-identity --profile $profile --region $region
```

## 3. Deploy the AWS backend

### 3.1 Install backend and infrastructure dependencies

The backend dependency command is useful for local tools and validation; the backend pins its dependencies in `backend\requirements.txt`.

```powershell
Set-Location "C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\Namma_Ooru\backend"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

Set-Location ..\infra
python -m pip install -r requirements-dev.txt
```

If `py -3.11` is unavailable, install Python 3.11 or invoke its `python.exe` explicitly. Do not substitute a different runtime for deployment parity.

### 3.2 Bootstrap CDK once per account and region

Read the account ID from the identity result, then bootstrap that account and region. Bootstrap creates CDK prerequisite resources (such as its asset bucket and roles), separate from the Namma Ooru application stacks.

```powershell
$accountId = aws sts get-caller-identity --profile $profile --region $region --query "Account" --output text
Set-Location "C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\Namma_Ooru\infra"
npx cdk bootstrap "aws://$accountId/$region" --profile $profile
```

Review CDK's security/IAM changes when prompted. This guide deliberately does not suppress approval prompts.

### 3.3 Deploy in the required order

The stack dependency and setup order matters:

1. `namma-ooru-data`
2. Validate, build, and upload KB documents to the data bucket
3. `namma-ooru-ai`
4. Start and complete Bedrock KB ingestion
5. `namma-ooru-backend`
6. Optional: `namma-ooru-monitoring`

Deploy the data stack first, then read the output required for the KB upload:

```powershell
Set-Location "C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\Namma_Ooru\infra"
npx cdk deploy namma-ooru-data --profile $profile

$sourceBucket = aws cloudformation describe-stacks --stack-name namma-ooru-data --region $region --profile $profile --query "Stacks[0].Outputs[?OutputKey=='SourceDataBucketName'].OutputValue" --output text
$sourceBucket
```

Complete [section 4.1](#41-validate-build-and-upload-kb-source) before continuing. Then deploy the AI stack and read the values required to ingest its data source:

```powershell
Set-Location "C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\Namma_Ooru\infra"
npx cdk deploy namma-ooru-ai --profile $profile

$kbId = aws cloudformation describe-stacks --stack-name namma-ooru-ai --region $region --profile $profile --query "Stacks[0].Outputs[?OutputKey=='KnowledgeBaseId'].OutputValue" --output text
$dataSourceId = aws cloudformation describe-stacks --stack-name namma-ooru-ai --region $region --profile $profile --query "Stacks[0].Outputs[?OutputKey=='DataSourceId'].OutputValue" --output text
$kbId
$dataSourceId
```

Complete [section 4.2](#42-ingest-the-uploaded-kb-source) and wait for a successful ingestion. Then deploy the backend and read the URL required by the local frontend:

```powershell
Set-Location "C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\Namma_Ooru\infra"
npx cdk deploy namma-ooru-backend --profile $profile

$apiUrl = aws cloudformation describe-stacks --stack-name namma-ooru-backend --region $region --profile $profile --query "Stacks[0].Outputs[?OutputKey=='BackendApiUrl'].OutputValue" --output text
$apiUrl

# Optional operational visibility:
npx cdk deploy namma-ooru-monitoring --profile $profile
```

Other outputs are `SourceDataBucketArn`, `VectorBucketArn`, `VectorIndexArn`, `KnowledgeBaseRoleArn`, and (if monitoring is deployed) `OperationsDashboardName`.

### 3.4 Do not deploy Amplify for this workflow

`namma-ooru-frontend` is optional and defaults to no resources because `namma-ooru:frontendEnabled` is false. Leave it disabled and do not deploy the stack when running the frontend locally. Enabling it creates an Amplify app and production branch, which adds hosting/build charges and is outside this quickstart.

## 4. Data & AI setup

### Catalog data versus KB data

`data\destinations.json` is included in the Lambda asset and loaded by the JSON repository at runtime. Therefore, **no S3 upload or AWS seed command is required** for catalog, filters, map, recommendation, search fallback, or itinerary endpoints.

The S3 source bucket exists for Bedrock Knowledge Base source documents only. CDK does **not** upload `data\kb\` and does **not** start ingestion. The following steps are mandatory before using deployed grounded chat, and must be repeated after every catalog/KB change.

### 4.1 Validate, build, and upload KB source

After deploying `namma-ooru-data` and reading `$sourceBucket` in section 3.3:

1. Validate the catalog. The script exits non-zero for invalid source data.
2. Regenerate the Markdown documents and `.metadata.json` sidecars.
3. Upload all generated KB source files.

```powershell
Set-Location "C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\Namma_Ooru"

python data\scripts\validate.py
python data\scripts\build_kb.py

aws s3 sync data\kb "s3://$sourceBucket/" --region $region --profile $profile
```

The source bucket is versioned and has a `RETAIN` removal policy. `aws s3 sync` without `--delete` does not remove obsolete documents; review and deliberately manage old objects if a document ID is removed. Do not add `--delete` unless you have confirmed the objects may be removed.

### 4.2 Ingest the uploaded KB source

After deploying `namma-ooru-ai` and reading `$kbId` and `$dataSourceId` in section 3.3, start an ingestion job and poll it until it completes successfully:

```powershell
$ingestionJobId = aws bedrock-agent start-ingestion-job --knowledge-base-id $kbId --data-source-id $dataSourceId --region $region --profile $profile --query "ingestionJob.ingestionJobId" --output text
aws bedrock-agent get-ingestion-job --knowledge-base-id $kbId --data-source-id $dataSourceId --ingestion-job-id $ingestionJobId --region $region --profile $profile
```

Repeat the final `get-ingestion-job` command until the job reports success before deploying/testing the backend chat flow. The exact terminal status is AWS-managed; do not treat a job merely being created as successful ingestion.

## 5. Run the frontend locally against AWS

The frontend reads the exact Vite environment variable `VITE_API_BASE_URL`. It strips a trailing slash. Because `vite.config.ts` has no proxy, this variable is required for a separately deployed backend.

```powershell
Set-Location "C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\Namma_Ooru\frontend"
npm ci

# $apiUrl is BackendApiUrl read after the backend deployment in section 3.3.
$env:VITE_API_BASE_URL = $apiUrl
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). Vite reads `VITE_API_BASE_URL` when it starts, so stop and restart `npm run dev` after changing the value.

### CORS requirement

API Gateway CORS is configured by CDK, not FastAPI. The default allowed origin is exactly `http://localhost:5173`; it permits `GET`, `POST`, and `content-type`, with no credentials. If Vite uses a different origin or port, change the `namma-ooru:corsAllowedOrigins` CDK context value to that exact origin and redeploy `namma-ooru-backend`. Do not weaken CORS to an unrestricted origin.

### Smoke checks

First verify the deployed API directly:

```powershell
Invoke-RestMethod -Uri "$apiUrl/health"
Invoke-RestMethod -Uri "$apiUrl/api/destinations"
```

Then, from the browser at `http://localhost:5173`, confirm that:

1. the catalog loads with no browser CORS/network error;
2. the destination detail route opens;
3. browser Network requests target `$apiUrl`, not the Vite origin;
4. after KB ingestion, chat returns a response or a clear grounded-information/dependency response rather than a CORS failure.

## 6. AWS resource inventory

The following is the complete inventory derived from the CDK application stacks. CDK bootstrap assets/roles are prerequisite resources and are not listed as Namma Ooru application resources.

| Deployment group | Resource | Purpose | Charge behavior |
| --- | --- | --- | --- |
| Backend required | S3 source-document bucket (versioned, SSE-S3) | Stores `data/kb` Markdown and metadata sidecars for the KB. Retained on stack deletion. | Storage, requests, and transfer usage; old versions can accumulate. |
| Backend required | S3 Vectors vector bucket | Persistent vector storage for RAG. | **Potentially material persistent/vector cost** plus usage; verify regional availability and pricing. |
| Backend required | S3 Vectors cosine index (1024 dimensions) | Index queried by the KB. | **Potentially material persistent/vector and operation cost**; no separate automatic cleanup policy is defined. |
| Backend required | Bedrock Knowledge Base | Retrieves grounded source chunks and connects the data source to vectors. | Ingestion, retrieval, embedding, and model-related usage. |
| Backend required | Bedrock S3 data source | Defines the KB source bucket. | Used by manually started ingestion jobs; associated ingestion/embedding/vector usage. |
| Backend required | IAM Knowledge Base service role and scoped policies | Lets Bedrock read the source bucket, invoke Titan embeddings, and access this vector store. | No normal direct service charge. |
| Backend required | Lambda execution role and scoped policies | Allows logs, KB retrieval, and the configured Bedrock generation profiles/models. | No normal direct service charge. |
| Backend required | Lambda function | FastAPI/Mangum backend; Python 3.11, 512 MB, 29-second timeout. | Request and GB-second usage; no provisioned concurrency, VPC, NAT, EC2, or fixed compute. |
| Backend required | API Gateway HTTP API, integrations/routes, Lambda permissions | Exposes the backend with CORS. | Request/data-transfer usage. |
| Backend required | CloudWatch Logs log group | Backend logs, retained one month; it is always created with the backend stack. | Log ingestion, storage, and query usage. |
| Optional monitoring | Two CloudWatch alarms | Lambda errors and API 5xx monitoring. | Alarm charges may apply. |
| Optional monitoring | CloudWatch dashboard/log query widgets | Operational dashboard and recent-log query. | Dashboard and Logs Insights query usage may apply. |
| **Skipped locally** | Amplify app and production branch | Hosted frontend only when `namma-ooru:frontendEnabled=true`. | Not created by default; hosting/build/data-transfer charges apply only if enabled. |

Current IaC does **not** create DynamoDB, VPC/subnets/NAT, EC2/ECS, RDS, OpenSearch, Cognito, Secrets Manager, SQS, EventBridge scheduling, Route 53, CloudFront as a direct application resource, or a durable review/itinerary database.

## 7. Single-user, light-usage cost analysis

### What can and cannot be estimated

A defensible fixed monthly number cannot be derived from this repository. Pricing is regional, time-sensitive, subject to service/model availability and free-tier eligibility, and depends on KB size, ingestion frequency, chat tokens, requests, stored vectors, logs, and data transfer. Use the official AWS Pricing Calculator with the **actual deployment region and selected models** before deploying.

For one very light user, ordinary Lambda/API requests and small source S3 documents are likely usage-driven and low relative to the RAG layer, subject to current free tiers. The cost drivers that need the most scrutiny are:

1. **Persistent/vector baseline:** S3 Vectors bucket/index storage and operations can be material even with little traffic.
2. **AI usage:** each KB refresh performs ingestion/embeddings; each deployed chat request retrieves from the KB and invokes Nova generation, with a possible fallback retry.
3. **Observability:** the backend-required CloudWatch log group can incur log ingestion, storage, and query charges; the dashboard/query use and two alarms are optional monitoring costs.
4. **Avoidable hosting:** Amplify is unnecessary for this local-frontend workflow and should remain disabled.

All price figures and rates must be treated as **regional and time-sensitive**. Check only current official sources before using numeric estimates:

- [AWS Pricing Calculator](https://calculator.aws/#/)
- [AWS Lambda pricing](https://aws.amazon.com/lambda/pricing/)
- [Amazon API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/)
- [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
- [Amazon S3 pricing](https://aws.amazon.com/s3/pricing/)
- [Amazon S3 Vectors pricing](https://aws.amazon.com/s3/pricing/#S3_Vectors)
- [Amazon CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [AWS Amplify pricing](https://aws.amazon.com/amplify/pricing/) (only if hosting is enabled)

Content in this cost section was rephrased for compliance with licensing restrictions.

### Cost controls

- Leave `namma-ooru-frontend` disabled for local use.
- Upload and ingest only when KB source changes; do not repeatedly ingest unchanged documents.
- Keep smoke-test chat volume low and monitor Bedrock usage during validation.
- Use the one-month log retention already configured; avoid unnecessary verbose logging and Logs Insights queries.
- Watch retained/versioned source-bucket objects and vector storage.
- For short-lived non-production use, run the teardown steps below after saving anything required.

## 8. Feature-readiness audit

| Capability | Audited validation status | Readiness notes |
| --- | --- | --- |
| Catalog, destination detail, city grouping, filters | Backend tests passed | Implemented, but only one deployable catalog record exists. |
| Search | Backend tests passed | Local mock has deterministic intent/fallback. Production Bedrock natural-language intent extraction is unavailable. |
| Map and filtered markers | Backend and frontend tests passed | Browser/deployed tile-provider behavior was not live-tested. |
| Recommendations, themed journeys, surprise pick | Backend and frontend tests passed | Functionally implemented; output breadth is limited by the one-record catalog. |
| Itinerary create/edit | Backend and frontend tests passed | Deterministic core implemented; plans are in-memory. Production Bedrock edit parsing is unavailable. |
| Reviews and AI-labelled summary | Tests passed | Submitted reviews use an in-memory repository and are not durable in Lambda. |
| AI-grounded chat | Unit tests passed | Live readiness is **unverified** until source upload, completed ingestion, model access, and a deployed smoke test succeed. |
| Dataset validator | Passed: `python data/scripts/validate.py` reported `1 valid, 0 error(s), 0 warning(s)` | Run after catalog changes. |
| KB document generation | Source and builder inspected; existing KB source present | The audit did not run the builder because it writes files. Run it before every source upload. |
| Frontend quality gates | Passed: typecheck, lint, production build, and 76 tests across 15 files | Build produced a non-fatal MapLibre chunk-size warning (>500 kB before gzip). |
| Backend quality gates | Passed: 188 tests and 4 property tests | Both runs emitted one local pytest configuration warning for `hypothesis_profile` under the audit's Python 3.12 environment. The project target remains Python 3.11. |
| CDK synth | Passed: `npx cdk synth` | CDK emitted cross-stack reference/feature-flag warnings. |
| CDK assertion tests | **Not green:** 28 passed, 1 failed | `tests/test_backend_stack.py::test_runtime_role_scopes_bedrock_to_profiles_and_associated_models` raises `TypeError: unhashable type: 'dict'` while putting a CloudFormation intrinsic dictionary into a Python set. Repair that test before calling the IaC test gate green. |
| Live AWS deployment | Not performed by audit | Unverified; follow this guide and perform smoke checks. |

The local audit command outcomes above are historical audit evidence, not a claim that deployment commands or AWS resources have been run from this guide.

## 9. Troubleshooting

| Symptom | Check / remediation |
| --- | --- |
| `npx cdk` cannot authenticate or bootstrap fails | Re-run `aws sts get-caller-identity --profile $profile --region $region`; verify the intended account/region and CDK permissions. |
| AI stack fails to create | Verify Bedrock Knowledge Base with S3 Vectors availability, regional support, and access to the configured Titan/Nova models/inference profiles in the selected account/region. These are prerequisites, not repository configuration errors. |
| Chat says grounded information is unavailable | Confirm `data\kb` was built, uploaded to `$sourceBucket`, and that the ingestion job completed successfully. Confirm the backend was deployed after the AI stack. |
| Browser shows a CORS or network error | Use `http://localhost:5173` or update `namma-ooru:corsAllowedOrigins` to the exact Vite origin and redeploy `namma-ooru-backend`. Confirm `$env:VITE_API_BASE_URL` equals `$apiUrl` before starting Vite. |
| Frontend calls its own Vite URL instead of AWS | `VITE_API_BASE_URL` was missing when Vite started. Set it, then restart `npm run dev`. |
| Catalog changes do not appear in deployed API | The catalog is packaged inside the Lambda. Rebuild/redeploy `namma-ooru-backend`; S3 upload alone only changes KB source. |
| Chat sources are stale after a catalog change | Run validation, `build_kb.py`, upload, and start a new ingestion job. |
| Reviews or itineraries disappear | This is current behavior: those repositories are process-local/in-memory and are reset by Lambda lifecycle events. |

## 10. Clean teardown and security

### Teardown

Destroy application stacks in reverse dependency order. Skip the frontend command because this local workflow does not deploy it; run it only if you explicitly enabled/deployed Amplify.

```powershell
Set-Location "C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\Namma_Ooru\infra"

npx cdk destroy namma-ooru-monitoring --profile $profile
# Only if it was explicitly enabled and deployed:
npx cdk destroy namma-ooru-frontend --profile $profile
npx cdk destroy namma-ooru-backend --profile $profile
npx cdk destroy namma-ooru-ai --profile $profile
npx cdk destroy namma-ooru-data --profile $profile
```

Review each destruction prompt. The source-data bucket is configured with `RETAIN`, so destroying `namma-ooru-data` does **not** guarantee that the S3 bucket or its versioned objects are deleted. Review retention requirements, then remove retained objects/buckets manually only when that data may be deleted. CDK bootstrap resources are separate and are not removed by the application-stack commands.

### Security warnings

- Do not commit `.env` files, access keys, personal tokens, stack outputs containing sensitive operational context, or other secrets. Commit only a value-free template such as `..\.env.example`.
- Use AWS profiles/SSO/IAM roles through the standard credential chain; never hard-code AWS credentials in source, CDK context, prompts, or logs.
- Review CDK IAM changes at deployment. The current stacks scope the KB and Lambda roles to the configured bucket, KB, vector store, and models/profiles.
- Keep CORS restricted to the exact frontend origin; do not use `*` for this deployed API.
- Do not echo secret values in terminal transcripts, errors, logs, or AI prompts.
