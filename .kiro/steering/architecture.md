# Architecture Steering — Namma Ooru

## Layers
- **Frontend:** React + TypeScript + Vite, Tailwind, React Query, Framer Motion, MapLibre GL.
  Deployed to AWS Amplify Hosting.
- **Backend:** FastAPI (Python 3.11), Pydantic models. Runs locally in dev; deploys to AWS Lambda
  behind API Gateway (HTTP API) via Mangum.
- **Data:** Versioned JSON dataset behind a repository abstraction; DynamoDB-ready. Destination
  data is never hard-coded into UI components.
- **AI/RAG:** Amazon Bedrock (LLM + Titan embeddings) + Bedrock Knowledge Base with S3 source and
  S3 Vectors store.
- **IaC:** AWS CDK v2 (Python) under `infra/`, split into stacks: data, ai, backend, frontend,
  monitoring.

## Rules
- Keep AI behind an interface with a local mock so the app is demoable and testable without live
  AWS. Live calls are gated by environment configuration.
- Prefer **deterministic cores** (itinerary engine, filter engine, review rules) as pure functions
  so they can be property-tested. The AI layer selects candidates and writes prose; it must route
  structural changes through the deterministic core so invariants always hold.
- The map is accessed through a `MapProvider` interface so providers are swappable (Req 10.4).
- Do not introduce microservices, Kubernetes, Kafka, Redis, complex auth, or extra databases
  unless a requirement demands it. Prefer the simplest design that satisfies the requirement.
- Backend deploys independently so a **local frontend can be tested against the deployed backend**
  before the frontend is deployed to Amplify.

## AWS / CDK
- Reusable constructs where they reduce duplication. Least-privilege IAM. Environment-specific
  config via CDK context. Useful CloudFormation outputs (API URL, bucket names, KB id). No
  hardcoded credentials; resolve via the standard AWS credential chain / IAM roles.
