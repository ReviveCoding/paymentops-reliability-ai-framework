# Run Verification

Verified after the final local/GitHub runnability hardening pass.

```text
make clean all
python -m pytest -q
FastAPI smoke test: /health and /investigate
```

## Final local results

| Item | Value |
|---|---:|
| `make clean all` | PASS |
| Local lightweight test harness | 21 passed, 0 failed |
| `python -m pytest -q` | 21 passed |
| Release gate | PASS |
| Release failed checks | [] |
| Repository audit | PASS |
| API contract validation | PASS |
| Enhanced PR-AUC | 0.829 |
| Enhanced F2 | 0.566 |
| Enhanced false auto-clear | 0.388 |
| Enhanced Brier | 0.154 |
| Enhanced ECE | 0.073 |
| Evidence-slot F1 | 1.000 |
| Data contract | PASS |
| Drift backtest | PASS |
| Red-team safety | PASS |
| Observability | traces/metrics/logs exported |
| FastAPI `/health` | PASS |
| FastAPI `/investigate` | PASS |

## Issue fixed in final pass

The repository audit originally checked for `reports/09_release_decision.md` before the release gate generated it, which created a circular dependency and could leave a stale `REVIEW` release result after a clean run. This was fixed by making the repository audit independent of the release-gate output. The release gate now reads a passing repository audit and produces `release_status: PASS` with no failed checks after `make clean all`.

## Docker note

Docker CLI is not available in this sandbox runtime, so Docker image build was not executed here. The repository includes a Dockerfile and GitHub Actions workflow for external verification.

## Claim boundary

The project is local/GitHub-runnable and uses public-style samples and synthetic ISO 20022-inspired payment workflows. It does not use proprietary bank data, real customer account data, production payment logs, or real AWS deployment logs.
