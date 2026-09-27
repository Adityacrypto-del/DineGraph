# Graph Report - DinegGraph  (2026-09-27)

## Corpus Check
- 29 files · ~25,114 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 3, .example 1, .ini 1)

## Summary
- 469 nodes · 867 edges · 30 communities (16 shown, 14 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 48 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c355b78e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_scenarios.py
- api.py
- dataclasses
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
- langgraph_checkpoint_sqlite
- __init__.py
- csv
- Design System Master File
- sqlalchemy_dialects
- compilerOptions
- sqlite3

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 45 edges
2. `create_app()` - 41 edges
3. `run()` - 31 edges
4. `RuleBasedLLM` - 20 edges
5. `Store` - 20 edges
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
- `_order_facts()` --uses--> `OrderItem`  [INFERRED]
  backend/dinegraph/graph.py → backend/dinegraph/state.py
- `build_graph()` --uses--> `Inventory`  [INFERRED]
  backend/dinegraph/graph.py → backend/dinegraph/inventory.py

## Import Cycles
- None detected.

## Communities (30 total, 14 thin omitted)

### Community 0 - "test_scenarios.py"
Cohesion: 0.09
Nodes (42): InMemoryInventory, Deterministic stand-in for tests and offline runs. Understands inputs like "2…, RuleBasedLLM, Every value the `status` field can take., Status, Scenario tests for DineGraph. They use the rule-based LLM and scripted…, Drive the graph with scripted user inputs and cook/serve results. outcomes is a…, run() (+34 more)

### Community 1 - "api.py"
Cohesion: 0.07
Nodes (44): ChatMessage, Counters, create_app(), busy(), config(), error_text(), get_menu(), get_session() (+36 more)

### Community 3 - "graph.py"
Cohesion: 0.12
Nodes (21): build_bill(), order_confirm(), parse_order(), request_payment(), _item(), _last_user_text(), r"""The DineGraph LangGraph. START -> take_order -> parse_order ->…, Stock and prices, behind one small interface the graph can use.… (+13 more)

### Community 6 - "test_api.py"
Cohesion: 0.17
Nodes (24): finish_order(), FlakyLLM, make_client(), Tests for the HTTP backend, using the offline LLM and scripted outcomes., Fails the first parse_order call with an API error, then works., say(), test_admin_menu_changes(), test_admin_stats() (+16 more)

### Community 7 - "Store"
Cohesion: 0.08
Nodes (16): make_engine(), _now(), Postgres storage for the backend: the menu with stock and prices, and order…, Take stock for every dish, or for none. Safe with several server processes., Create a dish, or change its quantity and/or price. New dishes need both., Upsert the order record. `stage` is the graph node that runs next ('' when…, Orders still in progress, oldest first: what the kitchen screen shows., Use the psycopg 3 driver for Postgres URLs given in the usual postgres:// form. (+8 more)

### Community 8 - "DineGraph"
Cohesion: 0.10
Nodes (19): Backend, Command-line chat, Configuration, Contents, Database, DineGraph, Features, Getting started (+11 more)

### Community 10 - "test_claude_wiring.py"
Cohesion: 0.08
Nodes (25): Anthropic, ClaudeLLM, Decision, DishRequest, OrderLLM, ParsedOrder, PaymentChoice, BaseModel (+17 more)

### Community 12 - "random_outcome"
Cohesion: 0.50
Nodes (4): Outcome, random_outcome(), The probability function: 40% failure, 60% success., test_random_outcome_is_about_forty_percent_failure()

### Community 15 - "build_graph"
Cohesion: 0.11
Nodes (12): build_graph(), cook(), final_message(), finish(), pay(), review_order(), serve(), user_decision() (+4 more)

### Community 17 - "main.py"
Cohesion: 0.14
Nodes (19): argparse, start_session(), The LLM layer. The graph talks to the LLM through three calls: parse_order user…, load_env(), main(), Command-line runner: python -m dinegraph.main [--offline] [--seed N], Read backend/.env if it exists. Variables already set in the shell take…, welcome_text() (+11 more)

### Community 18 - "Inventory"
Cohesion: 0.20
Nodes (6): Inventory, Protocol, Dish -> quantity available right now., Dish -> price per plate., Take dish -> quantity out of stock. All or nothing; False if any dish is short., Put reserved quantities back.

### Community 19 - "conftest.py"
Cohesion: 0.25
Nodes (8): db(), postgres_server(), The `db` fixture gives each API test its own fresh Postgres database, dropped…, The URL of a new, empty database., fixture, psycopg, pytest, uuid

### Community 20 - "api.ts"
Cohesion: 0.06
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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 195 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `build_graph` to `test_scenarios.py`, `api.py`, `graph.py`, `test_claude_wiring.py`, `random_outcome`, `main.py`, `Inventory`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `create_app()` connect `api.py` to `test_scenarios.py`, `test_api.py`, `Store`, `test_claude_wiring.py`, `random_outcome`, `build_graph`, `main.py`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `Store` connect `Store` to `api.py`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `build_graph()` (e.g. with `after_choose_payment()` and `after_cook()`) actually correct?**
  _`build_graph()` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `create_app()` (e.g. with `require_admin()` and `OrderLLM`) actually correct?**
  _`create_app()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _73 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_scenarios.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08734693877551021 - nodes in this community are weakly interconnected._