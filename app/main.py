import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from app.routes import full_analysis, validate  # noqa: E402

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(
    title="PharmaGuard API",
    description="AI-powered Pharmacogenomic Risk Prediction System",
    version="1.0.0"
)

# ---------------------------
# CORS Configuration
# ---------------------------
# The frontend is served from this same origin, so CORS is off unless
# CORS_ORIGINS (comma-separated) is set for a separately hosted frontend.
cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

# ---------------------------
# Frontend Path Resolution
# ---------------------------
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_candidates = [
    os.path.join(project_root, "frontend"),
    os.path.join(project_root, "Frontend"),
]
frontend_path = next((path for path in frontend_candidates if os.path.exists(path)), None)

# ---------------------------
# Base Endpoints
# ---------------------------
@app.get("/health")
def health_check():
    return {
        "status": "PharmaGuard backend running",
        "message": "Ready for VCF analysis"
    }

@app.get("/")
async def serve_landing_page():
    if frontend_path:
        landing_file = os.path.join(frontend_path, "landing.html")
        if os.path.exists(landing_file):
            return FileResponse(landing_file)
    return {"message": "Frontend directory or landing.html not found"}

# ---------------------------
# Include Routers
# ---------------------------
app.include_router(validate.router)
app.include_router(full_analysis.router)

# ---------------------------
# Static Files Configuration (must be last)
# ---------------------------
if frontend_path:
    # Mount the static directory to serve analysis.html, app.js, and CSS
    app.mount("/", StaticFiles(directory=frontend_path), name="static")
