# Graph Report - DinegGraph  (2026-09-27)

## Corpus Check
- 30 files · ~25,654 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 3, .example 1, .ini 1)

## Summary
- 472 nodes · 895 edges · 27 communities (17 shown, 10 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 53 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c595ebc9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_scenarios.py
- api.py
- initial_state
- graph.py
- difflib
- io
- test_api.py
- Store
- DineGraph
- math
- test_claude_wiring.py
- statistics
- random_outcome
- tempfile
- urllib_parse
- build_graph
- CLAUDE.md
- main.py
- Inventory
- conftest.py
- api.ts
- hashlib
- package.json
- __init__.py
- csv
- Design System Master File
- compilerOptions

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 45 edges
2. `create_app()` - 41 edges
3. `run()` - 31 edges
4. `Store` - 23 edges
5. `RuleBasedLLM` - 20 edges
6. `ClaudeLLM` - 19 edges
7. `make_client()` - 19 edges
8. `Status` - 17 edges
9. `initial_state()` - 16 edges
10. `InMemoryInventory` - 14 edges

## Surprising Connections (you probably didn't know these)
- `describe()` --uses--> `Status`  [INFERRED]
  backend/dinegraph/api.py → backend/dinegraph/state.py
- `create_app()` --uses--> `OrderLLM`  [INFERRED]
  backend/dinegraph/api.py → backend/dinegraph/llm.py
- `create_app()` --uses--> `Status`  [INFERRED]
  backend/dinegraph/api.py → backend/dinegraph/state.py
- `_last_user_text()` --uses--> `DineState`  [INFERRED]
  backend/dinegraph/graph.py → backend/dinegraph/state.py
- `_order_facts()` --uses--> `OrderItem`  [INFERRED]
  backend/dinegraph/graph.py → backend/dinegraph/state.py

## Import Cycles
- None detected.

## Communities (27 total, 10 thin omitted)

### Community 0 - "test_scenarios.py"
Cohesion: 0.10
Nodes (39): InMemoryInventory, Every value the `status` field can take., Status, Scenario tests for DineGraph. They use the rule-based LLM and scripted…, Drive the graph with scripted user inputs and cook/serve results. outcomes is a…, run(), run_with(), test_bill_is_shown_after_serving() (+31 more)

### Community 1 - "api.py"
Cohesion: 0.08
Nodes (42): ChatMessage, Counters, create_app(), busy(), config(), error_text(), get_menu(), get_session() (+34 more)

### Community 2 - "initial_state"
Cohesion: 0.28
Nodes (8): DineState, initial_state(), OrderItem, The LangGraph state shared by every node., langchain_core_messages, langgraph_graph_message, TypedDict, typing_extensions

### Community 3 - "graph.py"
Cohesion: 0.15
Nodes (14): build_bill(), order_confirm(), parse_order(), request_payment(), _item(), _last_user_text(), r"""The DineGraph LangGraph. START -> take_order -> parse_order ->…, Stock and prices, behind one small interface the graph can use.… (+6 more)

### Community 6 - "test_api.py"
Cohesion: 0.17
Nodes (24): finish_order(), FlakyLLM, make_client(), Tests for the HTTP backend, using the offline LLM and scripted outcomes., Fails the first parse_order call with an API error, then works., say(), test_admin_menu_changes(), test_admin_stats() (+16 more)

### Community 7 - "Store"
Cohesion: 0.06
Nodes (27): order_events(), postgres_checkpointer(), A LangGraph checkpointer that keeps sessions in Postgres, creating its tables…, make_engine(), _now(), Database storage for the backend: the menu with stock and prices, and order…, Take stock for every dish, or for none. Safe with several server processes., Create a dish, or change its quantity and/or price. New dishes need both. (+19 more)

### Community 8 - "DineGraph"
Cohesion: 0.10
Nodes (19): Backend, Command-line chat, Configuration, Contents, Database, DineGraph, Features, Getting started (+11 more)

### Community 10 - "test_claude_wiring.py"
Cohesion: 0.07
Nodes (31): Anthropic, ClaudeLLM, Decision, DishRequest, OrderLLM, ParsedOrder, PaymentChoice, BaseModel (+23 more)

### Community 12 - "random_outcome"
Cohesion: 0.50
Nodes (4): Outcome, random_outcome(), The probability function: 40% failure, 60% success., test_random_outcome_is_about_forty_percent_failure()

### Community 15 - "build_graph"
Cohesion: 0.11
Nodes (12): build_graph(), cook(), final_message(), finish(), pay(), review_order(), serve(), user_decision() (+4 more)

### Community 17 - "main.py"
Cohesion: 0.19
Nodes (12): argparse, load_env(), main(), Command-line runner: python -m dinegraph.main [--offline] [--seed N], Read backend/.env if it exists. Variables already set in the shell take…, full_order(), main(), Live check of DineGraph against the real Claude API. Run it once you have a… (+4 more)

### Community 18 - "Inventory"
Cohesion: 0.20
Nodes (6): Inventory, Protocol, Dish -> quantity available right now., Dish -> price per plate., Take dish -> quantity out of stock. All or nothing; False if any dish is short., Put reserved quantities back.

### Community 19 - "conftest.py"
Cohesion: 0.25
Nodes (8): Database, db(), The `db` fixture runs each API test on SQLite and, when a Postgres server is…, dataclasses, fixture, os, pytest, uuid

### Community 20 - "api.ts"
Cohesion: 0.05
Nodes (56): api, ApiError, ChatMessage, clock(), Counters, Health, json(), KitchenStage (+48 more)

### Community 22 - "package.json"
Cohesion: 0.07
Nodes (26): dependencies, lucide-react, react, react-dom, devDependencies, @types/node, @types/react, @types/react-dom (+18 more)

### Community 26 - "Design System Master File"
Cohesion: 0.12
Nodes (16): Additional Forbidden Patterns, Anti-Patterns (Do NOT Use), Buttons, Cards, Color Palette, Component Specs, Design System Master File, Global Rules (+8 more)

### Community 28 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noUnusedLocals (+6 more)

## Knowledge Gaps
- **73 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+68 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 189 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `build_graph` to `test_scenarios.py`, `api.py`, `initial_state`, `graph.py`, `test_claude_wiring.py`, `random_outcome`, `main.py`, `Inventory`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `create_app()` connect `api.py` to `test_scenarios.py`, `initial_state`, `test_api.py`, `Store`, `test_claude_wiring.py`, `random_outcome`, `build_graph`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `Store` connect `Store` to `api.py`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `build_graph()` (e.g. with `after_choose_payment()` and `after_cook()`) actually correct?**
  _`build_graph()` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `create_app()` (e.g. with `require_admin()` and `OrderLLM`) actually correct?**
  _`create_app()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _73 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_scenarios.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09797979797979799 - nodes in this community are weakly interconnected._