r"""The DineGraph LangGraph.

    START -> take_order -> parse_order -> order_confirm -> review_order
                                 \__________________________/   |
                                 (invalid input skips confirm)   |
    review_order --CONFIRMED--> cook
    review_order --PARTIAL / NOT_AVAILABLE / INVALID--> user_decision or take_order or finish
    user_decision --accept--> cook | --new order--> parse_order / take_order | --cancel--> finish
    cook --READY--> serve | --failed, retries left--> cook | --no retries--> finish
    serve --COMPLETE--> request_payment | --failed, serve+cook retries left--> cook | --otherwise--> finish
    request_payment -> choose_payment -> pay (unclear reply asks again)
    pay --PAID--> finish | --failed, retries left--> choose_payment | --no retries--> finish
    finish -> END

Routing is done in code from the state (status + retry counters), so it is
deterministic. The LLM reads the same state facts to phrase every customer
message, including the final completion message or apology.
"""

from __future__ import annotations

import random
from typing import Callable

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .llm import OrderLLM
from .menu import MENU, PRICES, lookup
from .state import MAX_DISHES, DineState, OrderItem, Status

FAILURE_CHANCE = 0.4  # cook, serve and card/UPI payments fail 40% of the time

# stage ("cook", "serve" or "pay") -> True if that attempt succeeded
Outcome = Callable[[str], bool]


def random_outcome(seed: int | None = None, failure_chance: float = FAILURE_CHANCE) -> Outcome:
    """The probability function: 40% failure, 60% success."""
    rng = random.Random(seed)
    return lambda stage: rng.random() >= failure_chance


def _last_user_text(state: DineState) -> str:
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return str(msg.content)
    return ""


def _order_facts(order: list[OrderItem]) -> list[dict]:
    return [
        {"dish": i["dish"], "requested": i["required_quantity"], "available": i["available_quantity"]}
        for i in order
    ]


def build_bill(order: list[OrderItem], prices: dict[str, int]) -> tuple[list[dict], int]:
    lines = [
        {"dish": i["dish"], "quantity": i["required_quantity"],
         "amount": i["required_quantity"] * prices.get(i["dish"], 0)}
        for i in order
    ]
    return lines, sum(line["amount"] for line in lines)


def build_graph(
    llm: OrderLLM,
    outcome: Outcome | None = None,
    menu: dict[str, int] | None = None,
    prices: dict[str, int] | None = None,
    checkpointer=None,
):
    menu = MENU if menu is None else menu
    prices = PRICES if prices is None else prices
    outcome = outcome or random_outcome()

    # ------------------------------------------------------------------ nodes

    def take_order(state: DineState) -> dict:
        text = interrupt({"prompt": "Your order"})
        return {"messages": [HumanMessage(content=text)]}

    def parse_order(state: DineState) -> dict:
        parsed = llm.parse_order(_last_user_text(state), list(menu))
        if not parsed.is_food_order or not parsed.items:
            return {"status": Status.INVALID, "order": [], "final_result": "not_food_order"}
        if len(parsed.items) > MAX_DISHES:
            return {"status": Status.INVALID, "order": [], "final_result": "too_many_dishes"}
        if any(i.quantity <= 0 for i in parsed.items):
            return {"status": Status.INVALID, "order": [], "final_result": "invalid_quantity"}
        order = [
            OrderItem(dish=i.dish, required_quantity=i.quantity, available_quantity=0)
            for i in parsed.items
        ]
        return {"status": Status.PLACED, "order": order, "final_result": ""}

    def order_confirm(state: DineState) -> dict:
        order = []
        for item in state["order"]:
            name, available = lookup(item["dish"], menu)
            order.append(OrderItem(
                dish=name,
                required_quantity=item["required_quantity"],
                available_quantity=available,
            ))
        if all(i["available_quantity"] >= i["required_quantity"] for i in order):
            status = Status.CONFIRMED
        elif all(i["available_quantity"] == 0 for i in order):
            status = Status.NOT_AVAILABLE
        else:
            status = Status.PARTIAL
        return {"order": order, "status": status}

    def review_order(state: DineState) -> dict:
        """The LLM reads the status written by order_confirm and talks to the user."""
        status = state["status"]
        if status == Status.CONFIRMED:
            text = llm.compose("order_confirmed", {"order": _order_facts(state["order"])})
            return {"messages": [AIMessage(content=text)]}

        # every unsuccessful attempt uses up one order retry
        retries = state["order_retries"] - 1
        facts: dict = {"attempts_left": retries}
        if status == Status.INVALID:
            situation = state["final_result"]  # reason stored by parse_order
            facts["max_dishes"] = MAX_DISHES
        else:
            situation = "partial_available" if status == Status.PARTIAL else "nothing_available"
            facts["order"] = _order_facts(state["order"])
        update: dict = {"order_retries": retries, "final_result": ""}
        # when attempts are gone and nothing can be salvaged, finish() speaks instead
        if retries > 0 or status == Status.PARTIAL:
            update["messages"] = [AIMessage(content=llm.compose(situation, facts))]
        return update

    def user_decision(state: DineState) -> dict:
        text = interrupt({"prompt": "Your choice"})
        partial_allowed = state["status"] == Status.PARTIAL
        decision = llm.classify_decision(text, partial_allowed)
        update: dict = {"messages": [HumanMessage(content=text)]}

        if decision.action == "accept_partial" and partial_allowed:
            order = [
                OrderItem(
                    dish=i["dish"],
                    required_quantity=min(i["required_quantity"], i["available_quantity"]),
                    available_quantity=i["available_quantity"],
                )
                for i in state["order"] if i["available_quantity"] > 0
            ]
            text = llm.compose("partial_accepted", {"order": _order_facts(order)})
            update.update(order=order, status=Status.CONFIRMED)
            update["messages"].append(AIMessage(content=text))
        elif decision.action == "new_order" and state["order_retries"] > 0:
            update["status"] = Status.PLACED if decision.has_order_details else Status.NEW
        elif decision.action in ("cancel", "new_order"):
            # a new order with no attempts left ends the session
            reason = "cancelled_by_user" if decision.action == "cancel" else "order_attempts_exhausted"
            update.update(status=Status.CANCELLED, final_result=reason)
        else:
            text = llm.compose("decision_unclear", {
                "can_accept_partial": partial_allowed,
                "can_place_new_order": state["order_retries"] > 0,
            })
            update["messages"].append(AIMessage(content=text))
        return update

    def cook(state: DineState) -> dict:
        if outcome("cook"):
            return {"status": Status.READY,
                    "messages": [AIMessage(content="Kitchen: your food is cooked and ready.", name="kitchen")]}
        left = state["cook_retries"] - 1
        note = "retrying" if left > 0 else "no cook attempts left"
        return {"status": Status.COOK_FAILED, "cook_retries": left,
                "messages": [AIMessage(content=f"Kitchen: cooking failed ({note}).", name="kitchen")]}

    def serve(state: DineState) -> dict:
        if outcome("serve"):
            return {"status": Status.COMPLETE,
                    "messages": [AIMessage(content="Waiter: your food has been served.", name="waiter")]}
        left = state["serve_retries"] - 1
        return {"status": Status.SERVE_FAILED, "serve_retries": left,
                "messages": [AIMessage(content="Waiter: serving failed, the dish could not be served.", name="waiter")]}

    def request_payment(state: DineState) -> dict:
        """The LLM shows the bill and asks how the user wants to pay."""
        lines, total = build_bill(state["order"], prices)
        text = llm.compose("bill", {"bill": lines, "total": total, "methods": ["cash", "card", "upi"]})
        return {"status": Status.PAYMENT_PENDING, "bill_total": total,
                "messages": [AIMessage(content=text)]}

    def choose_payment(state: DineState) -> dict:
        text = interrupt({"prompt": "Payment method"})
        choice = llm.classify_payment(text)
        update: dict = {"messages": [HumanMessage(content=text)]}
        if choice.method == "unclear":
            update["payment_method"] = ""
            update["messages"].append(AIMessage(content=llm.compose("payment_unclear", {})))
        else:
            update["payment_method"] = choice.method
        return update

    def pay(state: DineState) -> dict:
        method = state["payment_method"]
        # cash is handed over in person and always succeeds; card and UPI can fail
        if method == "cash" or outcome("pay"):
            return {"status": Status.PAID,
                    "messages": [AIMessage(content=f"Cashier: {method} payment received.", name="cashier")]}
        left = state["payment_retries"] - 1
        update: dict = {"status": Status.PAYMENT_FAILED, "payment_retries": left, "payment_method": "",
                        "messages": [AIMessage(content=f"Cashier: {method} payment failed.", name="cashier")]}
        if left > 0:
            text = llm.compose("payment_failed_retry", {
                "method": method, "payment_attempts_left": left, "total": state["bill_total"],
                "methods": ["cash", "card", "upi"],
            })
            update["messages"].append(AIMessage(content=text))
        return update

    def finish(state: DineState) -> dict:
        """The LLM reads the final state and writes the completion message or an apology."""
        status = state["status"]
        facts = {
            "order": _order_facts(state["order"]),
            "order_retries_left": state["order_retries"],
            "cook_retries_left": state["cook_retries"],
            "serve_retries_left": state["serve_retries"],
            "total": state["bill_total"],
            "method": state["payment_method"],
        }
        if status == Status.PAID:
            text = llm.compose("order_complete", facts)
            return {"final_result": "COMPLETED", "messages": [AIMessage(content=text)]}
        if status == Status.PAYMENT_FAILED:
            facts["reason"] = "payment_attempts_exhausted"
            text = llm.compose("payment_exhausted", facts)
            return {"status": Status.FAILED, "final_result": "NOT_COMPLETED: payment_attempts_exhausted",
                    "messages": [AIMessage(content=text)]}

        if status == Status.CANCELLED:
            reason = state["final_result"] or "cancelled_by_user"
        elif status == Status.COOK_FAILED:
            reason = "cook_attempts_exhausted"
        elif status == Status.SERVE_FAILED:
            reason = "serve_attempts_exhausted" if state["serve_retries"] == 0 else "cook_attempts_exhausted"
        else:
            reason = "order_attempts_exhausted"
        facts["reason"] = reason
        situation = "goodbye_cancelled" if reason == "cancelled_by_user" else "apology"
        text = llm.compose(situation, facts)
        final_status = Status.CANCELLED if reason == "cancelled_by_user" else Status.FAILED
        return {"status": final_status, "final_result": f"NOT_COMPLETED: {reason}",
                "messages": [AIMessage(content=text)]}

    # ------------------------------------------------------------------ routing

    def after_parse(state: DineState) -> str:
        return "order_confirm" if state["status"] == Status.PLACED else "review_order"

    def after_review(state: DineState) -> str:
        status = state["status"]
        if status == Status.CONFIRMED:
            return "cook"
        if status == Status.PARTIAL:
            return "user_decision"  # accept / new order / cancel (new order only if attempts remain)
        if state["order_retries"] > 0:
            return "take_order"
        return "finish"

    def after_decision(state: DineState) -> str:
        status = state["status"]
        if status == Status.CONFIRMED:
            return "cook"
        if status == Status.PLACED:
            return "parse_order"  # the reply already contains the new order
        if status == Status.NEW:
            return "take_order"
        if status == Status.CANCELLED:
            return "finish"
        return "user_decision"  # unclear reply, ask again

    def after_cook(state: DineState) -> str:
        if state["status"] == Status.READY:
            return "serve"
        return "cook" if state["cook_retries"] > 0 else "finish"

    def after_serve(state: DineState) -> str:
        if state["status"] == Status.COMPLETE:
            return "request_payment"
        if state["serve_retries"] > 0 and state["cook_retries"] > 0:
            return "cook"  # a failed serve means the dish has to be cooked again
        return "finish"

    def after_choose_payment(state: DineState) -> str:
        return "pay" if state["payment_method"] else "choose_payment"

    def after_pay(state: DineState) -> str:
        if state["status"] == Status.PAID:
            return "finish"
        return "choose_payment" if state["payment_retries"] > 0 else "finish"

    # ------------------------------------------------------------------ wiring

    g = StateGraph(DineState)
    for name, fn in [
        ("take_order", take_order), ("parse_order", parse_order),
        ("order_confirm", order_confirm), ("review_order", review_order),
        ("user_decision", user_decision), ("cook", cook), ("serve", serve),
        ("request_payment", request_payment), ("choose_payment", choose_payment), ("pay", pay),
        ("finish", finish),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "take_order")
    g.add_edge("take_order", "parse_order")
    g.add_conditional_edges("parse_order", after_parse, ["order_confirm", "review_order"])
    g.add_edge("order_confirm", "review_order")
    g.add_conditional_edges("review_order", after_review, ["cook", "user_decision", "take_order", "finish"])
    g.add_conditional_edges("user_decision", after_decision,
                            ["cook", "parse_order", "take_order", "finish", "user_decision"])
    g.add_conditional_edges("cook", after_cook, ["serve", "cook", "finish"])
    g.add_conditional_edges("serve", after_serve, ["request_payment", "cook", "finish"])
    g.add_edge("request_payment", "choose_payment")
    g.add_conditional_edges("choose_payment", after_choose_payment, ["pay", "choose_payment"])
    g.add_conditional_edges("pay", after_pay, ["finish", "choose_payment"])
    g.add_edge("finish", END)

    return g.compile(checkpointer=checkpointer or InMemorySaver())
