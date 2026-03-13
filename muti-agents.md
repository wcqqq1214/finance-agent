# 多智能体量化分析系统 (Multi-Agent Quant System) 架构蓝图

## 1. 项目概述
本项目旨在构建一个基于 LangGraph 的并行多智能体（Multi-Agent）金融分析系统。系统聚焦于美股和加密货币（如 BTC-USD, NVDA）的极简量化分析与宏观情绪结合。
核心逻辑采用“Fan-out / Fan-in”（并行分发与收束）架构：系统同时获取硬核的量化指标与软性的新闻情绪，最后由“首席投资官(CIO)”节点进行综合决策与冲突调和。

## 2. 技术栈要求
- **核心框架**: `langgraph`, `langchain-core`
- **大模型接口**: `langchain-openai` (底层接入 MiniMax API，需完全兼容 OpenAI 调用格式)
- **工具依赖**: `yfinance` (行情), `duckduckgo-search` (新闻), `pandas`
- **代码规范**: Python 3.13，必须包含完整的 Type Hinting 和 Google-style docstrings。所有状态传递必须使用最新的 LangGraph 语法。

## 3. 系统架构设计 (Graph Topology)



系统由 3 个独立的大模型节点（Nodes）组成一个有向图：
- **起点 (START)** 接收用户的资产查询请求。
- **并行执行 (Parallel Edges)**: 请求同时分发给 `Quant_Agent` 节点和 `News_Agent` 节点。
- **收束归总 (Fan-in)**: 两个 Agent 均执行完毕并返回结果后，状态流入 `CIO_Agent` 节点。
- **终点 (END)**: CIO 输出最终的调和决策报告。

### 3.1 全局状态 (State Definition)
需要定义一个继承自 `TypedDict` 的 `AgentState`，用于在节点间流转数据：
- `query`: 用户的原始提问（如 "分析一下 BTC-USD 现在的走势"）。
- `quant_report`: Quant Agent 生成的量化数据报告。
- `news_report`: News Agent 生成的市场情绪报告。
- `final_decision`: CIO Agent 生成的最终综合报告。

## 4. 节点 (Nodes) 与角色详细定义

### 4.1 节点 A: Quant Agent (量化分析师)
- **职责**: 专注于时间序列数据、均线计算和技术面特征提取。为未来接入 LightGBM 等机器学习预测模型预留数据接口空间。
- **绑定工具**: `get_stock_data(ticker: str)` (内部调用 `yfinance` 获取历史 K 线、计算均线（SMA、MACD等指标），甚至未来可以帮你预处理数据机器学习模型使用)。
- **System Prompt**: "你是一个严谨的量化数据分析师。你的任务是调用工具获取数据，并输出纯粹的技术面分析报告，不要包含任何新闻或主观情绪判断。"

### 4.2 节点 B: News Agent (市场情绪研究员)
- **职责**: 专注于抓取最新新闻，分析宏观基本面和市场恐慌/贪婪情绪。
- **绑定工具**: `search_financial_news(query: str)` (内部调用 `duckduckgo-search` 获取最新的新闻)。
- **System Prompt**: "你是一个敏锐的宏观情绪研究员。你的任务是调用搜索工具，提取关于特定资产的最新新闻，并总结当前的市场情绪偏向（利好/利空/中性）。"

### 4.3 节点 C: CIO Agent (首席投资官 - 调和者)
- **职责**: 接收并阅读 `quant_report` 和 `news_report`。不调用任何外部工具。负责处理技术面与消息面的背离（例如：技术面看跌，但突发重大利好新闻）。
- **System Prompt**: 
  "你是一个顶级的首席投资官 (CIO)。你将收到一份【量化技术面报告】和一份【宏观新闻情绪报告】。
  你的任务是综合这两份报告，给出最终的交易建议。
  核心调和规则：
  1. 如果技术面与消息面共振，请强化该方向的确定性。
  2. 如果两者产生冲突，必须明确指出“技术面与基本面背离”，并通常赋予重大突发新闻更高的短期权重。
  3. 你的输出必须包含：综合结论、数据面支撑、消息面支撑、以及明确的风险提示。"
