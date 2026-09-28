"""Runs the real GeminiLLM code against a fake Gemini API.

No API key or network is needed. It checks that each call sends the request the
generateContent endpoint expects (model, system prompt, JSON schema) and that the
parsed replies drive the graph correctly.
"""
import json

import httpx
import pytest
from google import genai
from google.genai import types

from dinegraph.graph import build_graph
from dinegraph.llm import ClaudeLLM, GeminiLLM, MissingKeyError, RuleBasedLLM, make_llm
from dinegraph.state import initial_state
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command


def reply(text: str | None, finish_reason: str = "STOP") -> dict:
    parts = [] if text is None else [{"text": text}]
    return {"candidates": [{"content": {"role": "model", "parts": parts}, "finishReason": finish_reason}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 10}}


class FakeAPI:
    """Answers generateContent from a function of the request body and records every request."""

    def __init__(self, answer):
        self.answer = answer
        self.requests: list[tuple[str, dict]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append((request.url.path, body))
        return httpx.Response(200, json=self.answer(body))

    def client(self) -> genai.Client:
        http = httpx.Client(transport=httpx.MockTransport(self))
        return genai.Client(api_key="test-key", http_options=types.HttpOptions(
            httpx_client=http, retry_options=types.HttpRetryOptions(attempts=1)))


def system_of(body: dict) -> str:
    return body["systemInstruction"]["parts"][0]["text"]


def schema_of(body: dict) -> dict | None:
    config = body.get("generationConfig", {})
    return config.get("responseSchema") or config.get("responseJsonSchema")


def test_parse_order_request_and_result():
    api = FakeAPI(lambda b: reply(json.dumps({"is_food_order": True, "items": [
        {"dish": "Veg Biryani", "quantity": 2, "note": "extra raita"}, {"dish": "Cold Coffee", "quantity": 1}]})))
    llm = GeminiLLM(model="gemini-3.5-flash", client=api.client())

    parsed = llm.parse_order("two biryanis with extra raita and a cold coffee", ["Veg Biryani", "Cold Coffee"])

    assert parsed.is_food_order
    assert [(i.dish, i.quantity, i.note) for i in parsed.items] == [
        ("Veg Biryani", 2, "extra raita"), ("Cold Coffee", 1, "")]
    path, body = api.requests[0]
    assert path.endswith("/models/gemini-3.5-flash:generateContent")
    assert "Veg Biryani, Cold Coffee" in system_of(body)
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert "is_food_order" in json.dumps(schema_of(body))
    assert body["contents"][0]["parts"][0]["text"] == "two biryanis with extra raita and a cold coffee"


def test_decision_and_payment():
    answers = iter([{"action": "cancel", "has_order_details": False}, {"method": "upi"}])
    api = FakeAPI(lambda b: reply(json.dumps(next(answers))))
    llm = GeminiLLM(client=api.client())

    assert llm.classify_decision("forget it", partial_allowed=True).action == "cancel"
    assert llm.classify_payment("I'll GPay you").method == "upi"
    assert "accept the available part" in system_of(api.requests[0][1])


def test_compose_sends_facts_and_returns_text():
    api = FakeAPI(lambda b: reply("  Your order is confirmed!  "))
    llm = GeminiLLM(client=api.client())

    assert llm.compose("order_confirmed", {"order": ["Masala Dosa x2"]}) == "Your order is confirmed!"
    body = api.requests[0][1]
    assert schema_of(body) is None
    assert "Masala Dosa x2" in body["contents"][0]["parts"][0]["text"]


@pytest.mark.parametrize("bad", [reply(None, "SAFETY"), reply("not json"), reply('{"items": 3}')])
def test_blocked_or_bad_replies_fall_back(bad):
    llm = GeminiLLM(client=FakeAPI(lambda b: bad).client())

    assert llm.parse_order("2 dosa", ["Masala Dosa"]).is_food_order is False
    assert llm.classify_payment("card").method == "unclear"


def test_blocked_compose_uses_the_template():
    llm = GeminiLLM(client=FakeAPI(lambda b: reply(None, "SAFETY")).client())

    assert llm.compose("payment_unclear", {}) == RuleBasedLLM().compose("payment_unclear", {})


def test_missing_key_is_reported_on_first_call(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    llm = GeminiLLM()  # no error yet, so the server can start

    with pytest.raises(MissingKeyError, match="GEMINI_API_KEY"):
        llm.parse_order("2 dosa", ["Masala Dosa"])


def test_make_llm_picks_the_provider(monkeypatch):
    monkeypatch.delenv("DINEGRAPH_LLM", raising=False)
    assert isinstance(make_llm(), GeminiLLM)
    assert isinstance(make_llm("offline"), RuleBasedLLM)
    monkeypatch.setenv("DINEGRAPH_LLM", "Claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    assert isinstance(make_llm(), ClaudeLLM)
    with pytest.raises(ValueError, match="gemini, claude, offline"):
        make_llm("grok")


def fake_restaurant(body: dict) -> dict:
    schema = json.dumps(schema_of(body) or {})
    if not schema_of(body):  # compose
        return reply("[" + body["contents"][0]["parts"][0]["text"].splitlines()[0] + "]")
    if "is_food_order" in schema:
        return reply(json.dumps({"is_food_order": True, "items": [{"dish": "Masala Dosa", "quantity": 2}]}))
    if "method" in schema:
        text = body["contents"][0]["parts"][0]["text"]
        return reply(json.dumps({"method": "card" if "card" in text else "unclear"}))
    return reply(json.dumps({"action": "accept_partial", "has_order_details": False}))


def test_full_conversation_through_the_graph():
    api = FakeAPI(fake_restaurant)
    graph = build_graph(GeminiLLM(client=api.client()), outcome=lambda stage: True,
                        menu={"Masala Dosa": 6}, prices={"Masala Dosa": 120}, checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "t1"}, "recursion_limit": 100}

    graph.invoke(initial_state("Welcome"), cfg)
    graph.invoke(Command(resume="2 dosas please"), cfg)
    state = graph.invoke(Command(resume="I'll pay by card"), cfg)

    assert state["status"] == "PAID"
    assert state["bill_total"] == 240
    assert state["payment_method"] == "card"
    assert state["final_result"] == "COMPLETED"
    assert state["messages"][-1].content.startswith("[Situation: order_complete")
