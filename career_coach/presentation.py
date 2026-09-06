"""Small presentation helpers kept outside the agent."""

from __future__ import annotations

from langchain_core.messages import AIMessage, ToolMessage


def build_execution_trace(messages: list) -> list[dict[str, str]]:
    """Create an interview-friendly trace without exposing chain-of-thought."""

    trace: list[dict[str, str]] = []
    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:
                trace.append(
                    {
                        "event": "tool_requested",
                        "detail": f"{call['name']}({call.get('args', {})})",
                    }
                )
        elif isinstance(message, ToolMessage):
            trace.append(
                {
                    "event": "tool_result",
                    "detail": f"{message.name or 'tool'} returned {message.content}",
                }
            )
    return trace
