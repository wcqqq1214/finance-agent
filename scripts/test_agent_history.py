"""End-to-end test for agent history system."""

from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.database.agent_history import (
    init_db,
    save_analysis_run,
    save_agent_execution,
    save_tool_call,
    query_analysis_runs,
    query_run_detail
)
from app.database.message_adapter import convert_messages_to_standard
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage


def test_complete_workflow():
    """Test complete workflow: write and query agent history."""
    print("=== Agent History System E2E Test ===\n")

    # Setup
    db_path = "data/agent_history.db"
    init_db(db_path)
    print("✓ Database initialized")

    # Create test data
    run_id = "20260321_999999"
    asset = "TEST"
    query = "Test query for E2E"
    tz = timezone(timedelta(hours=8))
    timestamp = datetime.now(tz)

    save_analysis_run(run_id, asset, query, timestamp, "Test decision", db_path)
    print(f"✓ Saved analysis run: {run_id}")

    # Create agent execution with messages
    import uuid
    exec_id = str(uuid.uuid4())

    messages = [
        SystemMessage(content="You are a test agent"),
        HumanMessage(content="Test query"),
        AIMessage(
            content="",
            tool_calls=[{"id": "call_1", "name": "test_tool", "args": {"param": "value"}}]
        ),
        ToolMessage(content='{"result": "success"}', tool_call_id="call_1"),
        AIMessage(content="Test complete")
    ]

    standard_messages = convert_messages_to_standard(messages)

    save_agent_execution(
        exec_id, run_id, "test", standard_messages,
        timestamp, "Test output", timestamp, db_path
    )
    print(f"✓ Saved agent execution: {exec_id}")

    # Save tool call
    call_id = str(uuid.uuid4())
    save_tool_call(
        call_id, exec_id, "test_tool",
        {"param": "value"}, "success", timestamp,
        {"result": "success"}, db_path=db_path
    )
    print(f"✓ Saved tool call: {call_id}")

    # Query back
    runs = query_analysis_runs(asset=asset, db_path=db_path)
    assert len(runs) >= 1
    print(f"✓ Queried {len(runs)} analysis runs")

    detail = query_run_detail(run_id, db_path)
    assert detail is not None
    assert len(detail["agents"]) == 1
    print(f"✓ Queried run detail with {len(detail['agents'])} agents")

    print("\n=== All tests passed! ===")


if __name__ == "__main__":
    test_complete_workflow()
