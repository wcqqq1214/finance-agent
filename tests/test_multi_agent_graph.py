"""Structure tests for multi-agent graph (no LLM calls)."""

from __future__ import annotations

from app.graph_multi import build_multi_agent_graph
from app.state import AgentState


def test_agent_state_typed_dict() -> None:
    s: AgentState = {"query": "test"}
    assert s["query"] == "test"


def test_build_multi_agent_graph_compiles() -> None:
    g = build_multi_agent_graph()
    assert g is not None
    # CompiledStateGraph has invoke
    assert hasattr(g, "invoke")
