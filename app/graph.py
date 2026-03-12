from __future__ import annotations

from typing import Any, Dict, List, Optional

import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.tools.finance_tools import get_us_stock_quote, search_news_with_duckduckgo


load_dotenv()


def _make_minimax_llm() -> ChatOpenAI:
    """Create a ChatOpenAI-compatible client that actually talks to MiniMax.

    This helper uses the MiniMax OpenAI-compatible API endpoint under the hood
    so that the rest of the LangGraph-based agent can treat it as a standard
    OpenAI chat completion model, while all traffic is routed to MiniMax.

    Environment variables:
        MINIMAX_API_KEY: The API key issued by MiniMax. This is required.
        MINIMAX_BASE_URL: Optional override for the MiniMax OpenAI-compatible
            base URL. If not provided, a sensible default is chosen:
            - ``https://api.minimaxi.com/v1`` for users in mainland China.
            - ``https://api.minimax.io/v1`` for international users.
            In this template we default to ``https://api.minimaxi.com/v1``.
        MINIMAX_MODEL: Optional model name, for example ``"MiniMax-M2.5"`` or
            ``"MiniMax-M2.5-highspeed"``. If omitted, ``"MiniMax-M2.5"`` is
            used by default.

    Returns:
        A ``ChatOpenAI`` instance configured to send OpenAI-style Chat
        Completions requests to the MiniMax OpenAI-compatible gateway.
    """

    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MINIMAX_API_KEY is not set in the environment. "
            "Please add it to your .env file before using the agent.",
        )

    base_url = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1")
    model = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.5")

    # ChatOpenAI is OpenAI-compatible and accepts a custom base_url, so we can
    # point it directly at MiniMax's OpenAI-compatible gateway.
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.0,
    )


TOOLS = [get_us_stock_quote, search_news_with_duckduckgo]

_LLM_WITH_TOOLS = _make_minimax_llm().bind_tools(TOOLS)


def agent(state: MessagesState, *, config: Optional[RunnableConfig] = None) -> MessagesState:
    """Core LLM node of the ReAct-style agent.

    This node:
    - Reads the conversation history from ``state["messages"]``.
    - Invokes the MiniMax-backed chat model that is already bound with all
      available tools.
    - Appends the model's response to the message list and returns the updated
      state.

    The LLM will decide whether to call tools or to produce a final answer
    directly. When it decides to call tools, the output message will contain
    ``tool_calls`` that will be picked up by the ``tools`` node.
    """

    messages = state.get("messages", [])
    response = _LLM_WITH_TOOLS.invoke(messages, config=config)
    return {"messages": messages + [response]}


tool_node = ToolNode(TOOLS)


def _should_continue(state: MessagesState) -> str:
    """Route control flow based on whether the LLM requested tool calls.

    Returns:
        - ``"tools"`` if the most recent assistant message contains tool
          invocation requests.
        - ``"END"`` otherwise, which terminates the conversation in this graph
          run.
    """

    messages = state.get("messages", [])
    if not messages:
        return END

    last = messages[-1]
    # For OpenAI-compatible models with tools, tool calls live in the
    # ``tool_calls`` attribute on assistant messages.
    tool_calls = getattr(last, "tool_calls", None)
    if tool_calls:
        return "tools"
    return END


def build_finance_agent_graph():
    """Construct and compile the LangGraph-based single-agent graph.

    The graph uses:
        - ``MessagesState`` as its single shared state container.
        - ``agent`` as the LLM node (MiniMax via OpenAI-compatible interface).
        - ``tool_node`` as the node that executes tools requested by the LLM.

    Edges (ReAct-style loop):
        START -> agent
        agent -> (END or tools)  # conditional based on tool calls
        tools -> agent           # feed tool results back into LLM
    """

    graph = StateGraph(MessagesState)

    graph.add_node("agent", agent)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", _should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


def run_once(user_input: str) -> List[Any]:
    """Convenience helper to invoke the graph once in a simple script.

    This function is primarily intended for Step 4 manual testing from a REPL
    or small CLI program. It:

    - Builds the compiled graph.
    - Starts from an initial state containing a single human message.
    - Runs the graph to completion and returns the final state messages.
    """

    compiled = build_finance_agent_graph()
    initial_state: Dict[str, Any] = {
        "messages": [
            SystemMessage(
                content=(
                    "You are a helpful financial analysis assistant. "
                    "Use tools for real-time market data and news when needed."
                ),
            ),
            HumanMessage(content=user_input),
        ],
    }
    final_state = compiled.invoke(initial_state)
    return final_state["messages"]

