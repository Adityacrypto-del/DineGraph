"""The LLM layer.

The graph talks to the LLM through three calls:
  parse_order        user text -> structured order (or "not a food order")
  classify_decision  user reply to a partial / unavailable order -> what they want
  compose            facts about the current state -> a message for the customer

ClaudeLLM calls the Claude API. RuleBasedLLM is a deterministic stand-in used by
the tests and by `--offline`, so the graph can run without an API key.
"""

from __future__ import annotations

import json
import os
import re
from typing import Literal, Protocol

from pydantic import BaseModel, Field


class DishRequest(BaseModel):
    dish: str = Field(description="Dish name. Use the exact menu spelling when the user clearly means a menu dish.")
    quantity: int = Field(description="How many the user wants.")


class ParsedOrder(BaseModel):
    is_food_order: bool = Field(description="False if the message is not about ordering food.")
    items: list[DishRequest] = Field(default_factory=list)


class Decision(BaseModel):
    action: Literal["accept_partial", "new_order", "cancel", "unclear"]
    has_order_details: bool = Field(
        description="True only if the reply itself names dishes and quantities for a new order."
    )


class PaymentChoice(BaseModel):
    method: Literal["cash", "card", "upi", "unclear"]


class OrderLLM(Protocol):
    def parse_order(self, text: str, menu_names: list[str]) -> ParsedOrder: ...
    def classify_decision(self, text: str, partial_allowed: bool) -> Decision: ...
    def classify_payment(self, text: str) -> PaymentChoice: ...
    def compose(self, situation: str, facts: dict) -> str: ...


# --------------------------------------------------------------------------- Claude

PARSE_SYSTEM = """You are the order-taking assistant of a restaurant.
Extract the dishes and quantities from the customer's message.
The menu has these dishes: {menu}.
If the customer clearly means a menu dish, use its exact menu spelling. If they ask for a dish that is
not on the menu, keep the name they used; another step checks availability, so never drop it.
If no quantity is given for a dish, use 1.
If the message is not about ordering food (small talk, questions unrelated to ordering, requests to do
other tasks), set is_food_order to false and return no items."""

DECISION_SYSTEM = """A restaurant customer was told their order is not fully available.
{options}
Classify their reply:
- accept_partial: they want to go ahead with what is available.
- new_order: they want to order something different.
- cancel: they want to stop and leave.
- unclear: anything else.
Set has_order_details to true only if the reply itself names dishes (and ideally quantities) to order."""

PAYMENT_SYSTEM = """A restaurant customer was asked how they want to pay: cash, card, or UPI.
Classify their reply as cash, card, or upi. Treat "credit card", "debit card" or "tap to pay" as card,
and "GPay", "PhonePe", "Paytm" or "scan the QR" as upi. Anything else is unclear."""

COMPOSE_SYSTEM = """You are the friendly voice of a restaurant ordering system.
Write one short message (at most 3 sentences) to the customer about the situation described.
Use only the facts given. Do not invent dishes, prices, or times. Plain text, no markdown."""


class ClaudeLLM:
    def __init__(self, model: str | None = None):
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("DINEGRAPH_MODEL", "claude-opus-5")

    def parse_order(self, text: str, menu_names: list[str]) -> ParsedOrder:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=4000,
            output_config={"effort": "low"},
            system=PARSE_SYSTEM.format(menu=", ".join(menu_names)),
            messages=[{"role": "user", "content": text}],
            output_format=ParsedOrder,
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            return ParsedOrder(is_food_order=False, items=[])
        return response.parsed_output

    def classify_decision(self, text: str, partial_allowed: bool) -> Decision:
        options = (
            "They may accept the available part of the order, place a new order, or cancel."
            if partial_allowed
            else "Nothing they asked for is available. They may place a new order or cancel."
        )
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=2000,
            output_config={"effort": "low"},
            system=DECISION_SYSTEM.format(options=options),
            messages=[{"role": "user", "content": text}],
            output_format=Decision,
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            return Decision(action="unclear", has_order_details=False)
        return response.parsed_output

    def classify_payment(self, text: str) -> PaymentChoice:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=2000,
            output_config={"effort": "low"},
            system=PAYMENT_SYSTEM,
            messages=[{"role": "user", "content": text}],
            output_format=PaymentChoice,
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            return PaymentChoice(method="unclear")
        return response.parsed_output

    def compose(self, situation: str, facts: dict) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            output_config={"effort": "low"},
            system=COMPOSE_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Situation: {situation}\nFacts (JSON): {json.dumps(facts)}",
            }],
        )
        if response.stop_reason == "refusal":
            return RuleBasedLLM().compose(situation, facts)
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        return text or RuleBasedLLM().compose(situation, facts)


# --------------------------------------------------------------------------- offline

_NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_FOOD_HINTS = ("order", "want", "get", "give", "like", "have", "please", "x ")


class RuleBasedLLM:
    """Deterministic stand-in for tests and offline runs.

    Understands inputs like "2 Veg Biryani, 1 Cold Coffee" or "3 x Sushi".
    """

    def parse_order(self, text: str, menu_names: list[str]) -> ParsedOrder:
        items: list[DishRequest] = []
        pattern = r"(\d+|" + "|".join(_NUMBER_WORDS) + r")\s*(?:x\s*)?([A-Za-z][A-Za-z ]*?)(?=\s*(?:,|\band\b|$|\d))"
        for qty_raw, dish in re.findall(pattern, text, flags=re.IGNORECASE):
            qty = int(qty_raw) if qty_raw.isdigit() else _NUMBER_WORDS[qty_raw.lower()]
            dish = dish.strip()
            canonical = next((m for m in menu_names if m.lower() == dish.lower()), dish.title())
            items.append(DishRequest(dish=canonical, quantity=qty))
        return ParsedOrder(is_food_order=bool(items), items=items)

    def classify_decision(self, text: str, partial_allowed: bool) -> Decision:
        low = text.lower()
        has_details = bool(re.search(r"\d", low))
        if has_details or any(w in low for w in ("new order", "something else", "change", "different")):
            return Decision(action="new_order", has_order_details=has_details)
        if any(w in low for w in ("cancel", "no thanks", "forget it", "leave", "quit")):
            return Decision(action="cancel", has_order_details=False)
        if partial_allowed and any(w in low for w in ("yes", "confirm", "accept", "go ahead", "ok", "fine")):
            return Decision(action="accept_partial", has_order_details=False)
        return Decision(action="unclear", has_order_details=False)

    def classify_payment(self, text: str) -> PaymentChoice:
        low = text.lower()
        for method, words in (("upi", ("upi", "gpay", "phonepe", "paytm", "qr")),
                              ("card", ("card",)), ("cash", ("cash",))):
            if any(w in low for w in words):
                return PaymentChoice(method=method)
        return PaymentChoice(method="unclear")

    def compose(self, situation: str, facts: dict) -> str:
        bill = "; ".join(
            f"{b['dish']} x{b['quantity']} = Rs {b['amount']}" for b in facts.get("bill", [])
        )
        order = ", ".join(
            f"{i['dish']} (asked {i['requested']}, available {i['available']})"
            for i in facts.get("order", [])
        )
        left = facts.get("attempts_left")
        retry = (f" You have {left} order attempt(s) left." if left
                 else " You have no order attempts left.")
        templates = {
            "not_food_order": "I can only help with food orders. Please tell me the dishes and quantities." + retry,
            "too_many_dishes": f"You can order at most {facts.get('max_dishes')} different dishes." + retry,
            "invalid_quantity": "Each dish needs a quantity of at least 1." + retry,
            "order_confirmed": f"Your order is confirmed: {order}. Sending it to the kitchen.",
            "partial_available": f"Only part of your order is available: {order}." + (
                " Reply 'confirm' to go ahead with what is available, or place a new order." if left
                else " Reply 'confirm' to go ahead with what is available, or 'cancel'."),
            "nothing_available": f"Sorry, none of that is available: {order}. Please place a new order." + retry,
            "partial_accepted": f"Going ahead with the available items: {order}.",
            "decision_unclear": "Sorry, I didn't get that. Reply 'confirm', place a new order, or 'cancel'.",
            "bill": f"Your bill: {bill}. Total Rs {facts.get('total')}. How would you like to pay: cash, card or UPI?",
            "payment_failed_retry": f"Your {facts.get('method')} payment failed. You have "
                                    f"{facts.get('payment_attempts_left')} payment attempt(s) left. "
                                    "Please choose cash, card or UPI.",
            "payment_unclear": "Please choose cash, card or UPI.",
            "order_complete": f"Payment of Rs {facts.get('total')} received by {facts.get('method')}. "
                              "Your order is complete. Enjoy your meal!",
            "payment_exhausted": f"We're sorry, your payment of Rs {facts.get('total')} could not be completed. "
                                 "Please settle the bill at the counter.",
            "goodbye_cancelled": "Your order has been cancelled. Hope to see you again!",
            "apology": f"We're very sorry, we could not complete your order ({facts.get('reason')}).",
        }
        return templates.get(situation, situation)
