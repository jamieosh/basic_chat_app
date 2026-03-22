# Vision: Lightweight Python Agent Workbench

## Mission

Build a lightweight, Python-first workbench for running, supervising, and comparing scoped agents through a simple web interface and other future surfaces.

The project should remain usable out of the box as a personal or small-team tool while staying easy to fork for more focused use cases.

## Product Framing

This repository is no longer best understood as only a chat app with an LLM behind it.

It is a workbench:

- chat is the first surface, not the whole product
- the runtime behind that surface should be replaceable and inspectable
- memory, tools, and model behavior should be experiment-friendly
- the default path should stay simple even if the architecture grows more capable

## Intended Users

- Solo Python developers exploring models, prompts, tools, memory, and agent behavior.
- Small teams that want a usable local-first agent workbench without adopting a large platform.
- Fork maintainers who want a clean base for a focused team chat or agent-driven application.

## Core Beliefs

- Python remains the center of gravity.
- The web UI should stay server-first and minimal-JavaScript by default.
- Chat is a valuable interaction pattern, but not the architectural boundary.
- The important boundary is between product surfaces and the agent runtime behind them.
- A session is richer than a transcript. It can later carry scope, tools, memory policy, artifacts, and execution history.
- Multiple concurrent scoped agents are a normal use case, especially for personal coding and research workflows.
- Inspectability matters. Traces, events, and explicit boundaries are more valuable than hidden magic.
- Open standards should be used where they help, but the project should not depend on every new standard to be useful.

## Always-Simple Commitments

- The default app must remain runnable and understandable without extra services.
- The core send flow must stay easy to follow.
- New capability should enter behind a small number of explicit seams.
- Contributors should be able to change model/runtime behavior without rewriting the UI.
- The project should stay fork-friendly rather than turning into a large hosted platform by default.

## What This Project Is Becoming

The intended long-term shape is:

- a lightweight web workbench for humans
- over a minimal agent harness/runtime layer
- with a small control-plane layer for sessions, runs, approvals, and scope

The control plane is important, but it starts small. Its first job is to support one person or a small team running multiple scoped agents safely and coherently. It is not an excuse to build a full enterprise orchestration platform from day one.

## In Scope

- A usable default workbench with a clean web UI.
- Clear boundaries between UI, runtime/harness, and control-plane concerns.
- Experiments with multiple models, memory approaches, and tool capabilities.
- Session-level behaviors such as compare, fork, replay, inspect, and resume.
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
- strengthens the boundary between UI and runtime
- improves experimentation with models, memory, tools, or workflows
- supports inspectability and explicit control
- avoids forcing platform-scale complexity into the default path
