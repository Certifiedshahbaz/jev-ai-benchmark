from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class AnalyzeRequest(BaseModel):
    message: str = Field(..., description="Customer message or support ticket text")
    customer_context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional customer metadata (VIP status, order history, policy limits, etc.)"
    )
    mode: str = Field(default="A", description="Question fan-out mode (A=5, B=15, C=25, D=50, E=100)")
    include_llm: bool = Field(default=True, description="Whether to run the conventional LLM baseline for benchmark comparison")
