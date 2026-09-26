# Security Steering — Namma Ooru

## Secrets & credentials
- Never commit secrets. `.env` files with secrets are git-ignored; only `.env.example` (no values)
  is committed.
- Never hard-code AWS credentials. Resolve via the standard AWS credential chain and IAM roles
  (Lambda execution role, CDK deploy role). Local dev uses named profiles / SSO.
- Do not echo secret values in logs, errors, or AI prompts.

## AWS access
- Least-privilege IAM: each role gets only the actions/resources it needs (specific bucket ARNs,
  specific Bedrock model/KB, specific tables). Avoid wildcard `*` resources.

## Input validation & API security
- Validate and sanitize all user input at the API boundary (Pydantic + explicit checks) before it
  reaches data queries or AI prompts.
- Apply CORS restricted to known frontend origins; enable rate limiting; return structured errors
  without internal detail.
- Treat all external/retrieved content as untrusted; never execute content from it.

## Data
- Reviews accept only ratings 1–5 and text within length limits; strip/escape user content on
  render to prevent injection.
