## Suggested Phases

The phase model now reflects a broader shift from "chat app with an agent backend" toward "lightweight workbench over explicit session, run, runtime, and control-layer concepts."

Completed phases are retained as historical milestones. Future phases are reframed around runtime separation, richer session-and-run concepts, multi-agent personal use, and optional connection to external runtime systems.

--

### 1. Reliable Single-Chat Baseline (Completed)

This phase established the original foundation: a developer could clone the repository, configure an API key, run the app, and immediately use a clean, predictable chat UI without writing additional code.

Phase 1 complete means:

- the app can be cloned, configured, started, and used without code changes
- the default UX is a reliable request/response chat loop
- runtime configuration is environment-driven rather than embedded in route logic
- the baseline UI works without a frontend build step
- extension seams for prompts, provider wiring, and basic chat behavior are explicit

Phase 1 intentionally did not include authentication, persisted multi-chat continuity, explicit session modeling, generalized runtime abstraction, or deployment hardening.

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

In later terminology, this phase mostly strengthened transcript continuity and chat lifecycle, but it did not yet make `session` and `run` first-class product concepts.

--

### 3. Harness Boundary And Runtime Decoupling (Completed)

This phase formalizes the separation between the workbench UI and the runtime behind it.

The goal is to make the web app a client of a clear runtime-facing contract rather than the place where provider-specific behavior lives.

Phase 3 should:

- complete the app-facing harness boundary
- bind each session to a stable runtime profile
- keep a small control/service layer between routes and harness execution
- move context assembly and execution concerns behind the harness layer
- keep the contract ready for streaming, tools, and alternative runtime shapes
- prove the seam with at least one meaningful non-default harness

Progress already made:

- the initial chat harness vocabulary and normalized contracts have already shipped as `P3-01`

Phase 3 is complete when the runtime boundary is real in practice, not just in naming.

Phase 3 established the idea that:

- the UI is not the runtime
- the harness is an execution boundary rather than the whole product model
- a session can carry stable runtime binding even when the visible surface still looks like a simple chat thread

--

### 4. Workbench Session Model And Advanced Interaction

This phase shifts the product from "multi-chat UI" toward a richer session-based workbench.

The goal is to make `session`, `run`, and `transcript` distinct and usable concepts in both the product and the architecture.

This phase should introduce or mature concepts such as:

- session identity beyond raw transcript history
- run identity beyond "the latest send"
- inspectable agent and runtime binding metadata
- compare, fork, replay, or resume workflows
- deliberate runtime comparison workflows without requiring arbitrary in-place model switching
- artifacts, outputs, and other session-adjacent records where useful
- lightweight scope, profile, or context-policy metadata where it supports the workbench model cleanly
- terminology and persistence that stop treating a chat transcript as the whole durable object

This is also the phase where the project should stay open to more than one runtime shape.

That does not mean full external-runtime integration must land in Phase 4. It does mean the session and run model should not assume that every execution always comes from a native runtime implemented inside this repository.

The emphasis is still product clarity, not feature sprawl.

--

### 5. Personal Agent Control Plane

This phase introduces a minimal control-plane model for one user running multiple scoped agents or sessions at the same time.

The point is not enterprise orchestration. The point is to support the reality that advanced users often want several concurrent agent sessions with different scopes, tools, or purposes.

This phase should focus on:

- multiple concurrent scoped agents
- explicit session, run, agent, and runtime bindings
- approvals, interrupts, and resumability
- background or long-running runs where appropriate
- better visibility into what each agent is doing and why
- destination-style surfaces beyond plain chat where useful, such as review queues, approvals, task outcomes, or scheduled outputs
- agent definitions as clearer first-class concepts, including behavior packages built from prompts, skills, tools, delegation rules, and context policy

This is the phase where the project should start to feel like a true workbench rather than only a chat UI.

This phase is also the natural place to mature the difference between:

- conversational continuation
- task-style invocation
- scheduled or background work
- explicit compare or branch workflows

--

### 6. Small-Team Shared Agent Operations

This phase extends the personal control-plane model into small-team use without jumping straight to a broad hosted platform.

Potential outcomes include:

- shared visibility into agent sessions and runs
- scoped team-level agents for specific projects or responsibilities
- shared artifacts, traces, and review workflows
- limited collaboration patterns around agent output and supervision
- named-user identity rather than browser-only identity
- shared or team-scoped context layers such as brand voice, engineering standards, or common capability bundles where useful

This phase is intentionally not "Slack for agents" as a product mandate. It is about making the small-team version of the workbench coherent and useful.

--

### 7. Optional Hardening And Deployment Paths

This phase provides a route for teams that want to run the project outside a purely local or trusted environment.

It may include:

- authentication and access controls
- admin controls over users, agents, capabilities, and runtime access
- user- and team-level capability provisioning
- more explicit policy and approval surfaces
- safer deployment defaults
- operational guidance for small hosted deployments
- selected protocol or integration hardening where needed
- stronger hardening around external or federated runtime connections where those are supported

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
- preserving a coherent user experience even when runtimes differ underneath

This is an ongoing engineering standard across every phase, not a separate product phase.
