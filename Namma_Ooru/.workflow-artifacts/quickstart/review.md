# AWS backend deployment and local frontend quickstart

The quickstart documents the requested Windows PowerShell workflow: it deploys the data, AI/RAG, and backend stacks while deliberately skipping the optional Amplify frontend stack, then points local Vite at `BackendApiUrl`. It correctly records the manual KB validation/build/upload/ingestion requirement, distinguishes bundled catalog data from KB source data, and grounds its cost guidance in official, regional and time-sensitive AWS references. However, the stated sequence cannot be followed as written because the KB commands require variables that the document defines only after the AI and backend deployments those commands precede. It also labels the backend's mandatory CloudWatch log group as optional monitoring, making the backend-only resource and cost inventory inaccurate. Watch for: **confirmed** deployment sequencing and resource-classification errors need correction before this is used to deploy.

**Verdict**: NEEDS_CHANGES

## High-level view

The data and AI workflow is structurally right—data stack, KB document preparation and upload, AI stack, ingestion, backend—but the output retrieval section is positioned after backend deployment. **Confirmed:** `$sourceBucket`, `$kbId`, and `$dataSourceId` are needed earlier, so a new deployer has no documented way to populate them at the point they are required.

The resource inventory otherwise tracks the CDK architecture closely and keeps Amplify separate for the requested local-frontend route. **Confirmed:** the `BackendLogGroup` is created by `BackendStack`, regardless of whether `namma-ooru-monitoring` is deployed; it must be classified as backend-required and included in the corresponding fixed/usage cost discussion.

<details>
<summary>Issues (2)</summary>

1. **Output variables are unavailable at KB setup** — **confirmed:** retrieve `SourceDataBucketName` immediately after deploying `namma-ooru-data`, then retrieve `KnowledgeBaseId` and `DataSourceId` immediately after `namma-ooru-ai`; only retrieve `BackendApiUrl` after the backend deploy. This removes the circular dependency in the documented flow.
2. **Backend log group is marked optional** — **confirmed:** move the one-month `BackendLogGroup` from “Optional monitoring” to “Backend required” in the resource inventory and cost framing, because `BackendStack` always creates it.

</details>

<details>
<summary>Details</summary>

## KB preparation cannot obtain its required stack outputs

Section 3.3 requires the data stack to be deployed, then directs the deployer to complete section 4 before the AI and backend stacks are deployed. Section 4's `aws s3 sync` command depends on `$sourceBucket`, while the ingestion commands depend on `$kbId` and `$dataSourceId`. The only definitions of all three are in section 3.5, which says to retrieve them “after deployment” and queries both `namma-ooru-ai` and `namma-ooru-backend`. **Confirmed:** following the stated order produces unset PowerShell variables—or requires the deployer to infer and reorder the commands—so the required KB upload and ingestion are not executable from the guide as written.

The source files and audit support a staged output read instead:

```text
namma-ooru-data
  └─ read SourceDataBucketName → build/upload data\kb
namma-ooru-ai
  └─ read KnowledgeBaseId + DataSourceId → ingest and wait
namma-ooru-backend
  └─ read BackendApiUrl → set VITE_API_BASE_URL and run Vite
```

Split section 3.5 at those boundaries, retain the documented `--profile` and `--region` arguments, and make each command block introduce the variables it consumes. The remainder of the data treatment is sound: `build_kb.py` is a local generator, no catalog S3 seed is claimed, the source bucket upload is explicitly manual, and the guide warns that a completed ingestion status—not merely job creation—is required.

## Backend observability is not optional infrastructure

The table classifies the CloudWatch Logs log group as “Optional monitoring,” alongside the two alarms and dashboard. **Confirmed:** `infra/namma_ooru_infra/backend_stack.py` always constructs `BackendLogGroup` before it creates the Lambda; only the alarms/dashboard belong to `MonitoringStack`. A backend-only deployment therefore creates the log group with one-month retention even if `namma-ooru-monitoring` is never deployed.

This is a documentation accuracy issue rather than merely a label preference: the requested resource inventory must separate backend-only resources from optional monitoring, and the single-user cost explanation should make clear that log ingestion, storage, and query charges remain possible on the minimum backend deployment. The guide already appropriately calls out CloudWatch as a cost driver, so moving the row and adjusting its group resolves the inconsistency.

</details>

<details>
<summary>File map</summary>

- `QUICKSTART.md` — deployment guide under review; contains the two corrections above.
- `.workflow-artifacts/quickstart/audit.md` — recorded validation outcomes and deployment facts used for this review.
- `infra/namma_ooru_infra/data_stack.py` — source-bucket output used before KB upload.
- `infra/namma_ooru_infra/ai_stack.py` — KB/data-source outputs used for ingestion.
- `infra/namma_ooru_infra/backend_stack.py` — mandatory log group, backend output, Lambda, and CORS configuration.
- `infra/namma_ooru_infra/frontend_stack.py` — optional Amplify resources.
- `data/scripts/build_kb.py` — local KB document generation behavior.
- `frontend/package.json` — local Vite/npm command definitions.

Full documentation diff/context: `QUICKSTART.md` and `.workflow-artifacts/quickstart/audit.md`.

</details>
