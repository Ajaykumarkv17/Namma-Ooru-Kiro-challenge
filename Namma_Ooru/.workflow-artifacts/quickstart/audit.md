# Namma Ooru deployment and readiness audit

**Audit date:** 2026-10-01 (local Windows workstation)  
**Scope:** Read-only analysis and non-destructive validation of `C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\Namma_Ooru`. No deployment, deletion, commit, or application-code change was performed.

## Executive assessment

The repository has a working React/Vite frontend, a FastAPI/Mangum backend, a JSON-backed catalog, deterministic itinerary/search/map/recommendation/review features, and CDK stacks for a Bedrock RAG backend. Local build/test checks mostly pass. It is **not accurate to call every feature production-ready yet**:

1. The shipped catalog and KB currently contain **one destination only** (`madurai-meenakshi-amman-temple`), so the intended statewide discovery breadth is not present in the deployable data.
2. CDK does **not** upload KB documents or start the Bedrock ingestion job. Those are required manual deployment steps for deployed chat/RAG to return grounded content.
3. The deployed backend still reads `data/destinations.json` packaged in the Lambda; it does not read the source S3 bucket at runtime. S3 is for the Bedrock KB only.
4. Reviews and generated itineraries are process-local/in-memory, so they are lost after a Lambda cold start/recycle and are not persistent multi-session data.
5. Production `BedrockAIProvider` deliberately leaves Bedrock search-intent extraction and natural-language itinerary-edit parsing unavailable. The local mock supports those flows deterministically; deployment must be smoke-tested to confirm the UI handles the documented dependency-unavailable response for those operations.
6. The infrastructure test suite has one failing test (details below), although CDK synthesis itself succeeds.

A `QUICKSTART.md` should present the backend as deployable after the manual KB data/ingestion steps and should clearly state these limitations rather than claim broad production readiness.

## 1. Repository layout and configuration

| Area | Path | Findings |
|---|---|---|
| Project root | `C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\Namma_Ooru` | Contains `backend/`, `frontend/`, `data/`, `infra/`, and `README.md`. |
| Backend | `...\Namma_Ooru\backend` | FastAPI source at `app/`, test suite at `tests/`, Python tooling in `pyproject.toml`, pinned dependencies in `requirements.txt`. |
| Frontend | `...\Namma_Ooru\frontend` | React + TypeScript + Vite source at `src/`; npm scripts/dependencies in `package.json`; lockfile is `package-lock.json`. |
| Dataset | `...\Namma_Ooru\data\destinations.json` | JSON catalog, currently one validated record. |
| KB source docs | `...\Namma_Ooru\data\kb\madurai-meenakshi-amman-temple.md` and `.md.metadata.json` | One generated KB document and S3 metadata sidecar. |
| Data tools | `...\Namma_Ooru\data\scripts\validate.py`, `...\Namma_Ooru\data\scripts\build_kb.py` | Validate the catalog and regenerate KB source documents locally; neither calls AWS. |
| Infrastructure | `...\Namma_Ooru\infra` | CDK v2 Python app: `app.py`, `cdk.json`, `namma_ooru_infra/`, and CDK assertion tests in `tests/`. |
| Existing docs | `...\Namma_Ooru\README.md`; `...\Namma_Ooru\infra\README.md` | README has local dev and itinerary contracts. Infra README documents stacks, outputs, and basic commands. |
| Environment template | `C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\.env.example` | This is **one directory above** `Namma_Ooru`, not inside the project root. It documents `VITE_API_BASE_URL`, `AWS_REGION`, AI variables, and no credentials. No `.env.example` was found under `Namma_Ooru`. |
| Actual environment files | Not found under `...\Namma_Ooru` during audit | Do not commit an actual `.env`; local frontend configuration can be passed in the PowerShell session. |

## 2. Backend facts

### Runtime, dependencies, and entry points

- Required/project target Python is **3.11**, as set in `backend/pyproject.toml` (`black`, Ruff, and mypy). The CDK Lambda runtime is explicitly `PYTHON_3_11` in `infra/namma_ooru_infra/backend_stack.py`.
- Dependency manager is plain pip, with pinned dependencies in `backend/requirements.txt`; install command for documentation: `python -m pip install -r requirements.txt` from `backend/` (prefer a Python 3.11 virtual environment for deployment parity).
- FastAPI app factory/ASGI app: `backend/app/main.py`, `create_app()` and module variable `app`.
- AWS Lambda adapter: `backend/app/lambda_handler.py`, handler `app.lambda_handler.handler`, implemented with `Mangum(app, lifespan="off")`.
- Local API command (derived from FastAPI entry point and installed Uvicorn dependency): from `backend/`, `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.
- Health endpoint is `GET /health`; API route modules include catalog, itinerary, map, search, recommendations, reviews, and `POST /api/chat`.
- The default repository is `JsonDestinationRepository` in `backend/app/catalog/repository.py`. It reads the package-relative `data/destinations.json` once at process construction. `DynamoDbDestinationRepository` is explicitly a non-working future stub and no DynamoDB table is deployed.
- Default AI provider is `mock`; production Lambda environment sets `AI_PROVIDER=bedrock`, `BEDROCK_KB_ID`, `BEDROCK_PRIMARY_MODEL_ID`, and `BEDROCK_FALLBACK_MODEL_ID`. `AWS_REGION` is resolved by the AWS SDK credential/config chain when present.

### Backend AWS deployment

`BackendStack` in `infra/namma_ooru_infra/backend_stack.py` packages the complete `backend/` directory (excluding test/cache paths), deploys a 512 MB, 29-second Python 3.11 Lambda, and connects it to API Gateway HTTP API. It relies on `AiStack` because Lambda environment configuration and IAM retrieval policy reference the generated Knowledge Base ID.

The stack output is `BackendApiUrl` (CloudFormation export `${appName}-backend-api-url`), which is the value needed by the local frontend.

### CORS and local frontend compatibility

API Gateway—not FastAPI middleware—provides CORS. Its configured default is exactly `http://localhost:5173`, from `infra/cdk.json` key `namma-ooru:corsAllowedOrigins`; it permits GET, POST, and `content-type`, disallows credentials, and caches preflight for one hour. Vite's default development port is 5173, so the documented local frontend command is compatible. If Vite uses another origin/port, redeploy the backend with that exact CORS origin via CDK context before using it.

## 3. Frontend facts

- Package manager: npm (`frontend/package-lock.json`); install with `npm ci` from `frontend/`.
- Commands from `frontend/package.json`:
  - Dev server: `npm run dev`
  - Production build: `npm run build` (runs `tsc --noEmit && vite build`)
  - Type check: `npm run typecheck`
  - Lint: `npm run lint`
  - Tests: `npm test`
  - Preview built site: `npm run preview`
- `frontend/src/api/client.ts` defines `API_BASE_URL` as `import.meta.env.VITE_API_BASE_URL`, stripping a trailing slash. If omitted, it uses relative API paths; Vite has no configured proxy (`frontend/vite.config.ts`), so a separately deployed backend **requires** `VITE_API_BASE_URL`.
- PowerShell session setting for local-to-deployed use: `$env:VITE_API_BASE_URL = '<BackendApiUrl>'; npm run dev`. Vite reads this at start time; restart after changing it.
- The frontend uses typed API clients and React Query hooks, so loading/error presentation is driven by the hook/client path instead of component-level fetch calls.

## 4. Required data and KB preparation

### What is bundled versus required

| Item | Status | Requirement before first deployed Bedrock chat use |
|---|---|---|
| Catalog JSON | `data/destinations.json` is bundled in Lambda code by `Code.from_asset(backend/)` | No S3 seed is required for catalog/read/search/map/recommendation/itinerary endpoints. The backend loads the JSON locally at runtime. |
| Dataset validation | `data/scripts/validate.py` exists and passed | Run it after any catalog change: `python data/scripts/validate.py`. |
| KB document construction | `data/scripts/build_kb.py` exists; current `data/kb/` has one document/sidecar | Required after catalog changes, before upload: `python data/scripts/build_kb.py`. It validates first and makes no AWS calls. |
| S3 upload | No script, CDK asset deployment, or custom resource uploads `data/kb/` | Required for RAG: copy `data/kb/*` to the `SourceDataBucketName` output. |
| Bedrock ingestion/reindex | No script/custom resource starts an ingestion job | Required after source upload and after any KB content change: call `aws bedrock-agent start-ingestion-job` with the deployed `KnowledgeBaseId` and `DataSourceId`, then poll its status. |

### Exact manual KB flow for QUICKSTART

The commands below are recommended for documentation **after** data and AI stacks exist. They are not executed in this audit.

```powershell
# From the Namma_Ooru repository root
python data/scripts/validate.py
python data/scripts/build_kb.py

# Read CloudFormation outputs (set the region to the CDK deployment region).
$region = '<AWS_REGION>'
$sourceBucket = aws cloudformation describe-stacks --stack-name namma-ooru-data --region $region --query "Stacks[0].Outputs[?OutputKey=='SourceDataBucketName'].OutputValue" --output text
$kbId = aws cloudformation describe-stacks --stack-name namma-ooru-ai --region $region --query "Stacks[0].Outputs[?OutputKey=='KnowledgeBaseId'].OutputValue" --output text
$dataSourceId = aws cloudformation describe-stacks --stack-name namma-ooru-ai --region $region --query "Stacks[0].Outputs[?OutputKey=='DataSourceId'].OutputValue" --output text

aws s3 sync data/kb "s3://$sourceBucket/" --region $region
$ingestionJobId = aws bedrock-agent start-ingestion-job --knowledge-base-id $kbId --data-source-id $dataSourceId --region $region --query 'ingestionJob.ingestionJobId' --output text
aws bedrock-agent get-ingestion-job --knowledge-base-id $kbId --data-source-id $dataSourceId --ingestion-job-id $ingestionJobId --region $region
```

Important: The CDK bucket has a `RETAIN` removal policy and versioning. Re-running `sync` without `--delete` will not remove obsolete KB source files; deliberately manage obsolete objects if document IDs are removed.

## 5. CDK stacks, resources, outputs, and deployment order

### Configuration and AWS identity

- CDK app entry point: `infra/app.py`; `infra/cdk.json` executes `python app.py`.
- Authentication is the normal AWS credential chain (AWS profile/SSO/IAM role). `app.py` optionally binds stacks to `CDK_DEFAULT_ACCOUNT` and `CDK_DEFAULT_REGION`; otherwise CDK resolves its environment using normal CDK/AWS configuration.
- Default context: app `namma-ooru`, vector dimension 1024, Titan Text Embeddings V2, Nova Pro primary profile, Nova 2 Lite fallback profile, CORS `http://localhost:5173`, frontend disabled. Optional frontend context keys are handled in `infra/namma_ooru_infra/config.py`.
- Before deploy, configure a profile/region and confirm identity with PowerShell: `aws sts get-caller-identity --profile <PROFILE>`; then use `--profile <PROFILE>` and `--region <AWS_REGION>` consistently. CDK bootstrap is required once per target account/region: `npx cdk bootstrap aws://<ACCOUNT_ID>/<AWS_REGION> --profile <PROFILE>`.

### Stacks

| Stack ID / class | Actual construct/resource names | Creates | Outputs | Backend-only relevance |
|---|---|---|---|---|
| `namma-ooru-data` / `DataStack` | `SourceData` → `Bucket` | Versioned, private, SSE-S3 source-document bucket | `SourceDataBucketName`, `SourceDataBucketArn` | **Required**: KB source location. |
| `namma-ooru-ai` / `AiStack` | `VectorStore` → `VectorBucket`, `Index`; `KnowledgeBaseRole`; `KnowledgeBase`; `SourceDocumentsDataSource` | S3 Vectors bucket/index, IAM service role/policies, Bedrock KB, Bedrock S3 data source | `KnowledgeBaseId`, `DataSourceId`, `VectorBucketArn`, `VectorIndexArn`, `KnowledgeBaseRoleArn` | **Required** for deployed AI chat/RAG; backend code requires its KB ID. |
| `namma-ooru-backend` / `BackendStack` | `BackendLogGroup`, `BackendRuntimeRole`, `BackendFunction`, `BackendApi`, route integrations | Lambda, explicit CloudWatch log group, Lambda role/policies, API Gateway HTTP API | `BackendApiUrl` | **Required**. |
| `namma-ooru-frontend` / `FrontendStack` | `FrontendApp`, `ProductionBranch` only when enabled | Optional Amplify app/production branch | `FrontendHostingUrl` only when enabled | **Skip** for a local Vite frontend. The stack remains synthesized but returns before creating Amplify resources when `frontendEnabled` is false. |
| `namma-ooru-monitoring` / `MonitoringStack` | `BackendLambdaErrorsAlarm`, `BackendApi5xxAlarm`, `OperationsDashboard` | Two CloudWatch alarms and dashboard/log query widgets | `OperationsDashboardName` | Optional operational visibility; no deployment dependency for serving the backend. |

### Correct deploy order for backend plus local frontend

1. Install infra development requirements and configure CDK/AWS identity.
2. `npx cdk bootstrap ...` once for the target account/region.
3. Deploy **`namma-ooru-data`**.
4. Validate/rebuild/upload `data/kb/` using the manual flow in section 4.
5. Deploy **`namma-ooru-ai`**.
6. Start and wait for the Bedrock data-source ingestion job to complete.
7. Deploy **`namma-ooru-backend`**. It is safe to include `namma-ooru-monitoring` after it if desired.
8. Obtain `BackendApiUrl`, set `VITE_API_BASE_URL`, and start the local Vite frontend. Do **not** deploy `namma-ooru-frontend`.
9. Smoke test `GET <BackendApiUrl>/health` and browser API calls from `http://localhost:5173`.

A compact PowerShell deployment form (after manual source upload at the indicated boundary) is:

```powershell
Set-Location infra
python -m pip install -r requirements-dev.txt
npx cdk deploy namma-ooru-data --profile <PROFILE>
# Return to repository root, run build/validate/upload from section 4.
Set-Location infra
npx cdk deploy namma-ooru-ai --profile <PROFILE>
# Return to repository root, start and complete ingestion from section 4.
Set-Location infra
npx cdk deploy namma-ooru-backend namma-ooru-monitoring --profile <PROFILE>
$apiUrl = aws cloudformation describe-stacks --stack-name namma-ooru-backend --region <AWS_REGION> --query "Stacks[0].Outputs[?OutputKey=='BackendApiUrl'].OutputValue" --output text
Set-Location ..\frontend
$env:VITE_API_BASE_URL = $apiUrl
npm ci
npm run dev
```

The examples deliberately omit `--require-approval never`; the deployer should review CDK's IAM/security changes. No infra deploy was run by this audit.

### Preconditions that code cannot verify locally

Before deployment, confirm in the chosen region that Amazon Bedrock Knowledge Bases with S3 Vectors and the configured models/profiles are available, and that the AWS account has model access. The default `.env.example` uses `ap-south-1`, while the actual CDK target is controlled by AWS/CDK environment configuration—not by that example file. These are deployment-account/region conditions and were not tested.

## 6. Full AWS resource inventory and cost classification

This is derived from the actual CDK definitions, not desired architecture. CDK bootstrap resources (CDK asset bucket/roles) are separate prerequisite resources and are not application stacks.

| Resource | IaC location / purpose | Charge behavior |
|---|---|---|
| S3 source-document bucket with versioning, SSE-S3, bucket policy | `SourceDataBucket` in DataStack; holds `data/kb` markdown and metadata | Storage/request/transfer usage billed. Versioning retains old versions, which can grow storage. Bucket is retained on stack deletion. |
| S3 Vectors vector bucket | `VectorStore.VectorBucket` in AiStack | Persistent vector storage is a potentially material baseline/usage driver even for one user; verify current regional pricing. |
| S3 Vectors cosine index (1024 dimensions) | `VectorStore.Index` in AiStack | Persistent vector index/storage and vector operations are potentially material; no automatic cleanup/retention policy is defined here. |
| Amazon Bedrock Knowledge Base | `AiStack.KnowledgeBase` | Retrieval/ingestion and embedding/model work are usage-billed; KB relies on the vector store. |
| Bedrock S3 data source | `AiStack.SourceDocumentsDataSource` | Used by explicitly started ingestion jobs; no auto-ingestion resource is present. Associated ingestion/embedding/vector usage applies. |
| IAM KB role and inline policies | `AiStack.KnowledgeBaseRole` | No direct normal service charge; grants KB limited source-bucket, Titan, and vector-store access. |
| Lambda execution role and inline policies | `BackendStack.BackendRuntimeRole` | No direct normal service charge; allows logs, Bedrock Retrieve, and two configured generation profiles/models. |
| Lambda function | `BackendStack.BackendFunction`; 512 MB / max 29s | Request and GB-second usage billed; no provisioned concurrency, VPC, NAT, EC2, or fixed compute is defined. |
| CloudWatch Logs log group | `BackendStack.BackendLogGroup`; 1-month retention | Log ingestion/storage/query usage billed. Retention limits retained log volume. |
| API Gateway HTTP API, integrations/routes, Lambda invocation permissions | `BackendStack.BackendApi` | Request/data-transfer usage billed; no REST API, custom domain, WAF, or caching layer is defined. |
| CloudWatch Lambda-error alarm and API-5xx alarm | MonitoringStack | Alarm charges may apply per configured alarm; no notification target/SNS subscription is created. |
| CloudWatch operations dashboard and log-query widget | MonitoringStack | Dashboard and Logs Insights query usage can incur charges depending on service free tiers/current pricing. |
| Amplify app and production branch | FrontendStack **only when** `namma-ooru:frontendEnabled=true` | Not created by default and should be skipped for this local-frontend workflow; hosting/build/data-transfer charges apply only if enabled. |

**Not created by current IaC:** DynamoDB, VPC, subnets, NAT gateways, Internet gateways, RDS, OpenSearch, ECS/EC2, Cognito, Secrets Manager, SQS, EventBridge scheduling, Route 53, CloudFront (apart from any service-managed Amplify behavior if optional hosting is enabled), or a persistent review/itinerary store.

## 7. Single-user, very-light-usage cost analysis

No numeric monthly total is defensible from this repository alone. Exact prices vary by AWS region, date, service tier/model, free-tier eligibility, usage volume, and S3 Vectors/Bedrock regional availability. The deployment target is not fixed in CDK (the parent `.env.example` merely suggests `ap-south-1`). A QUICKSTART should therefore include an AWS Pricing Calculator estimate made in the actual deployment region before deploying.

### Expected cost drivers

1. **Potential baseline/persistent costs:** S3 Vectors bucket/index/storage is the main resource to scrutinize for a tiny RAG app; source S3 versioned object storage and retained CloudWatch logs add smaller ongoing storage exposure. The monitoring stack also creates two alarms and a dashboard.
2. **Light request-driven costs:** Lambda invocations/duration, HTTP API requests, CloudWatch log ingestion, and ordinary S3 upload/storage requests should remain low for one light user, subject to free tiers and current pricing.
3. **AI-driven costs:** KB ingestion re-embeds changed KB documents, Titan embedding is used for ingestion/retrieval flow, and each deployed chat answer calls KB retrieval then Nova generation (with a possible fallback retry). These are the variable costs most likely to grow with use. The local mock has no AWS AI cost, but the deployed Lambda is forced to `AI_PROVIDER=bedrock`.
4. **Avoidable cost:** Do not enable the optional Amplify stack for the requested local frontend. Do not repeatedly re-ingest unchanged source documents. Keep test prompts/chat volume low while validating. Delete the whole non-production application only intentionally (source S3 is configured to retain) after verifying data-retention implications.

### Official, time-sensitive pricing references

Use only these official AWS pricing pages for current figures and select the actual region/model before quoting prices:

- [AWS Lambda pricing](https://aws.amazon.com/lambda/pricing/)
- [Amazon API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/)
- [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
- [Amazon S3 pricing](https://aws.amazon.com/s3/pricing/)
- [Amazon S3 Vectors pricing](https://aws.amazon.com/s3/pricing/#S3_Vectors)
- [Amazon CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [AWS Amplify pricing](https://aws.amazon.com/amplify/pricing/) (only if optional hosting is enabled)
- [AWS Pricing Calculator](https://calculator.aws/#/)

Content in this cost section was rephrased for compliance with licensing restrictions.

## 8. Feature-readiness inventory

| Capability | Evidence in repository | Validation / readiness status |
|---|---|---|
| Catalog browse, destination detail, city grouping/filtering | Catalog router/repository/models; frontend catalog pages/components | Backend unit/integration tests passed. Functionally implemented, but deployable catalog breadth is only one record. |
| Search | `backend/app/search/`, `frontend/src/pages/SearchPage.tsx` and API client | Backend tests passed. Local mock supplies deterministic intent/fallback. Production Bedrock intent extraction is explicitly unavailable, so production natural-language semantic parsing is not ready. |
| Map and filtered markers | `backend/app/map/`, `frontend/src/components/map/` using MapLibre provider interface | Backend tests and frontend tests passed; production map tile/provider operational behavior was not exercised against a browser/deployed service. |
| Recommendations / interest, themed journey, surprise pick | `backend/app/recommendations/`, frontend discovery components | Backend and frontend tests passed. Recommendations are limited by the one-record catalog. |
| AI-grounded chat | `BedrockAIProvider`, KB IaC, ChatWidget | Unit tests passed; deployment readiness is blocked on source upload, completed ingestion, model access, and a live smoke test. Local mock returns information-unavailable rather than retrieved content. |
| Itinerary creation/editing | deterministic `backend/app/itinerary/`; `ItineraryPlannerPage.tsx` | Backend and frontend tests passed. In-memory plans are non-persistent. Local mock supports command-style edits; production Bedrock edit parsing is unimplemented/unavailable. |
| Reviews and AI-labelled summary | `backend/app/reviews/`, `ReviewPanel.tsx` | Tests passed; repository is `InMemoryReviewRepository`, so submitted reviews are not durable in Lambda production. |
| Data validation / KB document generation | `data/scripts/validate.py`, `build_kb.py` | Validator passed on one record. KB builder was inspected but not run because it writes generated document files; current KB source files exist. |
| Frontend quality gate | `package.json`, 15 test files | Typecheck, lint, tests, and production build passed. Build emitted a non-fatal >500 kB chunk warning for the dynamically loaded MapLibre chunk. |
| Backend quality gate | `backend/tests/` including `tests/property/` | Full backend suite and property suite passed; both emitted one pytest configuration warning due to the audit interpreter/plugin environment. |
| CDK IaC | `infra/` stacks and assertion tests | `npx cdk synth` succeeded. Infra test suite has 1 failure of 29 due to `test_runtime_role_scopes_bedrock_to_profiles_and_associated_models` trying to put a CloudFormation intrinsic dictionary into a Python set; this needs repair before calling the IaC test gate green. |
| Live AWS deployment | No deployed environment inspected | **Not verified**. No AWS calls/deploys were made. |

## 9. Validation commands actually run

All commands below were non-destructive and run from the stated directory on the audit workstation.

| Command | Directory | Outcome |
|---|---|---|
| `python -m pytest tests -q` | `backend` | **PASS:** 188 passed in 34.52s. One `PytestConfigWarning`: unknown `hypothesis_profile` option under local Python 3.12 environment. |
| `python -m pytest tests/property -q` | `backend` | **PASS:** 4 passed in 39.48s. Same one pytest configuration warning. |
| `python data/scripts/validate.py` | Repository root | **PASS:** `Checked 1 record(s): 1 valid, 0 error(s), 0 warning(s).` |
| `npm run typecheck` | `frontend` | **PASS:** `tsc --noEmit` exited 0. |
| `npm run lint` | `frontend` | **PASS:** `eslint .` exited 0. |
| `npm run build` | `frontend` | **PASS:** Vite built successfully in 13.16s. Warning: MapLibre output chunk was 803.11 kB before gzip, over the 500 kB warning threshold. |
| `npm test` | `frontend` | **PASS:** 15 test files / 76 tests passed in 18.66s. |
| `python -m pytest tests -q` | `infra` | **FAIL:** 28 passed, 1 failed. `tests/test_backend_stack.py::test_runtime_role_scopes_bedrock_to_profiles_and_associated_models` raises `TypeError: unhashable type: 'dict'` when evaluating synthesized policy resources. |
| `npx cdk synth` | `infra` | **PASS:** Successfully synthesized all five named stacks to `infra/cdk.out`. CDK warned that cross-stack reference strength is defaulting to strong and that 79 feature flags are unconfigured. |

Installed audit toolchain observed: AWS CLI `2.32.22`, Python `3.12.7`, Node `v22.21.1`, npm `10.9.4`, and locally available `npx cdk 2.1134.0`. A global `cdk` command was not found, so documentation should use `npx cdk` from `infra/`.

## 10. QUICKSTART content requirements derived from this audit

The requested `QUICKSTART.md` should include, in order:

1. Prerequisites: Python 3.11, Node/npm, AWS CLI with configured profile/SSO, CDK via `npx`, model access and region support warning.
2. Backend dependency setup, `npx cdk bootstrap`, and the explicit Data → KB validate/build/upload → AI → ingestion → Backend (→ optional Monitoring) order.
3. Output retrieval for `BackendApiUrl` plus `GET /health` smoke test.
4. PowerShell-only local frontend instructions using `$env:VITE_API_BASE_URL = $apiUrl`, `npm ci`, and `npm run dev`, noting the required `http://localhost:5173` CORS origin.
5. Explicit statement that **Amplify/`namma-ooru-frontend` is skipped** for this workflow.
6. Required KB re-ingestion steps after every catalog/KB change.
7. The state/persistence and one-record catalog limitations from the executive assessment.
8. The AWS inventory and time-sensitive, official-source-only cost guidance above; do not publish stale regional numeric estimates as facts.
