# CI/CD and Docker Readiness

## Purpose

Add repository hygiene and CI/CD readiness evidence.

## Added files

| File | Purpose |
|---|---|
| `Dockerfile` | Containerized FastAPI service and local project runtime |
| `.github/workflows/ci.yml` | GitHub Actions workflow that installs dependencies, runs `make all`, and uploads reports/artifacts |

## Boundary

This is CI/CD-ready scaffolding. A remote GitHub Actions pass should only be claimed after pushing to GitHub and verifying a successful workflow run.
