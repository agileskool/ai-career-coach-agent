# ADR-001 — Use LangGraph for V0.1 orchestration

**Status:** Accepted

## Context

The project is being built both as a useful product experiment and as an interview showcase. The implementation therefore needs to make agent mechanics visible: state, model decisions, tool execution, routing, loops, and later persistence/human-in-the-loop.

## Decision

Use the LangGraph Graph API for the first version instead of starting with a higher-level `create_agent(...)` abstraction.

## Rationale

- makes state explicit;
- makes model and tool nodes visible;
- makes conditional routing inspectable;
- demonstrates the agent loop directly;
- provides a natural path to persistence and human-in-the-loop later;
- supports a stronger architecture discussion in interviews.

## Trade-offs

- more code than a higher-level agent helper;
- more framework concepts to learn;
- greater responsibility for graph design and state contracts.

The extra explicitness is intentional for this project's learning and showcase goals.
