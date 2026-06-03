from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


def external_root() -> Path:
    return Path(os.environ.get("PAYMENTOPS_EXTERNAL_DATA", Path.cwd().parent / "paymentops_external_data"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def find_input_csv(root: Path) -> Path | None:
    candidates = [
        root / "validation_outputs" / "external_common_case_schema.csv",
        root / "validation_outputs" / "external_common_case_schema_sample.csv",
        root / "pyspark_etl_outputs" / "sample_paymentops_cases.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def make_sample_csv(path: Path, rows: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write("case_id,source,event_time,text,amount,label\n")
        for i in range(rows):
            source = "ibm_aml_style" if i % 2 == 0 else "cfpb_complaint"
            high = 1 if i % 37 == 0 or i % 101 == 0 else 0
            amount = 100 + (i % 5000) * 1.7
            if high:
                amount *= 8.5
            text = "urgent fraud wire transfer review" if high else "routine payment service inquiry"
            ts = (base_time + timedelta(minutes=i)).isoformat()
            f.write(f"case_{i},{source},{ts},{text},{amount:.2f},{high}\n")
    return path


def pick_col(cols: list[str], candidates: list[str]) -> str | None:
    lower = {c.lower().strip(): c for c in cols}
    for cand in candidates:
        if cand.lower().strip() in lower:
            return lower[cand.lower().strip()]
    return None


def quoted(col_name: str) -> str:
    return "`" + col_name.replace("`", "``") + "`"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-rows", type=int, default=2000)
    parser.add_argument("--spark-master", default="local[2]")
    parser.add_argument("--shuffle-partitions", type=int, default=2)
    parser.add_argument("--force-sample", action="store_true")
    args = parser.parse_args()

    root = external_root()
    out_dir = root / "pyspark_etl_outputs"
    report_path = Path("reports") / "29_pyspark_etl_feature_store_artifact.md"
    metrics_path = Path("reports") / "pyspark_etl_feature_store_metrics.json"

    input_csv = None if args.force_sample else find_input_csv(root)
    generated_sample = False
    if input_csv is None:
        input_csv = make_sample_csv(out_dir / "sample_paymentops_cases.csv", args.sample_rows)
        generated_sample = True

    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    spark = (
        SparkSession.builder
        .appName("paymentops-pyspark-etl-smoke")
        .master(args.spark_master)
        .config("spark.sql.shuffle.partitions", str(args.shuffle_partitions))
        .config("spark.sql.ansi.enabled", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    raw = (
        spark.read
        .option("header", True)
        .option("inferSchema", False)
        .option("multiLine", True)
        .option("quote", '"')
        .option("escape", '"')
        .option("mode", "PERMISSIVE")
        .csv(str(input_csv))
    )

    cols = raw.columns
    case_col = pick_col(cols, ["case_id", "id", "complaint_id", "Complaint ID"])
    source_col = pick_col(cols, ["source", "dataset", "data_source"])
    time_col = pick_col(cols, ["event_time", "date_received", "Date received", "transaction_time", "timestamp", "date"])
    text_col = pick_col(cols, ["text", "narrative", "Consumer complaint narrative", "consumer_complaint_narrative", "description", "case_text"])
    amount_col = pick_col(cols, ["amount", "transaction_amount", "amt", "TransactionAmount", "transactionAmount"])
    label_col = pick_col(cols, ["label", "target", "is_fraud", "high_risk_label", "risk_label", "isFraud"])

    df = raw
    df = df.withColumn("case_id_clean", F.col(quoted(case_col)).cast("string") if case_col else F.monotonically_increasing_id().cast("string"))
    df = df.withColumn("source_clean", F.coalesce(F.col(quoted(source_col)).cast("string"), F.lit("unknown_source")) if source_col else F.lit(input_csv.parent.name))
    df = df.withColumn("event_time_clean", F.coalesce(F.to_timestamp(F.col(quoted(time_col)).cast("string")), F.current_timestamp()) if time_col else F.current_timestamp())

    if text_col:
        df = df.withColumn("text_clean", F.coalesce(F.col(quoted(text_col)).cast("string"), F.lit("")))
    else:
        text_candidates = [c for c in cols if any(k in c.lower() for k in ["issue", "product", "narrative", "text", "description"])]
        if text_candidates:
            df = df.withColumn("text_clean", F.concat_ws(" ", *[F.col(quoted(c)).cast("string") for c in text_candidates[:5]]))
        else:
            df = df.withColumn("text_clean", F.lit(""))

    amount_raw = F.coalesce(F.col(quoted(amount_col)).cast("string"), F.lit("")) if amount_col else F.lit("")
    amount_numeric = F.regexp_extract(amount_raw, r"[-+]?\d+(?:\.\d+)?", 0)
    df = df.withColumn("amount_clean", F.when(F.length(amount_numeric) > 0, amount_numeric.cast("double")).otherwise(F.lit(0.0)))

    if label_col:
        label_raw = F.lower(F.coalesce(F.col(quoted(label_col)).cast("string"), F.lit("")))
        label_number = F.regexp_extract(label_raw, r"[-+]?\d+", 0)
        df = df.withColumn(
            "label_clean",
            F.when(label_raw.rlike("true|fraud|high|yes"), F.lit(1))
            .when(F.length(label_number) > 0, label_number.cast("int"))
            .otherwise(F.lit(0)),
        )
    else:
        df = df.withColumn("label_clean", F.lit(0))

    p95_values = df.select("amount_clean").approxQuantile("amount_clean", [0.95], 0.01)
    amount_p95 = float(p95_values[0]) if p95_values else 0.0

    features = (
        df.select(
            F.col("case_id_clean").alias("case_id"),
            F.col("source_clean").alias("source"),
            F.col("event_time_clean").alias("event_time"),
            F.col("text_clean").alias("text"),
            F.col("amount_clean").alias("amount"),
            F.col("label_clean").alias("label"),
        )
        .withColumn("event_date", F.to_date("event_time"))
        .withColumn("event_month", F.date_format("event_time", "yyyy-MM"))
        .withColumn("text_length", F.length("text"))
        .withColumn("amount_log1p", F.log1p(F.greatest(F.col("amount"), F.lit(0.0))))
        .withColumn("amount_high_flag", (F.col("amount") >= F.lit(amount_p95)).cast("int"))
        .withColumn("risk_keyword_flag", F.lower(F.col("text")).rlike("fraud|urgent|wire|aml|suspicious|chargeback|unauthorized").cast("int"))
        .withColumn("etl_run_ts", F.current_timestamp())
    )

    slice_metrics = (
        features.groupBy("source", "event_month")
        .agg(
            F.count("*").alias("rows"),
            F.sum("label").alias("positives"),
            F.avg("label").alias("positive_rate"),
            F.avg("amount").alias("avg_amount"),
            F.avg("text_length").alias("avg_text_length"),
            F.avg("amount_high_flag").alias("amount_high_rate"),
            F.avg("risk_keyword_flag").alias("risk_keyword_rate"),
        )
        .orderBy("source", "event_month")
    )

    rows = features.count()
    positives = features.agg(F.sum("label")).first()[0] or 0
    sources = [r["source"] for r in features.select("source").distinct().collect()]

    feature_pdf = features.limit(args.sample_rows).toPandas()
    slice_pdf = slice_metrics.toPandas()

    feature_parquet_dir = out_dir / "feature_store_parquet"
    slice_parquet_dir = out_dir / "slice_metrics_parquet"
    csv_sample_dir = out_dir / "feature_store_sample_csv"
    feature_parquet_dir.mkdir(parents=True, exist_ok=True)
    slice_parquet_dir.mkdir(parents=True, exist_ok=True)
    csv_sample_dir.mkdir(parents=True, exist_ok=True)

    feature_parquet = feature_parquet_dir / "part-00000.parquet"
    slice_parquet = slice_parquet_dir / "part-00000.parquet"
    sample_csv = csv_sample_dir / "part-00000.csv"

    parquet_status = "PARQUET"
    try:
        feature_pdf.to_parquet(feature_parquet, index=False)
        slice_pdf.to_parquet(slice_parquet, index=False)
    except Exception as exc:
        parquet_status = f"CSV_FALLBACK: {type(exc).__name__}: {exc}"
        feature_parquet = None
        slice_parquet = None

    feature_pdf.to_csv(sample_csv, index=False)

    summary = {
        "status": "PASS",
        "input_csv": str(input_csv),
        "generated_sample": generated_sample,
        "rows": int(rows),
        "positives": int(positives),
        "positive_rate": float(positives / rows) if rows else 0.0,
        "sources": sources,
        "amount_p95": amount_p95,
        "parquet_status": parquet_status,
        "feature_store_parquet": str(feature_parquet) if feature_parquet else None,
        "slice_metrics_parquet": str(slice_parquet) if slice_parquet else None,
        "sample_csv": str(sample_csv),
        "claim_boundary": "Local PySpark ETL artifact using public/proxy or generated sample data. No production payment logs or proprietary bank data.",
    }

    write_text(metrics_path, json.dumps(summary, indent=2))
    write_text(
        report_path,
        "# PySpark ETL Feature Store Artifact\n\n"
        "## Claim boundary\n\n"
        "Local PySpark ETL artifact using public/proxy or generated sample data only. "
        "No production payment logs, proprietary bank data, real customer data, or JPMC data.\n\n"
        "## Outputs\n\n"
        f"- Input CSV: `{summary['input_csv']}`\n"
        f"- Generated sample: `{summary['generated_sample']}`\n"
        f"- Rows: `{summary['rows']}`\n"
        f"- Positives: `{summary['positives']}`\n"
        f"- Positive rate: `{summary['positive_rate']:.6f}`\n"
        f"- Amount p95: `{summary['amount_p95']:.6f}`\n"
        f"- Parquet status: `{summary['parquet_status']}`\n"
        f"- Feature store Parquet: `{summary['feature_store_parquet']}`\n"
        f"- Slice metrics Parquet: `{summary['slice_metrics_parquet']}`\n"
        f"- Sample CSV: `{summary['sample_csv']}`\n\n"
        "## Resume-safe wording\n\n"
        "Added a local PySpark ETL path that materializes PaymentOps-style feature-store artifacts, "
        "slice metrics, and validation reports under public/proxy data boundaries.\n",
    )

    spark.stop()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
