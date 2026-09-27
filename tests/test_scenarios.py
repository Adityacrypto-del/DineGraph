"""Scenario tests for DineGraph.

They use the rule-based LLM and scripted cook/serve outcomes, so they are
deterministic and need no API key.
"""

import uuid

import pytest
from langgraph.types import Command

from dinegraph.graph import build_graph
from dinegraph.llm import RuleBasedLLM
from dinegraph.state import Status, initial_state

MENU = {"Veg Biryani": 10, "Cold Coffee": 2, "Masala Dosa": 6, "Pasta Alfredo": 0}
PRICES = {"Veg Biryani": 220, "Cold Coffee": 150, "Masala Dosa": 120, "Pasta Alfredo": 300}
SERVED = [("cook", True), ("serve", True)]


def run(inputs, outcomes=()):
    """Drive the graph with scripted user inputs and cook/serve results.

    outcomes is a list of (stage, success) pairs, consumed in order. The test
    fails if the graph asks for a stage out of order or for more than scripted.
    """
    script = list(outcomes)

    def outcome(stage):
        assert script, f"unexpected extra {stage} attempt"
        expected, ok = script.pop(0)
        assert stage == expected, f"expected {expected}, graph ran {stage}"
        return ok

    graph = build_graph(RuleBasedLLM(), outcome=outcome, menu=MENU, prices=PRICES)
    config = {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": 100}
    graph.invoke(initial_state("welcome"), config)
    for text in inputs:
        assert graph.get_state(config).next, f"graph ended before input {text!r}"
        graph.invoke(Command(resume=text), config)
    state = graph.get_state(config)
    assert not state.next, "graph is still waiting for input"
    assert not script, f"unused outcomes: {script}"
    return state.values


def texts(state):
    return " ".join(str(m.content) for m in state["messages"])


# --------------------------------------------------------------------- happy path

def test_full_order_cooked_and_served_first_time():
    s = run(["2 Veg Biryani, 1 Cold Coffee", "cash"], [("cook", True), ("serve", True)])
    assert s["final_result"] == "COMPLETED"
    assert s["order"][0] == {"dish": "Veg Biryani", "required_quantity": 2, "available_quantity": 10}
    assert (s["order_retries"], s["cook_retries"], s["serve_retries"]) == (3, 2, 2)
    assert s["status"] == Status.PAID
    assert s["bill_total"] == 2 * 220 + 150
    assert "order is complete" in texts(s)


# --------------------------------------------------------------------- order stage

def test_unrelated_input_is_not_processed_and_uses_an_attempt():
    s = run(["what's the weather today?", "1 Masala Dosa", "cash"], [("cook", True), ("serve", True)])
    assert s["final_result"] == "COMPLETED"
    assert s["order_retries"] == 2
    assert "only help with food orders" in texts(s)


def test_more_than_three_dishes_is_rejected():
    s = run(["1 Veg Biryani, 1 Cold Coffee, 1 Masala Dosa, 1 Pasta Alfredo", "1 Veg Biryani", "cash"],
            [("cook", True), ("serve", True)])
    assert s["order_retries"] == 2
    assert "at most 3" in texts(s)


def test_dish_not_on_menu_gets_zero_available():
    graph = build_graph(RuleBasedLLM(), outcome=lambda stage: True, menu=MENU)
    config = {"configurable": {"thread_id": "t"}, "recursion_limit": 100}
    graph.invoke(initial_state("welcome"), config)
    graph.invoke(Command(resume="2 Sushi"), config)
    s = graph.get_state(config)
    assert s.next == ("take_order",)  # asked to order again
    assert s.values["status"] == Status.NOT_AVAILABLE
    assert s.values["order"] == [{"dish": "Sushi", "required_quantity": 2, "available_quantity": 0}]
    assert s.values["order_retries"] == 2


def test_nothing_available_three_times_ends_with_apology():
    s = run(["2 Sushi", "1 Pasta Alfredo", "3 Tacos"])
    assert s["status"] == Status.FAILED
    assert s["order_retries"] == 0
    assert s["final_result"] == "NOT_COMPLETED: order_attempts_exhausted"
    assert s["order"][0]["available_quantity"] == 0
    assert "very sorry" in texts(s)


def test_partial_order_accepted():
    s = run(["5 Cold Coffee, 1 Veg Biryani", "yes, go ahead", "cash"], [("cook", True), ("serve", True)])
    assert s["final_result"] == "COMPLETED"
    coffee = next(i for i in s["order"] if i["dish"] == "Cold Coffee")
    assert coffee["required_quantity"] == 2  # trimmed to what was available
    assert s["order_retries"] == 2


def test_partial_order_drops_missing_dishes_when_accepted():
    s = run(["1 Sushi, 1 Veg Biryani", "confirm", "cash"], [("cook", True), ("serve", True)])
    assert [i["dish"] for i in s["order"]] == ["Veg Biryani"]


def test_partial_order_replaced_with_new_order_in_same_reply():
    s = run(["5 Cold Coffee", "2 Masala Dosa", "cash"], [("cook", True), ("serve", True)])
    assert s["final_result"] == "COMPLETED"
    assert s["order"] == [{"dish": "Masala Dosa", "required_quantity": 2, "available_quantity": 6}]


def test_partial_order_new_order_without_details_asks_again():
    s = run(["5 Cold Coffee", "I want something else", "1 Veg Biryani", "cash"],
            [("cook", True), ("serve", True)])
    assert s["final_result"] == "COMPLETED"


def test_partial_order_cancelled():
    s = run(["5 Cold Coffee", "cancel please"])
    assert s["status"] == Status.CANCELLED
    assert s["final_result"] == "NOT_COMPLETED: cancelled_by_user"


def test_partial_on_last_attempt_can_still_be_accepted():
    s = run(["9 Tacos", "9 Tacos", "5 Cold Coffee", "ok", "cash"], [("cook", True), ("serve", True)])
    assert s["order_retries"] == 0
    assert s["final_result"] == "COMPLETED"


def test_partial_on_last_attempt_cannot_reorder():
    s = run(["9 Tacos", "9 Tacos", "5 Cold Coffee", "1 Veg Biryani"])
    assert s["final_result"] == "NOT_COMPLETED: order_attempts_exhausted"


def test_unclear_decision_asks_again():
    s = run(["5 Cold Coffee", "hmm", "yes", "cash"], [("cook", True), ("serve", True)])
    assert s["final_result"] == "COMPLETED"
    assert "didn't get that" in texts(s)


# --------------------------------------------------------------------- cook stage

def test_cook_fails_once_then_succeeds():
    s = run(["1 Veg Biryani", "cash"], [("cook", False), ("cook", True), ("serve", True)])
    assert s["final_result"] == "COMPLETED"
    assert s["cook_retries"] == 1


def test_cook_fails_twice_apology():
    s = run(["1 Veg Biryani"], [("cook", False), ("cook", False)])
    assert s["status"] == Status.FAILED
    assert s["cook_retries"] == 0
    assert s["final_result"] == "NOT_COMPLETED: cook_attempts_exhausted"


# --------------------------------------------------------------------- serve stage

def test_serve_fails_once_recook_and_serve():
    s = run(["1 Veg Biryani", "cash"], [("cook", True), ("serve", False), ("cook", True), ("serve", True)])
    assert s["final_result"] == "COMPLETED"
    assert (s["cook_retries"], s["serve_retries"]) == (2, 1)


def test_serve_fails_twice_apology():
    s = run(["1 Veg Biryani"], [("cook", True), ("serve", False), ("cook", True), ("serve", False)])
    assert s["serve_retries"] == 0
    assert s["final_result"] == "NOT_COMPLETED: serve_attempts_exhausted"


def test_serve_fail_recook_uses_last_cook_retry_and_fails():
    # first cook fails (1 cook retry left), second succeeds, serve fails,
    # re-cook is allowed but fails, leaving 0 cook retries -> apology
    s = run(["1 Veg Biryani"],
            [("cook", False), ("cook", True), ("serve", False), ("cook", False)])
    assert (s["cook_retries"], s["serve_retries"]) == (0, 1)
    assert s["final_result"] == "NOT_COMPLETED: cook_attempts_exhausted"


def test_serve_fails_then_recook_fails_twice():
    s = run(["1 Veg Biryani"],
            [("cook", True), ("serve", False), ("cook", False), ("cook", False)])
    assert s["final_result"] == "NOT_COMPLETED: cook_attempts_exhausted"


# --------------------------------------------------------------------- payment stage

def test_bill_is_shown_after_serving():
    s = run(["2 Masala Dosa", "cash"], SERVED)
    assert s["bill_total"] == 240
    assert "Total Rs 240" in texts(s)


def test_cash_always_succeeds_without_a_chance_roll():
    s = run(["1 Veg Biryani", "I'll pay cash"], SERVED)  # no ("pay", ...) outcome scripted
    assert (s["status"], s["payment_method"], s["payment_retries"]) == (Status.PAID, "cash", 2)
    assert s["final_result"] == "COMPLETED"


def test_card_payment_succeeds():
    s = run(["1 Veg Biryani", "card please"], SERVED + [("pay", True)])
    assert s["payment_method"] == "card"
    assert s["final_result"] == "COMPLETED"


def test_upi_fails_then_cash_succeeds():
    s = run(["1 Veg Biryani", "GPay", "cash then"], SERVED + [("pay", False)])
    assert s["payment_retries"] == 1
    assert s["payment_method"] == "cash"
    assert s["final_result"] == "COMPLETED"
    assert "payment failed" in texts(s)


def test_card_fails_twice_ends_unpaid():
    s = run(["1 Veg Biryani", "card", "upi"], SERVED + [("pay", False), ("pay", False)])
    assert s["payment_retries"] == 0
    assert s["status"] == Status.FAILED
    assert s["final_result"] == "NOT_COMPLETED: payment_attempts_exhausted"
    assert "settle the bill at the counter" in texts(s)


def test_unclear_payment_reply_asks_again_without_using_an_attempt():
    s = run(["1 Veg Biryani", "bitcoin?", "upi"], SERVED + [("pay", True)])
    assert s["payment_retries"] == 2
    assert "choose cash, card or UPI" in texts(s)


def test_partial_order_is_billed_for_what_was_served():
    s = run(["5 Cold Coffee", "confirm", "cash"], SERVED)
    assert s["bill_total"] == 2 * 150


def test_random_outcome_is_about_forty_percent_failure():
    from dinegraph.graph import random_outcome
    roll = random_outcome(seed=7)
    failures = sum(not roll("cook") for _ in range(10_000))
    assert 3700 < failures < 4300


# --------------------------------------------------------------------- stock

from dinegraph.inventory import InMemoryInventory


def run_with(inventory, inputs, outcomes):
    script = list(outcomes)
    graph = build_graph(RuleBasedLLM(), outcome=lambda stage: script.pop(0)[1], inventory=inventory)
    config = {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": 100}
    graph.invoke(initial_state("welcome"), config)
    for text in inputs:
        graph.invoke(Command(resume=text), config)
    return graph, config


def test_served_order_uses_up_stock():
    inv = InMemoryInventory(MENU, PRICES)
    run_with(inv, ["3 Masala Dosa", "cash"], SERVED)
    assert inv.menu()["Masala Dosa"] == 3
    assert MENU["Masala Dosa"] == 6  # the caller's dict is not changed


def test_kitchen_failure_puts_stock_back():
    inv = InMemoryInventory(MENU, PRICES)
    graph, config = run_with(inv, ["3 Masala Dosa"], [("cook", False), ("cook", False)])
    assert inv.menu()["Masala Dosa"] == 6
    assert graph.get_state(config).values["stock_reserved"] is False


def test_failed_payment_keeps_stock_used():
    inv = InMemoryInventory(MENU, PRICES)
    run_with(inv, ["1 Veg Biryani", "card", "card"], SERVED + [("pay", False), ("pay", False)])
    assert inv.menu()["Veg Biryani"] == 9  # the food was served


def test_second_customer_sees_reduced_stock():
    inv = InMemoryInventory(MENU, PRICES)
    run_with(inv, ["2 Cold Coffee", "cash"], SERVED)
    graph, config = run_with(inv, ["1 Cold Coffee"], [])
    s = graph.get_state(config).values
    assert s["status"] == Status.NOT_AVAILABLE


def test_stock_sold_out_while_customer_decides_rechecks_order():
    inv = InMemoryInventory(MENU, PRICES)
    script = list(SERVED)
    graph = build_graph(RuleBasedLLM(), outcome=lambda stage: script.pop(0)[1], inventory=inv)
    config = {"configurable": {"thread_id": "a"}, "recursion_limit": 100}
    graph.invoke(initial_state("welcome"), config)
    graph.invoke(Command(resume="5 Cold Coffee, 1 Veg Biryani"), config)  # partial, waiting
    assert inv.reserve({"Cold Coffee": 2})  # another customer takes the last coffees
    graph.invoke(Command(resume="confirm"), config)
    s = graph.get_state(config)
    assert "just sold out" in texts(s.values)
    # the recheck finds coffee gone, so it is partial again and the customer is asked again
    assert s.values["status"] == Status.PARTIAL
    graph.invoke(Command(resume="confirm"), config)
    graph.invoke(Command(resume="cash"), config)
    s = graph.get_state(config).values
    assert s["final_result"] == "COMPLETED"
    assert [i["dish"] for i in s["order"]] == ["Veg Biryani"]
    assert inv.menu() == {**MENU, "Cold Coffee": 0, "Veg Biryani": 9}


def test_offline_parser_reads_notes_and_number_words():
    from dinegraph.llm import RuleBasedLLM
    parsed = RuleBasedLLM().parse_order(
        "two masala dosa (extra spicy) and a cold coffee", ["Masala Dosa", "Cold Coffee"])
    assert [(i.dish, i.quantity, i.note) for i in parsed.items] == [
        ("Masala Dosa", 2, "extra spicy"), ("Cold Coffee", 1, "")]
