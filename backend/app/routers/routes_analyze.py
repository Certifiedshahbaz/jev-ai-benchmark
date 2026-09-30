import asyncio
from fastapi import APIRouter, HTTPException
from app.models.requests import AnalyzeRequest
from app.models.responses import (
    AnalyzeResponse, TokenUsageModel, TimingBreakdownModel,
    RoutingDecisionModel, LLMResultModel, ComparisonMetricsModel
)
from app.workflows.support_triage import get_questions_for_mode
from app.services.typesafe_service import typesafe_service
from app.services.llm_service import llm_service
from app.services.decision_service import decision_service
from app.config import settings

router = APIRouter(prefix="/api", tags=["analyze"])

def calculate_agreement(jev_answers: dict, llm_answers: dict) -> float:
    """Calculate normalized decision agreement between JEV and LLM."""
    if not jev_answers or not llm_answers:
        return 0.0

    matches = 0
    total = 0

    for key, j_val in jev_answers.items():
        if key not in llm_answers:
            continue
        total += 1
        l_val = llm_answers[key]

        # Extract pure value from JEV structure
        j_clean = j_val.get("choice") if isinstance(j_val, dict) and "choice" in j_val else (
            j_val.get("noul") if isinstance(j_val, dict) and "noul" in j_val else (
                j_val.get("score") if isinstance(j_val, dict) and "score" in j_val else j_val
            )
        )

        if isinstance(j_clean, str) and isinstance(l_val, str):
            if j_clean.lower().strip() == l_val.lower().strip():
                matches += 1
        elif isinstance(j_clean, (int, float)) and isinstance(l_val, (int, float, bool)):
            if isinstance(l_val, bool):
                # Noul probability comparison (>0.5 vs True)
                if (j_clean >= 0.5 and l_val) or (j_clean < 0.5 and not l_val):
                    matches += 1
            else:
                # Score distance tolerance <= 0.5
                if abs(float(j_clean) - float(l_val)) <= 0.5:
                    matches += 1
        elif isinstance(l_val, bool) and isinstance(j_clean, bool):
            if j_clean == l_val:
                matches += 1

    return round(matches / max(total, 1), 3)

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_ticket(request: AnalyzeRequest):
    """
    Analyze customer support message using TypeSafe Jev SystemOne architecture,
    compared side-by-side with a conventional LLM baseline (Groq/OpenAI).
    """
    try:
        questions = get_questions_for_mode(request.mode)
        customer_ctx = request.customer_context or {}
        
        state = {
            "message": request.message,
            "customer_context": customer_ctx,
        }

        # Run JEV and optionally LLM baseline concurrently
        if request.include_llm and settings.llm_api_key:
            jev_task = asyncio.create_task(typesafe_service.evaluate(state=state, questions=questions))
            llm_task = asyncio.create_task(llm_service.evaluate(state=state, questions=questions))
            jev_result, llm_result = await asyncio.gather(jev_task, llm_task, return_exceptions=True)
            
            if isinstance(jev_result, Exception):
                raise jev_result
        else:
            jev_result = await typesafe_service.evaluate(state=state, questions=questions)
            llm_result = None

        jev_answers = jev_result.get("answers", {})
        
        # Deterministic Python routing
        routing_obj = decision_service.route_ticket(answers=jev_answers, customer_context=customer_ctx)

        # JEV Cost calculation
        jev_in_tokens = jev_result.get("usage", {}).get("input_tokens") or 0
        jev_out_tokens = jev_result.get("usage", {}).get("output_tokens") or 0
        jev_cost_usd = (jev_in_tokens / 1_000_000.0) * settings.jev_input_price_per_million

        # LLM parsing
        llm_model_obj = None
        comparison_obj = None

        if llm_result and not isinstance(llm_result, Exception):
            llm_in_tokens = llm_result.get("usage", {}).get("input_tokens") or 0
            llm_out_tokens = llm_result.get("usage", {}).get("output_tokens") or 0
            llm_tot_tokens = llm_result.get("usage", {}).get("total_tokens") or (llm_in_tokens + llm_out_tokens)
            llm_cost_usd = llm_result.get("cost_usd", 0.0)

            llm_model_obj = LLMResultModel(
                provider=llm_result.get("provider", "groq"),
                model=llm_result.get("model", "unknown"),
                answers=llm_result.get("answers", {}),
                usage=TokenUsageModel(
                    input_tokens=llm_in_tokens,
                    output_tokens=llm_out_tokens,
                    total_tokens=llm_tot_tokens,
                ),
                cost_usd=llm_cost_usd,
                timing=TimingBreakdownModel(
                    prep_ms=llm_result.get("timing", {}).get("prep_ms", 0.0),
                    api_ms=llm_result.get("timing", {}).get("api_ms", 0.0),
                    total_ms=llm_result.get("timing", {}).get("total_ms", 0.0),
                ),
            )

            # Metrics
            jev_time = jev_result.get("timing", {}).get("total_ms", 1.0)
            llm_time = llm_result.get("timing", {}).get("total_ms", 1.0)
            agreement = calculate_agreement(jev_answers, llm_result.get("answers", {}))

            comparison_obj = ComparisonMetricsModel(
                latency_delta_ms=round(llm_time - jev_time, 2),
                latency_ratio=round(llm_time / max(jev_time, 0.1), 2),
                cost_delta_usd=round(llm_cost_usd - jev_cost_usd, 7),
                cost_ratio=round(llm_cost_usd / max(jev_cost_usd, 0.0000001), 2),
                token_delta=llm_tot_tokens - (jev_in_tokens + jev_out_tokens),
                agreement_score=agreement,
            )

        return AnalyzeResponse(
            status="success",
            mode=request.mode.upper(),
            question_count=len(questions),
            model=jev_result.get("model", "unknown"),
            request_id=jev_result.get("request_id"),
            answers=jev_answers,
            decision=RoutingDecisionModel(
                team=routing_obj.team,
                priority=routing_obj.priority,
                action=routing_obj.action,
                reason=routing_obj.reason,
                confidence_factors=routing_obj.confidence_factors,
                relevant_answers=routing_obj.relevant_answers,
                ignored_answers=routing_obj.ignored_answers,
            ),
            cost_usd=round(jev_cost_usd, 7),
            usage=TokenUsageModel(
                input_tokens=jev_in_tokens,
                output_tokens=jev_out_tokens,
                total_tokens=jev_in_tokens + jev_out_tokens,
            ),
            timing=TimingBreakdownModel(
                prep_ms=jev_result.get("timing", {}).get("prep_ms", 0.0),
                api_ms=jev_result.get("timing", {}).get("api_ms", 0.0),
                total_ms=jev_result.get("timing", {}).get("total_ms", 0.0),
            ),
            llm=llm_model_obj,
            comparison=comparison_obj,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
