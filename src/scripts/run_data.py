from __future__ import annotations

from src.utils import ensure_dirs
from src.data.ingest_cfpb import save_cfpb_sample
from src.data.ingest_fraud import save_fraud_sample
from src.data.generate_iso20022 import save_iso20022
from src.data.common_schema import save_common_cases
from src.data.quality_gates import write_data_inventory
from src.data.spark_feature_pipeline import run_spark_or_pandas_pipeline


def main() -> None:
    ensure_dirs()
    save_cfpb_sample()
    save_fraud_sample()
    save_iso20022()
    save_common_cases()
    run_spark_or_pandas_pipeline()
    write_data_inventory()


if __name__ == "__main__":
    main()
