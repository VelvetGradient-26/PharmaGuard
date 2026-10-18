from app.config.constants import ALLELE_FUNCTION, PHENOTYPE_THRESHOLDS, SUPPORTED_GENES
from app.services.vcf_parser import ParsedVCF

# status values: "called" (phenotype resolved), "indeterminate" (variants present but
# not interpretable), "not_covered" (gene absent from the VCF).


def build_profile(parsed: ParsedVCF):
    profile = {}
    for gene in sorted(SUPPORTED_GENES):
        profile[gene] = _build_gene(gene, [r for r in parsed.records if r.gene == gene])
    return profile


def _entry(status, phenotype, diplotype=None, rsids=None, warnings=None, phase_ambiguous=False):
    return {
        "status": status,
        "diplotype": diplotype,
        "phenotype": phenotype,
        "detected_variants": rsids or [],
        "phase_ambiguous": phase_ambiguous,
        "warnings": warnings or [],
    }


def _build_gene(gene, records):
    if not records:
        return _entry(
            "not_covered", "Unknown",
            warnings=[f"No {gene} records in the VCF; genotype was not assessed."],
        )

    carriers = [r for r in records if r.alt_copies > 0]
    rsids = [r.rsid for r in carriers]
    warnings = []

    # A no-call means a variant cannot be ruled out, so a "wild-type" answer is unsafe.
    no_calls = [r.rsid for r in records if r.no_call]
    if no_calls:
        return _entry(
            "indeterminate", "Indeterminate", rsids=rsids,
            warnings=[f"No-call genotype at {', '.join(no_calls)}; {gene} cannot be interpreted."],
        )

    alleles = []
    for r in carriers:
        alleles.extend([r.star] * r.alt_copies)

    if len(alleles) > 2:
        return _entry(
            "indeterminate", "Indeterminate", rsids=rsids,
            warnings=[f"{len(alleles)} variant alleles reported for {gene}; a diploid genotype has two."],
        )

    unknown = sorted({a for a in alleles if a not in ALLELE_FUNCTION[gene]})
    if unknown:
        return _entry(
            "indeterminate", "Indeterminate", rsids=rsids,
            warnings=[f"Allele(s) {', '.join(unknown)} have no known function mapping for {gene}."],
        )

    alleles = sorted(alleles + ["*1"] * (2 - len(alleles)), key=_allele_sort_key)
    # More than one heterozygous site: whether they sit on different chromosomes is unknown
    # without phasing, so the diplotype is the most likely one rather than a certainty.
    phase_ambiguous = sum(1 for r in carriers if r.alt_copies == 1) > 1
    if phase_ambiguous:
        warnings.append(f"Multiple heterozygous {gene} variants; phase unknown, diplotype assumes trans.")

    score = sum(ALLELE_FUNCTION[gene][a] for a in alleles)
    return _entry(
        "called", _phenotype_from_score(gene, score),
        diplotype="/".join(alleles), rsids=rsids, warnings=warnings,
        phase_ambiguous=phase_ambiguous,
    )


def _allele_sort_key(star):
    """Canonical order: *1 first, then by allele number, then suffix (*3A before *3C)."""
    digits = "".join(ch for ch in star if ch.isdigit())
    return int(digits), star


def _phenotype_from_score(gene, score):
    for ceiling, phenotype in PHENOTYPE_THRESHOLDS[gene]:
        if score <= ceiling:
            return phenotype
    return "Indeterminate"
