# DineGraph

A restaurant order management agent built with LangGraph and Claude. The design follows [approch.md](approch.md).

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=...            # needed for the Claude-powered mode
.venv/bin/python -m dinegraph.main      # talk to Claude
.venv/bin/python -m dinegraph.main --offline --seed 3   # rule-based parser, no API key
.venv/bin/python -m pytest -q           # scenario tests
```

The model defaults to `claude-opus-5`. Override it with the `DINEGRAPH_MODEL` environment variable.

## Graph

```
START -> take_order -> parse_order -> order_confirm -> review_order
                        (invalid input goes straight to review_order)
review_order  -> cook            when CONFIRMED
              -> user_decision   when PARTIAL (accept / new order / cancel)
              -> take_order      when NOT_AVAILABLE or INVALID and order attempts remain
              -> finish          when order attempts are used up
user_decision -> cook | parse_order | take_order | finish | user_decision (unclear reply)
cook          -> serve (READY) | cook (failed, retries left) | finish (no retries)
serve         -> request_payment (COMPLETE) | cook (failed, serve and cook retries left) | finish
request_payment -> choose_payment -> pay   (an unclear reply asks again)
pay           -> finish (PAID) | choose_payment (failed, retries left) | finish (no retries)
finish        -> END   (LLM writes "order complete" or an apology)
```

| Node | Role |
|---|---|
| take_order | Pauses the graph and waits for the user's order. |
| parse_order | LLM extracts dishes and quantities, rejects non-food input and more than 3 dishes. |
| order_confirm | Reads the menu, writes available quantity (0 if not on the menu), sets CONFIRMED, PARTIAL or NOT_AVAILABLE. |
| review_order | LLM reads the status, decrements the order counter on failure, and talks to the user. |
| user_decision | Waits for the user's choice after a partial order and classifies it with the LLM. |
| cook, serve | 60% success, 40% failure. Each failure decrements its counter. |
| request_payment | LLM shows the bill (quantity x price) and asks for cash, card or UPI. |
| choose_payment | Waits for the user's payment method and classifies it with the LLM. |
| pay | Cash always succeeds. Card and UPI fail 40% of the time, and each failure decrements the payment counter. |
| finish | LLM writes the final message and sets final_result. |

## State

| Field | Meaning |
|---|---|
| messages | Conversation between the user and the LLM, merged with `add_messages`. |
| order | Up to 3 items of dish, required_quantity, available_quantity. |
| status | NEW, INVALID, PLACED, CONFIRMED, PARTIAL, NOT_AVAILABLE, COOK_FAILED, READY, SERVE_FAILED, COMPLETE, PAYMENT_PENDING, PAYMENT_FAILED, PAID, CANCELLED, FAILED. |
| order_retries | Starts at 3. |
| cook_retries | Starts at 2. |
| serve_retries | Starts at 2. |
| payment_retries | Starts at 2. |
| payment_method | cash, card or upi. |
| bill_total | Total of the bill in rupees. |
| final_result | COMPLETED, or NOT_COMPLETED with the reason. |

The menu and prices live in [dinegraph/menu.py](dinegraph/menu.py). An order is COMPLETED only when it is served and paid.
