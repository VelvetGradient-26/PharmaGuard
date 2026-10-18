from app.config.constants import PRIMARY_GENE_MAP


CPIC_RULES = {

    "CODEINE": {
        "CYP2D6": {
            "PM": {
                "risk_label": "Ineffective",
                "severity": "high",
                "recommendation": "Avoid codeine. Use alternative analgesic not metabolized by CYP2D6."
            },
            "IM": {
                "risk_label": "Reduced Response",
                "severity": "moderate",
                "recommendation": "Consider alternative analgesic or monitor for reduced efficacy."
            },
            "NM": {
                "risk_label": "Safe",
                "severity": "none",
                "recommendation": "Use standard dosing."
            },
            "UM": {
                "risk_label": "Toxic",
                "severity": "critical",
                "recommendation": "Avoid codeine due to risk of morphine toxicity."
            }
        }
    },

    "WARFARIN": {
        "CYP2C9": {
            "PM": {
                "risk_label": "Toxic",
                "severity": "critical",
                "recommendation": "Reduce initial dose significantly and monitor INR closely."
            },
            "IM": {
                "risk_label": "Adjust Dosage",
                "severity": "high",
                "recommendation": "Lower starting dose and monitor INR."
            },
            "NM": {
                "risk_label": "Safe",
                "severity": "none",
                "recommendation": "Standard initial dosing."
            }
        }
    },

    "CLOPIDOGREL": {
        "CYP2C19": {
            "PM": {
                "risk_label": "Ineffective",
                "severity": "critical",
                "recommendation": "Avoid clopidogrel. Use alternative antiplatelet (e.g., prasugrel or ticagrelor)."
            },
            "IM": {
                "risk_label": "Reduced Response",
                "severity": "high",
                "recommendation": "Consider alternative antiplatelet therapy."
            },
            "NM": {
                "risk_label": "Safe",
                "severity": "none",
                "recommendation": "Use standard dosing."
            },
            "RM": {
                "risk_label": "Safe",
                "severity": "none",
                "recommendation": "Standard dosing appropriate."
            },
            "UM": {
                "risk_label": "Safe",
                "severity": "none",
                "recommendation": "Standard dosing appropriate."
            }
        }
    },

    "SIMVASTATIN": {
        "SLCO1B1": {
            "Normal": {
                "risk_label": "Safe",
                "severity": "none",
                "recommendation": "Use standard dosing."
            },
            "Decreased": {
                "risk_label": "Myopathy Risk",
                "severity": "moderate",
                "recommendation": "Use lower dose or consider alternative statin."
            },
            "Poor": {
                "risk_label": "Toxic",
                "severity": "high",
                "recommendation": "Avoid high doses. Consider alternative statin."
            }
        }
    },

    "AZATHIOPRINE": {
        "TPMT": {
            "PM": {
                "risk_label": "Toxic",
                "severity": "critical",
                "recommendation": "Avoid azathioprine or drastically reduce dose (≤10% of standard)."
            },
            "IM": {
                "risk_label": "Adjust Dosage",
                "severity": "high",
                "recommendation": "Reduce starting dose by 30–80% and monitor closely."
            },
            "NM": {
                "risk_label": "Safe",
                "severity": "none",
                "recommendation": "Use standard dosing."
            }
        }
    },

    "FLUOROURACIL": {
        "DPYD": {
            "NM": {
                "risk_label": "Safe",
                "severity": "none",
                "recommendation": "Use standard dosing."
            },
            "IM": {
                "risk_label": "Adjust Dosage",
                "severity": "high",
                "recommendation": "Reduce starting dose by 25–50% and titrate."
            },
            "PM": {
                "risk_label": "Toxic",
                "severity": "critical",
                "recommendation": "Avoid fluorouracil due to severe toxicity risk."
            }
        }
    }
}

CONFIDENCE_CLEAN = 0.95
CONFIDENCE_PHASE_AMBIGUOUS = 0.75


def evaluate_drug_risk(drug: str, profile: dict):
    """Look up the CPIC rule for a drug from the patient's primary-gene phenotype.

    Genes that were not genotyped, or could not be interpreted, yield an explicit
    "Unknown"/"Indeterminate" result rather than a reassuring default.
    """
    drug = drug.upper()

    if drug not in PRIMARY_GENE_MAP:
        raise ValueError(f"Unsupported drug: {drug}")

    gene = PRIMARY_GENE_MAP[drug]
    gene_profile = profile.get(gene)

    if gene_profile is None or gene_profile["status"] == "not_covered":
        return unknown_response(
            "Unknown",
            f"{gene} was not genotyped in the uploaded VCF, so no pharmacogenomic guidance can be given.",
        )

    if gene_profile["status"] != "called":
        detail = " ".join(gene_profile["warnings"]) or f"{gene} genotype could not be interpreted."
        return unknown_response("Indeterminate", f"{gene} genotype could not be interpreted. {detail}")

    gene_rules = CPIC_RULES.get(drug, {}).get(gene, {})
    rule = gene_rules.get(gene_profile["phenotype"])
    if rule is None:
        return unknown_response(
            "Unknown",
            f"No CPIC rule for {gene} phenotype '{gene_profile['phenotype']}' with {drug.title()}.",
        )

    confidence = CONFIDENCE_PHASE_AMBIGUOUS if gene_profile["phase_ambiguous"] else CONFIDENCE_CLEAN

    return {
        "risk_label": rule["risk_label"],
        "severity": rule["severity"],
        # Heuristic data-completeness score, not a statistical probability.
        "confidence_score": confidence,
        "clinical_recommendation": {
            "guideline_source": "CPIC",
            "recommendation_summary": rule["recommendation"],
            "dose_adjustment": rule["recommendation"],
            "monitoring_advice": "Monitor patient response as per CPIC guidelines."
        }
    }


def unknown_response(risk_label: str, reason: str):
    return {
        "risk_label": risk_label,
        "severity": "unknown",
        "confidence_score": 0.0,
        "clinical_recommendation": {
            "guideline_source": "CPIC",
            "recommendation_summary": reason,
            "dose_adjustment": "No pharmacogenomic dose adjustment can be derived from this result.",
            "monitoring_advice": "Follow standard clinical practice and consider clinical pharmacogenomic consultation."
        }
    }
