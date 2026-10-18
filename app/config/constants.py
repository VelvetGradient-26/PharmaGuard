import math

SUPPORTED_DRUGS = {
    "CODEINE",
    "WARFARIN",
    "CLOPIDOGREL",
    "SIMVASTATIN",
    "AZATHIOPRINE",
    "FLUOROURACIL"
}

PRIMARY_GENE_MAP = {
    "CODEINE": "CYP2D6",
    "WARFARIN": "CYP2C9",
    "CLOPIDOGREL": "CYP2C19",
    "SIMVASTATIN": "SLCO1B1",
    "AZATHIOPRINE": "TPMT",
    "FLUOROURACIL": "DPYD"
}

SUPPORTED_GENES = {
    "CYP2D6",
    "CYP2C19",
    "CYP2C9",
    "SLCO1B1",
    "TPMT",
    "DPYD"
}

# Known limits of a single-gene interpretation, surfaced as warnings per drug.
DRUG_LIMITATIONS = {
    "WARFARIN": "Only CYP2C9 is assessed; VKORC1 and CYP4F2 also influence warfarin dose and are not evaluated.",
    "AZATHIOPRINE": "Only TPMT is assessed; NUDT15 also influences thiopurine toxicity and is not evaluated.",
    "CODEINE": "CYP2D6 copy-number variation (deletions/duplications) is not assessed, so ultrarapid metabolizers cannot be detected.",
}

# Allele function values per gene, following the CPIC activity-score convention
# (1 = normal function, 0 = no function, in between = decreased function;
# CYP2C19 *17 is 1.5 = increased function). A diplotype's score is the sum of its
# two alleles. Verify against the current CPIC allele functionality tables before
# extending. Any star allele missing here makes the gene "Indeterminate" instead
# of being silently treated as normal.
ALLELE_FUNCTION = {
    "CYP2D6": {
        "*1": 1.0, "*2": 1.0, "*3": 0.0, "*4": 0.0, "*5": 0.0, "*6": 0.0,
        "*9": 0.5, "*10": 0.25, "*17": 0.5, "*41": 0.5,
    },
    "CYP2C19": {
        "*1": 1.0, "*2": 0.0, "*3": 0.0, "*4": 0.0, "*5": 0.0, "*6": 0.0,
        "*8": 0.0, "*9": 0.5, "*17": 1.5,
    },
    "CYP2C9": {
        "*1": 1.0, "*2": 0.5, "*3": 0.0, "*5": 0.5, "*6": 0.0, "*8": 0.5,
        "*11": 0.5, "*12": 0.5,
    },
    "SLCO1B1": {
        "*1": 1.0, "*1B": 1.0, "*5": 0.5, "*15": 0.5, "*17": 0.5,
    },
    "TPMT": {
        "*1": 1.0, "*2": 0.0, "*3A": 0.0, "*3B": 0.0, "*3C": 0.0, "*4": 0.0,
    },
    "DPYD": {
        "*1": 1.0, "*2A": 0.0, "*13": 0.0, "*5": 1.0, "*6": 1.0,
    },
}

# (max total score inclusive, phenotype), ascending. The first match wins.
PHENOTYPE_THRESHOLDS = {
    "CYP2D6": [(0.0, "PM"), (1.0, "IM"), (2.25, "NM"), (math.inf, "UM")],
    "CYP2C19": [(0.5, "PM"), (1.5, "IM"), (2.0, "NM"), (2.5, "RM"), (math.inf, "UM")],
    "CYP2C9": [(0.5, "PM"), (1.5, "IM"), (math.inf, "NM")],
    "SLCO1B1": [(1.0, "Poor"), (1.5, "Decreased"), (math.inf, "Normal")],
    "TPMT": [(0.0, "PM"), (1.0, "IM"), (math.inf, "NM")],
    "DPYD": [(0.5, "PM"), (1.5, "IM"), (math.inf, "NM")],
}

DISCLAIMER = (
    "For clinical research use only. Not a substitute for professional medical "
    "judgement; do not change a patient's therapy based on this output alone."
)
