"""The LangGraph state shared by every node."""

from typing import Annotated

from typing_extensions import NotRequired, TypedDict  # NotRequired is in typing from 3.11

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

MAX_DISHES = 3
ORDER_RETRIES = 3
COOK_RETRIES = 2
SERVE_RETRIES = 2
PAYMENT_RETRIES = 2
PAYMENT_METHODS = ("cash", "card", "upi")


class Status:
    """Every value the `status` field can take."""

    NEW = "NEW"                        # nothing ordered yet
    INVALID = "INVALID"                # input was not a usable food order
    PLACED = "PLACED"                  # LLM extracted dishes, waiting for order_confirm
    CONFIRMED = "CONFIRMED"            # every dish fully available
    PARTIAL = "PARTIAL"                # some dishes short or missing
    NOT_AVAILABLE = "NOT_AVAILABLE"    # nothing in the order is available
    COOK_FAILED = "COOK_FAILED"
    READY = "READY"                    # cooked, waiting to be served
    SERVE_FAILED = "SERVE_FAILED"
    COMPLETE = "COMPLETE"              # served, waiting for payment
    PAYMENT_PENDING = "PAYMENT_PENDING"  # bill shown, waiting for a payment method
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAID = "PAID"                      # served and paid: the order is complete
    CANCELLED = "CANCELLED"            # user gave up
    FAILED = "FAILED"                  # retries exhausted somewhere


class OrderItem(TypedDict):
    dish: str                 # dish name
    required_quantity: int    # what the user asked for
    available_quantity: int   # written by order_confirm from the menu (0 if not on menu)
    note: NotRequired[str]    # special instructions, e.g. "extra spicy"; absent when there are none


class DineState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]  # conversation between user and LLM
    order: list[OrderItem]    # up to MAX_DISHES items
    status: str
    order_retries: int        # starts at 3, decremented on every unsuccessful order attempt
    cook_retries: int         # starts at 2, decremented on every cook failure
    serve_retries: int        # starts at 2, decremented on every serve failure
    payment_retries: int      # starts at 2, decremented on every failed payment
    payment_method: str       # "cash", "card", "upi" or "" before the user chooses
    bill_total: int           # sum of quantity x price, set when the bill is shown
    stock_reserved: bool      # True once the confirmed order has been taken out of stock
    final_result: str         # "COMPLETED" or "NOT_COMPLETED: <reason>"
    table: NotRequired[int | None]  # table number when the order comes from a table, else None


def initial_state(welcome: str, table: int | None = None) -> DineState:
    from langchain_core.messages import AIMessage

    return DineState(
        messages=[AIMessage(content=welcome)],
        order=[],
        status=Status.NEW,
        order_retries=ORDER_RETRIES,
        cook_retries=COOK_RETRIES,
        serve_retries=SERVE_RETRIES,
        payment_retries=PAYMENT_RETRIES,
        payment_method="",
        bill_total=0,
        stock_reserved=False,
        final_result="",
        table=table,
    )
