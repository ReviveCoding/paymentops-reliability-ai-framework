from src.data.ingest_cfpb import generate_cfpb_sample
from src.data.ingest_fraud import generate_fraud_sample
from src.data.generate_iso20022 import generate_iso20022_cases


def test_sample_generators_have_rows():
    assert len(generate_cfpb_sample(10)) == 10
    assert len(generate_fraud_sample(10)) == 10
    assert len(generate_iso20022_cases(10)) == 10
