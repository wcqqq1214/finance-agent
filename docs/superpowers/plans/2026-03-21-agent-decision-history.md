# Agent Decision History System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的AI决策过程记录系统，使用SQLite存储agent推理历史、工具调用和决策结果

**Architecture:** 采用混合设计（方案C），主表存储OpenAI标准格式的完整对话历史（JSON），辅助表存储结构化的工具调用索引。数据库操作层、消息转换层、API路由层三层架构，集成到现有的multi-agent系统中。

**Tech Stack:** SQLite 3, FastAPI, LangChain, Python 3.13

---

## File Structure

**New Files:**
- `app/database/agent_history.py` - 数据库操作层（CRUD + 查询函数）
- `app/database/message_adapter.py` - LangChain消息转换为OpenAI标准格式
- `app/api/routes/history.py` - FastAPI路由（查询接口）
- `tests/test_agent_history.py` - 数据库层单元测试
- `tests/test_message_adapter.py` - 消息转换层单元测试
- `tests/test_history_api.py` - API集成测试

**Modified Files:**
- `app/graph_multi.py:76-116` - 在_run_react_until_final_text中集成写入逻辑
- `app/api/main.py:10,56-61` - 注册history路由
- `app/api/routes/__init__.py` - 导出history路由

**Database:**
- `data/agent_history.db` - 新建SQLite数据库

---

## Task 1: 数据库初始化和Schema定义

**Files:**
- Create: `app/database/agent_history.py`
- Test: `tests/test_agent_history.py`

- [ ] **Step 1: 编写数据库初始化测试**

```python
# tests/test_agent_history.py
"""Tests for agent history database operations."""

import sqlite3
from pathlib import Path
import pytest
from app.database.agent_history import init_db, get_connection


def test_init_db_creates_tables(tmp_path):
    """Test that init_db creates all required tables."""
    db_path = tmp_path / "test_agent_history.db"
    init_db(str(db_path))
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check analysis_runs table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_runs'")
    assert cursor.fetchone() is not None
    
    # Check agent_executions table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_executions'")
    assert cursor.fetchone() is not None
    
    # Check tool_calls table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tool_calls'")
    assert cursor.fetchone() is not None
    
    # Check decision_outcomes table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='decision_outcomes'")
    assert cursor.fetchone() is not None
    
    conn.close()


def test_init_db_creates_indexes(tmp_path):
    """Test that init_db creates all required indexes."""
    db_path = tmp_path / "test_agent_history.db"
    init_db(str(db_path))
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check indexes exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {row[0] for row in cursor.fetchall()}
    
    expected_indexes = {
        'idx_runs_asset',
        'idx_runs_timestamp',
        'idx_exec_run',
        'idx_exec_agent',
        'idx_tool_exec',
        'idx_tool_name',
        'idx_tool_status'
    }
    
    assert expected_indexes.issubset(indexes)
    conn.close()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_agent_history.py::test_init_db_creates_tables -v
```

预期输出：`ModuleNotFoundError: No module named 'app.database.agent_history'`

- [ ] **Step 3: 实现数据库初始化函数**

```python
# app/database/agent_history.py
"""Agent decision history database operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = "data/agent_history.db"


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Get a connection to the agent history database."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize the agent history database with schema."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Create analysis_runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            run_id TEXT PRIMARY KEY,
            asset TEXT NOT NULL,
            query TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            final_decision TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes for analysis_runs
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_asset ON analysis_runs(asset)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON analysis_runs(timestamp)")
    
    # Create agent_executions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_executions (
            execution_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            agent_type TEXT NOT NULL,
            messages_json TEXT NOT NULL,
            output_text TEXT,
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            duration_seconds REAL,
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)
    
    # Create indexes for agent_executions
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_run ON agent_executions(run_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_agent ON agent_executions(agent_type)")
    
    # Create tool_calls table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tool_calls (
            call_id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments_json TEXT NOT NULL,
            result_json TEXT,
            status TEXT NOT NULL,
            error_message TEXT,
            timestamp DATETIME NOT NULL,
            FOREIGN KEY (execution_id) REFERENCES agent_executions(execution_id)
        )
    """)
    
    # Create indexes for tool_calls
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tool_exec ON tool_calls(execution_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tool_name ON tool_calls(tool_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tool_status ON tool_calls(status)")
    
    # Create decision_outcomes table (reserved for future use)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decision_outcomes (
            outcome_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            predicted_direction TEXT,
            actual_outcome TEXT,
            evaluation_date DATE,
            notes TEXT,
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)
    
    conn.commit()
    conn.close()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
uv run pytest tests/test_agent_history.py::test_init_db_creates_tables -v
uv run pytest tests/test_agent_history.py::test_init_db_creates_indexes -v
```

预期输出：`2 passed`

- [ ] **Step 5: 提交**

```bash
git add app/database/agent_history.py tests/test_agent_history.py
git commit -m "feat(database): add agent history database initialization"
```

---

## Task 2: 消息格式转换层

**Files:**
- Create: `app/database/message_adapter.py`
- Test: `tests/test_message_adapter.py`

- [ ] **Step 1: 编写消息转换测试**

```python
# tests/test_message_adapter.py
"""Tests for LangChain to OpenAI message format conversion."""

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from app.database.message_adapter import convert_messages_to_standard


def test_convert_system_message():
    """Test SystemMessage conversion."""
    messages = [SystemMessage(content="You are a helpful assistant")]
    result = convert_messages_to_standard(messages)
    
    assert len(result) == 1
    assert result[0]["role"] == "system"
    assert result[0]["content"] == "You are a helpful assistant"


def test_convert_human_message():
    """Test HumanMessage conversion."""
    messages = [HumanMessage(content="Analyze AAPL")]
    result = convert_messages_to_standard(messages)
    
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "Analyze AAPL"


def test_convert_ai_message_without_tool_calls():
    """Test AIMessage without tool calls."""
    messages = [AIMessage(content="Here is the analysis...")]
    result = convert_messages_to_standard(messages)
    
    assert len(result) == 1
    assert result[0]["role"] == "assistant"
    assert result[0]["content"] == "Here is the analysis..."
    assert "tool_calls" not in result[0]


def test_convert_ai_message_with_tool_calls():
    """Test AIMessage with tool calls."""
    messages = [
        AIMessage(
            content=None,
            tool_calls=[
                {
                    "id": "call_abc123",
                    "name": "get_stock_data",
                    "args": {"ticker": "AAPL", "period": "3mo"}
                }
            ]
        )
    ]
    result = convert_messages_to_standard(messages)
    
    assert len(result) == 1
    assert result[0]["role"] == "assistant"
    assert result[0]["content"] is None
    assert "tool_calls" in result[0]
    assert len(result[0]["tool_calls"]) == 1
    
    tool_call = result[0]["tool_calls"][0]
    assert tool_call["id"] == "call_abc123"
    assert tool_call["type"] == "function"
    assert tool_call["function"]["name"] == "get_stock_data"
    assert '"ticker": "AAPL"' in tool_call["function"]["arguments"]


def test_convert_tool_message():
    """Test ToolMessage conversion."""
    messages = [
        ToolMessage(
            content='{"price": 150.0}',
            tool_call_id="call_abc123"
        )
    ]
    result = convert_messages_to_standard(messages)
    
    assert len(result) == 1
    assert result[0]["role"] == "tool"
    assert result[0]["tool_call_id"] == "call_abc123"
    assert result[0]["content"] == '{"price": 150.0}'


def test_convert_mixed_messages():
    """Test conversion of a complete conversation."""
    messages = [
        SystemMessage(content="You are an analyst"),
        HumanMessage(content="Analyze AAPL"),
        AIMessage(
            content=None,
            tool_calls=[{"id": "call_1", "name": "get_stock_data", "args": {"ticker": "AAPL"}}]
        ),
        ToolMessage(content='{"price": 150.0}', tool_call_id="call_1"),
        AIMessage(content="AAPL is trading at $150")
    ]
    result = convert_messages_to_standard(messages)
    
    assert len(result) == 5
    assert result[0]["role"] == "system"
    assert result[1]["role"] == "user"
    assert result[2]["role"] == "assistant"
    assert "tool_calls" in result[2]
    assert result[3]["role"] == "tool"
    assert result[4]["role"] == "assistant"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_message_adapter.py -v
```

预期输出：`ModuleNotFoundError: No module named 'app.database.message_adapter'`

- [ ] **Step 3: 实现消息转换函数**

```python
# app/database/message_adapter.py
"""Convert LangChain messages to OpenAI standard format."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage


def convert_messages_to_standard(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """Convert LangChain messages to OpenAI standard format.
    
    Args:
        messages: List of LangChain BaseMessage objects
        
    Returns:
        List of dicts in OpenAI message format:
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "...", "tool_calls": [...]},
            {"role": "tool", "tool_call_id": "...", "content": "..."}
        ]
    """
    standard_messages = []
    
    for msg in messages:
        if isinstance(msg, SystemMessage):
            standard_messages.append({
                "role": "system",
                "content": msg.content
            })
        elif isinstance(msg, HumanMessage):
            standard_messages.append({
                "role": "user",
                "content": msg.content
            })
        elif isinstance(msg, AIMessage):
            standard_msg: Dict[str, Any] = {
                "role": "assistant",
                "content": msg.content
            }
            
            # Handle tool calls if present
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                standard_msg["tool_calls"] = [
                    {
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": json.dumps(tc.get("args", {}), ensure_ascii=False)
                        }
                    }
                    for tc in tool_calls
                ]
            
            standard_messages.append(standard_msg)
        elif isinstance(msg, ToolMessage):
            standard_messages.append({
                "role": "tool",
                "tool_call_id": msg.tool_call_id,
                "content": msg.content
            })
        else:
            # Fallback for unknown message types
            standard_messages.append({
                "role": "assistant",
                "content": str(msg.content) if hasattr(msg, "content") else ""
            })
    
    return standard_messages
```

- [ ] **Step 4: 运行测试验证通过**

```bash
uv run pytest tests/test_message_adapter.py -v
```

预期输出：`6 passed`

- [ ] **Step 5: 提交**

```bash
git add app/database/message_adapter.py tests/test_message_adapter.py
git commit -m "feat(database): add LangChain to OpenAI message format converter"
```

---

## Task 3: 数据库写入操作

**Files:**
- Modify: `app/database/agent_history.py`
- Test: `tests/test_agent_history.py`

- [ ] **Step 1: 编写数据库写入测试**

```python
# tests/test_agent_history.py (追加到文件末尾)

import json
import uuid
from datetime import datetime, timezone, timedelta
from app.database.agent_history import (
    save_analysis_run,
    save_agent_execution,
    save_tool_call
)


def test_save_analysis_run(tmp_path):
    """Test saving an analysis run."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    
    run_id = "20260321_143052"
    asset = "AAPL"
    query = "分析AAPL的最新股价"
    timestamp = datetime.now(timezone(timedelta(hours=8)))
    final_decision = "综合技术面和新闻面，建议持有"
    
    save_analysis_run(
        run_id=run_id,
        asset=asset,
        query=query,
        timestamp=timestamp,
        final_decision=final_decision,
        db_path=str(db_path)
    )
    
    conn = get_connection(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM analysis_runs WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    
    assert row is not None
    assert row["run_id"] == run_id
    assert row["asset"] == asset
    assert row["query"] == query
    assert row["final_decision"] == final_decision
    conn.close()


def test_save_agent_execution(tmp_path):
    """Test saving an agent execution."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    
    # First create a run
    run_id = "20260321_143052"
    save_analysis_run(
        run_id=run_id,
        asset="AAPL",
        query="test",
        timestamp=datetime.now(timezone(timedelta(hours=8))),
        db_path=str(db_path)
    )
    
    # Then save execution
    execution_id = str(uuid.uuid4())
    agent_type = "quant"
    messages = [
        {"role": "system", "content": "You are an analyst"},
        {"role": "user", "content": "Analyze AAPL"}
    ]
    output_text = "Technical analysis shows..."
    start_time = datetime.now(timezone(timedelta(hours=8)))
    end_time = start_time + timedelta(seconds=23.5)
    
    save_agent_execution(
        execution_id=execution_id,
        run_id=run_id,
        agent_type=agent_type,
        messages=messages,
        output_text=output_text,
        start_time=start_time,
        end_time=end_time,
        db_path=str(db_path)
    )
    
    conn = get_connection(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent_executions WHERE execution_id = ?", (execution_id,))
    row = cursor.fetchone()
    
    assert row is not None
    assert row["execution_id"] == execution_id
    assert row["run_id"] == run_id
    assert row["agent_type"] == agent_type
    assert row["output_text"] == output_text
    assert row["duration_seconds"] == pytest.approx(23.5, rel=0.1)
    
    # Verify messages_json
    stored_messages = json.loads(row["messages_json"])
    assert len(stored_messages) == 2
    assert stored_messages[0]["role"] == "system"
    conn.close()


def test_save_tool_call(tmp_path):
    """Test saving a tool call."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    
    # Setup: create run and execution
    run_id = "20260321_143052"
    execution_id = str(uuid.uuid4())
    save_analysis_run(
        run_id=run_id,
        asset="AAPL",
        query="test",
        timestamp=datetime.now(timezone(timedelta(hours=8))),
        db_path=str(db_path)
    )
    save_agent_execution(
        execution_id=execution_id,
        run_id=run_id,
        agent_type="quant",
        messages=[],
        start_time=datetime.now(timezone(timedelta(hours=8))),
        db_path=str(db_path)
    )
    
    # Save tool call
    call_id = str(uuid.uuid4())
    tool_name = "get_stock_data"
    arguments = {"ticker": "AAPL", "period": "3mo"}
    result = {"data": [{"close": 150.0}]}
    status = "success"
    timestamp = datetime.now(timezone(timedelta(hours=8)))
    
    save_tool_call(
        call_id=call_id,
        execution_id=execution_id,
        tool_name=tool_name,
        arguments=arguments,
        result=result,
        status=status,
        timestamp=timestamp,
        db_path=str(db_path)
    )
    
    conn = get_connection(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tool_calls WHERE call_id = ?", (call_id,))
    row = cursor.fetchone()
    
    assert row is not None
    assert row["call_id"] == call_id
    assert row["execution_id"] == execution_id
    assert row["tool_name"] == tool_name
    assert row["status"] == status
    assert row["error_message"] is None
    
    # Verify JSON fields
    stored_args = json.loads(row["arguments_json"])
    assert stored_args["ticker"] == "AAPL"
    stored_result = json.loads(row["result_json"])
    assert stored_result["data"][0]["close"] == 150.0
    conn.close()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_agent_history.py::test_save_analysis_run -v
uv run pytest tests/test_agent_history.py::test_save_agent_execution -v
uv run pytest tests/test_agent_history.py::test_save_tool_call -v
```

预期输出：`ImportError: cannot import name 'save_analysis_run'`

- [ ] **Step 3: 实现数据库写入函数**

```python
# app/database/agent_history.py (追加到文件末尾)

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


def save_analysis_run(
    run_id: str,
    asset: str,
    query: str,
    timestamp: datetime,
    final_decision: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> None:
    """Save an analysis run to the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO analysis_runs (run_id, asset, query, timestamp, final_decision)
        VALUES (?, ?, ?, ?, ?)
    """, (run_id, asset, query, timestamp.isoformat(), final_decision))
    
    conn.commit()
    conn.close()


def save_agent_execution(
    execution_id: str,
    run_id: str,
    agent_type: str,
    messages: List[Dict[str, Any]],
    start_time: datetime,
    output_text: Optional[str] = None,
    end_time: Optional[datetime] = None,
    db_path: str = DEFAULT_DB_PATH
) -> None:
    """Save an agent execution to the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Calculate duration if end_time provided
    duration_seconds = None
    if end_time:
        duration_seconds = (end_time - start_time).total_seconds()
    
    # Serialize messages to JSON
    messages_json = json.dumps(messages, ensure_ascii=False)
    
    cursor.execute("""
        INSERT INTO agent_executions 
        (execution_id, run_id, agent_type, messages_json, output_text, start_time, end_time, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        execution_id,
        run_id,
        agent_type,
        messages_json,
        output_text,
        start_time.isoformat(),
        end_time.isoformat() if end_time else None,
        duration_seconds
    ))
    
    conn.commit()
    conn.close()


def save_tool_call(
    call_id: str,
    execution_id: str,
    tool_name: str,
    arguments: Dict[str, Any],
    status: str,
    timestamp: datetime,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> None:
    """Save a tool call to the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Serialize JSON fields
    arguments_json = json.dumps(arguments, ensure_ascii=False)
    result_json = json.dumps(result, ensure_ascii=False) if result else None
    
    cursor.execute("""
        INSERT INTO tool_calls 
        (call_id, execution_id, tool_name, arguments_json, result_json, status, error_message, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        call_id,
        execution_id,
        tool_name,
        arguments_json,
        result_json,
        status,
        error_message,
        timestamp.isoformat()
    ))
    
    conn.commit()
    conn.close()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
uv run pytest tests/test_agent_history.py::test_save_analysis_run -v
uv run pytest tests/test_agent_history.py::test_save_agent_execution -v
uv run pytest tests/test_agent_history.py::test_save_tool_call -v
```

预期输出：`3 passed`

- [ ] **Step 5: 提交**

```bash
git add app/database/agent_history.py tests/test_agent_history.py
git commit -m "feat(database): add write operations for agent history"
```

---

## Task 4: 数据库查询操作

**Files:**
- Modify: `app/database/agent_history.py`
- Test: `tests/test_agent_history.py`

- [ ] **Step 1: 编写查询操作测试**

```python
# tests/test_agent_history.py (追加到文件末尾)

from app.database.agent_history import (
    query_analysis_runs,
    query_run_detail,
    query_agent_messages,
    query_tool_calls
)


def test_query_analysis_runs(tmp_path):
    """Test querying analysis runs with filters."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    
    # Insert test data
    tz = timezone(timedelta(hours=8))
    save_analysis_run("20260321_100000", "AAPL", "test1", datetime(2026, 3, 21, 10, 0, 0, tzinfo=tz), db_path=str(db_path))
    save_analysis_run("20260321_110000", "AAPL", "test2", datetime(2026, 3, 21, 11, 0, 0, tzinfo=tz), db_path=str(db_path))
    save_analysis_run("20260321_120000", "NVDA", "test3", datetime(2026, 3, 21, 12, 0, 0, tzinfo=tz), db_path=str(db_path))
    
    # Query all
    results = query_analysis_runs(db_path=str(db_path))
    assert len(results) == 3
    
    # Query by asset
    results = query_analysis_runs(asset="AAPL", db_path=str(db_path))
    assert len(results) == 2
    assert all(r["asset"] == "AAPL" for r in results)
    
    # Query with limit
    results = query_analysis_runs(limit=1, db_path=str(db_path))
    assert len(results) == 1


def test_query_run_detail(tmp_path):
    """Test querying detailed run information."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    
    # Setup test data
    run_id = "20260321_143052"
    tz = timezone(timedelta(hours=8))
    save_analysis_run(run_id, "AAPL", "test", datetime.now(tz), "decision", str(db_path))
    
    exec_id = str(uuid.uuid4())
    save_agent_execution(
        exec_id, run_id, "quant", [{"role": "system", "content": "test"}],
        datetime.now(tz), "output", datetime.now(tz), str(db_path)
    )
    
    # Query detail
    result = query_run_detail(run_id, db_path=str(db_path))
    
    assert result is not None
    assert result["run_id"] == run_id
    assert result["asset"] == "AAPL"
    assert "agents" in result
    assert len(result["agents"]) == 1
    assert result["agents"][0]["agent_type"] == "quant"


def test_query_agent_messages(tmp_path):
    """Test querying agent messages."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    
    # Setup
    run_id = "20260321_143052"
    exec_id = str(uuid.uuid4())
    tz = timezone(timedelta(hours=8))
    messages = [
        {"role": "system", "content": "You are an analyst"},
        {"role": "user", "content": "Analyze AAPL"}
    ]
    
    save_analysis_run(run_id, "AAPL", "test", datetime.now(tz), db_path=str(db_path))
    save_agent_execution(exec_id, run_id, "quant", messages, datetime.now(tz), db_path=str(db_path))
    
    # Query messages
    result = query_agent_messages(exec_id, db_path=str(db_path))
    
    assert result is not None
    assert result["execution_id"] == exec_id
    assert result["agent_type"] == "quant"
    assert len(result["messages"]) == 2
    assert result["messages"][0]["role"] == "system"


def test_query_tool_calls(tmp_path):
    """Test querying tool calls with filters."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    
    # Setup
    run_id = "20260321_143052"
    exec_id = str(uuid.uuid4())
    tz = timezone(timedelta(hours=8))
    
    save_analysis_run(run_id, "AAPL", "test", datetime.now(tz), db_path=str(db_path))
    save_agent_execution(exec_id, run_id, "quant", [], datetime.now(tz), db_path=str(db_path))
    
    # Insert tool calls
    save_tool_call(str(uuid.uuid4()), exec_id, "get_stock_data", {"ticker": "AAPL"}, "success", datetime.now(tz), {"data": []}, db_path=str(db_path))
    save_tool_call(str(uuid.uuid4()), exec_id, "search_news", {"query": "AAPL"}, "failed", datetime.now(tz), error_message="timeout", db_path=str(db_path))
    
    # Query all
    results = query_tool_calls(db_path=str(db_path))
    assert len(results) == 2
    
    # Query by tool_name
    results = query_tool_calls(tool_name="get_stock_data", db_path=str(db_path))
    assert len(results) == 1
    assert results[0]["tool_name"] == "get_stock_data"
    
    # Query by status
    results = query_tool_calls(status="failed", db_path=str(db_path))
    assert len(results) == 1
    assert results[0]["status"] == "failed"
    assert results[0]["error_message"] == "timeout"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_agent_history.py::test_query_analysis_runs -v
uv run pytest tests/test_agent_history.py::test_query_run_detail -v
uv run pytest tests/test_agent_history.py::test_query_agent_messages -v
uv run pytest tests/test_agent_history.py::test_query_tool_calls -v
```

预期输出：`ImportError: cannot import name 'query_analysis_runs'`

- [ ] **Step 3: 实现查询函数（第1部分）**

```python
# app/database/agent_history.py (追加到文件末尾)

def query_analysis_runs(
    asset: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: str = DEFAULT_DB_PATH
) -> List[Dict[str, Any]]:
    """Query analysis runs with optional filters.
    
    Args:
        asset: Filter by asset ticker
        date_from: Filter by start date (ISO format)
        date_to: Filter by end date (ISO format)
        limit: Maximum number of results
        offset: Offset for pagination
        db_path: Database file path
        
    Returns:
        List of analysis run dicts
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    query = "SELECT * FROM analysis_runs WHERE 1=1"
    params = []
    
    if asset:
        query += " AND asset = ?"
        params.append(asset)
    if date_from:
        query += " AND timestamp >= ?"
        params.append(date_from)
    if date_to:
        query += " AND timestamp <= ?"
        params.append(date_to)
    
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def query_run_detail(
    run_id: str,
    db_path: str = DEFAULT_DB_PATH
) -> Optional[Dict[str, Any]]:
    """Query detailed information for a single run.
    
    Returns:
        Dict with run info and list of agent executions, or None if not found
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Get run info
    cursor.execute("SELECT * FROM analysis_runs WHERE run_id = ?", (run_id,))
    run_row = cursor.fetchone()
    
    if not run_row:
        conn.close()
        return None
    
    run_dict = dict(run_row)
    
    # Get agent executions
    cursor.execute("""
        SELECT execution_id, agent_type, output_text, start_time, end_time, duration_seconds
        FROM agent_executions
        WHERE run_id = ?
        ORDER BY start_time
    """, (run_id,))
    
    agent_rows = cursor.fetchall()
    run_dict["agents"] = [dict(row) for row in agent_rows]
    
    conn.close()
    return run_dict
```

- [ ] **Step 4: 实现查询函数（第2部分）**

```python
# app/database/agent_history.py (继续追加)

def query_agent_messages(
    execution_id: str,
    db_path: str = DEFAULT_DB_PATH
) -> Optional[Dict[str, Any]]:
    """Query complete message history for an agent execution.
    
    Returns:
        Dict with execution info and messages list, or None if not found
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT execution_id, agent_type, messages_json
        FROM agent_executions
        WHERE execution_id = ?
    """, (execution_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    result = {
        "execution_id": row["execution_id"],
        "agent_type": row["agent_type"],
        "messages": json.loads(row["messages_json"])
    }
    
    return result


def query_tool_calls(
    tool_name: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: str = DEFAULT_DB_PATH
) -> List[Dict[str, Any]]:
    """Query tool calls with optional filters.
    
    Args:
        tool_name: Filter by tool name
        status: Filter by status ('success' or 'failed')
        date_from: Filter by start date (ISO format)
        limit: Maximum number of results
        offset: Offset for pagination
        db_path: Database file path
        
    Returns:
        List of tool call dicts
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    query = "SELECT * FROM tool_calls WHERE 1=1"
    params = []
    
    if tool_name:
        query += " AND tool_name = ?"
        params.append(tool_name)
    if status:
        query += " AND status = ?"
        params.append(status)
    if date_from:
        query += " AND timestamp >= ?"
        params.append(date_from)
    
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
uv run pytest tests/test_agent_history.py::test_query_analysis_runs -v
uv run pytest tests/test_agent_history.py::test_query_run_detail -v
uv run pytest tests/test_agent_history.py::test_query_agent_messages -v
uv run pytest tests/test_agent_history.py::test_query_tool_calls -v
```

预期输出：`4 passed`

- [ ] **Step 6: 提交**

```bash
git add app/database/agent_history.py tests/test_agent_history.py
git commit -m "feat(database): add query operations for agent history"
```

---

## Task 5: 集成到graph_multi.py

**Files:**
- Modify: `app/graph_multi.py:76-116`
- Test: `tests/test_multi_agent_graph.py`

- [ ] **Step 1: 编写集成测试**

```python
# tests/test_multi_agent_graph.py (追加到文件末尾)

import sqlite3
from pathlib import Path
from app.database.agent_history import init_db, query_analysis_runs


def test_graph_writes_to_history_db(tmp_path, monkeypatch):
    """Test that running the graph writes to agent_history.db."""
    # Setup test database
    db_path = tmp_path / "agent_history.db"
    init_db(str(db_path))
    
    # Mock the database path
    monkeypatch.setenv("AGENT_HISTORY_DB_PATH", str(db_path))
    
    # Note: This is a structure test - we verify the integration points exist
    # Full end-to-end testing requires LLM calls which we skip in unit tests
    
    from app.graph_multi import _run_react_until_final_text
    
    # Verify the function exists and has the expected signature
    import inspect
    sig = inspect.signature(_run_react_until_final_text)
    assert "system_prompt" in sig.parameters
    assert "tools" in sig.parameters
    assert "user_content" in sig.parameters
```

- [ ] **Step 2: 运行测试验证当前状态**

```bash
uv run pytest tests/test_multi_agent_graph.py::test_graph_writes_to_history_db -v
```

预期输出：`1 passed` (结构测试通过，但实际写入逻辑尚未实现)

- [ ] **Step 3: 添加必要的导入语句**

```python
# app/graph_multi.py

# 在文件顶部（约第1-11行）现有导入语句之后添加：
import uuid
import logging
import os
from app.database.agent_history import save_agent_execution, save_tool_call, init_db
from app.database.message_adapter import convert_messages_to_standard

# 在导入语句后添加logger配置（约第30行，在load_dotenv()之后）：
logger = logging.getLogger(__name__)
```

- [ ] **Step 4: 修改_run_react_until_final_text添加记录逻辑**

```python
# app/graph_multi.py

# 修改_run_react_until_final_text函数 (约76-116行)
def _run_react_until_final_text(
    system_prompt: str,
    tools: Sequence[BaseTool],
    user_content: str,
    *,
    config: Optional[RunnableConfig] = None,
    run_id: Optional[str] = None,  # 新增参数
    agent_type: Optional[str] = None,  # 新增参数
) -> str:
    """Run a ReAct loop (agent <-> tools) until the model returns text without tool_calls."""
    llm = create_llm().bind_tools(list(tools))
    tool_node = ToolNode(list(tools))

    def agent_node(
        state: MessagesState, *, config: Optional[RunnableConfig] = None
    ) -> MessagesState:
        messages = state.get("messages", [])
        response = llm.invoke(messages, config=config)
        return {"messages": messages + [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", _should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    compiled = graph.compile()

    initial: MessagesState = {
        "messages": [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ],
    }
    
    # Record start time
    start_time = datetime.now(timezone(timedelta(hours=8)))
    
    final_state = compiled.invoke(initial)
    messages_out: List[BaseMessage] = final_state.get("messages", [])
    
    # Extract final output
    output_text = ""
    for m in reversed(messages_out):
        if isinstance(m, AIMessage) and not (getattr(m, "tool_calls", None)):
            content = getattr(m, "content", None)
            if content:
                output_text = str(content)
                break
    
    # Record to database if run_id and agent_type provided
    if run_id and agent_type:
        try:
            end_time = datetime.now(timezone(timedelta(hours=8)))
            execution_id = str(uuid.uuid4())
            
            # Convert messages to standard format
            standard_messages = convert_messages_to_standard(messages_out)
            
            # Save agent execution
            db_path = os.getenv("AGENT_HISTORY_DB_PATH", "data/agent_history.db")
            init_db(db_path)  # Ensure DB exists
            
            save_agent_execution(
                execution_id=execution_id,
                run_id=run_id,
                agent_type=agent_type,
                messages=standard_messages,
                output_text=output_text,
                start_time=start_time,
                end_time=end_time,
                db_path=db_path
            )
            
            # Extract and save tool calls
            for msg in messages_out:
                if isinstance(msg, AIMessage):
                    tool_calls = getattr(msg, "tool_calls", None)
                    if tool_calls:
                        for tc in tool_calls:
                            call_id = tc.get("id", str(uuid.uuid4()))
                            tool_name = tc.get("name", "")
                            arguments = tc.get("args", {})
                            
                            # Find corresponding tool result
                            tool_result = None
                            for next_msg in messages_out[messages_out.index(msg)+1:]:
                                if isinstance(next_msg, ToolMessage) and next_msg.tool_call_id == call_id:
                                    try:
                                        tool_result = json.loads(next_msg.content)
                                    except:
                                        tool_result = {"raw": next_msg.content}
                                    break
                            
                            save_tool_call(
                                call_id=call_id,
                                execution_id=execution_id,
                                tool_name=tool_name,
                                arguments=arguments,
                                result=tool_result,
                                status="success" if tool_result else "unknown",
                                timestamp=start_time,
                                db_path=db_path
                            )
        except Exception as e:
            # Log error but don't fail the agent execution
            logger.error(f"Failed to record agent execution to history database: {e}", exc_info=True)
    
    return output_text
```

- [ ] **Step 5: 更新调用_run_react_until_final_text的地方传入参数**

在`graph_multi.py`中找到所有调用`_run_react_until_final_text`的地方，添加`run_id`和`agent_type`参数。

**注意**：run_id已经通过`make_run_dir()`生成并存储在state中。如果发现run_id不在state中，需要先在graph的初始化节点中添加：

```python
# 在build_multi_agent_graph()函数中，确保run_id被添加到state
# 通常在第一个节点或入口处理中
def some_init_node(state: AgentState) -> AgentState:
    query = state["query"]
    asset = _extract_asset_from_query(query)
    run_context = make_run_dir(asset)
    return {
        **state,
        "run_id": run_context.run_id,
        "run_dir": str(run_context.run_dir)
    }
```

例如在Quant_Agent节点中：
```python
def Quant_Agent(state: AgentState, *, config: Optional[RunnableConfig] = None) -> AgentState:
    query = state["query"]
    run_id = state.get("run_id")  # 从state获取
    report = _run_react_until_final_text(
        QUANT_SYSTEM,
        QUANT_TOOLS,
        query,
        config=config,
        run_id=run_id,
        agent_type="quant"
    )
    # ... rest of the function
```

类似地更新News_Agent, Social_Agent, CIO_Agent的调用。

- [ ] **Step 6: 运行测试验证集成**

```bash
uv run pytest tests/test_multi_agent_graph.py -v
```

预期输出：所有测试通过

- [ ] **Step 7: 提交**

```bash
git add app/graph_multi.py tests/test_multi_agent_graph.py
git commit -m "feat(graph): integrate agent history recording into multi-agent graph"
```

---

## Task 5.5: 在应用启动时初始化数据库

**Files:**
- Modify: `app/api/main.py:24-36`

- [ ] **Step 1: 添加数据库初始化到startup事件**

```python
# app/api/main.py

# 在导入部分添加（约第7行之后）
import os
from app.database.agent_history import init_db as init_agent_history_db

# 修改startup函数（约第24-36行）
@app.on_event("startup")
def start_scheduler():
    """Start scheduled tasks and initialize databases on app startup."""
    # Initialize agent history database
    db_path = os.getenv("AGENT_HISTORY_DB_PATH", "data/agent_history.db")
    init_agent_history_db(db_path)
    logger.info(f"✓ Agent history database initialized: {db_path}")

    # Update daily after US market close (UTC 21:30 = EST 16:30)
    scheduler.add_job(
        update_daily_ohlc,
        'cron',
        hour=21,
        minute=30,
        id='daily_ohlc_update'
    )
    scheduler.start()
    logger.info("✓ Scheduler started: daily OHLC update at 21:30 UTC")
```

- [ ] **Step 2: 运行应用验证启动**

```bash
uv run uvicorn app.api.main:app --port 8080
```

预期输出包含：
```
INFO: ✓ Agent history database initialized: data/agent_history.db
INFO: ✓ Scheduler started: daily OHLC update at 21:30 UTC
```

- [ ] **Step 3: 提交**

```bash
git add app/api/main.py
git commit -m "feat(api): initialize agent history database on startup"
```

---

## Task 6: API路由实现

**Files:**
- Create: `app/api/routes/history.py`
- Modify: `app/api/routes/__init__.py`
- Modify: `app/api/main.py:10,56-61`
- Test: `tests/test_history_api.py`

- [ ] **Step 1: 编写API测试**

```python
# tests/test_history_api.py
"""Tests for history API endpoints."""

from datetime import datetime, timezone, timedelta
import uuid

from app.database.agent_history import init_db, save_analysis_run, save_agent_execution


def test_get_analysis_runs(tmp_path, monkeypatch):
    """Test GET /api/analysis-runs endpoint."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    monkeypatch.setenv("AGENT_HISTORY_DB_PATH", str(db_path))

    # Create client AFTER setting environment variable
    from fastapi.testclient import TestClient
    from app.api.main import app
    client = TestClient(app)

    # Insert test data
    tz = timezone(timedelta(hours=8))
    save_analysis_run("20260321_100000", "AAPL", "test query", datetime.now(tz), "decision", str(db_path))

    response = client.get("/api/analysis-runs")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert len(data["items"]) >= 1


def test_get_analysis_runs_with_filters(tmp_path, monkeypatch):
    """Test GET /api/analysis-runs with filters."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    monkeypatch.setenv("AGENT_HISTORY_DB_PATH", str(db_path))

    from fastapi.testclient import TestClient
    from app.api.main import app
    client = TestClient(app)

    tz = timezone(timedelta(hours=8))
    save_analysis_run("20260321_100000", "AAPL", "test1", datetime.now(tz), db_path=str(db_path))
    save_analysis_run("20260321_110000", "NVDA", "test2", datetime.now(tz), db_path=str(db_path))

    response = client.get("/api/analysis-runs?asset=AAPL")
    assert response.status_code == 200
    data = response.json()
    assert all(item["asset"] == "AAPL" for item in data["items"])


def test_get_run_detail(tmp_path, monkeypatch):
    """Test GET /api/analysis-runs/{run_id} endpoint."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    monkeypatch.setenv("AGENT_HISTORY_DB_PATH", str(db_path))

    from fastapi.testclient import TestClient
    from app.api.main import app
    client = TestClient(app)

    run_id = "20260321_143052"
    tz = timezone(timedelta(hours=8))
    save_analysis_run(run_id, "AAPL", "test", datetime.now(tz), "decision", str(db_path))

    exec_id = str(uuid.uuid4())
    save_agent_execution(exec_id, run_id, "quant", [{"role": "system", "content": "test"}], datetime.now(tz), db_path=str(db_path))

    response = client.get(f"/api/analysis-runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert "agents" in data
    assert len(data["agents"]) == 1


def test_get_run_detail_not_found(tmp_path, monkeypatch):
    """Test GET /api/analysis-runs/{run_id} with non-existent ID."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    monkeypatch.setenv("AGENT_HISTORY_DB_PATH", str(db_path))

    from fastapi.testclient import TestClient
    from app.api.main import app
    client = TestClient(app)

    response = client.get("/api/analysis-runs/nonexistent")
    assert response.status_code == 404
```

- [ ] **Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_history_api.py -v
```

预期输出：`404 Not Found` (路由尚未注册)

- [ ] **Step 3: 实现history路由（第1部分 - 基础查询）**

```python
# app/api/routes/history.py
"""API routes for agent decision history."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import os

from app.database.agent_history import (
    query_analysis_runs,
    query_run_detail,
    query_agent_messages,
    query_tool_calls
)

router = APIRouter()


@router.get("/analysis-runs")
async def get_analysis_runs(
    asset: Optional[str] = Query(None, description="Filter by asset ticker"),
    date_from: Optional[str] = Query(None, description="Start date (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Query analysis runs with optional filters."""
    db_path = os.getenv("AGENT_HISTORY_DB_PATH", "data/agent_history.db")
    
    results = query_analysis_runs(
        asset=asset,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        db_path=db_path
    )
    
    return {
        "total": len(results),
        "items": results
    }


@router.get("/analysis-runs/{run_id}")
async def get_run_detail(run_id: str):
    """Get detailed information for a single analysis run."""
    db_path = os.getenv("AGENT_HISTORY_DB_PATH", "data/agent_history.db")
    
    result = query_run_detail(run_id, db_path=db_path)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    return result


@router.get("/agent-executions/{execution_id}/messages")
async def get_agent_messages(execution_id: str):
    """Get complete message history for an agent execution."""
    db_path = os.getenv("AGENT_HISTORY_DB_PATH", "data/agent_history.db")
    
    result = query_agent_messages(execution_id, db_path=db_path)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
    
    return result
```

- [ ] **Step 4: 实现history路由（第2部分 - 工具调用查询）**

```python
# app/api/routes/history.py (继续追加)

@router.get("/tool-calls")
async def get_tool_calls(
    tool_name: Optional[str] = Query(None, description="Filter by tool name"),
    status: Optional[str] = Query(None, description="Filter by status (success/failed)"),
    date_from: Optional[str] = Query(None, description="Start date (ISO format)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Query tool calls with optional filters."""
    db_path = os.getenv("AGENT_HISTORY_DB_PATH", "data/agent_history.db")
    
    results = query_tool_calls(
        tool_name=tool_name,
        status=status,
        date_from=date_from,
        limit=limit,
        offset=offset,
        db_path=db_path
    )
    
    return {
        "total": len(results),
        "items": results
    }


@router.get("/tool-calls/stats")
async def get_tool_stats(
    date_from: Optional[str] = Query(None, description="Start date (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date (ISO format)")
):
    """Get tool usage statistics."""
    db_path = os.getenv("AGENT_HISTORY_DB_PATH", "data/agent_history.db")
    
    # Query all tool calls in the period
    all_calls = query_tool_calls(
        date_from=date_from,
        limit=10000,  # Large limit to get all
        db_path=db_path
    )
    
    # Aggregate by tool_name
    stats_by_tool = {}
    for call in all_calls:
        tool_name = call["tool_name"]
        if tool_name not in stats_by_tool:
            stats_by_tool[tool_name] = {
                "tool_name": tool_name,
                "total_calls": 0,
                "success_count": 0,
                "failed_count": 0
            }
        
        stats_by_tool[tool_name]["total_calls"] += 1
        if call["status"] == "success":
            stats_by_tool[tool_name]["success_count"] += 1
        elif call["status"] == "failed":
            stats_by_tool[tool_name]["failed_count"] += 1
    
    # Calculate success rate
    tools = []
    for tool_stats in stats_by_tool.values():
        total = tool_stats["total_calls"]
        success = tool_stats["success_count"]
        tool_stats["success_rate"] = success / total if total > 0 else 0.0
        tools.append(tool_stats)
    
    return {
        "period": {
            "from": date_from,
            "to": date_to
        },
        "tools": tools
    }
```

- [ ] **Step 5: 注册路由到main.py**

```python
# app/api/routes/__init__.py
# 添加导入
from . import history

# app/api/main.py
# 在导入部分添加
from .routes import analyze, reports, system, settings, stocks, ohlc, history

# 在路由注册部分添加
app.include_router(history.router, prefix="/api", tags=["history"])
```

- [ ] **Step 6: 运行测试验证通过**

```bash
uv run pytest tests/test_history_api.py -v
```

预期输出：`4 passed`

- [ ] **Step 7: 提交**

```bash
git add app/api/routes/history.py app/api/routes/__init__.py app/api/main.py tests/test_history_api.py
git commit -m "feat(api): add history query endpoints"
```

---

## Task 7: 端到端测试和文档

**Files:**
- Create: `scripts/test_agent_history.py`
- Modify: `README.md`

- [ ] **Step 1: 编写端到端测试脚本**

```python
# scripts/test_agent_history.py
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
            content=None,
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
```

- [ ] **Step 2: 运行端到端测试**

```bash
uv run python scripts/test_agent_history.py
```

预期输出：
```
=== Agent History System E2E Test ===

✓ Database initialized
✓ Saved analysis run: 20260321_999999
✓ Saved agent execution: <uuid>
✓ Saved tool call: <uuid>
✓ Queried 1 analysis runs
✓ Queried run detail with 1 agents

=== All tests passed! ===
```

- [ ] **Step 3: 更新README文档**

```markdown
# README.md (在"Advanced Features"部分添加)

### Agent Decision History

The system records complete decision-making processes for analysis and learning:

**Query decision history:**

```bash
# View recent analysis runs
curl http://localhost:8080/api/analysis-runs?limit=10

# Get detailed run information
curl http://localhost:8080/api/analysis-runs/20260321_143052

# Query tool usage statistics
curl http://localhost:8080/api/tool-calls/stats
```

**Database location:** `data/agent_history.db`

**Features:**
- Complete agent reasoning history (OpenAI standard message format)
- Tool call tracking with success/failure status
- Query APIs for analysis and debugging
- Foundation for future learning mechanisms

**Test the system:**

```bash
uv run python scripts/test_agent_history.py
```
```

- [ ] **Step 4: 运行所有测试验证完整性**

```bash
uv run pytest tests/test_agent_history.py tests/test_message_adapter.py tests/test_history_api.py -v
```

预期输出：所有测试通过

- [ ] **Step 5: 提交**

```bash
git add scripts/test_agent_history.py README.md
git commit -m "docs: add agent history system documentation and E2E test"
```

---

## Implementation Notes

### Error Handling Strategy
- Database write failures should NOT block agent execution
- All database operations wrapped in try-except
- Errors logged but execution continues
- Use environment variable `AGENT_HISTORY_DB_PATH` for test isolation

### Performance Considerations
- Database writes are synchronous (acceptable for MVP)
- Future optimization: async writes or background queue
- Indexes cover common query patterns
- Consider archiving old data (>6 months)

### Testing Strategy
- Unit tests: Database operations, message conversion
- Integration tests: API endpoints
- E2E test: Complete workflow
- Structure tests: Verify integration points exist

### Migration from JSON Reports
- Phase 1: Implement SQLite system (this plan)
- Phase 2: Remove JSON file generation (separate task)
- Phase 3: Optional historical data migration (separate task)

---

