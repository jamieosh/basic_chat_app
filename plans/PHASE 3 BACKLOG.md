# Phase 3 Backlog

This document tracks the proposed Phase 3 delivery slices for the chat harness boundary and its small control/service seam.

Completed items should move to `plans/done/PHASE 3 DONE.md` once shipped.

The intent is to keep the work incremental: each slice should leave the app runnable while tightening the harness boundary a little further.

## Completed Groundwork

`P3-01 Chat Agent Harness Vocabulary And Contracts` has already shipped and now lives in [`plans/done/PHASE 3 DONE.md`](/Users/jamie/Development/basic_chat_app/plans/done/PHASE%203%20DONE.md).

The rest of this backlog assumes `ChatHarness`, normalized harness types, and the first contract vocabulary are already in place.

## Proposed Items

### P3-08 Test, Docs, And Forking Guidance Alignment

Priority: P1

Problem:
Phase 3 will add important terminology and extension seams. Without explicit tests and documentation, contributors will drift back toward route-level coupling.

Deliver:

- add regression coverage for harness contract behavior, harness resolution, normalized failures, and default OpenAI parity
- add a fake or minimal test harness to prove the app is not coupled to OpenAI-specific wiring
- document one registry-backed path for adding a new harness implementation without touching unrelated web-chat code
- update [`README.md`](/Users/jamie/Development/basic_chat_app/README.md) to explain the Phase 3 chat harness boundary, control/service seam, and default customization path clearly
- update [`AGENTS.md`](/Users/jamie/Development/basic_chat_app/AGENTS.md) so the project summary, architecture notes, and contributor guidance stay aligned with the harness terminology
- update planning docs to keep Phase 3 terminology aligned with the contributor-facing docs and the newer workbench/control-layer framing
- align backlog, design, done, and contributor guidance as items ship

Acceptance criteria:

- contributors can follow one obvious path to add a new provider-backed harness
- Phase 3 terminology is consistent across code and docs
- [`README.md`](/Users/jamie/Development/basic_chat_app/README.md) and [`AGENTS.md`](/Users/jamie/Development/basic_chat_app/AGENTS.md) describe the same extension model as the Phase 3 planning docs
- the updated docs describe the UI layer, harness layer, and small control/service layer consistently
- tests lock the default harness behavior while leaving space for alternate implementations

What the user sees:
No direct product change, but the repo becomes much easier to understand and extend safely.

### P3-09 Alternative Harness Proof Implementation

Priority: P1

Problem:
The Phase 3 harness boundary can look clean on paper while still remaining OpenAI-shaped in practice. A fake harness helps test decoupling, but it does not prove that a real provider with different request, event, and failure shapes fits the contract well.

Deliver:

- implement one real non-default harness behind the Phase 3 harness contract, with Anthropic as the explicit Phase 3 proof target
- keep selection backend-configured only, with no user-facing harness picker
- validate that startup wiring, harness binding, observability, normalized failures, and default chat flow all work with the alternative harness
- use Anthropic specifically because it meaningfully stretches the contract instead of mostly mirroring an OpenAI-compatible wire shape

Acceptance criteria:

- the app can run end-to-end against Anthropic through backend configuration only
- no route-level provider-specific branching is needed to support the alternative harness
- harness logs and diagnostics remain normalized across the default and alternative harnesses
- the Anthropic harness proves the contract can absorb a materially different provider shape without reshaping the web chat layer

What the user sees:
No required UI change, but Phase 3 is now validated against a real alternative provider instead of only the default implementation.

## Sequencing Notes

- `P3-01`, `P3-02`, and `P3-03` are complete groundwork for the rest of Phase 3.
- `P3-04` makes the harness useful for memory evolution, and `P3-05` now provides the shipped event-capable execution surface for future streaming work.
- `P3-08` should tighten the remaining docs and forking guidance before the final proof step.
- `P3-09` should land late in Phase 3 as the real-world proof that the harness boundary is not only OpenAI in disguise.
