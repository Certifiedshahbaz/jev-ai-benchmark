from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.benchmarks.accuracy_runner import accuracy_runner

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])


class FieldAccuracy(BaseModel):
    field: str
    correct: int
    total: int
    ambiguous_count: int = 0
    accuracy: float


class FailedCase(BaseModel):
    case_id: str
    category: str
    message: str
    expected: Any
    actual: Any


class EngineAccuracyResult(BaseModel):
    model: str
    overall_accuracy: float
    total_evaluations: int
    total_correct: int
    ambiguous_matches: int = 0
    duration_seconds: float
    per_field_accuracy: Dict[str, FieldAccuracy]
    failed_case_ids: Dict[str, List[str]]
    failed_cases: Dict[str, List[FailedCase]]
    ambiguous_cases: Optional[Dict[str, List[FailedCase]]] = None


class DualAccuracyResponse(BaseModel):
    status: str = "success"
    total_cases: int
    duration_seconds: float
    results_file: str
    jev: EngineAccuracyResult
    llm: EngineAccuracyResult


@router.get("/accuracy/progress")
async def get_accuracy_progress():
    """
    Poll the current progress state of the running accuracy benchmark.
    """
    return accuracy_runner.get_progress()


@router.post("/accuracy/start")
async def start_accuracy_benchmark():
    """
    Start the dual accuracy benchmark as a non-blocking background job.
    Avoids long HTTP connection drops and allows frontend to poll live progress.
    """
    return accuracy_runner.start_background_run()


@router.get("/accuracy/latest", response_model=Optional[DualAccuracyResponse])
async def get_latest_accuracy_benchmark():
    """
    Get the most recent completed accuracy benchmark without re-running 98 API evaluations.
    """
    latest = accuracy_runner.get_latest_benchmark()
    if not latest:
        raise HTTPException(status_code=404, detail="No prior benchmark run found.")
    return latest


@router.post("/accuracy", response_model=DualAccuracyResponse)
async def run_accuracy_benchmark():
    """
    Run full 49-case curated benchmark dataset against both TypeSafe JEV System One
    and the conventional LLM baseline (Groq) with a hard 3-minute timeout.
    Returns comparative overall accuracy, per-field accuracy tables, and failure inspections.
    """
    try:
        results = await accuracy_runner.run_benchmark()
        return results
    except TimeoutError as te:
        raise HTTPException(status_code=504, detail=str(te))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Accuracy benchmark run failed: {str(e)}")
