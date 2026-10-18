import asyncio
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.config.constants import DISCLAIMER, DRUG_LIMITATIONS, PRIMARY_GENE_MAP, SUPPORTED_DRUGS
from app.services.cpic_rules import evaluate_drug_risk
from app.services.llm_service import generate_explanation
from app.services.phenotype_engine import build_profile
from app.services.vcf_parser import parse_vcf
from app.utils.uploads import read_vcf_text


router = APIRouter()


def _normalize_drugs(drugs: List[str]) -> List[str]:
    normalized = []
    for entry in drugs:
        for drug in entry.split(","):
            drug = drug.strip().upper()
            if drug and drug not in normalized:
                normalized.append(drug)
    return normalized


def _static_explanation(risk_data, gene_profile):
    reason = (gene_profile or {}).get("warnings") or ["Required gene was not genotyped in the uploaded VCF."]
    return {
        "summary": "No pharmacogenomic interpretation available for this drug.",
        "biological_mechanism": " ".join(reason),
        "clinical_impact": "Standard clinical practice applies; this result does not indicate normal drug response.",
        "cpic_alignment_note": "No CPIC-guided adjustment possible because the genotype could not be interpreted.",
        "variant_citations": [],
        "source": "static",
    }


@router.post("/full-analysis")
async def full_analysis(
    file: UploadFile = File(...),
    drugs: List[str] = Form(...)
):
    normalized_drugs = _normalize_drugs(drugs)
    if not normalized_drugs:
        raise HTTPException(status_code=422, detail="Select at least one drug.")

    unsupported = [d for d in normalized_drugs if d not in SUPPORTED_DRUGS]
    if unsupported:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported drug(s): {', '.join(unsupported)}. Supported: {', '.join(sorted(SUPPORTED_DRUGS))}.",
        )

    content = await read_vcf_text(file)
    try:
        parsed = parse_vcf(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    profile = build_profile(parsed)

    patient_id = f"PATIENT_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    risks = {drug: evaluate_drug_risk(drug, profile) for drug in normalized_drugs}

    # Explanations are network calls; run them concurrently off the event loop.
    async def explain(drug):
        gene = PRIMARY_GENE_MAP[drug]
        gene_profile = profile[gene]
        risk_data = risks[drug]
        if gene_profile["status"] != "called":
            return _static_explanation(risk_data, gene_profile)
        return await asyncio.to_thread(
            generate_explanation,
            gene=gene,
            drug=drug,
            phenotype=gene_profile["phenotype"],
            risk_label=risk_data["risk_label"],
            recommendation=risk_data["clinical_recommendation"]["recommendation_summary"],
            rsids=gene_profile["detected_variants"],
        )

    explanations = await asyncio.gather(*(explain(d) for d in normalized_drugs))

    responses = []
    for drug, explanation in zip(normalized_drugs, explanations):
        gene = PRIMARY_GENE_MAP[drug]
        gene_profile = profile[gene]
        risk_data = risks[drug]

        warnings = list(gene_profile["warnings"])
        if drug in DRUG_LIMITATIONS:
            warnings.append(DRUG_LIMITATIONS[drug])

        responses.append({
            "patient_id": patient_id,
            "drug": drug,
            "timestamp": timestamp,
            "risk_assessment": {
                "risk_label": risk_data["risk_label"],
                "confidence_score": risk_data["confidence_score"],
                "severity": risk_data["severity"]
            },
            "pharmacogenomic_profile": {
                "primary_gene": gene,
                "diplotype": gene_profile["diplotype"],
                "phenotype": gene_profile["phenotype"],
                "detected_variants": [{"rsid": rs} for rs in gene_profile["detected_variants"]]
            },
            "clinical_recommendation": risk_data["clinical_recommendation"],
            "llm_generated_explanation": explanation,
            "warnings": warnings,
            "quality_metrics": {
                "vcf_parsing_success": True,
                "genes_detected": len(parsed.genes_covered),
                "variants_detected": len(parsed.variants),
                "vcf_warnings": parsed.warnings
            },
            "disclaimer": DISCLAIMER
        })

    return responses
