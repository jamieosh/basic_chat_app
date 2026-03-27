# Harness-Style Agent Pattern: Fit With This Project

## Purpose

This document describes the agent pattern used by [`wedow/harness`](https://github.com/wedow/harness), compares it with this project's current architecture, and explains how we could support a similar file-driven implementation as an **optional runtime style**.

The key design goal is:

- keep this project's typed/persisted harness path as the default and reliability baseline
- allow a harness-style file/plugin execution mode for teams who want that flexibility
- treat our built-in adapters and services as convenience, not a mandatory implementation style

## Reference Project

- External reference: [`wedow/harness`](https://github.com/wedow/harness)
- Core docs:
  - [`README.md`](https://github.com/wedow/harness/blob/master/README.md)
  - [`docs/PROTOCOLS.md`](https://github.com/wedow/harness/blob/master/docs/PROTOCOLS.md)
  - [`bin/harness`](https://github.com/wedow/harness/blob/master/bin/harness)

## What Pattern `wedow/harness` Uses For An Agent

`wedow/harness` models an agent as a **minimal state-following kernel** plus **filesystem-discovered plugins**.

### Core Pattern

1. A tiny loop follows `next_state` values.
2. Each state dispatches ordered hook executables.
3. Hooks pass JSON through stdin/stdout pipelines.
4. Provider-specific logic is implemented in provider plugins.
5. Tool execution is implemented as tool plugins.
6. Session state is persisted as markdown files on disk.

The practical shape is:

- kernel: state runner + source discovery + command dispatch
- protocols: commands, providers, tools, hooks
- storage: filesystem session/message files
- extensibility: local overrides win by basename and path precedence

### Why It Feels Powerful

- very low ceremony for extension
- easy local/project overrides
- runtime hot-swappability for hooks/tools
- provider behavior remains outside the core loop

## How This Project Currently Models Agent Execution

This project already has a strong harness boundary, but with typed Python contracts and SQLite-backed lifecycle.

Primary components:

- `agents/chat_harness.py`
  - normalized request/result/event/failure contract
- `agents/harness_registry.py`
  - stable key-based harness binding resolution
- `services/chat_turns.py`
  - idempotent turn lifecycle, failure finalization, observability
- `persistence/repository.py`
  - chat/turn/run records, conflict-aware replay behavior
- `persistence/db.py`
  - schema/bootstrap for persisted run identity and status

## Concept Mapping: Harness Pattern vs This Project

| Harness concept | This project equivalent |
| --- | --- |
| state loop driven by `next_state` | `run_events()` + terminal collection/failure handling |
| provider plugin | provider-specific harness adapter (`openai`, `anthropic`) |
| canonical message format | normalized `ChatHarnessRequest` / `ConversationTurn` + persisted chat messages |
| tool call/result events | `ChatHarnessEvent` (`tool_call`, `tool_result`) contract surface |
| session files | SQLite chat/turn/run records |
| plugin discovery precedence | registry + configuration binding model |
| hook error stage | normalized `ChatHarnessFailure` + service-layer failure presentation |

## Could We Replicate Their Pattern Here?

Yes. We can replicate the behavior pattern (stateful, pluggable, provider-agnostic orchestration) in this architecture.

But we should not replace the current reliability boundaries. The right model is a **dual-path runtime**:

1. **Typed harness path (default)**
   - current adapters, context builders, and service lifecycle
2. **File-protocol path (optional)**
   - harness-compatible hooks/tools/providers loaded from filesystem
   - adapted into the same typed `ChatHarness` interface

## Proposed Implementation Shape For Optional File-Based Mode

### 1) Add a new harness adapter key

Introduce a new registered harness (example key: `fileflow`) that still implements `ChatHarness` and emits normalized events.

### 2) Add a file-protocol runtime adapter

Add an internal runtime that can:

- discover configured plugin roots
- resolve hooks/tools/providers by precedence
- execute hook pipelines in ordered stages
- map JSON stage output into typed `ChatHarnessEvent` objects

### 3) Keep SQLite as source-of-truth lifecycle

Even in file-protocol mode:

- request acceptance and idempotency remain in `ChatTurnService` / repository
- run status remains in `chat_session_runs` / `chat_turn_requests`
- route and HTMX behavior remains unchanged

### 4) Support optional file-state mirrors (if desired)

If teams want harness-style files, allow an optional mirror layer:

- write canonical markdown/json artifacts for debugging and compatibility
- do not make these files authoritative for lifecycle correctness

### 5) Preserve provider decoupling

Provider formatting/parsing logic should remain provider-owned, whether implemented as Python adapters or file plugins.

### 6) Preserve typed failure and observability

All file-protocol failures should map to `ChatHarnessFailure` codes so current UI/status behavior remains consistent.

## Key Differences And Why They Matter

### Typed contracts vs shell JSON pipelines

- This project: compile-time-ish structure and invariants through dataclasses and explicit events.
- Harness style: dynamic JSON contracts at runtime.

Why keep typed contracts: safer refactors, easier tests, clearer failure boundaries.

### SQLite lifecycle vs filesystem-only state

- This project: transaction-safe idempotency, replay semantics, and run status.
- Harness style: flexible artifacts, but weaker lifecycle guarantees by default.

Why keep SQLite lifecycle: required for duplicate request handling and conflict-aware finalization.

### Stable registry binding vs per-loop discovery

- This project: deterministic harness binding per chat/run.
- Harness style: dynamic redetect each loop.

Why keep stable binding: predictable behavior, reproducibility, and easier operations.

### Built-in security model vs ad hoc hook gating

- Harness style supports approval hooks.
- This project can support equivalent gates, but should enforce them through normalized policy points and observability.

Why: consistent policy enforcement and auditable run outcomes.

## Design Principle: Convenience, Not Constraint

Target principle:

- the system should allow multiple implementation styles behind `ChatHarness`
- the shipped Python adapters/services remain the easiest path
- advanced users can implement filesystem/plugin-driven behavior where needed
- both paths must converge into the same typed app-facing contract

In other words, file-driven execution should be a first-class **implementation option**, not a separate app model.

## Practical Guardrails If We Add File-Driven Mode

- keep one canonical app-facing contract: `ChatHarness`
- keep one canonical lifecycle authority: repository + service layer
- make plugin execution opt-in per harness key
- require explicit safety/approval policy for tool execution
- add dedicated tests for protocol mapping, failure normalization, and replay/idempotency interactions

## Summary

`wedow/harness` is a strong reference for plugin-first agent orchestration.

This project can support that style without giving up current reliability guarantees by:

- preserving typed contracts and persisted lifecycle as the control plane
- adding an optional file-protocol execution adapter as a data-plane/runtime choice
- ensuring both paths converge to the same normalized events, failure codes, and route behavior
