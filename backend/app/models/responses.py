from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class TokenUsageModel(BaseModel):
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

class TimingBreakdownModel(BaseModel):
    prep_ms: float
    api_ms: float
    total_ms: float

class RoutingDecisionModel(BaseModel):
    team: str
    priority: str
    action: str
    reason: str
    confidence_factors: Dict[str, Any] = Field(default_factory=dict)
    relevant_answers: Dict[str, Any] = Field(default_factory=dict)
    ignored_answers: List[str] = Field(default_factory=list)

class LLMResultModel(BaseModel):
    provider: str
    model: str
    answers: Dict[str, Any]
    usage: TokenUsageModel
    cost_usd: float
    timing: TimingBreakdownModel

class ComparisonMetricsModel(BaseModel):
    latency_delta_ms: float
    latency_ratio: float
    cost_delta_usd: float
    cost_ratio: float
    token_delta: int
    agreement_score: float

class AnalyzeResponse(BaseModel):
    status: str = "success"
    mode: str = "A"
    question_count: int
    model: str
    request_id: Optional[str] = None
    answers: Dict[str, Any]
    decision: Optional[RoutingDecisionModel] = None
    cost_usd: float = 0.0
    usage: TokenUsageModel
    timing: TimingBreakdownModel
    llm: Optional[LLMResultModel] = None
    comparison: Optional[ComparisonMetricsModel] = None
