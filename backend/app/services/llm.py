"""AI clients, injected as FastAPI dependencies so tests can swap in fakes (TEST-4).

Sprint analysis: Chat Completions (ANALYSIS_LLM_*)
Sprint review: Responses API with function tools (REVIEW_LLM_*)
Eason selected gpt-6-luna for both; explicit settings can still use a class proxy
"""

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from ..config import settings

TIMEOUT_SECONDS = 120


class LLMError(Exception):
    pass


def provider_error_message(error: Exception) -> str:
    """Expose actionable errors without provider bodies, credentials or request data"""
    if isinstance(error, LLMError):
        return str(error)
    if isinstance(error, APITimeoutError):
        return "The AI request timed out. Try again."
    if isinstance(error, APIConnectionError):
        return "Couldn't reach the AI provider. Check the API address and network."
    if isinstance(error, APIStatusError):
        messages = {
            400: "The AI provider rejected the request. Check model and API compatibility.",
            401: "AI API key was rejected. Check the backend API key.",
            403: "The AI API key doesn't have permission to use this model.",
            404: "AI model or endpoint not found. Check the model name and base URL.",
            429: "AI quota or rate limit reached. Check billing or try again later.",
        }
        return messages.get(error.status_code, f"The AI provider returned HTTP {error.status_code}. Try again later.")
    return "The AI request failed. Try again or check the backend configuration."


def _api_key(explicit_key: str | None, base_url: str | None) -> str | None:
    if explicit_key:
        return explicit_key
    url = urlsplit(base_url or "https://api.openai.com/v1")
    if url.scheme == "https" and url.netloc == "api.openai.com":
        return settings.openai_api_key or None
    return None


class AnalysisLLM:
    def __init__(self, client, model: str, reasoning_effort: str | None = None, max_output_tokens: int = 4096):
        self.client = client
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens

    def complete(self, system: str, user: str) -> tuple[str, dict]:
        kwargs = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_completion_tokens": self.max_output_tokens,
        }
        if self.reasoning_effort and self.reasoning_effort != "none":
            kwargs["reasoning_effort"] = self.reasoning_effort
        response = self.client.chat.completions.create(**kwargs)
        if response.choices and response.choices[0].finish_reason == "length":
            raise LLMError("The AI reached its output token limit. Increase ANALYSIS_LLM_MAX_OUTPUT_TOKENS and try again.")
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
    def __init__(self, client, model: str, reasoning_effort: str | None = None, max_output_tokens: int = 6000):
        self.client = client
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens

    def run_turn(self, instructions: str, input_items: list, tools: list[dict], json_schema: dict | None = None) -> ReviewTurn:
        kwargs = {"model": self.model, "instructions": instructions, "input": input_items}
        kwargs["max_output_tokens"] = self.max_output_tokens
        if self.reasoning_effort:
            kwargs["reasoning"] = {"effort": self.reasoning_effort}
        if tools:
            kwargs["tools"] = tools
        if json_schema:
            kwargs["text"] = {"format": {"type": "json_schema", **json_schema}}
        response = self.client.responses.create(**kwargs)
        if response.status == "incomplete":
            raise LLMError("The AI response was incomplete. Check REVIEW_LLM_MAX_OUTPUT_TOKENS and try again.")
        if response.status != "completed":
            raise LLMError("The AI provider did not complete the review response. Try again.")
        output_items = [item.model_dump(exclude_none=True) for item in response.output]
        calls = [
            ToolCall(call_id=item.call_id, name=item.name, arguments=item.arguments)
            for item in response.output
            if getattr(item, "type", None) == "function_call"
        ]
        usage = response.usage.model_dump() if getattr(response, "usage", None) else {}
        return ReviewTurn(tool_calls=calls, text=getattr(response, "output_text", None) or None, output_items=output_items, usage=usage)


def get_analysis_llm() -> AnalysisLLM | None:
    key = _api_key(settings.analysis_llm_api_key, settings.analysis_llm_base_url)
    if not (settings.analysis_llm_base_url and settings.analysis_llm_model and key):
        return None
    client = OpenAI(
        base_url=settings.analysis_llm_base_url,
        api_key=key,
        timeout=TIMEOUT_SECONDS,
        max_retries=1,
    )
    return AnalysisLLM(client, settings.analysis_llm_model, settings.analysis_llm_reasoning_effort, settings.analysis_llm_max_output_tokens)


def require_analysis_llm(llm: AnalysisLLM | None = Depends(get_analysis_llm)) -> AnalysisLLM:
    if llm is None:
        raise HTTPException(
            status_code=503,
            detail="Sprint analysis isn't configured. Set OPENAI_API_KEY (or ANALYSIS_LLM_API_KEY), ANALYSIS_LLM_BASE_URL and ANALYSIS_LLM_MODEL.",
        )
    return llm


def get_review_llm() -> ReviewLLM | None:
    key = _api_key(settings.review_llm_api_key, settings.review_llm_base_url)
    if not (key and settings.review_llm_model):
        return None
    client = OpenAI(
        base_url=settings.review_llm_base_url or None,
        api_key=key,
        timeout=TIMEOUT_SECONDS,
        max_retries=1,
    )
    return ReviewLLM(client, settings.review_llm_model, settings.review_llm_reasoning_effort, settings.review_llm_max_output_tokens)
