from __future__ import annotations

from pathlib import Path
import os
from src.utils import DATA_DIR, REPORTS_DIR, write_report
from src.data.common_schema import load_common_cases


def run_spark_or_pandas_pipeline() -> str:
    """Create a model-ready feature table using PySpark if available, with pandas fallback."""
    df = load_common_cases()
    out = DATA_DIR / "processed" / "feature_table.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    engine = "pandas_fallback"
    # Default to pandas for deterministic local/GitHub execution. Set
    # PAYMENTOPS_USE_PYSPARK=1 to exercise the local PySpark path.
    if os.environ.get("PAYMENTOPS_USE_PYSPARK", "0") == "1":
        try:
            from pyspark.sql import SparkSession
            spark = SparkSession.builder.master("local[1]").appName("paymentops_feature_pipeline").getOrCreate()
            sdf = spark.createDataFrame(df)
            sdf = sdf.withColumnRenamed("text", "case_text")
            pdf = sdf.toPandas()
            spark.stop()
            df = pdf.rename(columns={"case_text": "text"})
            engine = "pyspark_local"
        except Exception:
            engine = "pandas_fallback_after_pyspark_attempt"
    df["text_length"] = df["text"].fillna("").str.len()
    df["is_payment_case"] = (df["case_type"].str.contains("payment|fraud", case=False)).astype(int)
    df["amount_log"] = (df["amount"].astype(float) + 1.0).map(lambda x: __import__('math').log(x))
    df.to_csv(out, index=False)
    body = f"""
- Engine used: `{engine}`
- Rows processed: `{len(df)}`
- Output: `data/processed/feature_table.csv`
- Features added: `text_length`, `is_payment_case`, `amount_log`

This pipeline is intentionally runnable without a Spark installation. By default it uses a deterministic pandas fallback for CI stability. Set `PAYMENTOPS_USE_PYSPARK=1` to exercise the local Spark DataFrame path when PySpark is installed.
"""
    write_report(REPORTS_DIR / "pyspark_feature_pipeline_log.md", "PySpark-Compatible Feature Pipeline Log", body)
    return engine


if __name__ == "__main__":
    print(run_spark_or_pandas_pipeline())
