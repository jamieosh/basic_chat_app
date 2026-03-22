# Design Direction

This document explains the architectural direction of the project at the product and systems-thinking level.

It is intentionally not an implementation guide. It exists to explain how we think about the shape of the project, what boundaries matter, and what we are choosing to pursue or avoid.

## Why The Direction Is Changing

The project started as a lightweight web chat UI for experimenting with different models and agent-like capabilities such as memory and tool use.

That original idea still matters, but the surrounding ecosystem has changed.

The strongest recent signal is that chat is no longer the real architectural boundary. Modern harnesses and agent systems increasingly separate:

- the human-facing surface
- the runtime that executes the agent loop
- the control layer that owns sessions, routing, approvals, and longer-lived execution

That does not mean this project should become a giant agent platform. It means the architecture should stop treating the web chat as the center of the system.

## The Core Product Idea

The product is best understood as a lightweight Python agent workbench.

That means:

- the web UI is for humans to interact with, compare, inspect, and steer agents
- chat is the first interaction surface, not the only one
- the runtime behind the UI should be replaceable and inspectable
- the project should support more than one active scoped agent without assuming a large hosted platform

The main use case is not "one immortal agent that lives everywhere." It is closer to "one person or small team running several scoped agent sessions across projects and tasks."

## The Main Architectural Stance

### 1. Chat Is A Surface, Not The System

The system should not be modeled around a single linear transcript.

A transcript is one important record, but the more durable object is an agent session. Over time that session may include:

- transcript history
- runtime or harness identity
- scope and permissions
- memory policy
- tools or skills available
- artifacts and outputs
- execution events and approvals

This is the most important conceptual shift in the project.

### 2. UI And Runtime Must Be Separate Concerns

The web server should not own model-specific behavior or become the de facto harness.

Instead:

- the UI presents and controls sessions
- the runtime or harness executes agent behavior
- a small control layer coordinates the lifecycle between them

This separation keeps the frontend simple while making the backend more adaptable.

### 3. A Minimal Control Plane Is Worth Building

For this project, "control plane" does not mean a large enterprise system.

It means the smallest layer that can responsibly own:

- session identity and lifecycle
- agent scope and runtime binding
- runs and event history
- approvals, interrupts, and resumability
- eventual background or asynchronous work

The first target is personal use and small-team use, where multiple concurrent agents are already normal. This is closer to "mission control for my own agents" than to organization-wide workflow automation.

### 4. Complexity Should Move Behind Boundaries, Not Into The Default UX

The default experience must remain easy to run and easy to understand.

That means:

- server-rendered web UI remains a good default
- minimal JavaScript remains a good default
- heavy orchestration, background execution, or multi-agent behavior should not leak into the basic send flow unless deliberately enabled

The architecture can grow more capable while the default product stays calm.

## What We Are Choosing To Build

### A Workbench Rather Than A Platform

We are choosing a workbench posture:

- strong local and small-team usability
- explicit extension points
- inspectable behavior
- room for experiments with models, memory, and tools

We are not choosing to optimize first for multi-tenant hosting, broad channel distribution, or abstract platform completeness.

### One Repository With Strong Internal Boundaries

We are choosing to keep one repo for now.

The reason is simple: the architecture boundary is still being learned. Splitting into a separate partner repo too early would force premature packaging and interface design.

The intended dependency direction is:

- workbench UI depends on gateway/control and runtime-facing contracts
- gateway/control depends on runtime-facing contracts
- runtime and harness code do not depend on the web app

If that boundary becomes stable and useful across several surfaces, a later repo split can make sense. Not before.

### A Minimal Harness Core

The harness layer should stay small and explicit.

Its purpose is to define the common runtime contract for:

- invoking a session
- assembling context
- exposing capabilities
- emitting normalized events
- representing failures and observability coherently

It should not become a giant framework by accident.

### A Richer Session Model

The project should move away from treating "chat thread" as the only durable unit.

A session should be able to carry richer concepts over time, including:

- which runtime or harness it is bound to
- what scope it has
- what memory policy applies
- what artifacts belong to it
- what approvals or interrupts occurred

This does not require implementation complexity everywhere at once. It simply means the conceptual model must leave room for it.

### Memory As Several Different Things

"Memory" should not be treated as one generic feature.

The design should keep the following ideas distinct:

- canonical transcript history
- working context assembled for the current run
- durable user or project memory
- retrieval against external knowledge stores

Separating these concepts makes experimentation cleaner and prevents the UI layer from becoming responsible for memory policy.

### Open Standards Where Useful

The ecosystem is converging around a few useful standards and conventions:

- [`MCP`](https://modelcontextprotocol.io/)
- [`AGENTS.md`](https://agents.md/)
- [`Agent Skills`](https://github.com/agentskills)
- [`Agent Client Protocol`](https://agentclientprotocol.com/protocol/schema)
- [`A2A`](https://a2a.plus/docs)

We should be compatible with useful standards where it improves portability or interoperability, but we should not turn this project into a standards-compliance exercise.

## What We Are Explicitly Not Choosing

### Not A Full Omnichannel Agent Gateway

Projects like [OpenClaw](https://docs.openclaw.ai/index) are useful inspiration because they clearly separate a gateway, control UI, and channels.

We are adopting the lesson about separation.

We are not adopting the product goal of becoming a broad multi-channel agent gateway now.

### Not A Giant Batteries-Included Super Harness

[DeerFlow](https://github.com/bytedance/deer-flow) is valuable because it shows a real internal split between harness code and app code, and because it models sessions as richer than plain chat.

We are adopting the boundary lesson.

We are not adopting the "super agent harness" ambition as the baseline for this project.

### Not Framework-Led Product Design

Frameworks such as [LangGraph](https://www.langchain.com/langgraph), [Pydantic AI](https://ai.pydantic.dev/), or other agent stacks can be useful implementation tools.

They should not define the product boundary.

The project should be able to use one, many, or none of them behind the runtime layer.

### Not "Slack For Agents" As The Immediate Goal

The idea of managing many agents across people and teams is directionally real.

But that is a future consequence of building the right session and control model, not the current product target.

The near-term target remains personal and small-team workbench use.

### Not Hidden Magic

The system should prefer explicit boundaries, inspectable traces, and understandable defaults over silently injected behavior.

Predictability matters more than appearing clever.

## How We Think About Layers

### Workbench UI

The workbench is the human-facing layer.

Its job is to let people:

- chat
- inspect runs
- compare outputs
- fork and replay work
- review artifacts
- control approvals and interruptions

It should remain lightweight and readable.

### Harness Or Runtime Layer

The runtime layer is responsible for agent execution behavior.

Its job is to own:

- model interaction
- context assembly
- tool and skill orchestration
- memory policy used at execution time
- event production

It is not the UI and it should not be tied to any single transport.

### Control Layer

The control layer sits between surfaces and runtimes.

Its job is to own:

- sessions
- runs
- bindings between sessions and runtimes
- execution status
- approvals and resumability
- future background execution

This layer becomes more important as the project moves from "chat app" to "multi-session workbench."

## External Influences

The following projects matter because they illuminate specific decisions:

- [OpenClaw](https://docs.openclaw.ai/index)
  - Clear split between gateway, sessions, channels, and control UI.
  - Good evidence that chat clients should sit on top of a longer-lived agent layer.
- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
  - Strong signal toward a minimal core with explicit memory, skills, and MCP support.
  - Useful reminder that portability and migration between runtimes matter.
- [pi-ai / pi-agent-core / pi-coding-agent](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/)
  - Strong argument for a small, inspectable runtime core plus separate UI/product layers.
  - Helpful counterweight against feature bloat.
- [DeerFlow](https://github.com/bytedance/deer-flow)
  - Strong example of keeping harness code and app code separate inside one repo.
  - Useful richer-session model with artifacts, workspace, and event concerns.
- [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)
  - Clear influence on durable execution, interrupts, and long-running stateful workflows.
- [Pydantic AI](https://ai.pydantic.dev/)
  - Important Python-native path for agents, web surfaces, MCP, A2A, and message-history thinking.
- [Humanlayer ACP](https://github.com/humanlayer/agentcontrolplane)
  - Useful signal that "agent control plane" is becoming a real category centered on sessions, approvals, and durability.
- [GitHub Agent HQ / Agent Control Plane](https://github.blog/news-insights/product-news/github-copilot-the-agent-awakens/)
  - Strong evidence that multi-agent supervision and comparison are becoming mainstream workflow needs.
- [Aider](https://aider.chat/)
  - Ongoing reminder that simple, inspectable tools still win when they stay focused.
- [OpenHands](https://docs.openhands.dev/usage/architecture/runtime)
  - Helpful example of keeping a runtime distinct from the user-facing control surface.

## Design Consequences

The direction above leads to a few durable decisions:

- We should continue treating the web UI as important, but not as the system boundary.
- We should keep building a clean runtime-facing contract rather than embedding provider logic in routes.
- We should evolve from chat-thread thinking toward session thinking.
- We should make space for multiple scoped agents without turning the default setup into a platform.
- We should preserve local-first simplicity while preparing for richer runtime behavior behind the scenes.

## Decision Filter

When evaluating future work, prefer changes that:

- keep the default experience usable and calm
- sharpen the runtime/UI/control separation
- improve inspectability and explicit control
- support multi-session and multi-agent use without requiring a giant platform
- make experiments with models, memory, tools, and protocols easier

Reject or defer changes that:

- make the UI own runtime logic
- force framework-specific concepts into the product language
- expand into hosted-platform scope before the local workbench is solid
- add hidden behavior that reduces predictability
- multiply surface area without strengthening the core boundaries
