# Hermes Agent Core Pattern: Agent Kernel + Runtime Harness

## Purpose

This document analyzes the core of [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent), with focus on:

- where the actual agent loop lives
- what Hermes treats as its harness/runtime layers
- how that pattern maps to this project's architecture
- what we should adopt, adapt, or avoid

## Reference Project

- Repo: [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent)
- Core loop: [`run_agent.py`](https://github.com/NousResearch/hermes-agent/blob/main/run_agent.py)
- Tool runtime: [`model_tools.py`](https://github.com/NousResearch/hermes-agent/blob/main/model_tools.py), [`tools/registry.py`](https://github.com/NousResearch/hermes-agent/blob/main/tools/registry.py), [`tools/terminal_tool.py`](https://github.com/NousResearch/hermes-agent/blob/main/tools/terminal_tool.py), [`tools/approval.py`](https://github.com/NousResearch/hermes-agent/blob/main/tools/approval.py)
- Provider/runtime: [`hermes_cli/runtime_provider.py`](https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/runtime_provider.py), [`agent/anthropic_adapter.py`](https://github.com/NousResearch/hermes-agent/blob/main/agent/anthropic_adapter.py), [`agent/auxiliary_client.py`](https://github.com/NousResearch/hermes-agent/blob/main/agent/auxiliary_client.py)
- Session persistence: [`hermes_state.py`](https://github.com/NousResearch/hermes-agent/blob/main/hermes_state.py)
- Developer docs: [Architecture](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/architecture.md), [Agent Loop](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/agent-loop.md), [Provider Runtime](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/provider-runtime.md), [Tools Runtime](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/tools-runtime.md)

## Where The Core Agent Is

Hermes' core agent kernel is the `AIAgent` class in `run_agent.py`, especially `run_conversation(...)`.

That function is the orchestration center for:

- message lifecycle and conversation loop control
- API mode/provider call path selection
- tool-call execution (sequential or concurrent)
- retries, compression, and fallback model switching
- persistence/log flushing on all exit paths

In short: Hermes keeps one large runtime kernel that directly coordinates model I/O, tool execution, and reliability behavior.

## Hermes "Harness" Pattern (What Actually Makes It Up)

Hermes does not expose a small typed harness contract like our `ChatHarness`; instead it composes a runtime harness from subsystems around `AIAgent`.

### 1) Provider harness

- `runtime_provider.py` resolves provider/base URL/api key/api mode with explicit->config->env precedence.
- `AIAgent` supports three API modes: `chat_completions`, `codex_responses`, `anthropic_messages`.
- `anthropic_adapter.py` is a protocol adapter that translates message/tool formats and stop reasons.
- `auxiliary_client.py` routes side tasks (compression/vision/search/etc.) through a separate provider resolution chain.

Pattern: provider resolution and protocol normalization are first-class runtime concerns, not route-level logic.

### 2) Tool harness

- `model_tools.py` discovers tools by importing modules; tools self-register at import time.
- `tools/registry.py` provides schema exposure + dispatch as a central registry.
- `AIAgent` decides sequential vs concurrent execution per tool batch.
- `terminal_tool.py` abstracts execution backends (`local`, `docker`, `ssh`, `singularity`, `modal`, `daytona`), PTY, background process support, and task-scoped environment reuse.
- `approval.py` centralizes dangerous-command detection + approval state.

Pattern: the tool runtime is a pluggable execution fabric with centralized safety gates.

### 3) Prompt/context harness

- `AIAgent` builds and caches a session-level system prompt.
- Prompt assembly splits stable cached layers from ephemeral turn-only overlays.
- Compression and prompt-caching logic are integrated into the main loop.

Pattern: prompt lifecycle is treated as stateful runtime infrastructure.

### 4) Persistence harness

- `hermes_state.py` stores sessions/messages/token+cost metadata in SQLite.
- It preserves lineage via `parent_session_id` after compression splits.
- The main loop flushes session state on success/failure/interrupt paths.

Pattern: runtime state durability is directly integrated into execution, not bolted on later.

## Turn Lifecycle (Hermes Core Loop)

At a high level, `run_conversation()` behaves like:

1. initialize turn state, append user message
2. load/build cached system prompt
3. optionally preflight compress if context is already too large
4. build API messages (plus ephemeral layers and prompt cache controls)
5. make API call (prefers interruptible streaming path)
6. normalize response per API mode
7. if tool calls are returned:
8. validate/repair tool calls and args
9. execute tools (sequential or concurrent)
10. append tool results, continue loop
11. else finalize text response
12. persist logs/db/session metrics and return

Reliability behavior is embedded in-loop:

- retries/backoff
- context-length and payload-too-large compression retries
- fallback model activation on specific failure classes
- iteration budget control and budget pressure warnings
- interrupt support across API calls and tool execution

## Mapping To This Project

| Hermes concept | This project equivalent |
| --- | --- |
| `AIAgent.run_conversation()` orchestration kernel | `ChatTurnService.execute_started_turn()` + harness `run_events()` implementations |
| API mode switching and provider runtime resolution | `HarnessRegistry` binding + provider-specific harness adapters |
| Anthropic protocol adapter | `agents/anthropic_agent.py` inside our `ChatHarness` boundary |
| tool schema + dispatch registry | `ChatHarnessEvent` tool-call/tool-result vocabulary and future tool orchestration seam |
| integrated approval for risky terminal commands | service-layer policy + harness-level tool policy (future) |
| session DB with lineage and stats | `persistence/repository.py` + `chat_session_runs` + turn request lifecycle |
| always-persist-on-exit behavior | idempotent turn finalization in `ChatTurnService` and repository finalize methods |

## Could We Replicate This In Our Architecture?

Yes, but as an implementation style behind our harness contract, not as a replacement for our control plane.

A good fit is:

- keep our typed `ChatHarness` contract and `ChatTurnService` lifecycle as the stable control plane
- implement a `hermes_style` harness adapter that internally runs a Hermes-like loop/runtime
- map internal tool/progress/failure outcomes to normalized `ChatHarnessEvent` and `ChatHarnessFailure`
- keep route behavior, idempotent replay, and run-state persistence unchanged

This gives Hermes-style runtime behavior without sacrificing our current reliability boundaries.

## Key Differences And Why They Matter

### 1) Runtime monolith vs typed boundary layers

- Hermes: large runtime kernel owns many concerns end-to-end.
- Ours: app-facing typed boundary (`ChatHarness`) + service/repository split.

Why it matters: our split makes route behavior and lifecycle guarantees easier to test and evolve.

### 2) Dynamic registration vs startup registry binding

- Hermes: tool/provider discovery is highly dynamic at runtime.
- Ours: harness selection is explicit and persisted per chat session.

Why it matters: we trade some runtime flexibility for reproducibility and safer operations.

### 3) Agent-native tool runtime vs web-first turn contract

- Hermes is agent-runtime-first (long sessions, terminal backends, gateway).
- We are web-turn-first (HTMX request/response with deterministic completion semantics).

Why it matters: if we import Hermes-like behavior, we should keep multi-step runtime internals hidden behind one turn outcome and normalized events.

### 4) Broad execution surface area

- Hermes includes shell/runtime backends and approval pathways in core tooling.
- We currently ship chat harnesses and do not expose that execution surface in web routes.

Why it matters: if we add similar tools, policy/approval/audit boundaries must be explicit at service level.

## What We Should Learn From Hermes

1. Centralized provider runtime resolution is worth copying.
2. Protocol adapters per provider (especially Anthropic/OpenAI differences) should stay isolated.
3. Tool runtime should be one registry/dispatch surface, not route-level branching.
4. Interrupt/retry/compression/fallback are better as harness/runtime concerns than UI concerns.
5. Persisted system-prompt snapshots and stable prompt layering improve reproducibility.
6. Session lineage after compression is useful for long-running conversations.

## What We Should Not Copy Directly

1. Do not move idempotency/run-finalization out of `ChatTurnService` into an adapter loop.
2. Do not leak provider/tool-specific failure semantics into routes.
3. Do not make dynamic plugin discovery the only execution path.
4. Do not make filesystem/session artifacts the authoritative lifecycle store.

## Concrete Implementation Path For Our System

If we want Hermes-style runtime behavior in this codebase:

1. Add a new harness key (for example, `hermes_style`) in `HarnessRegistry`.
2. Implement a runtime adapter under `agents/` that:
   - manages provider runtime resolution
   - owns tool registry/dispatch
   - runs a conversation loop internally
   - emits normalized `ChatHarnessEvent` values
3. Keep `ChatTurnService` as the owner of:
   - request lifecycle/idempotency
   - persisted run status
   - failure presentation mapping
4. Add a policy seam for risky tool actions (approval + audit metadata) before exposing terminal/file mutation tools.
5. Keep optional file/plugin-defined tool/provider modules as a supported style, but require them to compile into typed harness events.

This preserves your principle that built-ins are convenience and alternate implementation styles remain possible.

## Summary

Hermes is a strong example of an agent-runtime kernel with layered harness subsystems (provider, tools, prompt, persistence). The main takeaway for this project is to adopt that runtime richness behind our existing typed harness/service boundaries, not to collapse our current architecture into a single runtime monolith.
