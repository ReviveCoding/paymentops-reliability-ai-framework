# PySpark ETL Feature Store Artifact

## Claim boundary

Local PySpark ETL artifact using public/proxy or generated sample data only. No production payment logs, proprietary bank data, real customer data, or JPMC data.

## Outputs

- Input CSV: `C:\Users\bjw-0\Downloads\paymentops_external_data_pyspark_smoke\pyspark_etl_outputs\sample_paymentops_cases.csv`
- Generated sample: `True`
- Rows: `2000`
- Positives: `74`
- Positive rate: `0.037000`
- Amount p95: `3408.200000`
- Parquet status: `PARQUET`
- Feature store Parquet: `C:\Users\bjw-0\Downloads\paymentops_external_data_pyspark_smoke\pyspark_etl_outputs\feature_store_parquet\part-00000.parquet`
- Slice metrics Parquet: `C:\Users\bjw-0\Downloads\paymentops_external_data_pyspark_smoke\pyspark_etl_outputs\slice_metrics_parquet\part-00000.parquet`
- Sample CSV: `C:\Users\bjw-0\Downloads\paymentops_external_data_pyspark_smoke\pyspark_etl_outputs\feature_store_sample_csv\part-00000.csv`

## Resume-safe wording

Added a local PySpark ETL path that materializes PaymentOps-style feature-store artifacts, slice metrics, and validation reports under public/proxy data boundaries.
