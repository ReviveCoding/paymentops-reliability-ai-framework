# Claim Boundary

This project is intentionally conservative in its claims.

## Data boundary

- Uses local sample data modeled after public financial-operations workflows.
- Uses synthetic ISO 20022-inspired pacs.008 and pacs.002 payment workflows.
- Does not use JPMorgan Chase data.
- Does not use proprietary bank data.
- Does not use real customer account data.
- Does not use production payment transaction logs.

## Deployment boundary

- Local/GitHub-runnable only.
- Production-style offline framework.
- Not deployed in production.
- No claim of regulatory certification.
- No claim of official bank validation.

## MCP and LangGraph boundary

- MCP-style artifacts are included as tool/resource/prompt contracts.
- This is not a hosted enterprise MCP server.
- LangGraph orchestration is optional and falls back to a deterministic local graph if the dependency is unavailable.

## AWS boundary

- AWS/SageMaker-compatible scaffolds may be included.
- Unless a user adds actual run logs, this project must not be described as AWS-deployed.
