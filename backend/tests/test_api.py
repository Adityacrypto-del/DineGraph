"""Tests for the HTTP backend, using the offline LLM and scripted outcomes."""

import time

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient

from dinegraph.api import create_app
from dinegraph.llm import RuleBasedLLM

MENU = {"Veg Biryani": 10, "Cold Coffee": 2, "Masala Dosa": 6}
PRICES = {"Veg Biryani": 220, "Cold Coffee": 150, "Masala Dosa": 120}


def make_client(db, outcomes=(), llm=None, **options):
    script = list(outcomes)
    app = create_app(
        llm=llm or RuleBasedLLM(),
        outcome=lambda stage: script.pop(0)[1],
        **db.options,
        menu=MENU,
        prices=PRICES,
        **options,
    )
    return TestClient(app)


def say(client, sid, text, expect=200):
    r = client.post(f"/sessions/{sid}/messages", json={"text": text})
    assert r.status_code == expect, r.text
    return r.json()


def test_health_and_menu(db):
    c = make_client(db)
    assert c.get("/health").json() == {"ok": True, "llm": "RuleBasedLLM", "kitchen_seconds": 0.0,
                                    "database": db.kind}
    menu = c.get("/menu").json()
    assert menu["max_dishes"] == 3
    assert {"dish": "Veg Biryani", "available": 10, "price": 220} in menu["items"]


def test_full_session_over_http(db):
    c = make_client(db, [("cook", True), ("serve", True), ("pay", True)])
    s = c.post("/sessions").json()
    sid = s["session_id"]
    assert s["waiting_for"] == "order" and not s["done"]
    assert s["messages"][0]["role"] == "assistant"
    assert s["counters"] == {"order_retries": 3, "cook_retries": 2, "serve_retries": 2, "payment_retries": 2}

    s = say(c, sid, "2 Veg Biryani")
    assert s["waiting_for"] == "payment"
    assert s["bill_total"] == 440
    roles = [m["role"] for m in s["messages"]]
    assert roles[1] == "user" and "kitchen" in roles and "waiter" in roles

    s = say(c, sid, "upi")
    assert s["done"] and s["waiting_for"] is None
    assert s["final_result"] == "COMPLETED"
    assert s["payment_method"] == "upi"

    # the finished session can be read back but not continued
    assert c.get(f"/sessions/{sid}").json()["final_result"] == "COMPLETED"
    say(c, sid, "one more thing", expect=409)


def test_partial_order_decision_over_http(db):
    c = make_client(db, [("cook", True), ("serve", True)])
    sid = c.post("/sessions").json()["session_id"]
    s = say(c, sid, "5 Cold Coffee")
    assert s["waiting_for"] == "decision"
    assert s["status"] == "PARTIAL"
    assert s["order"] == [{"dish": "Cold Coffee", "required_quantity": 5, "available_quantity": 2, "note": ""}]
    assert s["counters"]["order_retries"] == 2
    s = say(c, sid, "confirm")
    assert s["waiting_for"] == "payment"
    s = say(c, sid, "cash")
    assert s["final_result"] == "COMPLETED" and s["bill_total"] == 300


def test_unknown_session_and_empty_text(db):
    c = make_client(db)
    assert c.get("/sessions/nope").status_code == 404
    assert c.post("/sessions/nope/messages", json={"text": "hi"}).status_code == 404
    sid = c.post("/sessions").json()["session_id"]
    assert c.post(f"/sessions/{sid}/messages", json={"text": ""}).status_code == 422


def test_sessions_survive_an_app_restart(db):
    c1 = make_client(db)
    sid = c1.post("/sessions").json()["session_id"]
    say(c1, sid, "tell me a joke")
    c2 = make_client(db)  # new app, same database file
    s = c2.get(f"/sessions/{sid}").json()
    assert s["counters"]["order_retries"] == 2
    assert s["waiting_for"] == "order"


class FlakyLLM(RuleBasedLLM):
    """Fails the first parse_order call with an API error, then works."""

    def __init__(self):
        self.failed = False

    def parse_order(self, text, menu_names):
        if not self.failed:
            self.failed = True
            request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            raise anthropic.APIConnectionError(request=request)
        return super().parse_order(text, menu_names)


def test_llm_failure_can_be_retried(db):
    c = make_client(db, [("cook", True), ("serve", True)], llm=FlakyLLM())
    sid = c.post("/sessions").json()["session_id"]
    r = c.post(f"/sessions/{sid}/messages", json={"text": "1 Masala Dosa"})
    assert r.status_code == 502
    s = c.get(f"/sessions/{sid}").json()
    assert s["stalled"] and s["waiting_for"] is None
    say(c, sid, "again", expect=409)  # must retry first

    r = c.post(f"/sessions/{sid}/retry")
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["waiting_for"] == "payment" and not s["stalled"]
    assert c.post(f"/sessions/{sid}/retry").status_code == 409


# --------------------------------------------------------------------- stock, orders, admin

def finish_order(c, text, payment="cash"):
    sid = c.post("/sessions").json()["session_id"]
    say(c, sid, text)
    return sid, say(c, sid, payment)


def test_menu_stock_goes_down_and_is_shared_between_sessions(db):
    c = make_client(db, [("cook", True), ("serve", True)])
    finish_order(c, "2 Cold Coffee")
    menu = {i["dish"]: i["available"] for i in c.get("/menu").json()["items"]}
    assert menu["Cold Coffee"] == 0
    sid = c.post("/sessions").json()["session_id"]
    s = say(c, sid, "1 Cold Coffee")
    assert s["status"] == "NOT_AVAILABLE"


def test_orders_are_recorded(db):
    c = make_client(db, [("cook", True), ("serve", True), ("cook", False), ("cook", False)])
    paid, _ = finish_order(c, "2 Masala Dosa")
    failed = c.post("/sessions").json()["session_id"]
    say(c, failed, "1 Veg Biryani")

    orders = c.get("/orders").json()
    assert [o["session_id"] for o in orders] == [failed, paid]  # newest first
    o = c.get(f"/orders/{paid}").json()
    assert (o["status"], o["final_result"], o["bill_total"], o["payment_method"]) == \
        ("PAID", "COMPLETED", 240, "cash")
    assert o["items"][0]["dish"] == "Masala Dosa"
    assert [x["session_id"] for x in c.get("/orders", params={"status": "FAILED"}).json()] == [failed]
    assert c.get("/orders/nope").status_code == 404
    # the failed order's stock went back
    menu = {i["dish"]: i["available"] for i in c.get("/menu").json()["items"]}
    assert menu["Veg Biryani"] == 10 and menu["Masala Dosa"] == 4


def test_in_progress_session_has_an_order_record(db):
    c = make_client(db)
    sid = c.post("/sessions").json()["session_id"]
    assert c.get(f"/orders/{sid}").json()["status"] == "NEW"


def test_admin_menu_changes(db):
    c = make_client(db, [("cook", True), ("serve", True)])
    r = c.put("/admin/menu/Cold Coffee", json={"quantity": 20})
    assert r.json() == {"dish": "Cold Coffee", "available": 20, "price": 150}
    r = c.put("/admin/menu/cold coffee", json={"price": 170})  # case-insensitive
    assert r.json() == {"dish": "Cold Coffee", "available": 20, "price": 170}
    assert c.put("/admin/menu/Idli", json={"quantity": 5}).status_code == 422  # new dish needs a price
    assert c.put("/admin/menu/Idli", json={"quantity": 5, "price": 60}).status_code == 200
    assert c.put("/admin/menu/Idli", json={"quantity": -1}).status_code == 422

    _, s = finish_order(c, "2 Idli, 1 Cold Coffee")
    assert s["bill_total"] == 2 * 60 + 170

    assert c.delete("/admin/menu/Idli").status_code == 204
    assert c.delete("/admin/menu/Idli").status_code == 404
    assert "Idli" not in [i["dish"] for i in c.get("/menu").json()["items"]]


def test_admin_stats(db):
    c = make_client(db, [("cook", True), ("serve", True), ("pay", True),
                               ("cook", True), ("serve", True)])
    finish_order(c, "2 Masala Dosa", payment="upi")
    finish_order(c, "1 Veg Biryani", payment="cash")
    sid = c.post("/sessions").json()["session_id"]
    say(c, sid, "5 Cold Coffee")
    say(c, sid, "cancel")
    c.post("/sessions")  # still waiting for an order
    assert c.get("/admin/stats").json() == {
        "total_orders": 4, "completed": 2, "failed": 0, "cancelled": 1, "in_progress": 1,
        "revenue": 460, "revenue_by_method": {"upi": 240, "cash": 220},
    }


def test_admin_token(db, monkeypatch):
    monkeypatch.setenv("DINEGRAPH_ADMIN_TOKEN", "secret")
    c = make_client(db)
    assert c.get("/admin/stats").status_code == 401
    assert c.get("/admin/stats", headers={"X-Admin-Token": "wrong"}).status_code == 401
    assert c.get("/admin/stats", headers={"X-Admin-Token": "secret"}).status_code == 200
    assert c.put("/admin/menu/Veg Biryani", json={"quantity": 1}).status_code == 401
    assert c.get("/menu").status_code == 200  # customer routes stay open


def test_menu_seed_only_on_first_run(db):
    c1 = make_client(db)
    c1.put("/admin/menu/Veg Biryani", json={"quantity": 1})
    c2 = make_client(db)  # restart: the edited menu is kept, not reseeded
    menu = {i["dish"]: i["available"] for i in c2.get("/menu").json()["items"]}
    assert menu["Veg Biryani"] == 1


# --------------------------------------------------------------------- tables, notes, kitchen, tracking

def test_table_and_dish_notes(db):
    c = make_client(db, [("cook", True), ("serve", True)])
    s = c.post("/sessions", json={"table": 7}).json()
    assert s["table"] == 7
    sid = s["session_id"]
    s = say(c, sid, "2 Masala Dosa (extra spicy), 1 Cold Coffee")
    assert [(i["dish"], i["note"]) for i in s["order"]] == [("Masala Dosa", "extra spicy"), ("Cold Coffee", "")]
    say(c, sid, "cash")
    o = c.get(f"/orders/{sid}").json()
    assert o["table"] == 7 and o["stage"] == "" and o["items"][0]["note"] == "extra spicy"
    assert c.post("/sessions", json={"table": 0}).status_code == 422


def test_order_events_track_the_order(db):
    c = make_client(db, [("cook", False), ("cook", True), ("serve", True)])
    sid = c.post("/sessions", json={"table": 2}).json()["session_id"]
    say(c, sid, "1 Veg Biryani")
    say(c, sid, "cash")
    events = c.get(f"/orders/{sid}/events").json()
    assert [e["step"] for e in events] == [
        "start", "order_confirm", "reserve_stock", "cook", "cook", "serve", "request_payment", "pay", "finish"]
    assert events[0]["detail"] == "Seated at table 2."
    assert events[3]["detail"].startswith("Kitchen: cooking failed")
    assert events[-1]["status"] == "PAID" and events[-1]["detail"] == "COMPLETED"
    assert c.get("/orders/nope/events").status_code == 404


def test_kitchen_screen_follows_a_slow_kitchen(db):
    c = make_client(db, [("cook", True), ("serve", True)], kitchen_seconds=0.3)
    sid = c.post("/sessions", json={"table": 4}).json()["session_id"]
    s = c.post(f"/sessions/{sid}/messages", params={"wait": 0}, json={"text": "1 Masala Dosa (no onion)"}).json()
    assert s["busy"] and not s["stalled"]
    say(c, sid, "hello", expect=409)  # still cooking

    seen = []
    for _ in range(100):
        tickets = c.get("/kitchen").json()
        if tickets and tickets[0]["stage"] not in seen:
            seen.append(tickets[0]["stage"])
        if not c.get(f"/sessions/{sid}").json()["busy"]:
            break
        time.sleep(0.02)
    assert seen[:2] == ["cooking", "serving"]
    ticket = c.get("/kitchen").json()[0]
    assert ticket["stage"] == "paying" and ticket["table"] == 4 and ticket["items"][0]["note"] == "no onion"

    s = c.get(f"/sessions/{sid}").json()
    assert s["waiting_for"] == "payment" and s["next_step"] == "choose_payment"
    c.post(f"/sessions/{sid}/messages", json={"text": "cash"})
    for _ in range(100):
        if c.get(f"/sessions/{sid}").json()["done"]:
            break
        time.sleep(0.02)
    assert c.get("/kitchen").json() == []
