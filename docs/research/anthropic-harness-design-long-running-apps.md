# Anthropic Harness Design For Long-Running Apps: Planner/Generator/Evaluator Pattern

## Purpose

This document analyzes Anthropic's March 24, 2026 article on harness design for long-running application development and maps its lessons to our architecture.

Focus:

- what changed from the earlier initializer/coding-agent pattern
- how they frame context resets vs compaction
- where multi-agent decomposition actually helps
- what we should adopt, adapt, and avoid

## References

- Primary article: [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- Prior related Anthropic baseline: [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Earlier quickstart referenced by both articles:
  - [anthropics/claude-quickstarts/autonomous-coding](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding)
  - [`autonomous-coding/README.md`](https://github.com/anthropics/claude-quickstarts/blob/main/autonomous-coding/README.md)
  - [`autonomous-coding/agent.py`](https://github.com/anthropics/claude-quickstarts/blob/main/autonomous-coding/agent.py)
  - [`autonomous-coding/prompts/initializer_prompt.md`](https://github.com/anthropics/claude-quickstarts/blob/main/autonomous-coding/prompts/initializer_prompt.md)
  - [`autonomous-coding/prompts/coding_prompt.md`](https://github.com/anthropics/claude-quickstarts/blob/main/autonomous-coding/prompts/coding_prompt.md)

## What This Article Contributes

This is not just a repeat of the older initializer/coding-agent setup.

It adds two major ideas:

1. Separate generation from evaluation because models are overly lenient when grading their own work.
2. Treat harness complexity as model-version-dependent and continuously prune non-load-bearing parts.

The article frames harness design as an empirical loop:

- decompose roles when baseline fails
- tune and calibrate role behavior
- re-evaluate each component as models improve

## Core Pattern In The Article

### 1) Two persistent failure classes

Anthropic calls out:

- coherence loss near context limits ("context anxiety")
- self-evaluation bias (agents praising their own mediocre outputs)

This applies to both subjective design tasks and coding tasks.

### 2) Context reset vs compaction is a harness decision

Their distinction:

- compaction keeps one continuous agent with summarized history
- context resets create a fresh agent and rely on handoff artifacts

On earlier model behavior (Sonnet 4.5), they found resets were often required.
With Opus 4.5 in the newer harness, they ran continuous sessions with compaction and removed resets.

Implication: memory strategy is not static architecture; it is model- and task-dependent policy.

### 3) GAN-inspired separation of roles

The article first demonstrates:

- Generator agent creates output
- Evaluator agent grades against explicit criteria and gives critique

Then extends that into coding as:

- Planner: expands short user prompt into product spec
- Generator: builds app incrementally
- Evaluator: performs QA with hard thresholds and actionable failure feedback

### 4) Sprint contracts as a bridge layer

Before each sprint, generator and evaluator negotiate a contract for "done" and verification conditions.

Why this matters:

- planner spec stays intentionally high-level
- sprint contract translates user stories into testable acceptance criteria
- generator builds against explicit contract, evaluator validates against same contract

### 5) File-mediated inter-agent protocol

The article states that agents communicate via files for handoff/coordination, rather than hidden conversational state.

That gives durable, inspectable interfaces between specialized agents.

### 6) Quality/cost tradeoff is explicit

They show large quality gains against solo runs, but with high cost and runtime.
They also show a later simplified harness with lower complexity/cost while retaining meaningful QA lift.

## Key Principle: Harness Components Are Hypotheses

A strong point in this article is operational:

- each harness component encodes an assumption about model limits
- assumptions go stale as models improve
- therefore harnesses need periodic "component load-bearing" audits

This is highly relevant to our architecture evolution.

## Mapping To Our Architecture

| Anthropic concept | Our equivalent | Opportunity for us |
| --- | --- | --- |
| Planner role turns brief prompt into richer objective | context builder + prompt templates + potential planning harness | add optional objective-planning stage that emits structured objective artifacts |
| Generator role executes implementation work | harness adapter runtime behind `run_events()` | keep execution in harness adapter while preserving service-owned lifecycle |
| Evaluator role gates quality with thresholds | future QA/verification harness + failure normalization | add explicit post-run evaluator mode with typed pass/fail criteria and rerun signals |
| Sprint contract between generator/evaluator | run-scoped acceptance schema | store acceptance criteria per run in persistence and enforce during finalization |
| File-based handoff artifacts | persisted turn/run/session records | prefer DB-backed typed artifacts; optionally mirror to files for tool compatibility |
| Reset vs compaction policy | current deterministic turn flow + future context strategies | add configurable long-running memory strategy per harness/model profile |

## What We Should Learn

1. Split "build" and "judge" responsibilities when output quality depends on critical self-assessment.
2. Make acceptance criteria explicit before execution, not only after.
3. Treat memory policy (reset vs compaction) as configurable strategy, not ideology.
4. Keep long-running progress in structured artifacts the next run can reliably consume.
5. Measure harness ROI continuously: if a component no longer adds lift on newer models, remove it.

## What We Should Not Copy Blindly

1. Do not assume multi-agent is always better; use it only when measured lift justifies cost.
2. Do not rely on file-only inter-agent contracts when we already have stronger persistent run state.
3. Do not bake model-specific behaviors permanently into core architecture.
4. Do not import coding-specific evaluation criteria into the general harness contract.

## Practical Adaptation Path For Our System

1. Add optional run profiles:
   - `single_agent`
   - `planner_generator`
   - `planner_generator_evaluator`
2. Add typed acceptance contracts in persistence:
   - objective
   - completion criteria
   - verification results
3. Add an evaluator harness interface that can:
   - consume run artifacts
   - emit normalized failures and required fixes
   - gate promotion of run status
4. Add per-model memory policy flags for long-running tasks:
   - compaction-preferred
   - reset-with-handoff-preferred
5. Add periodic harness audits tied to model upgrades to simplify non-load-bearing scaffolding.

## Bottom Line

The biggest takeaway is not "three agents." It is "treat harness structure as adaptive control logic around model weaknesses, and re-tune it whenever model capability shifts."

For our architecture, this fits well if we keep typed persistence and lifecycle control in our service layer while allowing specialized planner/generator/evaluator execution styles behind the harness boundary.
