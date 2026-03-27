# Vision: Lightweight Python Agent Workbench

## Mission

Build a lightweight, Python-first workbench for running, supervising, and comparing scoped agents through a simple web interface and other future surfaces.

The project should remain usable out of the box as a personal or small-team tool while staying easy to fork for more focused use cases.

## Product Framing

This repository is no longer best understood as only a chat app with an LLM behind it.

It is a workbench:

- chat is the first surface, not the whole product
- the runtime behind that surface should be replaceable, inspectable, and not assumed to be native
- memory, tools, and model behavior should be experiment-friendly
- the default path should stay simple even if the architecture grows more capable

The long-term shape is a workbench over runtimes.

Some runtimes may be native to this repository. Others may be external or federated systems that the workbench can connect to and present through a consistent session-oriented user experience.

## Intended Users

- Solo Python developers exploring models, prompts, tools, memory, and agent behavior.
- Small teams that want a usable local-first agent workbench without adopting a large platform.
- Fork maintainers who want a clean base for a focused team chat or agent-driven application.

## Core Beliefs

- Python remains the center of gravity.
- The web UI should stay server-first and minimal-JavaScript by default.
- Chat is a valuable interaction pattern, but not the architectural boundary.
- The important boundary is between product surfaces and the runtime systems behind them.
- A session is richer than a transcript. It can later carry scope, agent identity, tools, memory policy, artifacts, and execution history.
- A run is a distinct execution inside a session, not just "the next message."
- An agent is a reusable behavior package, not just a model name.
- A harness is an execution adapter boundary, not the whole meaning of an agent.
- Multiple concurrent scoped agents are a normal use case, especially for personal coding and research workflows.
- Inspectability matters. Traces, events, and explicit boundaries are more valuable than hidden magic.
- Open standards should be used where they help, but the project should not depend on every new standard to be useful.

See [`plans/TERMINOLOGY.md`](/Users/jamie/Development/basic_chat_app/plans/TERMINOLOGY.md) for the working glossary and user-experience framing.

## Reliability Baseline (Plain English)

- Reliability comes from typed contracts plus persisted lifecycle records.
- Typed contracts mean key objects have defined fields, such as run requests, run events, and failures.
- Persisted lifecycle means run state changes are written to the database as they happen, such as accepted, started, completed, or failed.
- The database lifecycle record is the source of truth when logs, retries, or duplicate sends disagree.
- Optional runtime styles are welcome, but they must map back into the same typed contract and lifecycle truth.

## Always-Simple Commitments

- The default app must remain runnable and understandable without extra services.
- The core send flow must stay easy to follow.
- New capability should enter behind a small number of explicit seams.
- Contributors should be able to change model/runtime behavior without rewriting the UI.
- The project should stay fork-friendly rather than turning into a large hosted platform by default.

## Tool Strategy (Plain English)

- Start with a small default tool set so the model is not overloaded.
- Expose more tools only when needed for the current run.
- Track tool usage per run so we can see repeated failure patterns, latency, and retries.
- When the same generic tool pattern repeats, replace it with a simpler specialized tool.
- Keep high-ceiling tools available for flexibility when needed.
- Keep low-floor tools available for reliability and speed in common tasks.

## Safety And Policy (Plain English)

- Tool execution policy should be explicit, not implied.
- Risky actions should have clear approval rules before they run.
- Guardrails and audit metadata should be part of runtime behavior, not route hacks.
- Route handlers should stay simple and should not become policy engines.

## Model-Upgrade Audit Rule

- Harness design is not fixed forever.
- Each major model upgrade should trigger a quick audit of harness complexity.
- Keep components that provide measurable value.
- Remove non-load-bearing parts that add cost or confusion.

## What This Project Is Becoming

The intended long-term shape is:

- a lightweight web workbench for humans
- over a minimal runtime contract layer
- with a small control-plane layer for sessions, runs, approvals, and scope

That runtime contract should be able to support:

- native runtimes implemented in this repository
- provider-backed harness adapters
- external or federated agent runtime systems when that is a good fit

The control plane is important, but it starts small. Its first job is to support one person or a small team running multiple scoped agents safely and coherently. It is not an excuse to build a full enterprise orchestration platform from day one.

## In Scope

- A usable default workbench with a clean web UI.
- Clear boundaries between UI, runtime, and control-plane concerns.
- Experiments with multiple models, memory approaches, and tool capabilities.
- Session-level behaviors such as compare, fork, replay, inspect, and resume.
- Support for more than one runtime shape, as long as the workbench contract stays coherent.
- Personal and small-team workflows involving more than one agent at a time.

## Out Of Scope

- Becoming a general-purpose hosted agent platform.
- Recreating every feature of large harnesses or research frameworks.
- Building a full "Slack for agents" product as the primary target.
- Treating multi-channel messaging integrations as a baseline requirement.
- Forcing a specific framework or protocol to define the architecture.
- Enterprise-scale security, governance, and operations as the default local setup.

## Repo Strategy

- Keep one repository for now.
- Create strong internal boundaries before considering a repo split.
- Only split the harness/runtime into a separate partner repo once the boundary is stable, proven, and useful across more than one surface.

## Decision Filter

A proposed change is aligned if it:

- preserves a usable default workbench
- preserves typed contracts and persisted lifecycle as the reliability baseline
- strengthens the boundary between UI and runtime
- improves experimentation with models, memory, tools, or workflows
- improves tool policy and observability without forcing all tools on by default
- keeps terminology clear across session, run, transcript, agent, and runtime
- supports inspectability and explicit control
- avoids forcing platform-scale complexity into the default path
