from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.vcf_parser import parse_vcf
from app.utils.uploads import read_vcf_text

router = APIRouter()

@router.post("/validate-vcf")
async def validate_vcf(file: UploadFile = File(...)):
    content = await read_vcf_text(file)
    try:
        parsed = parse_vcf(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "valid": True,
        "variant_count": len(parsed.variants),
        "genes_covered": sorted(parsed.genes_covered),
        "warnings": parsed.warnings
    }
