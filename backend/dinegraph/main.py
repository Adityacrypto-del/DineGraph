"""Command-line runner: python -m dinegraph.main [--offline] [--seed N]"""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langgraph.types import Command

from .graph import build_graph, random_outcome
from .llm import ClaudeLLM, RuleBasedLLM
from .menu import MENU
from .state import MAX_DISHES, initial_state


def welcome_text(dishes: list[str] | None = None) -> str:
    lines = [f"  - {name}" for name in (MENU if dishes is None else dishes)]
    return (
        "Welcome to DineGraph! Here is our menu:\n" + "\n".join(lines)
        + f"\nOrder up to {MAX_DISHES} dishes with quantities, e.g. '2 Veg Biryani, 1 Cold Coffee'."
    )


def load_env() -> None:
    """Read backend/.env if it exists. Variables already set in the shell take precedence."""
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="DineGraph restaurant ordering agent")
    parser.add_argument("--offline", action="store_true", help="use the rule-based parser instead of Claude")
    parser.add_argument("--seed", type=int, default=None, help="seed the cook/serve failure chance")
    args = parser.parse_args()

    llm = RuleBasedLLM() if args.offline else ClaudeLLM()
    graph = build_graph(llm, outcome=random_outcome(args.seed))
    config = {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": 100}

    printed = 0
    result = graph.invoke(initial_state(welcome_text()), config)
    while True:
        messages = result["messages"]
        for msg in messages[printed:]:
            if isinstance(msg, AIMessage):
                speaker = (msg.name or "assistant").capitalize()
                if msg.name:  # kitchen / waiter already prefix their own text
                    print(f"  {msg.content}")
                else:
                    print(f"\n{speaker}: {msg.content}")
        printed = len(messages)

        if not graph.get_state(config).next:
            break
        text = input("\nYou: ").strip()
        result = graph.invoke(Command(resume=text), config)

    state = graph.get_state(config).values
    print(f"\nFinal result: {state['final_result']}  (status: {state['status']})")


if __name__ == "__main__":
    main()
