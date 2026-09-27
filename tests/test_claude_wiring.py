"""Runs the real ClaudeLLM code against a fake Anthropic API.

No API key or network is needed. It checks that each call sends the request the
Messages API expects (model, effort, structured-output schema) and that the
parsed replies drive the graph correctly.
"""
import json

import anthropic
import httpx2 as httpx
import pytest

from dinegraph.graph import build_graph
from dinegraph.llm import ClaudeLLM
from dinegraph.state import initial_state
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command


def reply(text: str, stop_reason: str = "end_turn") -> dict:
    return {
        "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5",
        "content": [{"type": "text", "text": text}], "stop_reason": stop_reason,
        "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 10},
    }


class FakeAPI:
    """Answers /v1/messages from a function of the request body and records every request."""

    def __init__(self, answer):
        self.answer = answer
        self.requests: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append(body)
        return httpx.Response(200, json=self.answer(body))

    def client(self) -> anthropic.Anthropic:
        return anthropic.Anthropic(api_key="test-key", max_retries=0,
                                   http_client=httpx.Client(transport=httpx.MockTransport(self)))


def schema_of(body: dict) -> dict:
    return body["output_config"]["format"]["schema"]


def test_parse_order_request_and_result():
    api = FakeAPI(lambda b: reply(json.dumps({"is_food_order": True, "items": [
        {"dish": "Veg Biryani", "quantity": 2}, {"dish": "Cold Coffee", "quantity": 1}]})))
    llm = ClaudeLLM(model="claude-opus-5", client=api.client())

    parsed = llm.parse_order("two biryanis and a cold coffee pls", ["Veg Biryani", "Cold Coffee"])

    assert parsed.is_food_order
    assert [(i.dish, i.quantity) for i in parsed.items] == [("Veg Biryani", 2), ("Cold Coffee", 1)]
    body = api.requests[0]
    assert body["model"] == "claude-opus-5"
    assert body["output_config"]["effort"] == "low"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert "is_food_order" in schema_of(body)["properties"]
    assert "Veg Biryani" in body["system"]
    assert body["messages"] == [{"role": "user", "content": "two biryanis and a cold coffee pls"}]


def test_refusal_is_treated_as_not_an_order():
    api = FakeAPI(lambda b: reply("", stop_reason="refusal"))
    llm = ClaudeLLM(client=api.client())
    assert llm.parse_order("something", ["Veg Biryani"]).is_food_order is False
    assert llm.classify_decision("x", True).action == "unclear"
    assert llm.classify_payment("x").method == "unclear"


def test_compose_returns_text_and_falls_back_when_empty():
    api = FakeAPI(lambda b: reply("Your order is confirmed."))
    assert ClaudeLLM(client=api.client()).compose("order_confirmed", {"items": []}) == "Your order is confirmed."
    assert "format" not in api.requests[0].get("output_config", {})

    empty = FakeAPI(lambda b: reply(""))
    assert ClaudeLLM(client=empty.client()).compose("order_complete", {}) != ""


def test_env_var_picks_the_model(monkeypatch):
    monkeypatch.setenv("DINEGRAPH_MODEL", "claude-sonnet-5")
    api = FakeAPI(lambda b: reply(json.dumps({"method": "upi"})))
    assert ClaudeLLM(client=api.client()).classify_payment("gpay").method == "upi"
    assert api.requests[0]["model"] == "claude-sonnet-5"


def fake_restaurant(body: dict) -> dict:
    """Plays Claude for a whole conversation, choosing the reply by the requested schema."""
    fmt = body.get("output_config", {}).get("format")
    user = body["messages"][0]["content"].lower()
    if fmt is None:  # compose
        return reply(f"[{body['messages'][0]['content'].splitlines()[0]}]")
    props = fmt["schema"]["properties"]
    if "is_food_order" in props:
        return reply(json.dumps({"is_food_order": True, "items": [{"dish": "Masala Dosa", "quantity": 2}]}))
    if "method" in props:
        return reply(json.dumps({"method": "card" if "card" in user else "unclear"}))
    return reply(json.dumps({"action": "accept_partial", "has_order_details": False}))


def test_full_conversation_through_the_graph():
    api = FakeAPI(fake_restaurant)
    graph = build_graph(ClaudeLLM(client=api.client()), outcome=lambda stage: True,
                        menu={"Masala Dosa": 6}, prices={"Masala Dosa": 120}, checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "t1"}, "recursion_limit": 100}

    graph.invoke(initial_state("Welcome"), cfg)
    graph.invoke(Command(resume="2 dosas please"), cfg)
    state = graph.invoke(Command(resume="I'll pay by card"), cfg)

    assert state["status"] == "PAID"
    assert state["bill_total"] == 240
    assert state["payment_method"] == "card"
    assert state["final_result"] == "COMPLETED"
    kinds = ["compose" if "format" not in r.get("output_config", {}) else
             next(iter(r["output_config"]["format"]["schema"]["properties"])) for r in api.requests]
    assert kinds[0] == "is_food_order" and "method" in kinds and "compose" in kinds
