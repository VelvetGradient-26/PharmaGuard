# PharmaGuard: Pharmacogenomic Risk Prediction System

Precision medicine algorithm developed for the **RIFT 2026 Hackathon** (Pharmacogenomics + Explainable AI Track).

PharmaGuard is an interpretable AI system that predicts patient-specific drug response risks and adverse events by combining pharmacogenomic data, genetic variants, and clinical features — while providing human-understandable AI-generated explanations.

## 🔗 Links

- **Live Demo**: https://pharmaguard-production.up.railway.app

## 🏗 Architecture Overview

PharmaGuard acts as a bridge between raw genomic data and actionable clinical insights. The architecture follows a seamless pipeline:

1. **Frontend Client**: A lightweight, responsive interface built with Vanilla JS and TailwindCSS captures the user's target medications and VCF file.
2. **VCF Parser & Phenotype Engine**: The FastAPI backend parses the raw VCF file, extracts clinically relevant variants (rsIDs, Star alleles), and computes the patient's diplotype and phenotype (e.g., Poor Metabolizer, Normal Metabolizer) based on established CPIC logic.
3. **Explainable AI Integration**: The clinical parameters are sent to an Ollama-hosted LLM (`gpt-oss:120b` via the Ollama API) to generate human-readable, biological mechanism explanations and clinical impact summaries.
4. **Result Delivery**: The processed risk assessment is returned to the frontend, displaying dynamic severity-coded alert cards with options to copy or export the clinical JSON report.

## 💻 Tech Stack

- **Frontend**: Vanilla JavaScript, HTML5, TailwindCSS (via CDN)
- **Backend**: Python 3.11, FastAPI, Uvicorn
- **AI & LLM**: Ollama API (`gpt-oss:120b`)
- **Deployment**: Docker, Railway
- **Data Processing**: Custom VCF parser handling VCFv4.2 format

## 🛠 Installation Instructions

1. **Clone the repository**

   ```bash
   git clone https://github.com/VelvetGradient-26/PharmaGuard.git
   cd PharmaGuard
   ```

2. **Set up a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies** (add `requirements-dev.txt` instead to also get the test tools)

   ```bash
   pip install -r requirements.txt
   ```

4. **Environment variables**: create a `.env` file in the repo root (see `.env.example`):

   ```env
   OLLAMA_API_KEY=your_ollama_api_key_here
   # Optional
   OLLAMA_MODEL=gpt-oss:120b
   OLLAMA_HOST=https://ollama.com
   MAX_UPLOAD_BYTES=5242880
   CORS_ORIGINS=https://my-separate-frontend.example   # CORS is off by default (same-origin)
   ```

   Without a key the analysis still runs; explanations fall back to static text (`"source": "fallback"`).

5. **Run the application**

   ```bash
   uvicorn app.main:app --reload
   ```

   Open `http://127.0.0.1:8000/`.

6. **Run the tests**

   ```bash
   pip install -r requirements-dev.txt
   python -m pytest
   ```

## Deployment Instructions

### Option A: Railway (Recommended)

1. Push your repository to GitHub.
2. In Railway choose **New Project** -> **Deploy from GitHub repo** and select the repository.
3. In the **Variables** tab add `OLLAMA_API_KEY`.
4. Railway builds the `Dockerfile`, which listens on the injected `$PORT` (default 8000).

### Option B: Docker

```bash
docker build -t pharmaguard .
docker run -p 8000:8000 --env-file .env pharmaguard
```

## 🧬 How phenotypes are determined

Each star allele has a function value (CPIC activity-score convention: 1 normal, 0 none, in between decreased, CYP2C19 `*17` 1.5 increased) defined in `app/config/constants.py`. A diplotype's score is the sum of its two alleles and is mapped to a phenotype per gene (e.g. DPYD `*1/*2A` has score 1 and is an Intermediate Metabolizer; `*2A/*2A` is a Poor Metabolizer). Zygosity comes from the genotype (`0/1` = one copy, `1/1` = two).

The engine fails safe rather than assuming "normal":

- an allele with no function mapping, a no-call genotype, or more than two variant alleles in a gene gives **Indeterminate**;
- a gene with no records in the VCF gives **Unknown** (not wild-type);
- several heterozygous variants in one gene are assumed to be on opposite chromosomes (VCFs are unphased) and the result carries lower confidence and a warning.

`confidence_score` is a heuristic data-completeness score (0.95 clean call, 0.75 phase-ambiguous, 0 uninterpretable), not a statistical probability.

## 📄 Input VCF requirements

- `##fileformat=VCFv4.x`, a `#CHROM` header line, and a `GT` field for the first sample column (extra samples are ignored with a warning).
- Records must carry `GENE=`, `STAR=` and `RS=` INFO tags for one of CYP2D6, CYP2C19, CYP2C9, SLCO1B1, TPMT, DPYD. Raw sequencer output without these tags is **not** interpreted; there is no rsID/position lookup table yet.
- Include reference (`0/0`) records for sites you tested so a gene counts as genotyped.
- Max upload size is 5 MB (`MAX_UPLOAD_BYTES`).

## 📖 API Documentation

### `GET /health`

Returns `{"status": "PharmaGuard backend running", "message": "Ready for VCF analysis"}`.

### `POST /validate-vcf`

- **Payload**: `multipart/form-data` (`file`)
- **Response**: `{"valid": true, "variant_count": <int>, "genes_covered": [...], "warnings": [...]}`
- **Errors**: `400` invalid or non-UTF-8 VCF, `413` file too large.

### `POST /full-analysis`

- **Payload**: `multipart/form-data` (`file`, `drugs`: repeated field or comma-separated, e.g. `WARFARIN,CODEINE`). Supported: CODEINE, WARFARIN, CLOPIDOGREL, SIMVASTATIN, AZATHIOPRINE, FLUOROURACIL.
- **Response**: always a JSON **array**, one object per drug, with `risk_assessment`, `pharmacogenomic_profile`, `clinical_recommendation`, `llm_generated_explanation` (with `source`: `ollama` | `fallback` | `static`), `warnings`, `quality_metrics` and a `disclaimer`.
- **Errors**: `400` invalid VCF, `413` too large, `422` no or unsupported drug.

## ⚠️ Limitations

- Warfarin guidance uses CYP2C9 only (no VKORC1/CYP4F2); azathioprine uses TPMT only (no NUDT15); CYP2D6 copy-number variation is not detected, so ultrarapid metabolizers are not identified.
- Allele function tables are a subset of CPIC's and should be reviewed against the current CPIC tables before any real use.
- Research prototype: not a medical device, and not for treatment decisions.

## 🧪 Sample VCFs

Files are in `VCF/` (plus `test.vcf` in the repo root):

- `test.vcf` and `VCF/TC_P1_PATIENT_001_Normal.vcf`: baseline patient, CYP2D6 `*1/*2` (normal), everything else wild-type.
- `VCF/PATIENT_002.vcf`: CYP2C19 `*2/*2` (PM), CYP2C9 `*2/*3` (PM), SLCO1B1 `*1/*5` (decreased).
- `VCF/PATIENT_003.vcf`: heterozygous DPYD `*2A`, CYP2D6 `*4`, CYP2C19 `*3` (all IM), TPMT `*3A/*3A` (PM), SLCO1B1 `*15/*15` (poor).

Usage: open the Analysis Workspace, select medications, upload a VCF, click **Run Analysis**, then **Export JSON** / **Copy JSON**.

## 👥 Team Members

- **Deepak K**
- **Pranav C**
- **Ruthvik N P**
