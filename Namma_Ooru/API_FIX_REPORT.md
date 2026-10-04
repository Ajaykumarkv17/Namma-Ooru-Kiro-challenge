# Backend API fix report

## Root causes confirmed

Read-only checks against the deployed API at `https://oxbywtml38.execute-api.us-east-1.amazonaws.com` returned HTTP 500 for both `GET /api/destinations` and the `OPTIONS /api/chat` preflight.

CloudWatch Logs for `/aws/lambda/namma-ooru-backend` identified the runtime failure:

```text
Runtime.ImportModuleError: Unable to import module 'app.lambda_handler': No module named 'mangum'
```

The deployed Lambda asset was created with `Code.from_asset(backend)` but did not install `backend/requirements.txt`. Consequently, Lambda could not import Mangum or initialize FastAPI. This affects every proxied route; it is not a frontend ErrorState issue and `GET /api/destinations` does not reach Bedrock.

The deployed HTTP API CORS configuration was already restricted to `http://localhost:5173`, `GET`/`POST`, and `content-type`, but its `ANY /{proxy+}` integration still sent the preflight to the failing Lambda and returned 500. The source now has an exact-origin FastAPI preflight response as a defense in depth measure, while API Gateway remains the primary CORS configuration.

A second packaging defect was found by source inspection: the JSON repository reads the project-level `data/destinations.json`, while the old Lambda asset contained only `backend/`. After fixing Mangum, the old package would therefore have failed catalog loading. The new bundle copies that dataset into the Lambda asset and the repository resolves the packaged path first.

## Changes made

- `infra/namma_ooru_infra/backend_stack.py`
  - Bundles a Linux Lambda asset using the Python 3.11 SAM build image.
  - Installs pinned backend requirements, including `mangum`.
  - Copies `backend/app` and `data/destinations.json` into the Lambda asset.
  - Passes the exact configured CORS origins to the application; default CDK context remains only `http://localhost:5173`.
- `backend/app/catalog/repository.py`
  - Resolves the packaged `/var/task/data/destinations.json` path in Lambda while retaining the project-level local-development path.
- `backend/app/main.py`
  - Adds an exact-origin CORS middleware fallback. It accepts only configured origins, only `GET`/`POST`, and `content-type`; it never uses `*`.
- `backend/tests/test_backend_foundation.py`
  - Adds regressions confirming catalog access initializes no AI provider and chat preflight returns 200 only for `http://localhost:5173`.
- `infra/tests/test_backend_stack.py`
  - Adds a regression assertion for dependency and dataset bundle inputs and checks the Lambda receives the configured CORS origins.
- `QUICKSTART.md`
  - Corrects the packaged dataset location and documents the required Docker Desktop/Linux-container prerequisite.

## Validation actually run

| Check | Result |
| --- | --- |
| Read-only deployed `GET /api/destinations` | Reproduced HTTP 500 before source changes. |
| Read-only deployed `OPTIONS /api/chat` | Reproduced HTTP 500 before source changes; API Gateway returned exact CORS headers but the proxy Lambda failed. |
| CloudWatch/Lambda configuration inspection | Confirmed `No module named 'mangum'` and confirmed deployed HTTP API uses only `http://localhost:5173` for CORS. |
| `backend`: full `python -m pytest` | **190 passed**; one pre-existing pytest warning: `hypothesis_profile` is unknown in this local Python 3.12 environment. |
| `backend`: `black --check` and `ruff check` | Passed. |
| `backend`: `mypy app` | Existing unrelated failure in `app/ai.py:198`: `str | None` is passed where `str` is expected. This file was not changed. |
| `data`: `python data/scripts/validate.py` | Passed: `1 valid, 0 error(s), 0 warning(s)`. |
| `infra`: bundle regression test (`pytest tests/test_backend_stack.py -k lambda_bundling`) | Passed: **1 passed**. |
| `infra`: full `pytest tests/test_backend_stack.py` | Blocked after the independent bundle test by the stopped Docker Desktop Linux daemon, because CDK must build a Linux Lambda artifact. |
| `infra`: `npx cdk synth namma-ooru-backend` | Blocked for the same Docker daemon issue. CDK showed the intended bundling command before failing to connect to `//./pipe/dockerDesktopLinuxEngine`. |
| `git diff --check` | Passed. |

Start Docker Desktop with Linux containers enabled, then rerun the infrastructure tests and synth below. The CDK bundle deliberately uses Linux so `pydantic-core` and other dependencies are compatible with AWS Lambda; do not replace it with a Windows local pip bundle.

## Redeploy and smoke test (Windows PowerShell)

Only the **backend stack** needs redeployment. Do **not** redeploy `namma-ooru-ai` unless you separately changed KB documents, model configuration, or AI infrastructure. No catalog S3 seed or Bedrock ingestion is required for `/health`, `/api/destinations`, or CORS verification.

```powershell
Set-Location "C:\Documents\AWS_POSTS\kirouniversity\kiro_university_challenge_ugmdu\Namma_Ooru"

# Start Docker Desktop first and wait until this returns a server version.
docker version --format '{{.Server.Version}}'

# Use the same profile/region as the existing deployment.
$profile = "<PROFILE>"
$region = "us-east-1"
$env:AWS_PROFILE = $profile
$env:AWS_DEFAULT_REGION = $region
$env:CDK_DEFAULT_REGION = $region

Set-Location .\infra
python -m pytest tests\test_backend_stack.py
npx cdk synth namma-ooru-backend --profile $profile
npx cdk deploy namma-ooru-backend --profile $profile

$apiUrl = aws cloudformation describe-stacks --stack-name namma-ooru-backend --region $region --profile $profile --query "Stacks[0].Outputs[?OutputKey=='BackendApiUrl'].OutputValue" --output text
$apiUrl

# All of these must be successful. The destination request must return JSON.
Invoke-WebRequest -Uri "$apiUrl/health" -UseBasicParsing
Invoke-WebRequest -Uri "$apiUrl/api/destinations" -UseBasicParsing

# This must return HTTP 200 with Access-Control-Allow-Origin: http://localhost:5173.
Invoke-WebRequest -Uri "$apiUrl/api/chat" -Method Options -UseBasicParsing -Headers @{
  Origin = "http://localhost:5173"
  "Access-Control-Request-Method" = "POST"
  "Access-Control-Request-Headers" = "content-type"
}

# Run the local frontend against the deployed backend.
Set-Location ..\frontend
npm ci
$env:VITE_API_BASE_URL = $apiUrl
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`) after the final command. Confirm the destination card loads and chat no longer reports a browser preflight failure. If the local Vite port is changed, update the CDK `namma-ooru:corsAllowedOrigins` context to that exact origin and redeploy **only** `namma-ooru-backend`.
