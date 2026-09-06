from langchain_core.messages import AIMessage

from career_coach.graph import _route_after_agent


def test_route_to_finalize_without_tool_call():
    state = {"messages": [AIMessage(content="I have enough information.")]}
    assert _route_after_agent(state) == "finalize"


def test_route_to_tools_when_model_requests_tool():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "calculate_learning_capacity",
                        "args": {"hours_per_week": 8, "target_months": 6},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            )
        ]
    }
    assert _route_after_agent(state) == "tools"
