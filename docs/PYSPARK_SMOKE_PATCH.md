# PySpark Smoke Patch

This patch replaces the PySpark ETL script with a Windows-safe smoke path.

It still uses PySpark for CSV ingestion, feature engineering, grouping, and metrics. It avoids Spark's Hadoop local-file writer on Windows by collecting the small smoke output to pandas and writing local artifacts outside Spark's Hadoop output committer.

Claim boundary: local public/proxy or generated sample data only. No production payment logs, JPMC systems, or proprietary bank data.
