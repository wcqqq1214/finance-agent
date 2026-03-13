# 机器学习量化预测模块 (LightGBM + SHAP) 架构蓝图

## 1. 模块定位与目标
本模块是多智能体金融分析系统中的“硬核大脑”插件。
- **核心任务**：获取特定资产（如美股、加密货币）的历史日 K 线数据，通过特征工程提炼量化指标，训练 LightGBM 模型预测**下一个交易日的涨跌方向（二分类）**。
- **设计哲学与避坑 (核心认知)**：**严禁尝试拟合具体的价格曲线（回归任务 Regression）！** 金融市场充满随机噪音，强行拟合绝对价格会导致严重的过拟合。本模块采用**二分类（分类任务 Classification）**，旨在拟合特征数据与涨跌胜率之间的关系（决策边界）。预测“涨跌概率”比预测“具体点位”容错率更高，且对 CIO Agent 的决策更有实质性参考价值。



- **Agent 适配性**：最关键的一环是使用 SHAP (Shapley Additive exPlanations) 解析树模型的“黑盒”，将特征贡献度转化为**自然语言解释报告**，以便外层的 Quant Agent 能够阅读并以此作为逻辑支撑，向 CIO Agent 汇报。

## 2. 技术栈与依赖库
- **基础数据与清洗**: `pandas`, `numpy`, `yfinance`
- **技术指标生成**: `pandas_ta` (极致简化特征工程的代码量)
- **机器学习框架**: `lightgbm`, `scikit-learn`
- **模型解释器**: `shap`
- **建议安装命令**: `uv add yfinance pandas numpy pandas-ta lightgbm shap scikit-learn`

### 2.1 数据源与调用策略

- **当前版本（v1）策略**  
  - 本模块内部 **直接使用 `yfinance` 拉取 OHLCV 日线数据**，不通过 MCP server 转发。  
  - 典型调用方式：`yfinance.download(ticker, period="3y", interval="1d")`。  
  - 数据获取逻辑与特征工程、模型训练放在同一 Python 进程内，便于调试与性能控制。

- **与现有系统的关系**  
  - 现有量化模块可能通过 MCP server 访问同一数据源，例如在 `quant.json.meta.source` 中标记为 `"yfinance_mcp"`。  
  - 本 ML 模块在自身输出结构中单独标记数据来源，例如：  
  ```json
  "ml_quant": {
    "data_source": "yfinance_direct",
    "...": "..."
  }
  ```  
  - 约定：**所有量化模块的行情底层均来自 yfinance，仅接入路径（直连 / MCP）不同。**

- **未来演进（可选）**  
  - 当需要统一数据访问层（多 Agent 复用缓存 / 速率控制 / 付费行情 API）时，可以将本模块的数据拉取部分替换为 MCP server 工具调用：  
    - MCP server 返回标准化的 OHLCV DataFrame 或等价 JSON；  
    - `run_ml_quant_analysis` 对外接口不变，仅替换内部的数据来源实现。  
  - 演进优先级：**先做直连 yfinance，待整体架构稳定后再考虑抽象为 MCP 服务。**

## 3. 核心数据与特征工程规范 (Feature Engineering Pipeline)

### 3.1 基础数据源 (Raw Data)
调用 `yfinance` 获取目标资产过去 3 年以上的日线数据（`Open`, `High`, `Low`, `Close`, `Volume`）。必须按日期升序排列，去除含有空值的脏数据。

### 3.2 衍生特征构建 (Derived Features)
使用 `pandas_ta` 库，必须生成以下四大类特征。**严禁将绝对价格直接喂给模型，必须全部转化为相对比例或指标！**

1. **收益率特征 (Returns)**:
   - `Ret_1d`: 1日简单收益率 (pct_change)
   - `Ret_3d`: 3日简单收益率
   - `Ret_5d`: 5日简单收益率
2. **动量与震荡特征 (Momentum)**:
   - `RSI_14`: 14日相对强弱指数
   - `MACD`, `MACD_Hist`: 平滑异同移动平均线及其柱状图
   - `CCI_14`: 14日顺势指标
3. **趋势乖离特征 (Trend Distance)**:
   - `Dist_SMA_20`: 收盘价与20日均线的偏离度 ($\frac{Close}{SMA_{20}} - 1$)
   - `Dist_SMA_50`: 收盘价与50日均线的偏离度
4. **波动与量价特征 (Volatility & Volume)**:
   - `ATR_14`: 14日真实波动幅度
   - `BBL_5_2.0`, `BBU_5_2.0`: 布林带宽度或收盘价在布林带中的相对位置
   - `Volume_Ratio`: 当日成交量与过去5日移动平均成交量的比值

### 3.3 目标标签定义 (Target Label)
预测目标为下一日的涨跌方向，属于二分类问题（Binary Classification）。模型不是在追逐上下跳动的 K 线，而是拟合出哪些技术特征组合最容易导致上涨或下跌。
将收盘价序列向上平移（`shift(-1)`）以构建未来一天的收盘价。
定义标签 $Y$：
$$Y_t = \begin{cases} 1, & \text{if } Close_{t+1} > Close_t \\ 0, & \text{otherwise} \end{cases}$$
构建完成后，必须执行 `dropna()` 删除最后一天（因为没有未来的标签）以及特征计算初期的 NaN 行。

## 4. 模型训练与 SHAP 解释逻辑

### 4.1 时序数据划分 (Time-Series Split)
**严禁使用随机打乱的交叉验证。**
必须按时间顺序切分数据集，例如前 80% 的时间作为训练集，后 20% 的时间作为测试集/验证集。

### 4.2 LightGBM 训练
初始化 `LGBMClassifier`，参数尽量轻量化防止过拟合（例如 `max_depth=4`, `n_estimators=100`, `learning_rate=0.05`）。

### 4.3 SHAP 解析与自然语言转化 (极其重要)
这是本项目最核心的价值。模型训练完成后，针对**最后一行数据（即最新一天的行情）**：
1. 使用 `shap.TreeExplainer` 计算该样本的 SHAP 值。
2. 提取出对预测结果（涨或跌）**正向贡献最大的前 3 个特征**和**负向压制最大的前 2 个特征**。
3. 编写一个格式化函数，将这些数值拼接成 Markdown 报告。例如：
   *"【LightGBM 量化预测报告】标的: BTC-USD。预测明日上涨概率为 65%。核心看多驱动力：1. RSI_14 处于极度超卖区间 (贡献度 +0.15)；2. Dist_SMA_20 乖离率修复 (贡献度 +0.08)。核心看空风险：Volume_Ratio 缩量严重 (压制度 -0.05)。"*

## 5. 给 Cursor 的开发步骤指令 (Step-by-Step Execution)
请 AI 助手按以下步骤生成 Python 代码，使用面向对象的设计或结构清晰的函数式编程：
1. **第一步：特征引擎 (`feature_engine.py`)**：编写一个接收 DataFrame 并利用 `pandas_ta` 批量生成上述所有规范特征的函数。
2. **第二步：模型训练与评估 (`model_trainer.py`)**：处理时间序列切分，训练 `LGBMClassifier`，并打印出测试集上的 Accuracy 和 AUC 评分。
3. **第三步：SHAP 解释器 (`shap_explainer.py`)**：编写计算 SHAP 值的逻辑，并实现将 Top 贡献特征转化为 Agent 易读的中文 Markdown 文本的函数。
4. **第四步：Agent 工具封装 (`quant_tool.py`)**：提供一个可以直接作为 LangChain `@tool` 调用的顶层接口，接收股票代码 `ticker`，内部自动走完拉取、计算、预测、解释的全流程，并返回最终报告。

## 6. 与 Quant/CIO 报告的集成规范

本模块定位为「量化预测 Tool」，由 Quant Agent 调用，并作为 `quant.json`、`cio.json` 报告的一部分提供给 CIO Agent 进行综合判断。

### 6.1 调用时机与频率（强约束）

1. **每个标的必须调用一次**  
   - Quant Agent 在为任意单一标的生成量化报告（`quant.json`）时，**必须调用一次**  
     `run_ml_quant_analysis(ticker: str) -> str`。  
   - 仅当出现以下情况时允许跳过（需记录日志）：  
     - 历史数据长度严重不足（如 < 180 个交易日）；  
     - 行情拉取失败（网络错误、交易所未覆盖该标的等）。

2. **与其它模块的关系**  
   - 该 Tool 的输出与现有 `indicators`、`levels`、`news`、`social` 等模块并列，组成完整的 Quant 报告输入：  
     - `indicators`: 传统技术指标与趋势判断；  
     - `ml_quant`: 机器学习视角下的下日方向概率与特征驱动力；  
     - `news`、`social`: 新闻与情绪因子；  
     - 最终由 Quant Agent 汇总为给 CIO 的决策提示。

### 6.2 在 `quant.json` 中的落盘结构规范

在现有 `quant.json` 结构基础上，为 LightGBM+SHAP 模块约定一个固定的 `ml_quant` 字段，例如：

```json
{
  "asset": "DOGE-USD",
  "module": "quant",
  "meta": {
    "generated_at_utc": "2026-03-13T13:17:17+00:00",
    "source": "yfinance_mcp"
  },
  "trend": "bullish",
  "indicators": {
    "ticker": "DOGE-USD",
    "last_close": 0.1003878116607666,
    "sma_20": 0.09380319118499755,
    "macd_line": -0.0018097101797977244,
    "macd_signal": -0.0030171046169960468,
    "macd_histogram": 0.0012073944371983223,
    "bb_middle": 0.09380319118499755,
    "bb_upper": 0.10051388686369585,
    "bb_lower": 0.08709249550629926,
    "period_rows": 91
  },
  "levels": {
    "support": 0.087,
    "resistance": 0.1005
  },
  "ml_quant": {
    "model": "lightgbm_v1",
    "target": "next_day_direction",
    "data_source": "yfinance_direct",
    "prob_up": 0.65,
    "prediction": "up",
    "metrics": {
      "accuracy": 0.58,
      "auc": 0.62,
      "train_test_split": "80_20_time_series"
    },
    "shap_insights": {
      "top_positive": [
        {"feature": "RSI_14", "value": 28.5, "shap": 0.15},
        {"feature": "Dist_SMA_20", "value": -0.03, "shap": 0.08},
        {"feature": "Volume_Ratio", "value": 1.4, "shap": 0.04}
      ],
      "top_negative": [
        {"feature": "MACD_Hist", "value": -0.002, "shap": -0.05},
        {"feature": "ATR_14", "value": 0.018, "shap": -0.03}
      ]
    },
    "markdown_report": "【LightGBM 量化预测报告】标的: DOGE-USD。预测明日上涨概率为 65%。核心看多驱动力：RSI_14 处于相对低位 (贡献度 +0.15)；Dist_SMA_20 乖离率有修复迹象 (贡献度 +0.08)。核心风险：MACD_Hist 仍略显疲弱 (压制度 -0.05)。"
  },
  "summary": "DOGE-USD is bullish as price trades above its 20-day SMA with positive MACD momentum, finding resistance near the upper Bollinger Band."
}
```

约定：

- `prob_up`：模型给出的**下一交易日上涨概率**（0–1 之间）；  
- `prediction`：基于 `prob_up` 与固定阈值（如 0.5）给出的方向标签 `"up"` / `"down"`；  
- `metrics`：用于评价模型在最近样本上的历史表现，主要暴露 `accuracy` 与 `auc` 给 CIO 参考；  
- `shap_insights`：只保留 Top 特征，既可供 Agent 总结，也方便人类肉眼快速扫一眼；  
- `markdown_report`：完整的中文说明，用于直接嵌入人类可读报告或 CIO Agent 的上下文。

### 6.3 CIO Agent 的使用方式

- CIO Agent 不直接根据 `prob_up` 做交易指令，而是将其视为**“技术面 + 机器学习”的证据来源**之一：  
  - 当 `trend == "bullish"` 且 `ml_quant.prob_up` 较高（如 > 0.6）时，可以在报告中加强「技术面 + 量化」的一致性表述；  
  - 当 `trend` 与 `ml_quant.prediction` 相反（例如趋势看多但 ML 预测下跌），需要在 CIO 报告中点明「模型与传统技术指标存在分歧」。  
- CIO Agent 在向用户/上级解释时优先引用：  
  - `ml_quant.markdown_report` 中的自然语言段落；  
  - `metrics` 中的模型历史表现，解释「这只是一个有噪声的概率信号，而非确定性预测」。  
