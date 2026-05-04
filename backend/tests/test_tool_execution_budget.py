from orchestrator import tool_orchestrator


def test_tool_budget_defaults_to_five_seconds():
    assert tool_orchestrator.TOOL_TIMEOUT_S <= 5.0
