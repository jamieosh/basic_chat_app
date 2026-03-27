# Search Tools and Context Engineering: Implications for This Project

## Purpose

This note reviews Elastic's discussion post on search tools for context engineering and maps its ideas to our current chat-harness architecture.

Primary question: do we have anything to learn from this for our system design?

## Reference

- Elastic blog: [The shell tool is not a silver bullet for context engineering](https://www.elastic.co/search-labs/blog/search-tools-context-engineering) (March 25, 2026)

## Core Ideas From The Elastic Post

The article's main claims are:

1. The right design question is not "filesystem vs database"; it is "what search interfaces should the agent use to build context?"
2. Shell tools are a strong general-purpose starting point, but not always the best steady-state interface.
3. Dedicated data/query tools outperform shell-only approaches for repeated structured/analytical retrieval tasks (latency, token cost, reliability).
4. Composing interfaces (shell + dedicated tools) usually beats any single interface, but increases complexity/cost.
5. Progressive disclosure matters: smaller default tool sets reduce context bloat and confusion.
6. Toolset design should follow observed query patterns from runtime logs, not prior assumptions.
7. A useful framing is "low floor vs high ceiling":
   - high-ceiling tools (like shell) are flexible but reasoning-heavy
   - low-floor tools (specialized) are easier/reliable but narrower

## Relation To Our Architecture

Our current architecture already has a strong place to apply these ideas:

- `agents/chat_harness.py` gives us typed tool-call/tool-result event vocabulary.
- `services/chat_turns.py` centralizes execution lifecycle and observability shaping.
- `agents/harness_registry.py` gives stable per-chat harness binding.
- `persistence/repository.py` and run tables give durable run identity/state.
- `agents/context_builders.py` gives us a seam for controlling model-facing context/tool guidance.

This means we can adopt the article's recommendations without changing route contracts.

## What We Already Do That Aligns

1. We already separate app-level lifecycle from provider/runtime implementation details.
2. We already have a normalized event model where tool usage can be represented.
3. We already persist run identity and status, which is a prerequisite for tool-pattern analysis.
4. We already keep provider behavior behind harness adapters instead of in routes.

## What We Can Learn (And Add)

### 1) Treat tool interfaces as first-class architecture, not just implementation detail

We should formally define context-retrieval interface classes in our harness layer (for example: filesystem search, database search, web search, memory recall) and track which class is being used per run.

### 2) Add progressive tool disclosure

We should avoid "all tools always exposed" and expose a minimal base toolset per harness, then add capabilities on demand. This fits naturally in harness-owned tool orchestration and context-builder layers.

### 3) Promote repeated shell query patterns into specialized tools

Where logs show repeated shell-based retrieval/query loops, we should add purpose-built tools with tighter contracts (lower floor) to reduce token overhead and failure rate.

### 4) Make tool telemetry a design driver

The article's strongest operational point is to use command/tool logs to decide when to specialize. For us, this means explicitly recording per-turn tool stats (tool count, retries, latency, failures, repeated sequences) in run metadata/observability.

### 5) Keep both high-ceiling and low-floor paths

Our system should support both:

- high-ceiling path: flexible, general-purpose retrieval/runtime tools
- low-floor path: specialized, reliable tools for common query patterns

This directly matches your design principle that built-ins are convenience and alternative implementation styles should remain possible.

## Gaps In Our Current System Relative To This

1. Tool orchestration is contract-ready but not yet a shipped product behavior.
2. We do not yet have progressive disclosure mechanics for toolsets.
3. We do not yet persist enough tool-usage analytics to drive specialization decisions.
4. We do not yet have an explicit framework for deciding when to move from generic to specialized tools.

## Recommended Direction For This Project

Yes, we have clear learnings to adopt.

The practical direction is:

1. Keep current typed harness + service/repository control plane unchanged.
2. Add optional tool-orchestration policy in harness adapters.
3. Start with minimal default tools and progressive disclosure.
4. Instrument tool usage deeply at run level.
5. Convert high-frequency/low-reliability generic patterns into specialized tools over time.

This preserves our architecture while improving context-engineering effectiveness.

## Bottom Line

The Elastic post reinforces our trajectory rather than contradicting it.

The biggest takeaway for us is not "use shell" or "use databases"; it is to design a measured, observable tool-interface strategy inside the harness boundary, then evolve tool shape from real usage data.
