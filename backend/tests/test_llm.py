"""Groq-first / Gemini-fallback routing."""
import dataclasses
from unittest.mock import patch

import groq
import httpx
import pytest

from app.core import llm
from app.core.config import get_settings


def _groq_error(cls, status):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return cls(message=f"HTTP {status}", response=httpx.Response(status, request=request), body=None)


@pytest.fixture(autouse=True)
def no_sleep():
    with patch.object(llm.time, "sleep") as sleep:
        yield sleep


def test_groq_success_does_not_touch_gemini():
    with patch.object(llm, "_groq_chat", return_value="groq answer") as g, \
         patch.object(llm, "_gemini_generate") as gem:
        assert llm.complete("t", "hi") == "groq answer"
    assert g.call_count == 1
    gem.assert_not_called()


def test_transient_groq_errors_retry_three_times_then_fall_back_to_gemini(no_sleep):
    err = _groq_error(groq.RateLimitError, 429)
    with patch.object(llm, "_groq_chat", side_effect=err) as g, \
         patch.object(llm, "_gemini_generate", return_value="gemini answer") as gem:
        assert llm.complete("t", "hi") == "gemini answer"
    assert g.call_count == 3
    assert gem.call_count == 1
    assert [c.args[0] for c in no_sleep.call_args_list] == [1.0, 2.0]  # backoff between attempts


def test_groq_recovers_on_second_attempt():
    err = _groq_error(groq.InternalServerError, 503)
    with patch.object(llm, "_groq_chat", side_effect=[err, "ok"]) as g, \
         patch.object(llm, "_gemini_generate") as gem:
        assert llm.complete("t", "hi") == "ok"
    assert g.call_count == 2
    gem.assert_not_called()


def test_permanent_groq_error_skips_remaining_retries():
    err = _groq_error(groq.NotFoundError, 404)  # e.g. model decommissioned
    with patch.object(llm, "_groq_chat", side_effect=err) as g, \
         patch.object(llm, "_gemini_generate", return_value="gemini answer"):
        assert llm.complete("t", "hi") == "gemini answer"
    assert g.call_count == 1


def test_empty_groq_response_counts_as_failure():
    with patch.object(llm, "_groq_chat", side_effect=llm.EmptyResponseError("empty")) as g, \
         patch.object(llm, "_gemini_generate", return_value="gemini answer"):
        assert llm.complete("t", "hi") == "gemini answer"
    assert g.call_count == 3


def test_both_providers_failing_raises():
    with patch.object(llm, "_groq_chat", side_effect=RuntimeError("groq down")), \
         patch.object(llm, "_gemini_generate", side_effect=RuntimeError("gemini down")) as gem:
        with pytest.raises(llm.LLMUnavailableError):
            llm.complete("t", "hi")
    assert gem.call_count == get_settings().gemini_max_attempts


def test_without_groq_key_goes_straight_to_gemini():
    no_groq = dataclasses.replace(get_settings(), groq_api_key="")
    with patch.object(llm, "get_settings", return_value=no_groq), \
         patch.object(llm, "_groq_chat") as g, \
         patch.object(llm, "_gemini_generate", return_value="gemini answer"):
        assert llm.complete("t", "hi") == "gemini answer"
    g.assert_not_called()


def test_json_mode_and_system_prompt_are_forwarded_to_both_providers():
    err = _groq_error(groq.RateLimitError, 429)
    with patch.object(llm, "_groq_chat", side_effect=err) as g, \
         patch.object(llm, "_gemini_generate", return_value="{}") as gem:
        llm.complete("t", "user text", system="sys", json_mode=True)
    model, messages, json_mode, _ = g.call_args.args
    assert model == get_settings().groq_text_model
    assert messages[0] == {"role": "system", "content": "sys"}
    assert json_mode is True
    assert gem.call_args.args == ("user text", "sys", True)


def test_vision_uses_groq_vision_model_then_gemini():
    err = _groq_error(groq.RateLimitError, 429)
    with patch.object(llm, "_groq_chat", side_effect=err) as g, \
         patch.object(llm, "_gemini_generate", return_value="page text") as gem:
        assert llm.complete_with_image("v", "read this", b"\xff\xd8fakejpeg") == "page text"
    assert g.call_args.args[0] == get_settings().groq_vision_model
    assert g.call_count == 3
    assert gem.call_count == 1


def test_vision_skips_groq_when_no_vision_model_configured():
    cfg = dataclasses.replace(get_settings(), groq_vision_model="")
    with patch.object(llm, "get_settings", return_value=cfg), \
         patch.object(llm, "_groq_chat") as g, \
         patch.object(llm, "_gemini_generate", return_value="page text"):
        assert llm.complete_with_image("v", "read", b"img") == "page text"
    g.assert_not_called()


def test_gpt_oss_request_shape():
    """The real Groq SDK call gets JSON mode + low reasoning effort, no reasoning text."""
    class FakeCompletions:
        def create(self, **kwargs):
            self.kwargs = kwargs
            msg = type("M", (), {"content": " {\"a\": 1} "})()
            return type("C", (), {"choices": [type("Ch", (), {"message": msg})()]})()

    fake = FakeCompletions()
    client = type("Client", (), {"chat": type("Chat", (), {"completions": fake})()})()
    with patch.object(llm, "_groq_client", return_value=client):
        out = llm._groq_chat("openai/gpt-oss-20b", [{"role": "user", "content": "x"}], True, None)
    assert out == '{"a": 1}'
    assert fake.kwargs["response_format"] == {"type": "json_object"}
    assert fake.kwargs["reasoning_effort"] == "low"
    assert fake.kwargs["include_reasoning"] is False
