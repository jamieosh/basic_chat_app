# Water Framework Architecture: What It Is and What We Can Learn

## Purpose

This document analyzes [`manthanguptaa/water`](https://github.com/manthanguptaa/water) as an agent-harness framework and maps its architecture to this project's design direction.

Main question: what should we learn from it for our own system?

## Reference

- Repository: [`manthanguptaa/water`](https://github.com/manthanguptaa/water)
- Core read points:
  - [`README.md`](https://github.com/manthanguptaa/water/blob/main/README.md)
  - [`water/core/flow.py`](https://github.com/manthanguptaa/water/blob/main/water/core/flow.py)
  - [`water/core/engine.py`](https://github.com/manthanguptaa/water/blob/main/water/core/engine.py)
  - [`water/core/task.py`](https://github.com/manthanguptaa/water/blob/main/water/core/task.py)
  - [`water/agents/llm.py`](https://github.com/manthanguptaa/water/blob/main/water/agents/llm.py)
  - [`water/agents/tools.py`](https://github.com/manthanguptaa/water/blob/main/water/agents/tools.py)
  - [`water/agents/react.py`](https://github.com/manthanguptaa/water/blob/main/water/agents/react.py)
  - [`water/agents/fallback.py`](https://github.com/manthanguptaa/water/blob/main/water/agents/fallback.py)
  - [`water/agents/approval.py`](https://github.com/manthanguptaa/water/blob/main/water/agents/approval.py)
  - [`water/agents/sandbox.py`](https://github.com/manthanguptaa/water/blob/main/water/agents/sandbox.py)
  - [`water/guardrails/base.py`](https://github.com/manthanguptaa/water/blob/main/water/guardrails/base.py)
  - [`water/guardrails/retry.py`](https://github.com/manthanguptaa/water/blob/main/water/guardrails/retry.py)
  - [`water/observability/trace.py`](https://github.com/manthanguptaa/water/blob/main/water/observability/trace.py)
  - [`water/observability/telemetry.py`](https://github.com/manthanguptaa/water/blob/main/water/observability/telemetry.py)

## What Water Actually Is

Water is not an "agent" implementation. It is a broad workflow/orchestration runtime that can host agent behavior as one workload type.

Its center of gravity is:

- a typed `Task` unit (`input_schema`, `output_schema`, `execute`, retry/timeout/rate-limit/circuit-breaker hooks)
- a composable `Flow` graph DSL
- an `ExecutionEngine` that executes node types (`sequential`, `parallel`, `branch`, `loop`, `map`, `dag`, `try_catch`, `agentic_loop`)

Agent features are implemented as modules on top of that generic runtime.

## Architecture Pattern

### 1) Execution graph first

`Flow` builds an explicit execution graph and then `register()` freezes it for execution.

Notable behavior in `Flow`/`ExecutionEngine`:

- fluent graph composition (`then`, `parallel`, `branch`, `loop`, `map`, `dag`, `try_catch`, `agentic_loop`)
- runtime dispatch by node type inside one engine
- optional storage-backed pause/stop/resume
- optional replay/checkpoint hooks
- middleware/hooks/events/telemetry passed through the execution path

Pattern: one generic execution core with many node semantics.

### 2) Agent behavior as task/node specializations

Agent pieces are wrappers around task execution rather than a separate app model:

- `create_agent_task` for prompt+provider calls
- `Tool` / `Toolkit` / `ToolExecutor` for tool-call loops
- `create_agentic_task` and `agentic_loop` for ReAct-style model-controlled loops
- `FallbackChain` for provider failover strategies
- `AgentOrchestrator` for multi-agent coordination patterns

Pattern: agent orchestration is embedded in the same generic flow runtime.

### 3) Safety/control primitives are first-class runtime modules

Water makes approval, sandboxing, and guardrails first-class modules:

- approval gates with risk levels and timeout policy
- sandbox backends (`InMemory`, `Subprocess`, `Docker`) for untrusted code execution
- guardrails with chainable actions and retry-with-feedback loops

Pattern: safety is implemented as reusable execution primitives, not as one-off route logic.

### 4) Observability and resilience are built into the runtime seams

Engine/task execution has explicit hooks for:

- task/flow lifecycle events
- per-span tracing and optional OpenTelemetry
- retry/backoff and task-level timeout
- checkpoint/cache/circuit-breaker/DLQ patterns

Pattern: non-functional concerns are integrated at the orchestration layer.

## Comparison With Our Architecture

Our current architecture is intentionally narrower and app-specific:

- `ChatHarness` is the stable app-facing contract.
- `HarnessRegistry` resolves stable provider bindings.
- `ChatTurnService` owns idempotent request lifecycle and normalized failure/result shaping.
- SQLite persistence is a mandatory control-plane authority for turn/run status.

Water differs by being a general runtime platform where chat/agent behavior is one use case among many.

### Concept mapping

| Water concept | Our equivalent |
| --- | --- |
| `Task` with typed I/O + execution policy | `ChatHarnessRequest`/`ChatHarnessResult` + service lifecycle policies |
| `Flow` graph | currently implicit per-turn service flow + harness adapter logic |
| `ExecutionEngine` node dispatcher | harness `run_events()` implementation + service-level orchestration |
| `agentic_loop` node | future tool-orchestration path inside harness contract |
| Guardrail/approval/sandbox modules | future harness policy and tool control seams |
| Pause/resume/checkpoint/replay runtime | early run/session groundwork, not yet full execution replay |

## What We Should Learn

1. Keep orchestration concerns centralized.
2. Keep safety/guardrails/tool control as first-class runtime seams.
3. Keep provider abstractions thin and swappable.
4. Keep observability wired at execution boundaries, not bolted on.
5. Consider a graph-style internal execution abstraction for complex multi-step harnesses.

## What We Should Not Copy Blindly

1. Do not replace our turn/run persistence control plane with an optional runtime-only state model.
2. Do not expand to a broad generic runtime surface unless product scope requires it.
3. Do not expose a very large default capability surface to the model by default.

## Practical Fit For Our System

A good way to apply Water-like ideas without destabilizing our architecture:

1. Keep existing `ChatHarness` + `ChatTurnService` boundaries as the source of truth.
2. Add optional internal "execution graph" orchestration inside harness adapters for advanced agent behaviors.
3. Add first-class guardrail/approval hooks around future tool execution surfaces.
4. Expand run metadata to support replay-friendly debugging for multi-step harness runs.
5. Add dynamic tool selection policy (similar spirit to Water's tool selector) when tool count grows.

## Bottom Line

Yes, there is useful signal here.

Water reinforces a strong architectural principle: treat agent behavior as orchestrated execution with explicit reliability, safety, and observability seams. For us, the right move is to borrow those runtime patterns behind our existing typed harness/service control plane, not to replace that control plane.
