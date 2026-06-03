# PySpark-Compatible Feature Pipeline Log

- Engine used: `pandas_fallback`
- Rows processed: `288`
- Output: `data/processed/feature_table.csv`
- Features added: `text_length`, `is_payment_case`, `amount_log`

This pipeline is intentionally runnable without a Spark installation. By default it uses a deterministic pandas fallback for CI stability. Set `PAYMENTOPS_USE_PYSPARK=1` to exercise the local Spark DataFrame path when PySpark is installed.
