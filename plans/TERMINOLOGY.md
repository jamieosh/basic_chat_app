# Workbench Terminology

This document defines the working vocabulary for the repository.

The goal is to stop overloading words like "chat" or "agent" so product discussions, code design, and user-facing behavior can stay aligned.

## Why This Exists

The project began as a chat app. That makes some terms feel obvious in the UI, but too vague in the architecture.

For example:

- a user thinks they are "opening a chat"
- the system is actually loading a durable session
- the visible message list is a transcript
- pressing send starts a run
- the run is executed by a runtime through some adapter boundary

All of those things are related, but they are not the same.

## Core Terms

### Session

A `session` is the durable container for an ongoing unit of work.

A session may include:

- a transcript
- one or more runs
- runtime binding metadata
- agent identity
- scope or profile metadata
- artifacts or outputs
- lineage such as forked-from or replay-derived relationships

From the user's point of view, a session is often what they think of as "a chat I can come back to later."

### Run

A `run` is one execution inside a session.

A run starts because a user sends a message, retries something, replays something, resumes work, or invokes a task.

A run may produce:

- assistant transcript output
- run metadata
- events
- artifacts
- errors or approvals

Runs are important because not every meaningful action in the workbench is just "another message."

### Transcript

A `transcript` is the ordered record of visible user and assistant messages within a session.

It is the canonical conversational history.

It is not the whole durable system state.

### Message

A `message` is one entry in the transcript, such as a user turn or an assistant turn.

Messages are the visible pieces of a conversation. They should not be forced to carry every kind of metadata or output in the system.

### Chat

`Chat` is primarily a surface or interaction style.

In the UI, a user sees a chat-like experience:

- a sidebar or list of things they can open
- a message stream
- a text box
- a send action

In the simplest case, one visible "chat" maps closely to one session.

In a richer workbench, chat remains a useful surface, but it is not the full domain model.

### Conversation

A `conversation` is the human-level concept of an ongoing exchange.

It usually corresponds closely to the transcript, but a session may contain multiple conversational arcs or shifts in purpose over time.

Conversation is useful language for UX and product thinking, but it is less precise than session or transcript for system design.

### Task

A `task` is a goal-oriented piece of work.

Examples:

- summarize this document
- compare two model responses
- draft a design
- prepare a morning report

A task may happen in one run or across many runs inside the same session.

Tasks are about intent, not necessarily about persistence identity.

### Agent

An `agent` is a reusable behavior package.

An agent may include:

- a core instruction set such as `SOUL.md`
- prompt or behavior files
- skills
- available tools
- sub-agent definitions or delegation rules
- memory and context policy
- tone, persona, or standards
- model or runtime preferences

An agent is not just a model name.

An agent is also not the same thing as a single session. The same agent definition may be used in many sessions.

### Harness

A `harness` is an execution adapter boundary.

Its job is to take a normalized request from the workbench, execute it against some runtime, and return normalized results, events, and failures.

A harness may handle:

- request construction
- provider or runtime invocation
- context assembly hooks
- tool-call normalization
- event production
- failure mapping

A harness is smaller and more technical than an agent definition.

It helps the workbench speak to different runtimes without turning the UI into provider-specific code.

### Runtime

A `runtime` is the system that actually executes a run.

Examples of runtime shapes:

- a native runtime implemented in this repository
- a provider-backed harness such as an OpenAI or Anthropic adapter
- an external or federated agent runtime system such as OpenClaw or Hermes

The workbench should be able to present a consistent user experience even when runtime shapes differ.

### Runtime Binding

A `runtime binding` is the session-level decision about what runtime a session is attached to.

That may include:

- runtime type
- harness key
- provider or model details
- version or profile details
- external runtime identifiers where applicable

### Context

`Context` is the information assembled for a run.

It may include:

- transcript history
- session profile
- user or project information
- brand voice or engineering standards
- memory retrieved for the run
- tool state

Context is execution input, not the same thing as transcript history or long-term memory.

### Memory

`Memory` is an overloaded term and should be used carefully.

Keep these separate:

- transcript history
- run-time working context
- durable user or project memory
- external retrieval or knowledge sources

### Artifact

An `artifact` is a non-transcript output attached to a session or run.

Examples:

- a generated plan
- a comparison result
- a report
- an approval item
- a structured summary

Artifacts exist because not every useful output should be hidden inside a chat message.

### Lineage

`Lineage` describes how sessions or runs are related.

Examples:

- forked from
- replayed from
- derived from
- compared against

Lineage makes branch, compare, and resume workflows inspectable rather than implicit.

## How These Terms Relate

The intended relationship is:

- a session contains one or more runs
- a session may have a transcript as one important record
- a transcript contains messages
- a run may append messages to the transcript
- a run may also produce artifacts and metadata outside the transcript
- an agent definition shapes how runs behave within a session
- a runtime executes those runs
- a harness is one adapter boundary through which the workbench talks to that runtime

## What The User Sees

In the current web UI, the user mostly experiences the system as a chat website.

They see:

- a list of chat entries
- a selected chat view
- a message stream
- a text box and send action

The user naturally thinks:

- "I opened a chat"
- "I can see my conversation"
- "I sent a message"
- "the AI replied"

That language is useful in the UI, but the backend meaning is more precise.

## What Is Happening Behind The Scenes

When the user opens a chat entry:

- the system loads a session
- it loads that session's transcript and metadata
- it renders the transcript in a chat-shaped surface

When the user sends a message:

- the system creates a new run in the existing session
- it assembles context for that run
- it executes the run through the bound runtime
- it records the outcome
- it appends visible transcript output where appropriate

When the user retries, forks, replays, or compares:

- the system may create a new run
- or it may create a new session with lineage back to the earlier one
- the transcript may be reused, summarized, or partially projected
- the runtime may stay the same or deliberately differ

That is why a "chat" should be treated as a surface, not the full system model.

## User-Experience Translation

Useful translation between user language and system language:

- "chat in the sidebar" -> session entry
- "message stream" -> transcript
- "send" -> start a run
- "AI response" -> visible result of a run
- "try again" -> another run
- "start from here" -> new session with lineage
- "compare outputs" -> multiple runs or sessions viewed together

## Why This Matters For Product Design

This vocabulary helps the project avoid several common traps:

- treating every feature as just more chat messages
- confusing agent behavior with provider implementation
- tying the workbench too tightly to one native runtime
- making replay, compare, scheduling, or artifacts feel unnatural

It also leaves room for the workbench to connect to external runtime systems in the future while keeping a coherent user experience.
