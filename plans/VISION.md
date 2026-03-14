# Vision: Python-First LLM Chat Workbench

## Mission

A lightweight, web-based LLM chat application that is functional out of the box and serves as a clear, fast framework for experimenting with chat ideas, model integrations, testing out various frameworks (e.g. memory, tools/MCP, etc.), and building simple chat based application experiments.

## Intended Users

- Solo Python developers exploring LLM chat behavior.
- Small teams building custom chat-based applications.
- Fork maintainers who want a clean starting point, not a full product platform.

## Product Positioning

This project is a workbench, not a full-featured end-user product, but it will always be usable in it's default state.

It prioritizes speed of iteration, clarity, and extensibility over breadth of built-in functionality.

## Core Principles

- Python-first developer experience.
- Server-first web architecture with minimal JavaScript.
- Lightweight frontend and low browser-side complexity.
- Adaptive web UI, usable on all platforms.
- Clear, straightforward APIs and class boundaries.
- Few required files and methods to extend or fork.
- Working defaults before optional sophistication.
- Deterministic default behavior where predictability matters.

## Always-Simple Commitments

Even as features grow, these must remain simple:

- Project structure is easy to scan and understand.
- Extension points are obvious and limited in number.
- Core chat flow works without additional coding.
- Major behavior changes can be made with small, localized edits.

## Scope and Non-Goals

### In Scope

- Functional chat app with clear extension seams.
- Iteration-friendly architecture for models, memory, and tools.
- Responsive web UI suitable for desktop and mobile.

### Out of Scope

- Internet-scale reliability and complexity.
- "Everything included" agent framework behavior.
- Mandatory enterprise-grade security in default setup.
- Replicating LLM or Agent frameworks.

## Security Philosophy

- The default template is not required to be secure by default.
- The framework must make it feasible to add secure patterns when needed.
- Security hardening is a later, optional maturity concern.

## Phased Maturity Model

Each phase must:

1. Deliver a usable, runnable chat experience without writing new code.
2. Mature one clear capability area.
3. Explicitly defer complexity not needed for that phase.

## Decision Filter

A proposed feature or change is aligned only if it:

- Preserves out-of-box usability.
- Keeps extension points clear and small.
- Avoids forcing extra complexity into basic usage.
- Improves experimentation velocity for the next phase.
