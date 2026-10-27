"""Exercise the real OpenAI SDK against MockTransport, never a paid API"""

import json

import httpx
import pytest
from fastapi import HTTPException
from openai import OpenAI

from app.config import Settings
from app.services import llm
from app.services.llm import AnalysisLLM, LLMError, ReviewLLM, provider_error_message
from app.services.sprint_review import TOOLS, VERDICT_SCHEMA


def chat_response(text="## Summary\nOn track.", finish_reason="stop"):
    return {
        "id": "chatcmpl-test", "object": "chat.completion", "created": 0, "model": "gpt-6-luna",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


def review_response(output, status="completed"):
    return {
        "id": "resp_test", "object": "response", "created_at": 0, "model": "gpt-6-luna",
        "status": status, "output": output,
        "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
    }


def message_output(text):
    return {"id": "msg_test", "type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": text, "annotations": []}]}


@pytest.fixture
def sdk():
    clients = []

    def make(handler):
        client = OpenAI(
            api_key="test-only-key", base_url="https://api.openai.com/v1", max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        clients.append(client)
        return client

    yield make
    for client in clients:
        client.close()


def test_provider_defaults_are_disabled_and_runtime_budgets_are_shared():
    settings = Settings(_env_file=None)
    assert settings.analysis_llm_base_url is None
    assert settings.analysis_llm_model is None
    assert settings.review_llm_base_url is None
    assert settings.review_llm_model is None
    assert settings.analysis_llm_reasoning_effort == "medium"
    assert settings.review_llm_reasoning_effort == "high"
    assert settings.analysis_llm_max_output_tokens == 4096
    assert settings.review_llm_max_output_tokens == 6000


@pytest.mark.parametrize("source", ["environment", "dotenv"])
def test_legacy_shared_key_cannot_enable_either_feature(monkeypatch, tmp_path, source):
    env_file = None
    if source == "environment":
        monkeypatch.setenv("OPENAI_API_KEY", "legacy-test-key")
    else:
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=legacy-test-key\n", encoding="utf-8")
    settings = Settings(_env_file=env_file)
    monkeypatch.setattr(llm, "settings", settings)
    for area in ("analysis", "review"):
        setattr(settings, f"{area}_llm_model", "gpt-6-luna")
        setattr(settings, f"{area}_llm_base_url", "https://api.openai.com/v1")
    assert not hasattr(settings, "openai_api_key")
    assert llm.get_analysis_llm() is None
    assert llm.get_review_llm() is None


def test_each_feature_requires_its_own_key_and_uses_its_provider(monkeypatch):
    settings = Settings(_env_file=None, analysis_llm_base_url="https://proxy.example/v1",
                        analysis_llm_model="classroom-chat", analysis_llm_api_key="proxy-test-key",
                        analysis_llm_reasoning_effort="none", review_llm_model="gpt-6-luna")
    monkeypatch.setattr(llm, "settings", settings)
    assert llm.get_review_llm() is None
    analysis = llm.get_analysis_llm()
    try:
        assert analysis.client.api_key == "proxy-test-key"
        assert str(analysis.client.base_url) == "https://proxy.example/v1/"
        assert analysis.model == "classroom-chat"
        assert analysis.reasoning_effort == "none"
    finally:
        analysis.client.close()
    settings.analysis_llm_api_key = None
    settings.review_llm_api_key = "review-test-key"
    assert llm.get_analysis_llm() is None
    review = llm.get_review_llm()
    try:
        assert review.client.api_key == "review-test-key"
        assert str(review.client.base_url) == "https://api.openai.com/v1/"
        assert review.reasoning_effort == "high"
    finally:
        review.client.close()


@pytest.mark.parametrize("area,missing", [("analysis", "base_url"), ("analysis", "model"), ("review", "model")])
def test_explicit_key_still_requires_feature_configuration(monkeypatch, area, missing):
    settings = Settings(_env_file=None)
    for field, value in (("base_url", "https://api.openai.com/v1"), ("model", "gpt-6-luna"), ("api_key", "test-only-key")):
        setattr(settings, f"{area}_llm_{field}", value)
    setattr(settings, f"{area}_llm_{missing}", None)
    monkeypatch.setattr(llm, "settings", settings)
    assert getattr(llm, f"get_{area}_llm")() is None


def test_blank_compose_values_use_backend_defaults(monkeypatch):
    for area in ("analysis", "review"):
        for name in ("REASONING_EFFORT", "MAX_OUTPUT_TOKENS"):
            monkeypatch.setenv(f"{area.upper()}_LLM_{name}", "")
    settings = Settings(_env_file=None)
    assert (settings.analysis_llm_reasoning_effort, settings.analysis_llm_max_output_tokens) == ("medium", 4096)
    assert (settings.review_llm_reasoning_effort, settings.review_llm_max_output_tokens) == ("high", 6000)


def test_analysis_configuration_helper_reports_feature_key():
    with pytest.raises(HTTPException) as captured:
        llm.require_analysis_llm(None)
    assert captured.value.status_code == 503
    assert "ANALYSIS_LLM_API_KEY" in captured.value.detail
    assert "OPENAI_API_KEY" not in captured.value.detail
    configured = object()
    assert llm.require_analysis_llm(configured) is configured


def test_analysis_sdk_sends_luna_low_effort_and_completion_limit(sdk):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=chat_response())

    text, usage = AnalysisLLM(sdk(respond), "gpt-6-luna", "low", 4096).complete("Use given metrics", "Sprint data")
    assert text == "## Summary\nOn track."
    assert usage["completion_tokens"] == 20
    assert requests[0].url == "https://api.openai.com/v1/chat/completions"
    body = json.loads(requests[0].content)
    assert body["model"] == "gpt-6-luna"
    assert body["reasoning_effort"] == "low"
    assert body["max_completion_tokens"] == 4096
    assert body["messages"][0]["content"] == "Use given metrics"
    assert "temperature" not in body and "top_p" not in body


@pytest.mark.parametrize("effort", [None, "none"])
def test_classroom_analysis_omits_disabled_reasoning_and_keeps_token_limit(sdk, effort):
    requests = []

    def respond(request):
        requests.append(request)
        body = json.loads(request.content)
        if "reasoning_effort" in body:
            return httpx.Response(400, json={"error": {"message": "Unsupported reasoning_effort"}})
        return httpx.Response(200, json=chat_response())

    text, _ = AnalysisLLM(sdk(respond), "classroom-chat", effort, 4096).complete("Use given metrics", "Sprint data")
    assert text == "## Summary\nOn track."
    body = json.loads(requests[0].content)
    assert body["model"] == "classroom-chat"
    assert "reasoning_effort" not in body
    assert body["max_completion_tokens"] == 4096


@pytest.mark.parametrize("text,finish,expected", [("Partial", "length", "token limit"), (None, "stop", "empty response")])
def test_analysis_rejects_truncated_or_empty_output(sdk, text, finish, expected):
    client = sdk(lambda request: httpx.Response(200, json=chat_response(text, finish)))
    with pytest.raises(LLMError, match=expected):
        AnalysisLLM(client, "gpt-6-luna").complete("Rules", "Sprint")


def test_review_sdk_round_trip_preserves_reasoning_and_function_items(sdk):
    requests = []
    verdict = {"verdict": "no_evidence", "summary": "No code evidence.", "criteria": [], "evidence": [], "has_tests": None}

    def respond(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(200, json=review_response([
                {"id": "rs_test", "type": "reasoning", "summary": []},
                {"id": "fc_test", "type": "function_call", "call_id": "call_test", "name": "read_file",
                 "arguments": '{"path":"app.py"}', "status": "completed"},
            ]))
        return httpx.Response(200, json=review_response([message_output(json.dumps(verdict))]))

    review = ReviewLLM(sdk(respond), "gpt-6-luna", "low", 6000)
    inputs = [{"role": "user", "content": "Review this story"}]
    first = review.run_turn("Read only", inputs, TOOLS, VERDICT_SCHEMA)
    assert first.tool_calls[0].name == "read_file"
    assert first.tool_calls[0].call_id == "call_test"
    inputs += first.output_items
    inputs.append({"type": "function_call_output", "call_id": "call_test", "output": "No code"})
    second = review.run_turn("Read only", inputs, TOOLS, VERDICT_SCHEMA)
    assert json.loads(second.text) == verdict
    assert second.usage["output_tokens"] == 20
    body = json.loads(requests[1].content)
    assert all(request.url == "https://api.openai.com/v1/responses" for request in requests)
    assert body["model"] == "gpt-6-luna" and body["reasoning"] == {"effort": "low"}
    assert body["max_output_tokens"] == 6000
    assert body["text"]["format"] == {"type": "json_schema", **VERDICT_SCHEMA}
    assert [item.get("type") for item in body["input"]][1:] == ["reasoning", "function_call", "function_call_output"]
    assert "temperature" not in body


@pytest.mark.parametrize("status", ["incomplete", "failed"])
def test_review_rejects_unfinished_response(sdk, status):
    client = sdk(lambda request: httpx.Response(200, json=review_response([], status)))
    with pytest.raises(LLMError):
        ReviewLLM(client, "gpt-6-luna").run_turn("Read only", [], [])


@pytest.mark.parametrize("status,expected", [(400, "compatibility"), (401, "key"), (403, "permission"),
                                           (404, "model"), (429, "quota"), (500, "HTTP 500")])
def test_provider_errors_are_actionable_without_exposing_body(sdk, status, expected):
    client = sdk(lambda request: httpx.Response(status, json={"error": {"message": "test-only-secret-never-display"}}))
    with pytest.raises(Exception) as captured:
        AnalysisLLM(client, "gpt-6-luna").complete("Rules", "Sprint")
    message = provider_error_message(captured.value)
    assert expected in message
    assert "test-only-secret" not in message


@pytest.mark.parametrize("kind", ["timeout", "connection"])
def test_transport_errors_are_actionable(sdk, kind):
    def fail(request):
        error = httpx.ReadTimeout if kind == "timeout" else httpx.ConnectError
        raise error("test-only-secret-never-display", request=request)

    with pytest.raises(Exception) as captured:
        AnalysisLLM(sdk(fail), "gpt-6-luna").complete("Rules", "Sprint")
    message = provider_error_message(captured.value)
    assert ("timed out" if kind == "timeout" else "Couldn't reach") in message
    assert "test-only-secret" not in message
