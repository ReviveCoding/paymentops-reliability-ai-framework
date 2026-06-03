# Full Public Dataset Adapter Readiness

## Purpose

Document full-public-dataset adapter readiness while keeping the repository small and sample-data runnable.

## Added adapters

| Adapter | Local input expected | Output |
|---|---|---|
| `src/data/adapters/cfpb_full_adapter.py` | CFPB complaint CSV export | Project common case schema |
| `src/data/adapters/ieee_cis_adapter.py` | IEEE-CIS transaction CSV and optional identity CSV | Project common case schema |
| `src/data/adapters/ibm_aml_adapter.py` | IBM AML-style transaction CSV | Project common case schema |

## Boundary

The adapters do not download public datasets and do not include large raw files. They only standardize user-provided local public exports.
