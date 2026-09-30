import time
from typing import Dict, Any, Optional, Union
from app.config import settings

# Official TypeSafe SDK imports
try:
    from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Score, RetryPolicy
except ImportError:
    try:
        from typesafe_ai import AsyncTypeSafeClient, Choice, Noul, Score, RetryPolicy
    except ImportError:
        from typesafe import AsyncTypeSafeClient, Choice, Noul, Score, RetryPolicy


class TypeSafeService:
    """
    Service wrapper for TypeSafe AI Jev / SystemOne API using the official typesafe-sdk.
    Includes high-precision timing instrumentation (perf_counter).
    """

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or settings.typesafe_api_key
        self.default_model = default_model or settings.jev_model

    def _clean_answer(self, ans: Any) -> Dict[str, Any]:
        """Format an Answer object into a clean dictionary, stripping internal Pydantic fields."""
        if hasattr(ans, "model_dump"):
            dump = ans.model_dump()
            return dump
        
        cleaned = {}
        # Standard answer fields we care about
        relevant_attrs = ["type", "choice", "noul", "score", "confidence", "probabilities", "legend"]
        for attr in relevant_attrs:
            if hasattr(ans, attr):
                val = getattr(ans, attr)
                if val is not None:
                    cleaned[attr] = val
        return cleaned if cleaned else str(ans)

    async def evaluate(
        self,
        state: Union[str, Dict[str, Any], list],
        questions: Dict[str, Union[Choice, Noul, Score, Dict[str, Any]]],
        model: Optional[str] = None,
        max_retries: int = 0,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Evaluate state against questions using TypeSafe Jev API.
        """
        t0 = time.perf_counter()
        target_model = model or self.default_model
        api_key_to_use = self.api_key or settings.typesafe_api_key

        # Ensure questions are SDK instances if dicts were passed
        formatted_questions = {}
        for key, q in questions.items():
            if isinstance(q, (Choice, Noul, Score)):
                formatted_questions[key] = q
            elif isinstance(q, dict):
                q_type = q.get("type", "choice").lower()
                instructions = q.get("instructions", "")
                if q_type == "choice":
                    formatted_questions[key] = Choice(
                        instructions=instructions,
                        criteria=q.get("criteria", {})
                    )
                elif q_type == "noul":
                    formatted_questions[key] = Noul(instructions=instructions)
                elif q_type == "score":
                    formatted_questions[key] = Score(
                        instructions=instructions,
                        criteria=q.get("criteria", [])
                    )
                else:
                    raise ValueError(f"Unknown question type '{q_type}' for key '{key}'")
            else:
                formatted_questions[key] = q

        t1 = time.perf_counter()

        retry_policy = RetryPolicy(max_retries=max_retries) if 'RetryPolicy' in globals() else None

        client_kwargs = {
            "api_key": api_key_to_use,
            "model": target_model,
        }
        if retry_policy is not None:
            client_kwargs["retry"] = retry_policy

        async with AsyncTypeSafeClient(**client_kwargs) as client:
            response = await client.system_one(
                state=state,
                questions=formatted_questions,
            )

        t2 = time.perf_counter()

        # Extract usage
        input_tokens = getattr(response.usage, "input_tokens", None) if hasattr(response, "usage") and response.usage else None
        output_tokens = getattr(response.usage, "output_tokens", None) if hasattr(response, "usage") and response.usage else None

        # Clean answers
        raw_answers = getattr(response, "answers", {})
        answers_dict = {}
        if isinstance(raw_answers, dict):
            for k, ans in raw_answers.items():
                answers_dict[k] = self._clean_answer(ans)

        choices_dict = {k: self._clean_answer(v) for k, v in getattr(response, "choices", {}).items()}
        nouls_dict = {k: self._clean_answer(v) for k, v in getattr(response, "nouls", {}).items()}
        scores_dict = {k: self._clean_answer(v) for k, v in getattr(response, "scores", {}).items()}

        prep_time_ms = (t1 - t0) * 1000
        api_time_ms = (t2 - t1) * 1000
        total_time_ms = (t2 - t0) * 1000

        return {
            "model": getattr(response, "model", target_model),
            "answers": answers_dict,
            "choices": choices_dict,
            "nouls": nouls_dict,
            "scores": scores_dict,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
            "request_id": getattr(response, "request_id", None),
            "timing": {
                "prep_ms": round(prep_time_ms, 3),
                "api_ms": round(api_time_ms, 3),
                "total_ms": round(total_time_ms, 3),
            },
        }

typesafe_service = TypeSafeService()
