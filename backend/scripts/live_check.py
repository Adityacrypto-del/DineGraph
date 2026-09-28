"""Live check of DineGraph against a real LLM: Gemini (default) or Claude.

Run it once you have a key, set in your shell or in backend/.env:

    python scripts/live_check.py            # DINEGRAPH_LLM, default gemini (GEMINI_API_KEY)
    python scripts/live_check.py claude     # Claude (ANTHROPIC_API_KEY)

It sends about 15 short requests (free on Gemini's free tier, a few cents on
Claude), prints one line per check, and exits with status 1 if any fail.
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.types import Command  # noqa: E402

from dinegraph.graph import build_graph  # noqa: E402
from dinegraph.llm import RuleBasedLLM, make_llm  # noqa: E402
from dinegraph.main import load_env  # noqa: E402
from dinegraph.menu import MENU, PRICES  # noqa: E402
from dinegraph.state import initial_state  # noqa: E402

MENU_NAMES = list(MENU)


def items(parsed):
    return {i.dish: i.quantity for i in parsed.items}


CHECKS = [
    ("order: plain list", lambda llm: llm.parse_order("2 veg biryani and a cold coffee", MENU_NAMES),
     lambda r: r.is_food_order and items(r) == {"Veg Biryani": 2, "Cold Coffee": 1}),
    ("order: casual wording", lambda llm: llm.parse_order("can I get three margherita pizzas pls", MENU_NAMES),
     lambda r: r.is_food_order and items(r) == {"Margherita Pizza": 3}),
    ("order: no quantity means 1", lambda llm: llm.parse_order("gulab jamun", MENU_NAMES),
     lambda r: r.is_food_order and items(r) == {"Gulab Jamun": 1}),
    ("order: dish not on menu is kept", lambda llm: llm.parse_order("2 sushi rolls", MENU_NAMES),
     lambda r: r.is_food_order and len(r.items) == 1 and r.items[0].quantity == 2),
    ("order: unrelated text rejected", lambda llm: llm.parse_order("what's the weather in Mumbai?", MENU_NAMES),
     lambda r: not r.is_food_order and not r.items),
    ("decision: accept", lambda llm: llm.classify_decision("ok fine, go ahead with what you have", True),
     lambda r: r.action == "accept_partial"),
    ("decision: cancel", lambda llm: llm.classify_decision("forget it, I'm leaving", True),
     lambda r: r.action == "cancel"),
    ("decision: new order with dishes", lambda llm: llm.classify_decision("instead give me 2 masala dosas", True),
     lambda r: r.action == "new_order" and r.has_order_details),
    ("payment: GPay is UPI", lambda llm: llm.classify_payment("I'll pay with gpay"),
     lambda r: r.method == "upi"),
    ("payment: debit card", lambda llm: llm.classify_payment("debit card"),
     lambda r: r.method == "card"),
    ("payment: nonsense is unclear", lambda llm: llm.classify_payment("banana"),
     lambda r: r.method == "unclear"),
    ("compose: bill message", lambda llm: llm.compose("bill", {"lines": ["2 x Veg Biryani = Rs 440"], "total": 440}),
     lambda r: isinstance(r, str) and "440" in r and len(r) < 600),
]


def full_order(llm) -> tuple[bool, str]:
    graph = build_graph(llm, outcome=lambda stage: True, menu=dict(MENU), prices=dict(PRICES),
                        checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "live"}, "recursion_limit": 100}
    graph.invoke(initial_state("Welcome to DineGraph."), cfg)
    graph.invoke(Command(resume="two masala dosas and one cold coffee please"), cfg)
    state = graph.invoke(Command(resume="card"), cfg)
    ok = state["status"] == "PAID" and state["bill_total"] == 2 * PRICES["Masala Dosa"] + PRICES["Cold Coffee"]
    return ok, f"status {state['status']}, bill Rs {state['bill_total']}, result {state['final_result']}"


def main() -> int:
    load_env()
    llm = make_llm(sys.argv[1] if len(sys.argv) > 1 else None)
    if isinstance(llm, RuleBasedLLM):
        print("DINEGRAPH_LLM is offline. Run with gemini or claude to check a real model.")
        return 2
    keys = ("GEMINI_API_KEY", "GOOGLE_API_KEY") if type(llm).__name__ == "GeminiLLM" else ("ANTHROPIC_API_KEY",)
    if not any(os.environ.get(k) for k in keys):
        print(f"{keys[0]} is not set. Export it or add it to backend/.env, then run this again.")
        return 2
    print(f"{type(llm).__name__}, model {llm.model}\n")
    failures = 0
    for name, call, check in CHECKS:
        start = time.perf_counter()
        try:
            result = call(llm)
            ok = check(result)
            shown = result if isinstance(result, str) else result.model_dump()
        except Exception as exc:  # show API errors per check instead of stopping
            ok, shown = False, f"{type(exc).__name__}: {exc}"
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:34} {time.perf_counter() - start:5.1f}s  {str(shown)[:110]}")

    start = time.perf_counter()
    try:
        ok, detail = full_order(llm)
    except Exception as exc:
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {'full order through the graph':34} {time.perf_counter() - start:5.1f}s  {detail}")

    total = len(CHECKS) + 1
    print(f"\n{total - failures} of {total} checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
