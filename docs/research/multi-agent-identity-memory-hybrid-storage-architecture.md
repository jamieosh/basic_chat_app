# Multi-Agent Identity, Shared Memory, and Hybrid Storage

## Purpose

This document turns the product idea discussed in-thread into an architecture pattern:

- multiple persistent agents with distinct personalities/capabilities
- multiple chats (threads) per agent
- memory shared across that agent’s chats
- asset-aware context (files/documents scoped to the right task)
- optional agent-to-agent sharing with user-directed policy

It also explains why many systems lean file-first, what they gain/lose, and how file and DB patterns should coexist in our system.

## References

- Anthropic: [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- OpenAI: [Agents SDK guide](https://developers.openai.com/api/docs/guides/agents-sdk)
- LangGraph: [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- Letta: [Memory blocks](https://docs.letta.com/guides/core-concepts/memory/memory-blocks/)
- OpenHands: [Runtime architecture](https://docs.openhands.dev/openhands/usage/architecture/runtime)
- MCP Spec: [Base protocol overview (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18/basic/index)
- Google ADK: [A2A introduction](https://google.github.io/adk-docs/a2a/intro/)
- MemGPT: [Towards LLMs as Operating Systems](https://research.memgpt.ai/)
- Generative Agents paper page: [Interactive Simulacra of Human Behavior](https://research.google/pubs/generative-agents-interactive-simulacra-of-human-behavior/)
- Local context in this repo:
  - [docs/research/hermes-agent-core-harness-pattern.md](./hermes-agent-core-harness-pattern.md)
  - [docs/research/hermes-practical-usage-walnut-context-loop.md](./hermes-practical-usage-walnut-context-loop.md)

## Your Idea As A Product Model

The idea is coherent and strong. It implies five first-class entities:

1. `Agent` (identity): persona, objectives, tool permissions, safety policy.
2. `Thread` (conversation): independent transcript/workstream under one agent.
3. `Memory` (cross-thread state): what the agent learns across its threads.
4. `Assets` (documents/files): attached artifacts with ownership and retrieval policy.
5. `Share channels` (optional inter-agent exchange): explicit scope of what may flow between agents.

This is more than “chat history.” It is a persistent collaborator model.

## Are Agents Just Configs, Or Structurally Different?

Both, depending on task class.

### Config-level differences (lightweight)

- persona/tone/system prompt
- default tools enabled
- retrieval preferences
- memory read/write policy
- response format

Anthropic explicitly notes one case where “separate agents” were only different initial prompts while system prompt/tools/harness stayed otherwise identical. That is real, useful, and often enough for advisory/research variants.

### Structural differences (heavyweight)

- execution substrate (shell/browser/file mutation/code execution)
- isolation/sandboxing/security approvals
- planning and verification loops
- artifact/checkpoint/rollback mechanics
- test/quality gates and failure recovery

OpenHands is a concrete example of structural runtime needs: sandboxed Docker execution, action execution server, pluginized runtime features, and explicit isolation/reproducibility concerns.

## Extreme Test Case: Coding Agent vs Holiday Agent

### Holiday planning agent (mostly config + light tools)

- web/search/document parsing
- preference and trip memory
- itinerary generation
- lower side-effect risk
- verification is mostly factual/citation quality and user preference fit

### Coding agent (requires structural runtime)

- executes shell commands and modifies code
- must run tests/lint/build and recover from failures
- needs workspace isolation and permission controls
- requires stronger checkpointing, audit, and rollback
- must protect secrets, repo state, and dependency/runtime boundaries

Conclusion: a coding agent is not just “holiday agent + stronger model.” It usually requires a different runtime and policy envelope.

## Why So Many Systems Are File-First

File-first patterns are popular because they optimize iteration speed and inspectability:

1. Fast authoring: prompts/skills/scripts are editable as plain files.
2. Human-readable state: progress logs and memory files are debuggable in any editor.
3. Tool interoperability: any agent/tool can read/write files without API coupling.
4. Git-native workflows: versioning, diffs, blame, rollback are trivial.
5. Local-first operation: lightweight deployment for always-on personal agents.

Anthropic’s long-running harness article uses file artifacts (`claude-progress.txt`, `init.sh`, feature JSON) + git history explicitly to bridge fresh contexts and keep incremental work coherent across sessions.

## Why Typed DB-Centric Systems Still Matter

DB-first control planes solve different problems:

1. idempotency and conflict-safe request lifecycle
2. strong run/session status integrity
3. concurrent access safety and queryability
4. observability and audit at scale
5. reliable replay/finalization semantics

LangGraph’s persistence model is DB/checkpointer-friendly for exactly these reasons: thread IDs, checkpoints, replay, interrupts, and fault tolerance.

## File vs DB: The Real Answer Is Hybrid

The practical design is not either/or.

### Control plane in DB

- authoritative entities and state transitions
- run lifecycle/status, approvals, conflicts
- permissions and policy decisions
- indexing/query/reporting/retention

### Context/artifact plane in files (optional but first-class)

- prompts, skills, SOPs, notes, generated reports
- editable memory artifacts
- project-specific shared context stores

### Synchronization contract

- DB stores artifact metadata/provenance/version/hash
- files hold content optimized for human/tool editing
- writes are mediated through policy hooks and conflict semantics

This mirrors where the ecosystem is converging:

- Letta: memory blocks can be shared across agents, marked read-only, and managed with explicit agent scope.
- MemGPT: virtual context and storage tiers.
- MCP: modular capability layers and explicit protocol contracts.

## What We Can Add To Your Current Thinking

1. Memory scopes should be explicit, not implied.
- `thread_memory`: topic-local
- `agent_memory`: shared across one agent’s threads
- `shared_memory`: cross-agent, policy-governed

2. Memory writes need conflict semantics.
- last-write-wins is easy but risky
- add CAS/version checks or append-only logs for critical artifacts
- preserve provenance (`who wrote what, when, from which run`)

3. Sharing should be capsule-based, not free-form.
- “share this summary with agent X”
- include scope, TTL, and allowed use
- audit every import/export event

4. Forgetting/retention is a product feature, not cleanup.
- expiry classes for ephemeral vs durable memory
- user controls for delete/redact/export
- policy by memory scope

5. Retrieval must be scope-aware.
- asset linkage + topic tags + recency + confidence
- avoid cross-topic contamination (Malta booking in France thread)

6. Different agent profiles need different quality gates.
- coding: tests, static checks, security checks
- planning/research: citation/source diversity and freshness checks

## Mapping To Our Current Architecture

Current strengths in this repo:

- typed harness boundary (`ChatHarness`)
- stable harness binding per session (`chat_sessions.harness_key`, `harness_version`)
- persisted run lifecycle (`chat_session_runs`, `chat_turn_requests`)
- service-owned idempotent control flow (`ChatTurnService`)

These are excellent control-plane foundations for multi-agent evolution.

## What We Likely Need To Add

### Data model evolution

1. `agents`
- `id`, `owner_client_id`, `name`, `profile_key`, `persona`, `policy_json`, `created_at`

2. `agent_threads`
- maps chat sessions to an agent (`agent_id`, `chat_session_id`, `topic_key`, `status`)

3. `agent_memories`
- normalized memory entries with `scope` (`thread|agent|shared`), provenance, and retention

4. `agent_assets`
- file/doc metadata (`owner_agent_id`, optional `thread_id`, labels, checksum, ACL)

5. `agent_share_events`
- explicit inter-agent transfer records with user intent + policy outcome

### Harness/context evolution

1. Extend context builders to merge scoped memory + scoped assets.
2. Add memory writeback policies (“must write summary”, “append insights”, “no write without approval”).
3. Add retrieval guards against wrong-topic bleed.
4. Add run profiles (`advisory`, `research`, `coding`) with distinct gates/policies.

### Runtime evolution

1. Keep web-turn flow as-is for chat UX.
2. Add optional background/scheduled run orchestrator for persistent agents.
3. Add stronger execution sandbox/policy path for coding agents.

## Inter-Agent Communication Model

Use two layers, not one:

1. Local sub-agents (same runtime/process) for orchestration speed.
2. Remote agents (A2A-style contract) when crossing team/system boundaries.

Google ADK’s A2A guidance aligns with this split: local sub-agents for internal modular decomposition, remote A2A when integrating independent services with explicit formal contracts.

## User-Facing Behavior To Target

1. User can create named agents with clear role and capability profile.
2. User can open many threads under one agent.
3. Agent remembers relevant prior history across threads by scope.
4. User can attach files either to an agent globally or to one thread.
5. User can direct “share this with agent X” and see what moved.
6. User can inspect why an agent used a memory/file in a response.

## Experienced-Builder Guardrails

1. Treat DB lifecycle as authority; do not move correctness into ad hoc file flows.
2. Treat files as interoperable artifacts with metadata + provenance, not hidden state.
3. Separate capability config from runtime capability (permission does not imply safe execution environment).
4. Version agent profiles and policies; profile drift should be explicit.
5. Enforce approval boundaries for side-effecting tools, especially in coding profiles.

## Recommended Direction For This Project

1. Keep current typed/session/run core intact as control plane.
2. Add first-class `agent` identity and `agent_thread` mapping.
3. Add scoped memory and asset metadata tables.
4. Add optional file-artifact sync adapters to support walnut/skill-style workflows.
5. Introduce profile-driven runtime policies so “holiday” and “coding” can share the same platform but run with different safety and verification envelopes.

This gives us the flexibility people like in file-first systems, without giving up the reliability guarantees of the typed DB-based architecture we already have.

