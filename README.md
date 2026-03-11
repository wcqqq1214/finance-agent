## finance-agent

基于 Python 3.13、LangChain 与 LangGraph 的单体金融分析 Agent。

### 技术栈

- **语言**: Python 3.13
- **核心框架**: `langchain`, `langgraph`, `langchain-openai`
- **数据处理**: `pandas`, `yfinance`
- **搜索工具**: `tavily-python`, `duckduckgo-search`
- **环境变量管理**: `python-dotenv`

### 安装与环境

1. 创建并激活 Python 3.13 的 uv 虚拟环境（已完成）  
2. 安装依赖：

```bash
uv sync
```

3. 在项目根目录创建 `.env` 文件，例如：

```bash
OPENAI_API_KEY=你的OpenAIKey
TAVILY_API_KEY=你的TavilyKey
MINIMAX_API_KEY=你的MinimaxKey
# 若使用其他模型或服务，可以在此处继续添加
```

### 验证第一个金融工具函数

在完成依赖安装后，可以在终端中运行以下命令验证行情工具是否正常工作：

```bash
uv run python -c "from app.tools.finance_tools import get_us_stock_quote; from pprint import pprint; pprint(get_us_stock_quote('AAPL'))"
```

你也可以尝试一个无效代码，确认错误处理逻辑：

```bash
uv run python -c "from app.tools.finance_tools import get_us_stock_quote; from pprint import pprint; pprint(get_us_stock_quote('INVALID123'))"
```

### 下一步开发

- Step 2：继续扩展更多金融与搜索工具函数，并集成到 LangGraph 图中。