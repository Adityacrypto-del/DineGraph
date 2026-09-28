# Graph Report - DinegGraph  (2026-09-28)

## Corpus Check
- 30 files · ~26,370 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 3, .example 1, .ini 1)

## Summary
- 511 nodes · 972 edges · 31 communities (17 shown, 14 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 56 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c8347eeb`
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
- test_gemini_wiring.py
- statistics
- test_claude_wiring.py
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
- menu.py

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 47 edges
2. `create_app()` - 41 edges
3. `run()` - 31 edges
4. `RuleBasedLLM` - 25 edges
5. `GeminiLLM` - 20 edges
6. `Store` - 20 edges
7. `make_client()` - 19 edges
8. `initial_state()` - 18 edges
9. `Status` - 17 edges
10. `ClaudeLLM` - 16 edges

## Surprising Connections (you probably didn't know these)
- `describe()` --uses--> `Status`  [INFERRED]
  backend/dinegraph/api.py → backend/dinegraph/state.py
- `create_app()` --uses--> `MissingKeyError`  [INFERRED]
  backend/dinegraph/api.py → backend/dinegraph/llm.py
- `create_app()` --uses--> `OrderLLM`  [INFERRED]
  backend/dinegraph/api.py → backend/dinegraph/llm.py
- `create_app()` --uses--> `Status`  [INFERRED]
  backend/dinegraph/api.py → backend/dinegraph/state.py
- `_last_user_text()` --uses--> `DineState`  [INFERRED]
  backend/dinegraph/graph.py → backend/dinegraph/state.py

## Import Cycles
- None detected.

## Communities (31 total, 14 thin omitted)

### Community 0 - "test_scenarios.py"
Cohesion: 0.10
Nodes (40): InMemoryInventory, initial_state(), Every value the `status` field can take., Status, Scenario tests for DineGraph. They use the rule-based LLM and scripted…, Drive the graph with scripted user inputs and cook/serve results. outcomes is a…, run(), run_with() (+32 more)

### Community 1 - "api.py"
Cohesion: 0.08
Nodes (42): ChatMessage, Counters, create_app(), busy(), config(), error_text(), get_menu(), get_session() (+34 more)

### Community 3 - "graph.py"
Cohesion: 0.16
Nodes (15): build_bill(), request_payment(), r"""The DineGraph LangGraph. START -> take_order -> parse_order ->…, Stock and prices, behind one small interface the graph can use.…, DineState, OrderItem, The LangGraph state shared by every node., langchain_core_messages (+7 more)

### Community 6 - "test_api.py"
Cohesion: 0.18
Nodes (23): finish_order(), FlakyLLM, make_client(), Tests for the HTTP backend, using the offline LLM and scripted outcomes., Fails the first parse_order call with an API error, then works., say(), test_admin_menu_changes(), test_admin_stats() (+15 more)

### Community 7 - "Store"
Cohesion: 0.08
Nodes (16): make_engine(), _now(), Postgres storage for the backend: the menu with stock and prices, and order…, Take stock for every dish, or for none. Safe with several server processes., Create a dish, or change its quantity and/or price. New dishes need both., Upsert the order record. `stage` is the graph node that runs next ('' when…, Orders still in progress, oldest first: what the kitchen screen shows., Use the psycopg 3 driver for Postgres URLs given in the usual postgres:// form. (+8 more)

### Community 8 - "DineGraph"
Cohesion: 0.09
Nodes (20): Backend, Choosing the LLM, Command-line chat, Configuration, Contents, Database, DineGraph, Features (+12 more)

### Community 10 - "test_gemini_wiring.py"
Cohesion: 0.05
Nodes (45): ClaudeLLM, Decision, DishRequest, GeminiLLM, make_llm(), MissingKeyError, OrderLLM, ParsedOrder (+37 more)

### Community 12 - "test_claude_wiring.py"
Cohesion: 0.16
Nodes (17): Anthropic, fake_restaurant(), FakeAPI, Request, Response, Runs the real ClaudeLLM code against a fake Anthropic API. No API key or…, Answers /v1/messages from a function of the request body and records every…, Plays Claude for a whole conversation, choosing the reply by the requested… (+9 more)

### Community 15 - "build_graph"
Cohesion: 0.11
Nodes (11): build_graph(), cook(), final_message(), finish(), pay(), review_order(), serve(), _order_facts() (+3 more)

### Community 17 - "main.py"
Cohesion: 0.13
Nodes (18): argparse, __getattr__(), Outcome, random_outcome(), The probability function: 40% failure, 60% success., load_env(), main(), Command-line runner: python -m dinegraph.main [--offline] [--seed N] (+10 more)

### Community 18 - "Inventory"
Cohesion: 0.20
Nodes (6): Inventory, Protocol, Dish -> quantity available right now., Dish -> price per plate., Take dish -> quantity out of stock. All or nothing; False if any dish is short., Put reserved quantities back.

### Community 19 - "conftest.py"
Cohesion: 0.22
Nodes (9): db(), postgres_server(), The `db` fixture gives each API test its own fresh Postgres database, dropped…, The URL of a new, empty database., fixture, os, psycopg, pytest (+1 more)

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

### Community 30 - "menu.py"
Cohesion: 0.22
Nodes (8): order_confirm(), parse_order(), user_decision(), _item(), _last_user_text(), lookup(), The restaurant menu: dish name -> quantity currently available. Edit this dict…, Case-insensitive menu lookup. Returns (canonical name, available quantity). A…

## Knowledge Gaps
- **74 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+69 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 209 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `build_graph` to `test_scenarios.py`, `api.py`, `graph.py`, `test_gemini_wiring.py`, `test_claude_wiring.py`, `main.py`, `Inventory`, `menu.py`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `create_app()` connect `api.py` to `test_scenarios.py`, `test_api.py`, `Store`, `test_gemini_wiring.py`, `build_graph`, `main.py`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Why does `Store` connect `Store` to `api.py`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `build_graph()` (e.g. with `after_choose_payment()` and `after_cook()`) actually correct?**
  _`build_graph()` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `create_app()` (e.g. with `require_admin()` and `MissingKeyError`) actually correct?**
  _`create_app()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `RuleBasedLLM` (e.g. with `main()` and `test_make_llm_picks_the_provider()`) actually correct?**
  _`RuleBasedLLM` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `GeminiLLM` (e.g. with `test_blocked_or_bad_replies_fall_back()` and `test_make_llm_picks_the_provider()`) actually correct?**
  _`GeminiLLM` has 2 INFERRED edges - model-reasoned connections that need verification._