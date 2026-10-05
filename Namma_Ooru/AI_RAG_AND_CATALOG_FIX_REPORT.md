# AI/RAG and catalog repair report

## Completed source changes

- `data/destinations.json` now contains **50 valid, source-attributed Tamil Nadu destinations** and `data/kb` contains exactly **50 Markdown documents and 50 metadata sidecars**.
- The catalog deliberately covers Chennai, Madurai, Coimbatore, Tiruchirappalli, Thanjavur, Kanchipuram, Tirunelveli, Kanyakumari, Nilgiris/Ooty, Chengalpattu/Mamallapuram, Ramanathapuram/Rameswaram, Vellore, Salem, Erode, Thoothukudi, Dindigul/Kodaikanal, and Theni, plus Tenkasi, Tiruvannamalai, Viluppuram, Nagapattinam, Cuddalore, Ariyalur, Krishnagiri, and Sivaganga.
- Each record uses a Tamil Nadu Tourism source URL and `Tamil Nadu Tourism` government-tourism attribution with retrieval date `2026-10-05`; dynamic details that were not sourced remain absent/null rather than invented. A malformed Mamallapuram source hostname was corrected.
- Itinerary generation treats a catalog city or Tamil Nadu district named in the trip context as a hard candidate constraint. When the catalog has no matching destination, it returns the requested empty days with `no_data_reason`; it does not substitute places from another location. The regression includes a Chennai request against a Madurai-only fixture.
- Chat still returns the safe `AI_UNAVAILABLE` public response when Bedrock fails; it never fabricates an answer. The frontend presents an accessible retry state. The backend now writes only the Bedrock error code (when supplied by AWS) or exception class to Lambda logs. It does **not** log the question, retrieved content, credentials, or raw downstream error text. The accompanying regression verifies this.

## Read-only deployed diagnosis (us-east-1)

Read-only AWS inspection on 2026-10-05 found Lambda `namma-ooru-backend` active with `AI_PROVIDER=bedrock`, `BEDROCK_KB_ID=LIU7ZQBCZM`, primary profile `us.amazon.nova-pro-v1:0`, and fallback profile `global.amazon.nova-2-lite-v1:0`. Knowledge Base `LIU7ZQBCZM` is `ACTIVE`; data source `HDTMOYVPZM` is `AVAILABLE`.

The currently deployed Lambda logs contain only Lambda start/end/report records, not the downstream Bedrock exception. Consequently, the existing 503 cannot be attributed safely to model access, IAM, a quota, or an AWS service outage from the available evidence. The new source-level safe diagnostic is **not deployed yet**; deploy it first, reproduce one chat request, then inspect the resulting error code in CloudWatch.

The deployed KB predates this 50-record catalog. Uploading the rebuilt documents and starting an ingestion job is required before deployed chat can retrieve this catalog. This is independent of the 503 diagnosis.

For Bedrock error semantics and cross-Region profile prerequisites, see [Amazon Bedrock InvokeModel errors](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModel.html) and [cross-Region inference profile access troubleshooting](https://repost.aws/knowledge-center/bedrock-access-denied-exception). If the new log says `AccessDeniedException`, enable/request access for both configured Nova profiles/models in the account and permit every destination Region required by the profiles (including Organizations SCPs). If it says `ResourceNotFoundException` or `ValidationException`, confirm the profile IDs and KB configuration. `ThrottlingException`, `ServiceQuotaExceededException`, `ModelNotReadyException`, and `ServiceUnavailableException` require the corresponding retry/quota/service-availability action; the source code must not fake a response.

## Validation completed

- `python data/scripts/validate.py`: **50 valid, 0 errors, 0 warnings**.
- `python data/scripts/build_kb.py`: **50 KB documents, 50 metadata sidecars**.
- `cd backend; python -m pytest`: **192 passed** (one pre-existing `hypothesis_profile` pytest configuration warning).
- `cd backend; ruff check app tests`, `black --check app tests`, and `mypy app tests`: passed.
- `cd frontend; npm test`: **15 files, 76 tests passed**.
- `cd frontend; npm run typecheck`, `npm run lint`, and `npm run build`: passed. Vite emitted only its existing large-chunk warning.
- `cd infra; python -m pytest tests`: **30 passed**.
- `cd infra; npx cdk synth namma-ooru-backend`: **passed on Windows**. The local bundler rebuilt the Lambda asset using Python 3.11-compatible `manylinux2014_x86_64` wheels without Docker. No cloud resource was changed.

## Required deployment and ingestion (not run)

These commands are intentionally provided for the account owner to run after reviewing the source changes. No deployment, S3 upload, or KB ingestion was performed in this work session.

```powershell
$region = 'us-east-1'
$profile = '<your-profile>'
$kbId = 'LIU7ZQBCZM'
$dataSourceId = 'HDTMOYVPZM'

# Re-run locally from the repository root before deploying.
python data/scripts/validate.py
python data/scripts/build_kb.py

# Deploy only the backend stack so the location safety and safe Bedrock diagnostics reach Lambda.
Push-Location infra
npx cdk deploy namma-ooru-backend --profile $profile
Pop-Location

# Upload all rebuilt KB source documents, then start and poll the ingestion.
$bucket = aws cloudformation describe-stacks --stack-name namma-ooru-data --region $region --profile $profile --query "Stacks[0].Outputs[?OutputKey=='SourceDataBucketName'].OutputValue" --output text
aws s3 sync data/kb "s3://$bucket/" --delete --region $region --profile $profile
$job = aws bedrock-agent start-ingestion-job --knowledge-base-id $kbId --data-source-id $dataSourceId --region $region --profile $profile --query 'ingestionJob.ingestionJobId' --output text
aws bedrock-agent get-ingestion-job --knowledge-base-id $kbId --data-source-id $dataSourceId --ingestion-job-id $job --region $region --profile $profile
```

After the ingestion job reports `COMPLETE`, get the backend URL from the backend stack output and smoke-test it:

```powershell
$apiUrl = aws cloudformation describe-stacks --stack-name namma-ooru-backend --region $region --profile $profile --query "Stacks[0].Outputs[?contains(OutputKey,'ApiUrl')].OutputValue" --output text
Invoke-WebRequest -Uri "$apiUrl/health" -UseBasicParsing
Invoke-WebRequest -Uri "$apiUrl/api/destinations" -UseBasicParsing
Invoke-RestMethod -Method Post -Uri "$apiUrl/api/chat" -ContentType 'application/json' -Body '{"question":"Tell me about Meenakshi Amman Temple"}'
Invoke-RestMethod -Method Post -Uri "$apiUrl/api/itineraries" -ContentType 'application/json' -Body '{"destination_context":"3-day Chennai temples and food trip","day_count":3}'
```

If chat remains 503 after the backend deploy, inspect the safe error code without exposing prompts or secrets:

```powershell
aws logs tail '/aws/lambda/namma-ooru-backend' --since 15m --region $region --profile $profile --format short
```

The location-safe source changes and this report do not claim that the deployed Lambda, Amplify frontend, S3 KB documents, or ingestion job have been updated.
