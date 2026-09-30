import asyncio
import time
import json
from typing import Dict, Any, Optional
import openai
from openai import AsyncOpenAI
from app.config import settings

class LLMService:
    """
    Conventional LLM Baseline service using OpenAI-compatible SDK (Groq default).
    Solicits structured JSON output for the exact same decision problem.
    """

    def __init__(self):
        self.provider = settings.llm_provider
        self.model = settings.llm_model
        self.input_price = settings.llm_input_price_per_million
        self.output_price = settings.llm_output_price_per_million

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=settings.llm_api_key or "placeholder",
            base_url=settings.llm_base_url or "https://api.groq.com/openai/v1",
        )

    def _build_system_prompt(self, questions: Dict[str, Any]) -> str:
        q_descriptions = []
        for key, q in questions.items():
            instructions = getattr(q, "instructions", "")
            if hasattr(q, "criteria") and isinstance(q.criteria, dict):
                criteria_str = ", ".join([f"'{k}': {v}" for k, v in q.criteria.items()])
                q_descriptions.append(f"- {key} (choice from [{criteria_str}]): {instructions}")
            elif hasattr(q, "criteria") and isinstance(q.criteria, list):
                q_descriptions.append(f"- {key} (numeric score 0 to {len(q.criteria)-1}): {instructions} [Legend: {q.criteria}]")
            else:
                q_descriptions.append(f"- {key} (boolean true/false or probability 0.0-1.0): {instructions}")

        prompt = (
            "You are an AI triage decision engine. Analyze the customer message and context.\n"
            "You must return ONLY a valid JSON object matching the requested fields exactly.\n"
            "Do NOT include conversational text, apologies, markdown formatting, or explanations.\n\n"
            "Requested Decision Schema:\n" + "\n".join(q_descriptions) + "\n\n"
            "Return JSON format:\n"
            "{\n  \"decisions\": {\n    \"field_name\": value\n  }\n}"
        )
        return prompt

    async def evaluate(
        self,
        state: Dict[str, Any],
        questions: Dict[str, Any],
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        target_model = model or self.model
        client = self._get_client()

        system_prompt = self._build_system_prompt(questions)
        user_content = json.dumps(state, indent=2)

        t1 = time.perf_counter()

        response = None
        max_retries = 3
        backoff = 1.5
        for attempt in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    model=target_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                break
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "Rate limit" in err_str or isinstance(e, openai.RateLimitError)) and attempt < max_retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    raise e

        t2 = time.perf_counter()

        content = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(content)
            if "decisions" in parsed and isinstance(parsed["decisions"], dict):
                answers = parsed["decisions"]
            else:
                answers = parsed
        except json.JSONDecodeError:
            answers = {"raw_output": content}

        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0

        # Cost calculation
        cost_usd = (
            (prompt_tokens / 1_000_000.0) * self.input_price +
            (completion_tokens / 1_000_000.0) * self.output_price
        )

        return {
            "provider": self.provider,
            "model": target_model,
            "answers": answers,
            "usage": {
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "cost_usd": round(cost_usd, 7),
            "timing": {
                "prep_ms": round((t1 - t0) * 1000, 3),
                "api_ms": round((t2 - t1) * 1000, 3),
                "total_ms": round((t2 - t0) * 1000, 3),
            },
        }

llm_service = LLMService()
