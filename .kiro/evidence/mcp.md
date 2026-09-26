# MCP Integration — Evidence (Kiro University Lesson 6)

Namma Ooru uses the **Model Context Protocol (MCP)** for real development tasks: researching
Amazon Bedrock / S3 Vectors implementation details and reviewing repository information. MCP
servers are trusted, relevant integrations — not decoration.

## Configured servers

> Note: MCP is configured through Kiro's MCP settings (`.kiro/settings/mcp.json`). That file is
> managed by the IDE and is not committed with secrets. Add the following via the MCP settings
> UI or by editing `.kiro/settings/mcp.json` yourself (the token comes from your environment, not
> source control):

```jsonc
{
  "mcpServers": {
    "aws-docs": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": { "FASTMCP_LOG_LEVEL": "ERROR" },
      "disabled": false,
      "autoApprove": ["search_documentation", "read_documentation", "recommend"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}" },
      "disabled": false
    }
  }
}
```

| Server | Why it was needed | Secrets |
|---|---|---|
| `aws-docs` (AWS Documentation MCP) | Authoritative, current AWS docs for the Bedrock + S3 Vectors RAG design instead of relying on possibly-stale model knowledge. | none |
| `github` | Review repository info (issues, PRs, files) against the private challenge repo. | `GITHUB_PERSONAL_ACCESS_TOKEN` via env only — never committed. |

## Evidence of real use

**Task:** Validate that the planned RAG architecture (Bedrock Knowledge Base + S3 as source +
S3 Vectors as vector store + RetrieveAndGenerate) is a supported, current AWS pattern before
committing to it in `design.md`.

**MCP call:** `aws-docs.search_documentation` with the phrase
*"Amazon Bedrock Knowledge Bases S3 Vectors vector store RetrieveAndGenerate"*.

**Returned (authoritative AWS docs):**
- `s3-vectors-bedrock-kb.html` — *RetrieveAndGenerate* over a Knowledge Base.
- `s3-vectors-getting-started.html` — *"Create an Amazon Bedrock knowledge base that uses S3
  Vectors as its vector store for a fully managed RAG workflow."*
- References to S3 vector bucket / S3 vector index and the Retrieve / RetrieveAndGenerate runtime
  operations.

**How Kiro used it:** confirmed the design's RAG choice is a first-class, fully-managed AWS
pattern (S3 Vectors is a valid Bedrock KB vector store; RetrieveAndGenerate is the runtime op),
so `design.md` §5 and the `ai_stack` in §6 were kept as specified rather than switching to
OpenSearch Serverless / Aurora. This directly de-risked Requirement 5.

## Secret handling
- No credentials or tokens are committed. The GitHub token is supplied via the environment.
- MCP-returned content is treated as untrusted data and is not executed.
