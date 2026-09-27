"""HTTP backend for DineGraph.

Run:  uvicorn dinegraph.api:app --reload

Each session is one LangGraph thread. Starting a session runs the graph until it
pauses for the first order. Sending a message resumes the paused graph with the
user's text and runs it until the next pause or the end.

Graph runs happen in a background thread. After every step the order record is
saved and an activity event is written, so the kitchen screen and order tracking
update while the kitchen works. A request waits up to DINEGRAPH_WAIT_SECONDS for
the graph to pause; if it is still running, the session comes back with busy=true
and the client polls GET /sessions/{id}. Busy sessions are tracked in memory, so
run a single server process.

Environment variables:
  DINEGRAPH_OFFLINE=1        use the rule-based LLM instead of Claude
  DINEGRAPH_DB=path.sqlite   where sessions are saved (default dinegraph.sqlite)
  DINEGRAPH_CORS_ORIGINS     comma-separated frontend origins (default the Vite dev server)
  DINEGRAPH_MODEL            Claude model (default claude-opus-5)
  DINEGRAPH_ADMIN_TOKEN      if set, /admin routes need the header X-Admin-Token with this value
  DINEGRAPH_KITCHEN_SECONDS  seconds each cook and serve attempt takes (default 0)
  DINEGRAPH_WAIT_SECONDS     how long a request waits for the graph to pause (default 15)
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
import uuid
from collections import defaultdict
from typing import Literal

import anthropic
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from pydantic import BaseModel, Field

from .graph import Outcome, build_graph, random_outcome
from .llm import ClaudeLLM, OrderLLM, RuleBasedLLM
from .main import welcome_text
from .state import MAX_DISHES, Status, initial_state
from .store import Store

RECURSION_LIMIT = 100


# --------------------------------------------------------------------------- schemas

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "kitchen", "waiter", "cashier"]
    content: str


class OrderLine(BaseModel):
    dish: str
    required_quantity: int
    available_quantity: int
    note: str = ""


class Counters(BaseModel):
    order_retries: int
    cook_retries: int
    serve_retries: int
    payment_retries: int


class SessionView(BaseModel):
    session_id: str
    messages: list[ChatMessage]
    waiting_for: Literal["order", "decision", "payment"] | None = Field(
        description="What the graph is paused for, or null when it is not waiting for the user."
    )
    prompt: str | None
    done: bool
    stalled: bool = Field(description="True if a step failed (for example an LLM error). Call /retry.")
    busy: bool = Field(description="True while the graph is still running. Poll GET /sessions/{id}.")
    next_step: str | None = Field(description="The graph node that runs next, or null when finished.")
    error: str | None = Field(description="Why the last run stopped, when the session is stalled.")
    table: int | None
    status: str
    order: list[OrderLine]
    counters: Counters
    bill_total: int
    payment_method: str
    final_result: str


class NewSession(BaseModel):
    table: int | None = Field(default=None, ge=1, le=999, description="Table number, if seated.")


class UserMessage(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class MenuItem(BaseModel):
    dish: str
    available: int
    price: int


class MenuView(BaseModel):
    max_dishes: int
    items: list[MenuItem]


class MenuUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=0)
    price: int | None = Field(default=None, ge=0)


class OrderRecord(BaseModel):
    session_id: str
    status: str
    final_result: str
    items: list[OrderLine]
    bill_total: int
    payment_method: str
    created_at: str
    updated_at: str
    table: int | None
    stage: str = Field(description="The graph node that runs next, or empty once finished.")


class OrderEvent(BaseModel):
    at: str
    step: str
    status: str
    detail: str


KitchenStage = Literal["cooking", "serving", "paying"]


class KitchenTicket(BaseModel):
    session_id: str
    table: int | None
    stage: KitchenStage
    status: str
    items: list[OrderLine]
    bill_total: int
    created_at: str
    updated_at: str


class Stats(BaseModel):
    total_orders: int
    completed: int
    failed: int
    cancelled: int
    in_progress: int
    revenue: int
    revenue_by_method: dict[str, int]


# --------------------------------------------------------------------------- helpers

WAIT_QUERY = Query(default=None, ge=0, le=60, description=(
    "Seconds to wait for the graph to pause before answering with busy=true. "
    "Defaults to DINEGRAPH_WAIT_SECONDS."))

KITCHEN_STAGES: dict[str, KitchenStage] = {
    "cook": "cooking", "serve": "serving",
    "request_payment": "paying", "choose_payment": "paying", "pay": "paying",
}


def describe(step: str, update: dict, values: dict) -> str | None:
    """A one-line activity entry for a finished graph step, or None for steps not worth showing."""
    status = values["status"]
    said = [m for m in update.get("messages", []) if isinstance(m, BaseMessage)]
    named = next((str(m.content) for m in said if isinstance(m, AIMessage) and m.name), None)
    if step in ("cook", "serve", "pay"):
        return named
    if step == "parse_order" and status == Status.INVALID:
        return "Could not read an order from the message."
    if step == "order_confirm":
        return {Status.CONFIRMED: "Every dish is available.",
                Status.PARTIAL: "Only part of the order is available.",
                Status.NOT_AVAILABLE: "Nothing in the order is available."}.get(status)
    if step == "user_decision":
        return {Status.CONFIRMED: "Guest accepted the available part of the order.",
                Status.CANCELLED: "Guest cancelled the order."}.get(status)
    if step == "reserve_stock":
        return "Order sent to the kitchen." if values["stock_reserved"] else \
            "Stock changed meanwhile; checking the order again."
    if step == "request_payment":
        return f"Bill shown: Rs {values['bill_total']}."
    if step == "finish":
        return values["final_result"]
    return None


# --------------------------------------------------------------------------- app

def create_app(
    llm: OrderLLM | None = None,
    outcome: Outcome | None = None,
    db_path: str | None = None,
    menu: dict[str, int] | None = None,
    prices: dict[str, int] | None = None,
    kitchen_seconds: float | None = None,
    wait_seconds: float | None = None,
) -> FastAPI:
    """`menu` and `prices` seed the menu table the first time a database is created."""
    if llm is None:
        llm = RuleBasedLLM() if os.environ.get("DINEGRAPH_OFFLINE") == "1" else ClaudeLLM()
    if kitchen_seconds is None:
        kitchen_seconds = float(os.environ.get("DINEGRAPH_KITCHEN_SECONDS", "0"))
    if wait_seconds is None:
        wait_seconds = float(os.environ.get("DINEGRAPH_WAIT_SECONDS", "15"))

    path = db_path or os.environ.get("DINEGRAPH_DB", "dinegraph.sqlite")

    def connect() -> sqlite3.Connection:
        conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")  # readers don't block the writer
        return conn

    store = Store(connect(), seed_menu=menu, seed_prices=prices)
    pace = (lambda stage: time.sleep(kitchen_seconds)) if kitchen_seconds > 0 else None
    graph = build_graph(llm, outcome=outcome or random_outcome(), inventory=store,
                        checkpointer=SqliteSaver(connect()), pace=pace)
    admin_token = os.environ.get("DINEGRAPH_ADMIN_TOKEN")
    locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)
    workers: dict[str, threading.Thread] = {}  # session -> background run still going
    errors: dict[str, Exception] = {}          # session -> why its last run stopped

    app = FastAPI(title="DineGraph", description="Restaurant ordering agent built on LangGraph")
    origins = os.environ.get("DINEGRAPH_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    app.add_middleware(CORSMiddleware, allow_origins=origins.split(","),
                       allow_methods=["*"], allow_headers=["*"])

    def config(session_id: str) -> dict:
        return {"configurable": {"thread_id": session_id}, "recursion_limit": RECURSION_LIMIT}

    def snapshot(session_id: str):
        snap = graph.get_state(config(session_id))
        if not snap.values:
            raise HTTPException(404, "Session not found")
        return snap

    def view(session_id: str) -> SessionView:
        snap = snapshot(session_id)
        v = snap.values
        pending = snap.interrupts[0].value if snap.interrupts else None
        messages = []
        for m in v["messages"]:
            role = (m.name or "assistant") if isinstance(m, AIMessage) else "user"
            messages.append(ChatMessage(role=role, content=str(m.content)))
        return SessionView(
            session_id=session_id,
            messages=messages,
            waiting_for=pending["kind"] if pending else None,
            prompt=pending["prompt"] if pending else None,
            done=not snap.next,
            stalled=bool(snap.next) and not pending and not busy(session_id),
            busy=busy(session_id),
            next_step=snap.next[0] if snap.next else None,
            error=error_text(errors[session_id])[1] if session_id in errors else None,
            table=v.get("table"),
            status=v["status"],
            order=[OrderLine(**i) for i in v["order"]],
            counters=Counters(
                order_retries=v["order_retries"], cook_retries=v["cook_retries"],
                serve_retries=v["serve_retries"], payment_retries=v["payment_retries"],
            ),
            bill_total=v["bill_total"],
            payment_method=v["payment_method"],
            final_result=v["final_result"],
        )

    def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
        if admin_token and x_admin_token != admin_token:
            raise HTTPException(401, "Missing or wrong X-Admin-Token header.")

    def busy(session_id: str) -> bool:
        worker = workers.get(session_id)
        return worker is not None and worker.is_alive()

    def error_text(exc: Exception) -> tuple[int, str] | tuple[None, str]:
        if isinstance(exc, anthropic.APIError):
            # the failed step is left pending in the checkpoint; /retry re-runs it
            return 502, f"LLM call failed: {exc.__class__.__name__}. POST /sessions/{{id}}/retry to try again."
        if isinstance(exc, TypeError) and "authentication" in str(exc):
            # the Anthropic SDK raises TypeError when it finds no credentials at all
            return 503, "No Claude credentials found. Set ANTHROPIC_API_KEY, or run the server with DINEGRAPH_OFFLINE=1."
        return None, f"{exc.__class__.__name__}: {exc}"

    def save(session_id: str, step: str | None = None, update: dict | None = None) -> None:
        """Keep the order record in step with the session, and log the step that just ran."""
        snap = graph.get_state(config(session_id))
        if not snap.values:
            return
        store.save_order(session_id, snap.values, snap.next[0] if snap.next else "")
        detail = describe(step, update or {}, snap.values) if step else None
        if detail:
            store.add_event(session_id, step, snap.values["status"], detail)

    def work(session_id: str, graph_input) -> None:
        try:
            # "sync" writes each step's checkpoint before its update is yielded,
            # so save() reads the state as it is after that step
            for chunk in graph.stream(graph_input, config(session_id), stream_mode="updates",
                                      durability="sync"):
                for step, update in chunk.items():
                    if step != "__interrupt__":
                        save(session_id, step, update)
        except Exception as exc:  # reported by run() or, later, by the session view
            errors[session_id] = exc
        finally:
            save(session_id)  # even after a failure
            workers.pop(session_id, None)

    def run(session_id: str, graph_input, wait: float | None = None) -> None:
        """Start the graph in the background and wait up to `wait` seconds (default
        `wait_seconds`) for it to pause.

        Callers hold the session lock and have checked the session is not busy.
        """
        errors.pop(session_id, None)
        worker = threading.Thread(target=work, args=(session_id, graph_input), daemon=True)
        workers[session_id] = worker
        worker.start()
        worker.join(wait_seconds if wait is None else wait)
        exc = errors.get(session_id)
        if exc is not None and not worker.is_alive():
            code, text = error_text(exc)
            if code is None:
                raise exc
            raise HTTPException(code, text.replace("{id}", session_id)) from exc

    def require_idle(session_id: str) -> None:
        if busy(session_id):
            raise HTTPException(409, "Still working on the last message. Poll GET /sessions/{id}.")

    # ------------------------------------------------------------------ routes

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "llm": type(llm).__name__, "kitchen_seconds": kitchen_seconds}

    @app.get("/menu", response_model=MenuView)
    def get_menu() -> MenuView:
        return MenuView(max_dishes=MAX_DISHES, items=[
            MenuItem(dish=i["dish"], available=i["quantity"], price=i["price"])
            for i in store.menu_items()
        ])

    @app.post("/sessions", response_model=SessionView, status_code=201)
    def start_session(body: NewSession | None = None) -> SessionView:
        session_id = uuid.uuid4().hex
        table = body.table if body else None
        with locks[session_id]:
            # a new session only has to reach the first order prompt, so always wait for it
            run(session_id, initial_state(welcome_text(list(store.menu())), table=table), wait=60)
            store.add_event(session_id, "start", Status.NEW,
                            f"Seated at table {table}." if table else "Session started.")
            return view(session_id)

    @app.get("/sessions/{session_id}", response_model=SessionView)
    def get_session(session_id: str) -> SessionView:
        return view(session_id)

    @app.post("/sessions/{session_id}/messages", response_model=SessionView)
    def send_message(session_id: str, body: UserMessage, wait: float | None = WAIT_QUERY) -> SessionView:
        with locks[session_id]:
            snap = snapshot(session_id)
            require_idle(session_id)
            if not snap.next:
                raise HTTPException(409, "This session has finished. Start a new one.")
            if not snap.interrupts:
                raise HTTPException(409, "The last step failed. POST /retry before sending a message.")
            run(session_id, Command(resume=body.text.strip()), wait)
            return view(session_id)

    @app.post("/sessions/{session_id}/retry", response_model=SessionView)
    def retry(session_id: str, wait: float | None = WAIT_QUERY) -> SessionView:
        with locks[session_id]:
            snap = snapshot(session_id)
            require_idle(session_id)
            if not snap.next or snap.interrupts:
                raise HTTPException(409, "Nothing to retry.")
            run(session_id, None, wait)
            return view(session_id)

    # ------------------------------------------------------------------ orders

    @app.get("/orders", response_model=list[OrderRecord])
    def list_orders(
        status: str | None = Query(default=None, description="Filter by status, e.g. PAID or FAILED."),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict]:
        return store.list_orders(status, limit, offset)

    @app.get("/orders/{session_id}", response_model=OrderRecord)
    def get_order(session_id: str) -> dict:
        order = store.get_order(session_id)
        if order is None:
            raise HTTPException(404, "Order not found")
        return order

    @app.get("/orders/{session_id}/events", response_model=list[OrderEvent])
    def order_events(session_id: str) -> list[dict]:
        """What has happened to the order so far, oldest first."""
        if store.get_order(session_id) is None:
            raise HTTPException(404, "Order not found")
        return store.events(session_id)

    # ------------------------------------------------------------------ kitchen

    @app.get("/kitchen", response_model=list[KitchenTicket])
    def kitchen() -> list[KitchenTicket]:
        """Orders the kitchen is cooking, the waiters are serving, or that wait for payment."""
        return [
            KitchenTicket(**{k: o[k] for k in KitchenTicket.model_fields if k != "stage"},
                          stage=KITCHEN_STAGES[o["stage"]])
            for o in store.active_orders() if o["stage"] in KITCHEN_STAGES
        ]

    # ------------------------------------------------------------------ admin

    admin = [Depends(require_admin)]

    @app.put("/admin/menu/{dish}", response_model=MenuItem, dependencies=admin)
    def upsert_dish(dish: str, body: MenuUpdate) -> MenuItem:
        """Add a dish (needs quantity and price) or change its stock and/or price."""
        try:
            item = store.upsert_item(dish.strip(), body.quantity, body.price)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return MenuItem(dish=item["dish"], available=item["quantity"], price=item["price"])

    @app.delete("/admin/menu/{dish}", status_code=204, dependencies=admin)
    def delete_dish(dish: str) -> None:
        if not store.delete_item(dish):
            raise HTTPException(404, "Dish not found")

    @app.get("/admin/stats", response_model=Stats, dependencies=admin)
    def stats() -> dict:
        return store.stats()

    return app


def __getattr__(name: str):
    # build the app lazily so importing this module (e.g. in tests) needs no API key
    if name == "app":
        global app
        app = create_app()
        return app
    raise AttributeError(name)
