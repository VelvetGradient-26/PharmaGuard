import re
from dataclasses import dataclass, field
from typing import List

from app.config.constants import SUPPORTED_GENES

RSID_RE = re.compile(r"^rs\d{1,12}$")
STAR_RE = re.compile(r"^\*\d{1,3}[A-Za-z]?$")
FILEFORMAT_RE = re.compile(r"^##fileformat=VCFv4\.\d$")


@dataclass
class VariantRecord:
    gene: str
    star: str
    rsid: str
    genotype: str
    alt_copies: int  # number of copies of this star allele the patient carries (0-2)
    no_call: bool = False


@dataclass
class ParsedVCF:
    records: List[VariantRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def variants(self) -> List[VariantRecord]:
        """Records where the patient carries at least one non-reference allele."""
        return [r for r in self.records if r.alt_copies > 0]

    @property
    def genes_covered(self) -> set:
        return {r.gene for r in self.records}


def _parse_genotype(genotype: str):
    """Return (alt_copies, no_call, multiallelic) for a GT string like 0/1, 1|1, ./1, 1."""
    tokens = re.split(r"[/|]", genotype)
    alt_copies = 0
    no_call = False
    multiallelic = False
    for token in tokens:
        if token == "0":
            continue
        if token.isdigit():
            alt_copies += 1
            if int(token) > 1:
                multiallelic = True
        else:
            no_call = True
    return alt_copies, no_call, multiallelic


def parse_vcf(file_content: str) -> ParsedVCF:
    """Parse a PGx VCF whose records carry GENE, STAR and RS INFO tags.

    Reference (0/0) records are kept so callers know which genes were actually
    genotyped; use ``ParsedVCF.variants`` for the alt-carrying subset.
    """
    lines = [ln for ln in file_content.lstrip("﻿").splitlines() if ln.strip()]

    if not lines or not FILEFORMAT_RE.match(lines[0].strip()):
        raise ValueError("Invalid VCF format: first line must be ##fileformat=VCFv4.x")

    if not any(ln.startswith("#CHROM") for ln in lines):
        raise ValueError("Invalid VCF format: missing #CHROM header line")

    parsed = ParsedVCF()
    by_key = {}  # (gene, star) -> VariantRecord; duplicates keep the most-alt call
    skipped = 0

    for line in lines:
        if line.startswith("#"):
            if line.startswith("#CHROM") and len(line.split("\t")) > 10:
                parsed.warnings.append(
                    "Multiple samples found in VCF; only the first sample was analysed."
                )
            continue

        columns = line.strip().split("\t")
        if len(columns) < 10:
            skipped += 1
            continue

        info_field, format_field, sample_field = columns[7], columns[8], columns[9]

        format_parts = format_field.split(":")
        sample_parts = sample_field.split(":")
        if "GT" not in format_parts or format_parts.index("GT") >= len(sample_parts):
            skipped += 1
            continue
        genotype = sample_parts[format_parts.index("GT")]

        info = {}
        for part in info_field.split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                info[key] = value

        gene, star, rsid = info.get("GENE"), info.get("STAR"), info.get("RS")
        if not (gene and star and rsid):
            continue
        # Reject anything that is not a plain gene/star/rsID: these values are later
        # rendered in the UI and embedded in an LLM prompt.
        if gene not in SUPPORTED_GENES or not STAR_RE.match(star) or not RSID_RE.match(rsid):
            skipped += 1
            continue

        alt_copies, no_call, multiallelic = _parse_genotype(genotype)
        if multiallelic:
            parsed.warnings.append(
                f"{rsid}: multi-allelic genotype {genotype} treated as carrying {star}."
            )

        record = VariantRecord(gene, star, rsid, genotype, alt_copies, no_call)
        existing = by_key.get((gene, star))
        if existing is None:
            by_key[(gene, star)] = record
            parsed.records.append(record)
        elif record.alt_copies > existing.alt_copies or (existing.no_call and not record.no_call):
            parsed.records[parsed.records.index(existing)] = record
            by_key[(gene, star)] = record

    if skipped:
        parsed.warnings.append(f"{skipped} malformed or unrecognised record(s) were skipped.")

    if not parsed.records:
        raise ValueError(
            "No pharmacogenomic records found: variants need GENE, STAR and RS INFO tags "
            f"for one of {', '.join(sorted(SUPPORTED_GENES))}."
        )

    return parsed
