from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import routes_health, routes_analyze, routes_benchmark

app = FastAPI(
    title="SERALI JEV WORKFORCE LAB",
    description="Engineering benchmark laboratory evaluating TypeSafe Jev architecture vs LLM baseline",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes_health.router)
app.include_router(routes_analyze.router)
app.include_router(routes_benchmark.router)

@app.get("/")
async def root():
    return {"message": "SERALI JEV WORKFORCE LAB API is running. Check /api/health or /docs."}
