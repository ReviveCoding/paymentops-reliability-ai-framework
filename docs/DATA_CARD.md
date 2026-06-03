# Data Card

This project supports local evaluation with external public/proxy datasets stored outside the repository.

## External Data Root

Set:

    $env:PAYMENTOPS_EXTERNAL_DATA = "C:\Users\bjw-0\Downloads\paymentops_external_data"

## Supported External Datasets

- CFPB complaint narratives
- IBM AML-style synthetic transaction data
- Generated common-schema validation outputs
- Generated model-improvement and score-alignment outputs

## Committed to GitHub

- source code
- tests
- lightweight sample reports
- documentation
- CI configuration
- small synthetic/sample fixtures when needed

## Not Committed to GitHub

- full external datasets
- raw CFPB full-data CSVs
- raw IBM AML full-data CSVs
- large generated validation CSVs
- model artifacts
- compressed raw datasets
- credentials or secrets

## Large Artifact Rule

Large generated artifacts should be written under:

    C:\Users\bjw-0\Downloads\paymentops_external_data
