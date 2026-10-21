"""AI clients, injected as FastAPI dependencies so tests can swap in fakes (TEST-4).

Sprint analysis: Chat Completions through the class LiteLLM proxy (ANALYSIS_LLM_*).
Sprint review: Responses API with function tools on a Codex model (REVIEW_LLM_*); an empty
base URL calls OpenAI directly (AI-7).
"""

from dataclasses import dataclass, field

from fastapi import Depends, HTTPException
from openai import OpenAI

from ..config import settings

TIMEOUT_SECONDS = 120


class LLMError(Exception):
    pass


class AnalysisLLM:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model

    def complete(self, system: str, user: str) -> tuple[str, dict]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        text = response.choices[0].message.content if response.choices else None
        if not text:
            raise LLMError("The AI provider returned an empty response")
        usage = response.usage.model_dump() if getattr(response, "usage", None) else {}
        return text, usage


@dataclass
class ToolCall:
    call_id: str
    name: str
    arguments: str


@dataclass
class ReviewTurn:
    tool_calls: list[ToolCall]
    text: str | None
    # Items to send back as input on the next turn so the model keeps its context.
    output_items: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


class ReviewLLM:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model

    def run_turn(self, instructions: str, input_items: list, tools: list[dict], json_schema: dict | None = None) -> ReviewTurn:
        kwargs = {"model": self.model, "instructions": instructions, "input": input_items}
        if tools:
            kwargs["tools"] = tools
        if json_schema:
            kwargs["text"] = {"format": {"type": "json_schema", **json_schema}}
        response = self.client.responses.create(**kwargs)
        output_items = [item.model_dump(exclude_none=True) for item in response.output]
        calls = [
            ToolCall(call_id=item.call_id, name=item.name, arguments=item.arguments)
            for item in response.output
            if getattr(item, "type", None) == "function_call"
        ]
        usage = response.usage.model_dump() if getattr(response, "usage", None) else {}
        return ReviewTurn(tool_calls=calls, text=getattr(response, "output_text", None) or None, output_items=output_items, usage=usage)


def get_analysis_llm() -> AnalysisLLM | None:
    if not (settings.analysis_llm_base_url and settings.analysis_llm_model):
        return None
    client = OpenAI(
        base_url=settings.analysis_llm_base_url,
        api_key=settings.analysis_llm_api_key or "not-set",
        timeout=TIMEOUT_SECONDS,
        max_retries=1,
    )
    return AnalysisLLM(client, settings.analysis_llm_model)


def require_analysis_llm(llm: AnalysisLLM | None = Depends(get_analysis_llm)) -> AnalysisLLM:
    if llm is None:
        raise HTTPException(
            status_code=503,
            detail="Sprint analysis isn't configured. Set ANALYSIS_LLM_BASE_URL and ANALYSIS_LLM_MODEL.",
        )
    return llm


def get_review_llm() -> ReviewLLM | None:
    if not (settings.review_llm_api_key and settings.review_llm_model):
        return None
    client = OpenAI(
        base_url=settings.review_llm_base_url or None,
        api_key=settings.review_llm_api_key,
        timeout=TIMEOUT_SECONDS,
        max_retries=1,
    )
    return ReviewLLM(client, settings.review_llm_model)
