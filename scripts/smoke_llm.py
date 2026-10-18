"""Manual smoke test for the Ollama integration (makes a live API call).

Run from the repo root: python -m scripts.smoke_llm
"""
from app.services.llm_service import generate_explanation

if __name__ == "__main__":
    print(generate_explanation(
        gene="CYP2C19",
        drug="CLOPIDOGREL",
        phenotype="PM",
        risk_label="Ineffective",
        recommendation="Avoid clopidogrel. Use alternative antiplatelet (e.g., prasugrel or ticagrelor).",
        rsids=["rs4244285"],
    ))
