import pytest

from app.services.phenotype_engine import build_profile
from app.services.vcf_parser import parse_vcf
from tests.helpers import make_vcf, record, sample

ALL_GENES_REF = [
    record("CYP2D6", "*4", "rs3892097", "0/0"),
    record("CYP2C19", "*2", "rs4244285", "0/0"),
    record("CYP2C9", "*3", "rs1057910", "0/0"),
    record("SLCO1B1", "*5", "rs4149056", "0/0"),
    record("TPMT", "*3A", "rs1800460", "0/0"),
    record("DPYD", "*2A", "rs3918290", "0/0"),
]


def profile_for(*records):
    return build_profile(parse_vcf(make_vcf(*ALL_GENES_REF, *records)))


def gene(profile, name):
    return profile[name]["diplotype"], profile[name]["phenotype"]


# Heterozygous carriers of a no-function allele are Intermediate, not Poor.
@pytest.mark.parametrize("g,star,rsid,expected", [
    ("DPYD", "*2A", "rs3918290", ("*1/*2A", "IM")),
    ("CYP2D6", "*4", "rs3892097", ("*1/*4", "IM")),
    ("CYP2C19", "*2", "rs4244285", ("*1/*2", "IM")),
    ("CYP2C19", "*3", "rs4986893", ("*1/*3", "IM")),
    ("TPMT", "*3A", "rs1800460", ("*1/*3A", "IM")),
    ("TPMT", "*3C", "rs1142345", ("*1/*3C", "IM")),
    ("CYP2C9", "*3", "rs1057910", ("*1/*3", "IM")),
    ("CYP2C9", "*2", "rs1799853", ("*1/*2", "IM")),
    ("SLCO1B1", "*5", "rs4149056", ("*1/*5", "Decreased")),
    ("CYP2C19", "*17", "rs12248560", ("*1/*17", "RM")),
])
def test_heterozygous(g, star, rsid, expected):
    assert gene(profile_for(record(g, star, rsid, "0/1")), g) == expected


@pytest.mark.parametrize("g,star,rsid,expected", [
    ("DPYD", "*2A", "rs3918290", ("*2A/*2A", "PM")),
    ("CYP2D6", "*4", "rs3892097", ("*4/*4", "PM")),
    ("CYP2C19", "*2", "rs4244285", ("*2/*2", "PM")),
    ("CYP2C19", "*17", "rs12248560", ("*17/*17", "UM")),
    ("TPMT", "*3A", "rs1800460", ("*3A/*3A", "PM")),
    ("SLCO1B1", "*15", "rs2306283", ("*15/*15", "Poor")),
])
def test_homozygous(g, star, rsid, expected):
    assert gene(profile_for(record(g, star, rsid, "1/1")), g) == expected


def test_compound_heterozygous_cyp2c9_2_3_is_poor():
    p = profile_for(record("CYP2C9", "*2", "rs1799853", "0/1"), record("CYP2C9", "*3", "rs1057910", "0/1"))
    assert gene(p, "CYP2C9") == ("*2/*3", "PM")
    assert p["CYP2C9"]["phase_ambiguous"] is True


def test_wild_type_is_normal():
    p = profile_for()
    assert gene(p, "DPYD") == ("*1/*1", "NM")
    assert gene(p, "SLCO1B1") == ("*1/*1", "Normal")
    assert all(v["status"] == "called" for v in p.values())


def test_unmapped_allele_is_indeterminate_not_normal():
    p = profile_for(record("CYP2C19", "*99", "rs99", "0/1"))
    assert p["CYP2C19"]["phenotype"] == "Indeterminate"
    assert p["CYP2C19"]["status"] == "indeterminate"
    assert "*99" in p["CYP2C19"]["warnings"][0]


def test_more_than_two_alt_alleles_is_indeterminate():
    p = profile_for(record("TPMT", "*3A", "rs1800460", "1/1"), record("TPMT", "*2", "rs1800462", "0/1"))
    assert p["TPMT"]["status"] == "indeterminate"


def test_no_call_is_indeterminate():
    p = profile_for(record("DPYD", "*13", "rs67376798", "./."))
    assert p["DPYD"]["phenotype"] == "Indeterminate"


def test_gene_missing_from_vcf_is_not_covered_not_wild_type():
    parsed = parse_vcf(make_vcf(record("DPYD", "*2A", "rs3918290", "0/0")))
    p = build_profile(parsed)
    assert p["DPYD"]["status"] == "called"
    assert p["CYP2D6"]["status"] == "not_covered"
    assert p["CYP2D6"]["phenotype"] == "Unknown"
    assert p["CYP2D6"]["diplotype"] is None


def test_sample_patient_003_regression():
    p = build_profile(parse_vcf(sample("VCF/PATIENT_003.vcf")))
    assert gene(p, "DPYD") == ("*1/*2A", "IM")
    assert gene(p, "CYP2D6") == ("*1/*4", "IM")
    assert gene(p, "CYP2C19") == ("*1/*3", "IM")
    assert gene(p, "TPMT") == ("*3A/*3A", "PM")
    assert gene(p, "SLCO1B1") == ("*15/*15", "Poor")
    assert gene(p, "CYP2C9") == ("*1/*1", "NM")


def test_sample_patient_002():
    p = build_profile(parse_vcf(sample("VCF/PATIENT_002.vcf")))
    assert gene(p, "CYP2C19") == ("*2/*2", "PM")
    assert gene(p, "CYP2C9") == ("*2/*3", "PM")
    assert gene(p, "SLCO1B1") == ("*1/*5", "Decreased")


def test_sample_normal_patient_has_no_actionable_phenotype():
    p = build_profile(parse_vcf(sample("VCF/TC_P1_PATIENT_001_Normal.vcf")))
    assert gene(p, "CYP2D6") == ("*1/*2", "NM")
    assert {v["phenotype"] for k, v in p.items() if k != "SLCO1B1"} == {"NM"}
