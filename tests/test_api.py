import io

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import full_analysis
from app.utils import uploads
from tests.helpers import make_vcf, record, sample

client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    calls = []

    def fake(**kwargs):
        calls.append(kwargs)
        return {
            "summary": "stub", "biological_mechanism": "stub", "clinical_impact": "stub",
            "cpic_alignment_note": "stub", "variant_citations": kwargs["rsids"], "source": "gemini",
        }

    monkeypatch.setattr(full_analysis, "generate_explanation", fake)
    return calls


def post(vcf, drugs, name="p.vcf"):
    data = vcf.encode() if isinstance(vcf, str) else vcf
    return client.post(
        "/full-analysis",
        files={"file": (name, io.BytesIO(data), "text/plain")},
        data={"drugs": drugs},
    )


def test_health():
    assert client.get("/health").status_code == 200


def test_single_drug_still_returns_list():
    r = post(sample("VCF/PATIENT_003.vcf"), ["FLUOROURACIL"])
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) == 1
    assert body[0]["pharmacogenomic_profile"]["phenotype"] == "IM"
    assert body[0]["risk_assessment"]["risk_label"] == "Adjust Dosage"
    assert "disclaimer" in body[0]


def test_multiple_drugs_comma_separated_and_deduplicated():
    r = post(sample("VCF/PATIENT_002.vcf"), ["warfarin, codeine", "WARFARIN"])
    assert [x["drug"] for x in r.json()] == ["WARFARIN", "CODEINE"]


def test_warfarin_limitation_warning_present():
    r = post(sample("VCF/PATIENT_002.vcf"), ["WARFARIN"])
    assert any("VKORC1" in w for w in r.json()[0]["warnings"])


def test_unsupported_drug_422():
    r = post(sample("VCF/PATIENT_002.vcf"), ["ASPIRIN"])
    assert r.status_code == 422 and "ASPIRIN" in r.json()["detail"]


def test_blank_drug_422():
    assert post(sample("VCF/PATIENT_002.vcf"), [" , "]).status_code == 422


def test_invalid_vcf_400():
    assert post("garbage", ["CODEINE"]).status_code == 400


def test_non_utf8_400_on_both_endpoints():
    r = client.post("/validate-vcf", files={"file": ("x.vcf", io.BytesIO(b"\xff\xfe\x00bad"), "text/plain")})
    assert r.status_code == 400
    assert post(b"\xff\xfe\x00bad", ["CODEINE"]).status_code == 400


def test_oversized_upload_413(monkeypatch):
    monkeypatch.setattr(uploads, "MAX_UPLOAD_BYTES", 100)
    r = post(sample("VCF/PATIENT_003.vcf"), ["CODEINE"])
    assert r.status_code == 413


def test_validate_endpoint_reports_coverage():
    r = client.post("/validate-vcf", files={"file": ("x.vcf", io.BytesIO(sample("VCF/PATIENT_003.vcf").encode()), "text/plain")})
    body = r.json()
    assert body["valid"] and body["variant_count"] == 5
    assert "CYP2D6" in body["genes_covered"]


def test_uncovered_gene_skips_llm_and_is_not_reassuring(fake_llm):
    vcf = make_vcf(record("DPYD", "*2A", "rs3918290", "0/0"))
    item = post(vcf, ["CODEINE"]).json()[0]
    assert item["risk_assessment"]["risk_label"] == "Unknown"
    assert item["risk_assessment"]["severity"] == "unknown"
    assert item["llm_generated_explanation"]["source"] == "static"
    assert fake_llm == []


def test_llm_called_once_per_covered_drug(fake_llm):
    post(sample("VCF/PATIENT_003.vcf"), ["CODEINE", "WARFARIN"])
    assert len(fake_llm) == 2
    assert {c["drug"] for c in fake_llm} == {"CODEINE", "WARFARIN"}


def test_llm_failure_falls_back_with_200(monkeypatch):
    from app.services import llm_service

    def boom():
        raise RuntimeError("no key")

    monkeypatch.undo()
    monkeypatch.setattr(llm_service, "_get_client", boom)
    r = post(sample("VCF/PATIENT_003.vcf"), ["CODEINE"])
    assert r.status_code == 200
    assert r.json()[0]["llm_generated_explanation"]["source"] == "fallback"
