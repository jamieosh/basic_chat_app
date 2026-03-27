# Deer-Flow Core Pattern: LangGraph Runtime + Publishable Harness

## Purpose

This document analyzes [`bytedance/deer-flow`](https://github.com/bytedance/deer-flow) with focus on:

- where the core agent runtime lives
- what Deer-Flow treats as its harness boundary
- how that maps to our architecture and agent thinking
- what we should adopt, adapt, or avoid

## Reference Project

- Repository: [`bytedance/deer-flow`](https://github.com/bytedance/deer-flow)
- Core architecture docs:
  - [`README.md`](https://github.com/bytedance/deer-flow/blob/main/README.md)
  - [`backend/docs/ARCHITECTURE.md`](https://github.com/bytedance/deer-flow/blob/main/backend/docs/ARCHITECTURE.md)
  - [`backend/docs/HARNESS_APP_SPLIT.md`](https://github.com/bytedance/deer-flow/blob/main/backend/docs/HARNESS_APP_SPLIT.md)
- Core runtime/harness code:
  - [`backend/langgraph.json`](https://github.com/bytedance/deer-flow/blob/main/backend/langgraph.json)
  - [`backend/packages/harness/deerflow/agents/lead_agent/agent.py`](https://github.com/bytedance/deer-flow/blob/main/backend/packages/harness/deerflow/agents/lead_agent/agent.py)
  - [`backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py`](https://github.com/bytedance/deer-flow/blob/main/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py)
  - [`backend/packages/harness/deerflow/tools/tools.py`](https://github.com/bytedance/deer-flow/blob/main/backend/packages/harness/deerflow/tools/tools.py)
  - [`backend/packages/harness/deerflow/subagents/executor.py`](https://github.com/bytedance/deer-flow/blob/main/backend/packages/harness/deerflow/subagents/executor.py)
  - [`backend/packages/harness/deerflow/client.py`](https://github.com/bytedance/deer-flow/blob/main/backend/packages/harness/deerflow/client.py)
  - [`backend/packages/harness/pyproject.toml`](https://github.com/bytedance/deer-flow/blob/main/backend/packages/harness/pyproject.toml)
- App boundary and enforcement:
  - [`backend/app/gateway/app.py`](https://github.com/bytedance/deer-flow/blob/main/backend/app/gateway/app.py)
  - [`backend/tests/test_harness_boundary.py`](https://github.com/bytedance/deer-flow/blob/main/backend/tests/test_harness_boundary.py)
  - [`backend/tests/test_client.py`](https://github.com/bytedance/deer-flow/blob/main/backend/tests/test_client.py)

## What Deer-Flow Is, Architecturally

Deer-Flow is best read as:

1. A LangGraph-driven agent runtime (lead agent + middleware + tools + subagents)
2. A publishable harness package (`deerflow-harness`) intended to be app-agnostic
3. An application layer (Gateway API + channels) that depends on the harness, not vice versa

In other words, it is not just "an agent"; it is a packaged runtime platform with app integrations on top.

## Core Agent Pattern

### 1) Runtime entrypoint is a single lead-agent factory

`langgraph.json` points graph creation at `deerflow.agents:make_lead_agent` with a checkpointer provider.  
The lead runtime is centered in `make_lead_agent(...)`:

- resolve model from runtime config + app config
- assemble tools dynamically
- assemble middleware chain dynamically
- build system prompt with skills/memory/subagent instructions
- create LangChain agent with `ThreadState`

Pattern: one runtime kernel function composes model + tools + middleware + prompt + state schema at run start.

### 2) Middleware pipeline is the real orchestration spine

Deer-Flow pushes most execution behavior into ordered middleware:

- thread data setup
- sandbox lifecycle
- uploads/context injection
- guardrail gate
- summarization
- todo/planning behavior
- title and memory updates
- tool-error normalization
- loop detection
- clarification interruption

Pattern: "agent behavior" is a middleware composition problem, not route logic.

### 3) Tool system is multi-source and runtime-resolved

`get_available_tools(...)` composes:

- config-defined tools (reflection-resolved)
- built-ins
- optional subagent tool (`task`)
- MCP tools (cached + config-mtime invalidation)
- optional ACP integration

It also supports deferred tool schema exposure via `tool_search` to reduce model context footprint.

Pattern: tool plane is dynamic, source-agnostic, and token-budget-aware.

### 4) Subagents are first-class runtime primitives

The `task` tool delegates into `SubagentExecutor`, which:

- creates subagents with filtered tools
- runs them asynchronously in background thread pools
- propagates thread/sandbox context
- streams progress events
- enforces timeout and concurrency limits

Pattern: delegation is a built-in execution primitive, not an external orchestration layer.

### 5) State model combines LangGraph thread state + filesystem + optional long-term memory

`ThreadState` extends `AgentState` with sandbox/thread-data/artifacts/todos/viewed-images.  
Per-thread working directories are mapped into virtual paths (`/mnt/user-data/...`), and memory is persisted separately (JSON, debounced updates).

Pattern: execution state is split across graph state, local filesystem, and sidecar memory store.

## Harness Boundary Pattern

Deer-Flow's most useful architectural move is its explicit Harness/App split:

- Harness package: `backend/packages/harness/deerflow/*` (publishable)
- App package: `backend/app/*` (gateway/channels/product concerns)
- Boundary rule: harness must not import app, enforced by test

This is close to our direction philosophically: core runtime as reusable infrastructure, app UX as a separate layer.

## Mapping To Our Architecture

| Deer-Flow concept | Our current equivalent |
| --- | --- |
| `make_lead_agent` LangGraph runtime composition | `ChatHarness` implementation + `HarnessRegistry` |
| middleware pipeline as orchestration core | `ChatTurnService` orchestration + harness-internal policy/runtime behavior |
| dynamic tool composition (built-in/config/MCP) | `ChatHarnessEvent` tool-call/result vocabulary + future orchestration hook |
| subagent task runtime | potential internal multi-step harness orchestration behind `run_events()` |
| checkpointer + thread state | `chat_session_runs` + turn request lifecycle in SQLite |
| publishable harness vs app split | `agents/` + `services/` + route boundaries in our app |
| embedded client returning app-aligned shapes | potential future SDK aligned to our route contract |

## Could We Replicate This Pattern In Our System?

Yes, as an implementation style behind our existing typed boundary.

Feasible fit:

1. Keep `ChatHarness` + `ChatTurnService` + repository lifecycle as control-plane authority.
2. Add a Deer-Flow-style harness adapter that internally uses middleware/tool/subagent runtime composition.
3. Map runtime outputs into normalized `ChatHarnessEvent` and `ChatHarnessFailure`.
4. Keep HTTP/HTMX behavior and idempotent replay semantics unchanged.

This would preserve our design principle: built-ins are convenience; alternate runtime styles should still fit.

## Key Differences That Matter

### 1) Runtime composition location

- Deer-Flow: heavy runtime behavior in middleware/prompt/tool composition around LangGraph agent.
- Ours: stronger app-side lifecycle ownership (`ChatTurnService` + persistence guarantees).

Why it matters: we should borrow runtime richness without moving lifecycle authority out of our service/repository layer.

### 2) State authority

- Deer-Flow: thread state + filesystem + sidecar memory/checkpointer.
- Ours: SQLite turn/run lifecycle is primary authority.

Why it matters: our idempotency/conflict guarantees depend on DB-first run lifecycle; keep that authoritative.

### 3) Dynamism vs determinism

- Deer-Flow: dynamic reflection-based tool/model wiring from config files.
- Ours: explicit registry binding and typed harness contracts.

Why it matters: their flexibility is powerful, but we should keep typed normalization boundaries for reliability.

### 4) Streaming-first runtime

- Deer-Flow is strongly streaming/event-centric.
- Our current web flow still targets deterministic final HTMX append behavior (non-streaming render path).

Why it matters: we can still carry internal events, but final UX semantics remain intentionally simpler today.

## What We Should Learn

1. Harness/App split as a hard boundary with automated enforcement is strong and practical.
2. Middleware composition is an effective place for cross-cutting runtime policies.
3. Deferred tool-schema exposure (`tool_search`) is a useful context-budget optimization pattern.
4. Subagent delegation works best as a first-class primitive with explicit concurrency and timeout controls.
5. Embedded client parity tests against app response models are a good contract-discipline pattern.

## What We Should Avoid Copying Blindly

1. Do not shift run lifecycle authority away from our persisted turn/run tables.
2. Do not let dynamic reflection bypass typed normalization and failure mapping.
3. Do not conflate long-term memory sidecar state with authoritative run lifecycle state.
4. Do not import broad prompt/runtime complexity into routes; keep it harness-internal.

## Practical Implementation Path For Us

If we want Deer-Flow-like behavior in our system:

1. Add an optional `deerflow_style` harness key in `HarnessRegistry`.
2. Implement internal middleware-like execution stages inside that harness adapter.
3. Add configurable tool-source composition (built-in + registry + optional external source) behind typed events.
4. Keep run acceptance/finalization/idempotency in `ChatTurnService`.
5. Preserve our normalized failure and observability paths at service boundary.
6. Optionally support file-based skill/tool definitions as one pluggable source, not the only runtime mode.

## Bottom Line

Deer-Flow is a strong reference for "agent harness as runtime platform" with a serious Harness/App boundary and rich orchestration internals.

For our architecture, the right move is to adopt its composition patterns behind our existing typed, persisted control plane, while keeping file/config-driven implementations as an optional and valid style rather than a replacement for the core guarantees.
