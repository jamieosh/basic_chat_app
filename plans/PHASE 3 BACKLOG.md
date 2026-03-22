# Phase 3 Backlog

This document tracks the proposed Phase 3 delivery slices for the chat harness boundary and its small control/service seam.

Completed items should move to `plans/done/PHASE 3 DONE.md` once shipped.

The intent is to keep the work incremental: each slice should leave the app runnable while tightening the harness boundary a little further.

## Completed Groundwork

`P3-01 Chat Agent Harness Vocabulary And Contracts` has already shipped and now lives in [`plans/done/PHASE 3 DONE.md`](/Users/jamie/Development/basic_chat_app/plans/done/PHASE%203%20DONE.md).

The rest of this backlog assumes `ChatHarness`, normalized harness types, and the first contract vocabulary are already in place.

## Proposed Items

### P3-09 Alternative Harness Proof Implementation

Priority: P1

Problem:
The Phase 3 harness boundary can look clean on paper while still remaining OpenAI-shaped in practice. A fake harness helps test decoupling, but it does not prove that a real provider with different request, event, and failure shapes fits the contract well.

Deliver:

- implement one real non-default harness behind the Phase 3 harness contract, with Anthropic as the explicit Phase 3 proof target
- keep selection backend-configured only, with no user-facing harness picker
- make provider selection explicit in runtime configuration so contributors can choose OpenAI or Anthropic without code changes for new chats
- validate that startup wiring, harness binding, observability, normalized failures, and default chat flow all work with the alternative harness
- use Anthropic specifically because it meaningfully stretches the contract instead of mostly mirroring an OpenAI-compatible wire shape

Acceptance criteria:

- the app can run end-to-end against Anthropic through backend configuration only
- provider choice is clearly controlled through configuration for new chats, with OpenAI and Anthropic both being valid configured defaults once the Anthropic harness ships
- no route-level provider-specific branching is needed to support the alternative harness
- harness logs and diagnostics remain normalized across the default and alternative harnesses
- the Anthropic harness proves the contract can absorb a materially different provider shape without reshaping the web chat layer

Configuration intent:

- use backend/runtime configuration rather than a user-facing picker
- keep `DEFAULT_CHAT_HARNESS_KEY` as the selector for which harness new chats bind to, for example `openai` or `anthropic`
- keep provider credentials and provider-specific defaults in environment variables, for example `OPENAI_API_KEY` for OpenAI and `ANTHROPIC_API_KEY` for Anthropic
- preserve existing per-chat binding behavior so changing the default only affects newly created chats

What the user sees:
No required UI change, but Phase 3 is now validated against a real alternative provider instead of only the default implementation.

## Sequencing Notes

- `P3-01`, `P3-02`, and `P3-03` are complete groundwork for the rest of Phase 3.
- `P3-04` makes the harness useful for memory evolution, and `P3-05` now provides the shipped event-capable execution surface for future streaming work.
- `P3-09` should land late in Phase 3 as the real-world proof that the harness boundary is not only OpenAI in disguise.
