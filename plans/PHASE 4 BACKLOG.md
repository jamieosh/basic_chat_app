# Phase 4 Backlog — Workbench Session Model And Advanced Interaction

> **Goal:** This phase shifts the product from "multi-chat UI" toward a richer session-based workbench. The goal is to make `session`, `run`, and `transcript` distinct and useful concepts, while exposing the beginnings of workbench-style interaction without turning Phase 4 into a full control-plane or integration phase.

Items are ordered by priority. Each item gets a feature branch `codex/<kebab-slug>` and plan file `plans/<kebab-slug>.md` when work begins. Run `$feature-start` to pick the next item.

---

## P4-01 — Session Model And Persistence Groundwork

**Size:** Large  
**Dependencies:** None

This item makes the session concept explicit in the persistence model, service vocabulary, and contributor docs without breaking the current chat restore and send flow. It should also establish the minimum groundwork for explicit run identity instead of relying only on the current turn-request mechanics. It matters because every later Phase 4 slice depends on the app no longer treating transcript history as the whole durable object of the system. Out of scope for this item are user-facing branching workflows, artifact records, or broad UI redesign.

**What the user will see:** Little or no visible UI change yet. The main effect should be a more stable foundation for later session-oriented features without regressing the existing chat experience.

---

## P4-02 — Session Metadata And Inspectability Surface

**Size:** Medium  
**Dependencies:** P4-01

This item exposes stable session identity, agent identity, runtime binding, and other high-signal session metadata in the product so users can inspect what a session is and what it is bound to. It should also introduce the smallest useful session profile or context-policy surface, such as lightweight scope, notes, or reusable guidance metadata. It matters because the workbench posture depends on visible, inspectable state rather than backend-only assumptions. Out of scope for this item are lineage actions such as fork or replay and any heavy control-plane behavior.

**What the user will see:** Users should start seeing session-oriented metadata in the interface, such as clearer session, agent, runtime, or scope details, rather than only a chat title and transcript.

---

## P4-03 — Session Lineage And Fork Workflow

**Size:** Medium  
**Dependencies:** P4-01, P4-02

This item adds a deliberate fork or duplicate flow that creates a new session from an existing one with visible parent-child lineage. It matters because compare and branch workflows are central to the portfolio direction, and they should be modeled as explicit session relationships rather than improvised transcript edits. This item may include minimal metadata needed to support later runtime comparison, as long as it remains branch-oriented and inspectable. Out of scope for this item are full compare dashboards or complex merge behavior between branches.

**What the user will see:** Users should be able to branch work from an existing session and recognize that the new session came from an earlier one.

---

## P4-04 — Replay And Resume Workflow Foundation

**Size:** Large  
**Dependencies:** P4-01, P4-02

This item introduces deliberate replay and resume-style workflows so users can continue work from an earlier point or prior run state without mutating history invisibly. It should establish the minimal useful distinction between normal conversational continuation and deliberate replay/compare-style runs. It may include narrow runtime-compare workflows where replay or branch semantics make that explicit, but not arbitrary per-message switching. It matters because the workbench needs intentional revisit behavior that is richer than simply appending another message to the same transcript. Out of scope for this item are autonomous retries, background orchestration, or a large approval system.

**What the user will see:** Users should gain a clearer way to continue or revisit prior work intentionally, instead of relying only on manual transcript prompting.

---

## P4-05 — Session Run Record Foundation

**Size:** Large  
**Dependencies:** P4-01, P4-04

This item introduces a cleaner model for inspectable run metadata beyond the current turn-request implementation details. It should make run identity, run history, and basic run intent visible enough to support concepts such as conversational sends, replay runs, compare runs, or resume-related runs without overdesigning a future workflow engine. It matters because later approvals, interrupts, resumability, and background execution all need durable run identity and history that are more explicit than the current send lifecycle storage. Out of scope for this item are full background workers, multi-agent scheduling, or a complete control-plane UI.

**What the user will see:** Some session or run details may become easier to inspect, but the main value is a stronger internal model for later control-plane features.

---

## P4-06 — Session Artifacts And Non-Transcript Outputs

**Size:** Medium  
**Dependencies:** P4-01, P4-05

This item adds a narrow session-adjacent record type for outputs that should not live only in chat messages, such as structured run notes, derived outputs, or future artifact references. It matters because the portfolio direction depends on sessions carrying more than transcript text, while still keeping the transcript canonical for conversation history. Out of scope for this item are a generic file manager, large attachment families, or full project container support.

**What the user will see:** Users may start seeing certain outputs or records attached to a session outside the main transcript, even if the initial surface stays lightweight.

---

## P4-07 — Lightweight Session Profile And Context Policy

**Size:** Medium  
**Dependencies:** P4-01, P4-02

This item adds the smallest useful session-level profile, scope, or context-policy concept that helps the workbench model without turning the app into a file-management system or a full user-profile system. It matters because later personal-agent and small-team phases need a cleaner way to describe what a session is for beyond its title and transcript, and where shared guidance such as standards or reusable session instructions might eventually live. Out of scope for this item are full workspace containers, broad filesystem integration, durable user identity, or a general project-management layer.

**What the user will see:** Users should be able to give sessions a clearer sense of scope, profile, or guidance context, but without a major shift in the app’s simple chat-first posture.

---

## Deferred

Items considered for this phase but intentionally pushed out. Move to `plans/PARKING LOT.md` after writing this file.

- **Broad file attachments and project containers**: Useful for the longer-term workbench shape, but too large for the first session-model phase and better suited to a later workbench maturity phase.
- **Archive browsing and deleted-chat recovery workflows**: Still relevant UX gaps, but they do not advance the core Phase 4 session model as directly as lineage, replay, and inspectability work.
- **Deep external-runtime integration**: The Phase 4 model should remain open to external or federated runtimes later, but proving that integration is not required for this phase.
- **Arbitrary user-facing runtime switching inside a live transcript**: Better deferred until the session model and run records are more explicit, so runtime choice does not leak back into ad hoc UI behavior.
