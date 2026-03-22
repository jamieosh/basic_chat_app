## Suggested Phases

The phase model now reflects a broader shift from "chat app with an agent backend" toward "lightweight workbench over a minimal harness and control layer."

Completed phases are retained as historical milestones. Future phases are reframed around runtime separation, richer session concepts, and multi-agent personal use.

--

### 1. Reliable Single-Chat Baseline (Completed)

This phase established the original foundation: a developer could clone the repository, configure an API key, run the app, and immediately use a clean, predictable chat UI without writing additional code.

Phase 1 complete means:

- the app can be cloned, configured, started, and used without code changes
- the default UX is a reliable request/response chat loop
- runtime configuration is environment-driven rather than embedded in route logic
- the baseline UI works without a frontend build step
- extension seams for prompts, provider wiring, and basic chat behavior are explicit

Phase 1 intentionally did not include authentication, persisted multi-chat continuity, streaming responses, generalized runtime abstraction, or deployment hardening.

--

### 2. Conversation Continuity And Chat Lifecycle (Completed)

This phase made the workbench practically useful by introducing persisted multi-chat behavior and lightweight lifecycle management without making authentication a baseline requirement.

Phase 2 complete means:

- chats persist across reloads and restarts
- chats are browser-cookie scoped rather than account scoped
- users can create, revisit, switch, and delete chats from the default UI
- `/chats/{chat_id}` restores the selected transcript on full page load
- duplicate request IDs replay the stored outcome instead of creating duplicate turns

Phase 2 established a local-first, personal-use conversation model while keeping the UI server-rendered and HTMX-first.

--

### 3. Harness Boundary And Runtime Decoupling (In Progress)

This phase formalizes the separation between the workbench UI and the runtime behind it.

The goal is to make the web app a client of a clear harness/runtime contract rather than the place where provider-specific behavior lives.

Phase 3 should:

- complete the app-facing harness boundary
- bind each chat or session to a stable runtime profile
- move context assembly and execution concerns behind the harness layer
- keep the contract ready for streaming, tools, and alternative runtimes
- prove the seam with at least one meaningful non-default harness

Progress already made:

- the initial chat harness vocabulary and normalized contracts have already shipped as `P3-01`

Phase 3 is complete when the runtime boundary is real in practice, not just in naming.

--

### 4. Workbench Session Model And Advanced Interaction

This phase shifts the product from "multi-chat UI" toward a richer session-based workbench.

The goal is to make sessions more expressive than a plain transcript and to expose the beginnings of workbench-style interaction.

This phase should introduce or mature concepts such as:

- session identity beyond raw transcript history
- compare, fork, replay, or resume workflows
- runtime- and session-level metadata that users can inspect
- artifacts, outputs, and other session-adjacent records where useful
- file and project context where it supports the workbench model cleanly

The emphasis is still product clarity, not feature sprawl.

--

### 5. Personal Agent Control Plane

This phase introduces a minimal control-plane model for one user running multiple scoped agents or sessions at the same time.

The point is not enterprise orchestration. The point is to support the reality that advanced users often want several concurrent agent sessions with different scopes, tools, or purposes.

This phase should focus on:

- multiple concurrent scoped agents
- explicit session and runtime bindings
- approvals, interrupts, and resumability
- background or long-running runs where appropriate
- better visibility into what each agent is doing and why

This is the phase where the project should start to feel like a true workbench rather than only a chat UI.

--

### 6. Small-Team Shared Agent Operations

This phase extends the personal control-plane model into small-team use without jumping straight to a broad hosted platform.

Potential outcomes include:

- shared visibility into agent sessions and runs
- scoped team-level agents for specific projects or responsibilities
- shared artifacts, traces, and review workflows
- limited collaboration patterns around agent output and supervision

This phase is intentionally not "Slack for agents" as a product mandate. It is about making the small-team version of the workbench coherent and useful.

--

### 7. Optional Hardening And Deployment Paths

This phase provides a route for teams that want to run the project outside a purely local or trusted environment.

It may include:

- authentication and access controls
- more explicit policy and approval surfaces
- safer deployment defaults
- operational guidance for small hosted deployments
- selected protocol or integration hardening where needed

These concerns are important, but they remain optional maturity work rather than the baseline identity of the project.

--

## Cross-Cutting Engineering Standard

The repository should remain easy for both humans and coding agents to understand.

That means:

- clear boundaries
- explicit terminology
- predictable defaults
- strong tests around core lifecycle behavior
- contributor guidance that stays aligned with the architecture

This is an ongoing engineering standard across every phase, not a separate product phase.
