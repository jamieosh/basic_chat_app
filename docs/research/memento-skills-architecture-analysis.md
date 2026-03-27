# Memento-Skills Architecture: Skill-Centric Agent Kernel + Capability Store

## Purpose

This document analyzes [`Memento-Teams/Memento-Skills`](https://github.com/Memento-Teams/Memento-Skills) with focus on:

- where the core agent loop lives
- what acts as its harness/runtime boundary
- how the pattern maps to our architecture
- what we should adopt, adapt, or avoid

## Reference Project

- Repository: [`Memento-Teams/Memento-Skills`](https://github.com/Memento-Teams/Memento-Skills)
- Core architecture files:
  - [`README.md`](https://github.com/Memento-Teams/Memento-Skills/blob/main/README.md)
  - [`core/memento_s/agent.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/memento_s/agent.py)
  - [`core/memento_s/phases/intent.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/memento_s/phases/intent.py)
  - [`core/memento_s/phases/planning.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/memento_s/phases/planning.py)
  - [`core/memento_s/phases/execution.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/memento_s/phases/execution.py)
  - [`core/memento_s/phases/reflection.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/memento_s/phases/reflection.py)
  - [`core/memento_s/phases/state.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/memento_s/phases/state.py)
  - [`core/memento_s/tools.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/memento_s/tools.py)
  - [`core/memento_s/policies/builtin_policies.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/memento_s/policies/builtin_policies.py)
  - [`core/memento_s/stream_output.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/memento_s/stream_output.py)
  - [`core/context/manager.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/context/manager.py)
  - [`core/context/compaction.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/context/compaction.py)
  - [`core/skill/gateway.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/skill/gateway.py)
  - [`core/skill/provider.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/skill/provider.py)
  - [`core/skill/retrieval/multi_recall.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/skill/retrieval/multi_recall.py)
  - [`core/skill/execution/executor.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/skill/execution/executor.py)
  - [`core/skill/store/library.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/skill/store/library.py)
  - [`core/manager/session_manager.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/manager/session_manager.py)
  - [`core/manager/conversation_manager.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/core/manager/conversation_manager.py)
  - [`cli/commands/agent.py`](https://github.com/Memento-Teams/Memento-Skills/blob/main/cli/commands/agent.py)

## What Memento-Skills Is

Memento-Skills is a full agent runtime, not just a prompt/tool wrapper. It is organized around skills as first-class capability units, with a layered stack for:

- agent orchestration (phases + run state)
- skill discovery/search/execute contracts
- skill storage and retrieval (local plus cloud catalog)
- execution sandbox and tool policies
- session/conversation persistence
- event-stream output for CLI/GUI surfaces

Its center of gravity is skill routing and skill execution, not provider-specific chat abstraction.

## Where The Core Agent Loop Lives

The core loop is `MementoSAgent.reply_stream()` in `core/memento_s/agent.py`.

It orchestrates:

1. Initialization (`SkillProvider`, `ToolDispatcher`, profile, per-session context managers)
2. Intent recognition (`direct`, `agentic`, `interrupt`)
3. Route:
   - `direct` / `interrupt` -> direct streaming response
   - `agentic` -> planning -> execution -> reflection
4. Structured event emission (`RUN_STARTED`, `PLAN_GENERATED`, `TOOL_CALL_*`, `RUN_FINISHED`, etc.)

The heavy execution logic is delegated to phase modules rather than embedded in one large function.

## Harness Pattern (How It Is Structured)

### 1) Phase-based orchestration kernel

`phases/` splits execution into explicit stage functions and state:

- `recognize_intent`
- `generate_plan`
- `run_plan_execution`
- `reflect`
- `AgentRunState` (mutable run state, retries, blocked skills, duplicate tool-call tracking)

`execution.py` uses a hierarchical loop:

- outer loop over plan steps
- inner bounded ReAct-style loop per step
- reflection only at step boundaries
- optional replanning with limits

### 2) Narrow agent tool interface, broad skill internals

Agent-exposed tools are intentionally narrow:

- `search_skill`
- `execute_skill`

This is important. The model does not directly see every builtin tool at top level. It mainly selects and runs skills, while each skill can internally use builtin tools via `SkillExecutor`.

### 3) Skill contract boundary is explicit

`core/skill/gateway.py` defines a strict contract:

- `discover()`
- `search(query, k, cloud_only)`
- `execute(skill_name, params, options)`

with typed DTOs (`SkillManifest`, `SkillExecutionResponse`, status/error enums). This is effectively its harness contract between agent orchestration and capability runtime.

### 4) Skill provider layers retrieval, download, execution, and governance

`SkillProvider` in `core/skill/provider.py` composes:

- local store/cache
- recall/reranking (`MultiRecall`)
- optional cloud catalog search/download
- dependency/API-key checks
- execution via `SkillExecutor`

Notable behavior:

- local-first search/rerank
- on-demand cloud skill download and add to local library
- auto-install missing dependencies (sandbox-mediated)

### 5) Context engine is first-class runtime infrastructure

`ContextManager` owns:

- token budgeting
- history loading with budget-aware truncation
- system prompt assembly
- auto-compress and compact flows
- scratchpad archival on compaction

This is similar to a dedicated context subsystem rather than ad hoc prompt concatenation.

### 6) Event stream as runtime contract

`stream_output.py` defines a stable event vocabulary and accumulator pipeline. `reply_stream` emits events consumed by CLI/GUI and persistence sinks.

This gives a clear execution telemetry surface, even when UI surfaces differ.

## "Self-Evolving" Claim vs Implemented Runtime

The README positions a `Read -> Execute -> Reflect -> Write` loop. In code, read/execute/reflect are clearly implemented in the core runtime.

The write-back/evolution part is partly present as capability and tooling (skill store add/remove/update paths, skill creator tooling, disk-backed skill library), but it is not the dominant default control loop in `reply_stream` today.

Implication: strong skill runtime exists now; fully automatic continuous skill mutation appears more like a supported direction than the single enforced loop.

## Mapping To Our Architecture

| Memento-Skills concept | Our equivalent |
| --- | --- |
| `MementoSAgent.reply_stream()` orchestrator | `ChatTurnService.execute_started_turn()` + harness `run_events()` |
| phase modules (`intent/plan/execute/reflect`) | harness-internal orchestration plus service lifecycle |
| `SkillGateway` contract | `ChatHarness` contract |
| `SkillProvider` runtime composition | provider harness adapters + future tool orchestration seam |
| `search_skill` / `execute_skill` agent-facing tools | normalized tool-call/tool-result events |
| `ContextManager` budget/compaction | harness-owned context builders + future compaction extensions |
| AG-UI event stream | `ChatHarnessEvent` stream with deterministic final assistant render |
| session/conversation services | `chat_sessions`, `messages`, `chat_session_runs`, turn requests in SQLite |

## Could We Implement This Pattern In Our System?

Yes, as a harness implementation style behind our current control plane.

Feasible approach:

1. Keep our `ChatTurnService` and persistence lifecycle as authority.
2. Add an optional skill-centric harness adapter that internally runs phased orchestration.
3. Keep top-level model tool exposure narrow (`search_skill`/`execute_skill` style), with richer internal skill execution runtime.
4. Map all runtime outputs to normalized `ChatHarnessEvent` and `ChatHarnessFailure`.
5. Keep our route and idempotent replay behavior unchanged.

This aligns with the principle that built-ins are convenience, and file-based implementations should remain valid.

## Key Differences That Matter

### 1) Primary abstraction

- Memento-Skills: skills are the primary abstraction.
- Ours: harness contract plus run lifecycle are the primary abstraction.

Why it matters: our persistence and replay guarantees should remain service-owned.

### 2) Dynamic capability loading

- Memento-Skills supports cloud catalog lookup and on-demand skill download.
- Ours uses explicit harness binding and stable chat-level provider ownership.

Why it matters: dynamic loading is useful, but must be policy-gated and auditable in our system.

### 3) Output contract

- Memento-Skills is event-stream-first across CLI/GUI.
- Our current web flow is deterministic final-response-first (with event vocabulary available internally).

Why it matters: we can adopt richer internal events without changing user-facing HTMX behavior.

### 4) State distribution

- Memento-Skills state spans DB, local skill filesystem, and scratchpad/context files.
- Ours is currently more centralized around DB-backed turn/run lifecycle.

Why it matters: we should keep one authoritative lifecycle source, and treat sidecar files as auxiliary artifacts.

## What We Should Learn

1. A phase module split (`intent/plan/execute/reflect`) keeps agent logic maintainable.
2. A narrow top-level agent tool interface scales better than exposing a large raw tool surface.
3. A formal capability gateway contract is valuable for runtime swapability.
4. Context management deserves a dedicated subsystem with explicit token and compaction policy.
5. Streaming event vocabularies are useful as internal contracts even when UI is not streaming-first.

## What We Should Avoid Copying Blindly

1. Do not move lifecycle authority from `ChatTurnService` and persisted run records into harness-internal state.
2. Do not allow ungoverned dynamic skill download/execute paths in production.
3. Do not rely on loosely coupled sidecar files as authoritative run truth.
4. Do not blur the line between "supports skill evolution" and "guarantees reliable automatic skill mutation."

## Practical Path For Our System

1. Add an optional `skill_runtime` harness key in `HarnessRegistry`.
2. Implement phased execution internals in that adapter using our typed events.
3. Add a `SkillGateway`-like interface inside `agents/` for local file-backed capabilities.
4. Add policy-gated optional external capability catalog integration.
5. Keep finalization, idempotency, and failure shaping in `services/chat_turns.py`.
6. Treat capability files as implementation assets, while preserving typed harness boundaries as the contract.

## Bottom Line

Memento-Skills is a strong reference for a skill-centric agent runtime with explicit phase orchestration and capability contracts.

For our architecture, the right move is to borrow this as an optional harness implementation style behind our existing typed, persisted control plane, not as a replacement for that control plane.
