from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/api", tags=["health"])

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "serali-jev-workforce-lab",
        "version": "1.0.0",
        "config": {
            "jev_model": settings.jev_model,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
        }
    }
