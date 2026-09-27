# Graph Report - DinegGraph  (2026-09-27)

## Corpus Check
- 28 files · ~24,750 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 3, .css 1)

## Summary
- 449 nodes · 836 edges · 23 communities (13 shown, 10 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 47 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `de6d85ff`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_scenarios.py
- api.py
- build_graph
- difflib
- io
- test_api.py
- Store
- DineGraph
- math
- test_claude_wiring.py
- statistics
- llm.py
- tempfile
- urllib_parse
- Inventory
- CLAUDE.md
- __init__.py
- api.ts
- hashlib
- package.json
- csv
- Design System Master File
- compilerOptions

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 45 edges
2. `create_app()` - 40 edges
3. `run()` - 31 edges
4. `RuleBasedLLM` - 20 edges
5. `Store` - 20 edges
6. `ClaudeLLM` - 19 edges
7. `make_client()` - 19 edges
8. `Status` - 17 edges
9. `initial_state()` - 16 edges
10. `InMemoryInventory` - 14 edges

## Surprising Connections (you probably didn't know these)
- `make_client()` --calls--> `create_app()`  [EXTRACTED]
  tests/test_api.py → dinegraph/api.py
- `test_random_outcome_is_about_forty_percent_failure()` --calls--> `random_outcome()`  [EXTRACTED]
  tests/test_scenarios.py → dinegraph/graph.py
- `test_full_conversation_through_the_graph()` --calls--> `build_graph()`  [EXTRACTED]
  tests/test_claude_wiring.py → dinegraph/graph.py
- `run()` --calls--> `build_graph()`  [EXTRACTED]
  tests/test_scenarios.py → dinegraph/graph.py
- `run_with()` --calls--> `build_graph()`  [EXTRACTED]
  tests/test_scenarios.py → dinegraph/graph.py

## Import Cycles
- None detected.

## Communities (23 total, 10 thin omitted)

### Community 0 - "test_scenarios.py"
Cohesion: 0.10
Nodes (39): InMemoryInventory, Every value the `status` field can take., Status, Scenario tests for DineGraph. They use the rule-based LLM and scripted…, Drive the graph with scripted user inputs and cook/serve results. outcomes is a…, run(), run_with(), test_bill_is_shown_after_serving() (+31 more)

### Community 2 - "api.py"
Cohesion: 0.08
Nodes (41): collections, ChatMessage, Counters, create_app(), busy(), config(), error_text(), get_menu() (+33 more)

### Community 3 - "build_graph"
Cohesion: 0.05
Nodes (50): argparse, build_bill(), build_graph(), cook(), final_message(), finish(), order_confirm(), parse_order() (+42 more)

### Community 6 - "test_api.py"
Cohesion: 0.16
Nodes (25): fastapi_testclient, httpx, finish_order(), FlakyLLM, make_client(), Tests for the HTTP backend, using the offline LLM and scripted outcomes., Fails the first parse_order call with an API error, then works., say() (+17 more)

### Community 7 - "Store"
Cohesion: 0.09
Nodes (11): Connection, datetime, _now(), SQLite storage for the backend: the menu with stock and prices, and order…, Create a dish, or change its quantity and/or price. New dishes need both., Upsert the order record. `stage` is the graph node that runs next ('' when…, Orders still in progress, oldest first: what the kitchen screen shows., Store (+3 more)

### Community 8 - "DineGraph"
Cohesion: 0.10
Nodes (18): Backend, Command-line chat, Configuration, Contents, DineGraph, Features, Getting started, How the graph works (+10 more)

### Community 10 - "test_claude_wiring.py"
Cohesion: 0.12
Nodes (20): Anthropic, ClaudeLLM, One structured-output call. A refusal or an unreadable reply returns…, httpx2, langgraph_checkpoint_memory, pytest, Request, Response (+12 more)

### Community 12 - "llm.py"
Cohesion: 0.12
Nodes (14): Decision, DishRequest, OrderLLM, ParsedOrder, PaymentChoice, BaseModel, Protocol, The LLM layer. The graph talks to the LLM through three calls: parse_order user… (+6 more)

### Community 15 - "Inventory"
Cohesion: 0.20
Nodes (6): Inventory, Protocol, Dish -> quantity available right now., Dish -> price per plate., Take dish -> quantity out of stock. All or nothing; False if any dish is short., Put reserved quantities back.

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
- **72 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+67 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 186 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `build_graph` to `test_scenarios.py`, `api.py`, `test_claude_wiring.py`, `llm.py`, `Inventory`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `create_app()` connect `api.py` to `test_scenarios.py`, `build_graph`, `test_api.py`, `Store`, `test_claude_wiring.py`, `llm.py`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `Store` connect `Store` to `api.py`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `build_graph()` (e.g. with `after_choose_payment()` and `after_cook()`) actually correct?**
  _`build_graph()` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `create_app()` (e.g. with `require_admin()` and `OrderLLM`) actually correct?**
  _`create_app()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _72 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_scenarios.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09797979797979799 - nodes in this community are weakly interconnected._