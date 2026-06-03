# Repository Runnability and Efficiency Audit

## Purpose

This audit checks whether the repository remains lightweight, local/GitHub runnable, and portfolio-safe after the hardening loop.

## Summary

| Field | Value |
|---|---|
| audit_status | `PASS` |
| num_files | `260` |
| num_python_files | `101` |
| num_report_files | `67` |
| total_size_mb | `1.734121` |

## Large files

`[]`

## Missing required files

`[]`

## Runnable commands

- `make all`
- `make test`
- `make serve`

## Optimization decision

No generated raw public datasets or large binaries are committed. The repository keeps sample/synthetic data for portability and keeps full-dataset adapters as code rather than cached data.
