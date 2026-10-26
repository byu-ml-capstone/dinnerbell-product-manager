"""Exercise the real OpenAI SDK against MockTransport, never a paid API"""

import json

import httpx
import pytest
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


def test_default_model_and_output_budgets():
    settings = Settings(_env_file=None)
    assert settings.analysis_llm_max_output_tokens == 4096
    assert settings.review_llm_max_output_tokens == 6000


def test_shared_key_configures_both_clients_only_for_openai(monkeypatch):
    monkeypatch.setattr(llm.settings, "openai_api_key", "shared-test-key")
    for area in ("analysis", "review"):
        monkeypatch.setattr(llm.settings, f"{area}_llm_model", "gpt-6-luna")
        monkeypatch.setattr(llm.settings, f"{area}_llm_base_url", "https://api.openai.com/v1")
        monkeypatch.setattr(llm.settings, f"{area}_llm_api_key", "")
    analysis, review = llm.get_analysis_llm(), llm.get_review_llm()
    try:
        assert analysis.model == review.model == "gpt-6-luna"
        assert analysis.client.api_key == review.client.api_key == "shared-test-key"
    finally:
        analysis.client.close()
        review.client.close()
    for area in ("analysis", "review"):
        monkeypatch.setattr(llm.settings, f"{area}_llm_base_url", "https://proxy.example/v1")
    assert llm.get_analysis_llm() is None
    assert llm.get_review_llm() is None
    monkeypatch.setattr(llm.settings, "analysis_llm_api_key", "proxy-test-key")
    analysis = llm.get_analysis_llm()
    try:
        assert analysis.client.api_key == "proxy-test-key"
    finally:
        analysis.client.close()


def test_independent_key_overrides_shared_key(monkeypatch):
    monkeypatch.setattr(llm.settings, "openai_api_key", "shared-test-key")
    monkeypatch.setattr(llm.settings, "review_llm_api_key", "review-test-key")
    monkeypatch.setattr(llm.settings, "review_llm_model", "gpt-6-luna")
    monkeypatch.setattr(llm.settings, "review_llm_base_url", "")
    review = llm.get_review_llm()
    try:
        assert review.client.api_key == "review-test-key"
        assert str(review.client.base_url) == "https://api.openai.com/v1/"
    finally:
        review.client.close()


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
