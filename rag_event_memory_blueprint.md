### RAG 历史事件记忆库开发蓝图

```markdown
# 历史事件 RAG 记忆库 (Event-Driven Fused Memory) 开发蓝图

## 1. 模块定位与核心目标
- **痛点**：传统大模型（News Agent）分析突发新闻时缺乏具体的历史参照物，且无法准确定量该新闻对特定资产的真实冲击幅度。
- **解决方案**：构建一个“融合记忆库”。将【历史重大新闻文本】与【事件发生后的真实收益率】拼接成标准化的“复盘档案”，随后将其向量化并存入 ChromaDB。
- **目标应用**：为 News Agent 提供一个专用的 `@tool`。当今日发生类似事件（如“财报暴雷”、“高管离职”、“非农超预期”）时，Agent 可以检索出历史上高度相似的事件档案，并直接看到当时市场的真实反应，从而辅助 CIO Agent 做出避险或顺势决策。



## 2. 技术栈与依赖包
- **向量数据库**: `chromadb`, `langchain-chroma` (极其轻量的本地化向量存储)
- **文本嵌入 (Embeddings)**: `langchain-openai` (配置使用兼容的 Embedding 模型，如 MiniMax 或 OpenAI 的 text-embedding-3-small)
- **数据获取与处理**: `yfinance`, `pandas`
- **建议安装命令**: `uv add chromadb langchain-chroma langchain-openai yfinance pandas`

## 3. 核心数据流设计 (Data Pipeline)

### 3.1 步骤一：构建“融合记忆块” (Fused Memory Block)
在存入数据库前，必须将纯文本新闻和量化数据结合。
**数据结构示例：**
```text
【历史事件复盘】
标的：META
日期：2022-10-27
事件摘要：META发布Q3财报，Reality Labs元宇宙部门巨亏，净利润同比大幅下降，引发市场恐慌。
市场真实反应：
- 次日(T+1)真实收益率：-24.56% (极端跳空暴跌)
- 后续(T+5)累计收益率：-28.32% (趋势延续)

```

*技术实现*：编写一个数据预处理脚本，接收历史新闻列表（含日期、Ticker、文本），通过 `yfinance` 自动计算该日期后 1 天和 5 天的 `Close` 收益率，并格式化为上述字符串。

### 3.2 步骤二：向量化与元数据存储 (Vectorization & Storage)

使用 `Chroma` 建立本地持久化存储（存放在 `./chroma_db` 目录下）。
**极其重要的 Metadata 规则**：
存入 Document 时，必须同时写入元数据（Metadata）。
`metadata = {"ticker": "META", "date": "2022-10-27", "event_type": "earnings"}`
*目的*：当 News Agent 搜索“特斯拉召回”时，可以通过 `filter={"ticker": "TSLA"}` 强制 Chroma 数据库只检索特斯拉的历史，防止搜到福特汽车的召回事件造成幻觉。

### 3.3 步骤三：Agent 检索工具封装 (RAG Tool)

为 News Agent 创建 LangChain 工具 `@tool`。
**函数签名设计**：

```python
@tool
def search_historical_event_impact(query: str, ticker: str) -> str:
    """
    当发生突发新闻、财报发布或宏观数据公布时，调用此工具查询目标标的（ticker）历史上发生类似事件时的真实市场反应。
    
    Args:
        query (str): 事件关键词，例如 "earnings miss", "CEO resigns", "interest rate hike".
        ticker (str): 股票代码，例如 "AAPL", "NVDA".
    """
    # 内部逻辑：连接 ChromaDB -> 使用 query 搜索相似度最高的 Top 3 文档 -> 应用 ticker 过滤 -> 返回融合记忆文本。

```

## 4. 给 Cursor 的执行指令 (Step-by-Step)

请 AI 助手按以下结构分模块生成 Python 代码：

1. **模块一 (`build_event_memory.py`)**：

- 编写 `fetch_post_event_returns(ticker, date)` 函数，利用 `yfinance` 计算 T+1 和 T+5 收益率。
- 编写 `create_memory_document(ticker, date, news_summary)` 函数，将收益率和新闻组装成标准格式文本。
- 编写 `init_chroma_db(docs, metadatas)`，将其持久化到本地 `./chroma_db`。

1. **模块二 (`rag_tools.py`)**：

- 编写带有 `@tool` 装饰器的 `search_historical_event_impact` 函数。
- 配置正确的 Embeddings 接口和 Chroma retriever 逻辑，必须实现根据 `ticker` 进行元数据过滤（Metadata Filtering）。

1. **测试入口 (`tests/test_rag_memory.py`)**：

- 提供一段模拟数据（Mock Data，如 2 条关于 NVDA 财报和 1 条关于 META 财报的历史新闻）。
- 运行构建脚本，并模拟 News Agent 调用 `@tool` 查询 "NVDA 财报超预期"，验证是否成功返回带有具体跌涨幅度的复盘报告，且未混入 META 的数据。



