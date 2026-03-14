# Phase 1 Backlog

This backlog captures the work needed to complete the "Reliable Single-Chat Baseline" phase.  
Items are intentionally unnumbered so they can be reordered as priorities change.

-- 

## Keep Default Behavior Deterministic And Neutral

The default baseline should avoid hidden or domain-specific assumptions so results are reproducible across users and forks. This item ensures the initial behavior remains explicit and stable, making comparisons between experiments easier. Determinism is especially important in a workbench intended for rapid technical iteration.

- Remove or isolate hardcoded domain context from the default chat behavior.
- Keep prompt and baseline memory behavior explicit rather than implicit.
- Document what deterministic behavior means in this phase.

-- 

## Introduce A Lightweight App-Side Chat Abstraction Seam

The current architecture can evolve over time, but Phase 1 should still lay a clean foundation for future provider and orchestration work. This item is about creating a small, practical boundary at the app layer, without over-designing a full framework abstraction. The intention is to reduce coupling now while keeping future design choices open.

- Define a minimal application-facing chat interface boundary.
- Keep the existing OpenAI path as the default implementation behind that boundary.
- Avoid broad class proliferation while making extension points obvious.

-- 

## Align CORS And Configuration With Phase 1 Security Posture

Phase 1 does not require full security or authentication features, but it should avoid contradictory or risky default settings. This item aligns runtime configuration with the project's stated "dev-first baseline" position and reduces future migration cost when auth arrives in Phase 2. It also helps avoid confusion for teams deploying small internal forks.

- Make CORS behavior explicit and environment-driven.
- Align credential-related settings with the current no-auth baseline.
- Add short documentation clarifying Phase 1 security expectations and limits.

-- 

## Expand Regression Coverage For Baseline Reliability

A small project still needs strong confidence in its core behavior. This item adds focused, deterministic tests around known fragile paths so refactors and experiments do not regress the baseline chat flow. The emphasis is on high-signal test coverage, not test volume.

- Add tests for key error and fallback paths in message processing.
- Add tests for rendering/formatting edge cases that affect chat output.
- Keep tests offline and deterministic with mocked external dependencies.

-- 

## Tighten Documentation For Contributors And Forks

Phase 1 completion should be obvious to new contributors and fork maintainers. This item ensures docs consistently describe what exists today, what is intentionally deferred, and where core extension seams live. Clear docs reduce onboarding time and keep implementation choices aligned with vision.

- Keep README, VISION, and PHASES language aligned around current scope.
- Add a concise "Phase 1 complete means..." definition for maintainers.
- Clarify where to change prompts, model wiring, and chat UI behavior safely.
