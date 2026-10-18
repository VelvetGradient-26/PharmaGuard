import pytest

from app.config.constants import (
    ALLELE_FUNCTION, PHENOTYPE_THRESHOLDS, PRIMARY_GENE_MAP, SUPPORTED_DRUGS, SUPPORTED_GENES,
)
from app.services.cpic_rules import CPIC_RULES, evaluate_drug_risk
from app.services.phenotype_engine import build_profile
from app.services.vcf_parser import parse_vcf
from tests.helpers import make_vcf, record


def profile(*records):
    return build_profile(parse_vcf(make_vcf(*records)))


def test_every_supported_drug_gene_and_phenotype_has_a_rule():
    assert set(PRIMARY_GENE_MAP) == SUPPORTED_DRUGS
    assert set(ALLELE_FUNCTION) == set(PHENOTYPE_THRESHOLDS) == SUPPORTED_GENES
    for drug, gene in PRIMARY_GENE_MAP.items():
        phenotypes = {p for _, p in PHENOTYPE_THRESHOLDS[gene]}
        rules = set(CPIC_RULES[drug][gene])
        # CYP2D6 UM and friends are defined for completeness; every other phenotype must be covered.
        assert phenotypes - rules <= {"UM"} if gene == "CYP2D6" else phenotypes <= rules, (drug, gene)


def test_het_dpyd_gets_dose_reduction_not_avoid():
    result = evaluate_drug_risk("FLUOROURACIL", profile(record("DPYD", "*2A", "rs3918290", "0/1")))
    assert result["risk_label"] == "Adjust Dosage"
    assert result["confidence_score"] == 0.95


def test_hom_dpyd_is_avoid():
    result = evaluate_drug_risk("FLUOROURACIL", profile(record("DPYD", "*2A", "rs3918290", "1/1")))
    assert result["risk_label"] == "Toxic" and result["severity"] == "critical"


def test_phase_ambiguity_lowers_confidence():
    p = profile(record("CYP2C9", "*2", "rs1799853", "0/1"), record("CYP2C9", "*3", "rs1057910", "0/1"))
    assert evaluate_drug_risk("WARFARIN", p)["confidence_score"] == 0.75


def test_uncovered_gene_is_unknown_not_safe():
    result = evaluate_drug_risk("CODEINE", profile(record("DPYD", "*2A", "rs3918290", "0/0")))
    assert result["risk_label"] == "Unknown"
    assert result["severity"] == "unknown"
    assert result["confidence_score"] == 0.0


def test_indeterminate_gene_is_not_safe():
    result = evaluate_drug_risk("CLOPIDOGREL", profile(record("CYP2C19", "*99", "rs99", "0/1")))
    assert result["risk_label"] == "Indeterminate"
    assert result["confidence_score"] == 0.0


def test_unsupported_drug_raises():
    with pytest.raises(ValueError):
        evaluate_drug_risk("ASPIRIN", {})
