---
name: Model Comparison Report Generation
description: Design for automated multi-model comparison and markdown report generation
type: design
---

# 量化预测模型对比报告生成设计

## 目标

创建自动化工具，对比三个量化预测模型（LightGBM、GRU、LSTM）的参数配置和预测效果，生成结构化的 Markdown 报告。

## 范围

- 扩展 `app/ml/model_registry.py` 添加对比逻辑
- 创建独立脚本 `scripts/ml/compare_models.py` 用于生成报告
- 输出标准化 Markdown 文档到 `docs/model_comparison_report.md`
- 支持任意股票代码和日期范围

## 架构

### 数据流

```
build_features(symbol, start_date, end_date)  ← 时间截断前置
    ↓
train_all_models(X, y, model_types=[...])
    ├─ LightGBM 训练 → metrics + prediction + training_time
    ├─ GRU 训练 → metrics + prediction + training_time
    └─ LSTM 训练 → metrics + prediction + training_time
    ↓
generate_comparison_report(results, symbol, date_range, X)
    ├─ 提取异构模型参数（LightGBM vs PyTorch）
    ├─ 计算融合信号（加权平均，权重=AUC）
    ├─ 提取 LightGBM 特征重要性
    └─ 返回结构化数据
    ↓
format_comparison_markdown(report)
    ↓ (返回 Markdown 字符串)
保存到文件
```

### 关键设计决策

#### 1. 时间窗口一致性
- **原则**：date_range 必须与模型实际训练数据一致
- **实现**：date_range 作为参数前置到 `build_features(symbol, start_date, end_date)`
- **验证**：在 `generate_comparison_report()` 中检查 X 的时间范围是否与 date_range 匹配

#### 2. 融合信号计算
- **算法**：加权平均，权重基于验证集 AUC
  ```
  fusion_score = (P_lgb * AUC_lgb + P_gru * AUC_gru + P_lstm * AUC_lstm) / (AUC_lgb + AUC_gru + AUC_lstm)
  ```
- **优势**：表现更好的模型获得更高话语权
- **存储**：在 predictions 字典中新增 `fusion_score` 字段

#### 3. 异构模型参数提取
- **LightGBM**：使用 `model.get_params()` 提取所有参数
- **PyTorch（GRU/LSTM）**：从传入的 `DLConfig` 实例中读取配置
- **实现**：在 `generate_comparison_report()` 中根据模型类型分发参数提取逻辑

### 核心函数

#### 1. `generate_comparison_report(results, symbol, date_range, X, dl_config=None)`

**输入：**
- `results`: `train_all_models()` 的返回值，包含每个模型的 model、metrics、prediction、training_time
- `symbol`: 股票代码（如 "AAPL"）
- `date_range`: 元组 `(start_date, end_date)`，格式 "YYYY-MM-DD"（必须与 X 的时间范围一致）
- `X`: 特征矩阵（用于验证时间范围和计算特征重要性）
- `dl_config`: DLConfig 实例（用于提取 PyTorch 模型参数）

**输出：**
```python
{
    "metadata": {
        "symbol": "AAPL",
        "date_range": ("2024-01-01", "2024-12-31"),
        "generated_at": "2026-04-01 10:30:00",
        "data_points": 252  # 交易日数量
    },
    "parameters": {
        "lightgbm": {
            "n_estimators": 200,
            "learning_rate": 0.01,
            "max_depth": 3,
            "num_leaves": 7,
            "min_child_samples": 50,
            "subsample": 0.6,
            "colsample_bytree": 0.5,
            "reg_alpha": 1.0,
            "reg_lambda": 1.0,
        },
        "gru": {
            "hidden_size": 32,
            "num_layers": 1,
            "dropout": 0.4,
            "seq_len": 15,
            "learning_rate": 0.0005,
            "weight_decay": 0.0001,
            "batch_size": 32,
            "max_epochs": 100,
        },
        "lstm": {
            "hidden_size": 32,
            "num_layers": 1,
            "dropout": 0.4,
            "seq_len": 15,
            "learning_rate": 0.0005,
            "weight_decay": 0.0001,
            "batch_size": 32,
            "max_epochs": 100,
        }
    },
    "metrics": {
        "lightgbm": {
            "mean_auc": 0.542,
            "mean_accuracy": 0.521,
            "fold_aucs": [0.53, 0.54, 0.55, 0.54, 0.53],
            "fold_accuracies": [0.51, 0.52, 0.53, 0.52, 0.51],
            "train_test_split": "TimeSeriesSplit_n5",
            "training_time_seconds": 2.34
        },
        "gru": {
            "mean_auc": 0.551,
            "mean_accuracy": 0.535,
            "fold_aucs": [0.54, 0.55, 0.56, 0.55, 0.54],
            "fold_accuracies": [0.52, 0.53, 0.54, 0.53, 0.52],
            "seq_len": 15,
            "training_time_seconds": 45.67
        },
        "lstm": {
            "mean_auc": 0.548,
            "mean_accuracy": 0.532,
            "fold_aucs": [0.53, 0.55, 0.56, 0.54, 0.53],
            "fold_accuracies": [0.52, 0.53, 0.54, 0.53, 0.51],
            "seq_len": 15,
            "training_time_seconds": 52.11
        }
    },
    "predictions": {
        "lightgbm": 0.542,
        "gru": 0.518,
        "lstm": 0.521,
        "fusion_score": 0.527  # 加权平均，权重=AUC
    },
    "feature_importance": {
        "lightgbm": {
            "top_features": [
                {"name": "RSI_14", "importance": 0.245},
                {"name": "Volume_Ratio", "importance": 0.189},
                {"name": "MACD_Signal", "importance": 0.156}
            ]
        }
    }
}
```

**职责：**
- 根据模型类型分发参数提取逻辑（LightGBM 用 get_params()，PyTorch 用 DLConfig）
- 聚合 metrics 数据，包括 training_time_seconds
- 计算融合信号（加权平均，权重=mean_auc）
- 提取 LightGBM 的 Top 3 特征重要性
- 验证 date_range 与 X 的时间范围一致
- 返回结构化字典

#### 2. `format_comparison_markdown(report)`

**输入：** 上述结构化报告字典

**输出：** Markdown 字符串，包含以下部分：

1. **标题和元数据**
   - 股票代码、日期范围、生成时间、数据点数

2. **参数对比表**
   - 按模型列出所有关键参数
   - 突出差异（如 hidden_size、seq_len、正则化强度）

3. **性能指标表**
   - Mean AUC、Mean Accuracy
   - 各折的 AUC 和 Accuracy
   - 交叉验证策略说明
   - **新增**：训练耗时（training_time_seconds）

4. **最新预测信号表**
   - 三个模型的预测概率
   - 看涨/看跌判断（> 0.5 为看涨）
   - **新增**：融合信号（加权平均）
   - 信号一致性评估

5. **特征重要性（LightGBM 专属）**
   - Top 3 特征及其重要性分数
   - 当前主导因子解释

6. **综合评定**
   - 各模型的优缺点
   - 推荐使用场景
   - 信号融合建议

**职责：**
- 将结构化数据转换为可读的 Markdown
- 使用表格、列表、代码块等格式
- 添加解释性文本和建议
- 突出耗时和特征重要性信息

### 脚本 `scripts/ml/compare_models.py`

**功能：**
```python
async def main(
    symbol: str = "AAPL",
    start_date: str = None,  # 默认过去 1 年
    end_date: str = None,    # 默认今天
    output_path: str = "docs/model_comparison_report.md"
):
    """
    1. 加载特征数据（时间截断前置）
    2. 训练三个模型，记录耗时
    3. 生成对比报告（包括融合信号、特征重要性）
    4. 保存 Markdown 文件
    """
```

**使用方式：**
```bash
uv run python scripts/ml/compare_models.py --symbol AAPL --start-date 2024-01-01 --end-date 2024-12-31 --output docs/model_comparison_report.md
```

**关键实现细节：**
- 在 `build_features()` 调用时传入 start_date 和 end_date，确保时间窗口一致
- 在 `train_all_models()` 中记录每个模型的 training_time_seconds
- 将 DLConfig 实例传给 `generate_comparison_report()`，用于提取 PyTorch 参数

## 数据流和错误处理

### 成功路径
1. 特征数据可用（时间范围明确）→ 训练三个模型（记录耗时）→ 生成报告（融合信号、特征重要性）→ 保存文件

### 错误处理
- 特征数据不足：抛出 `ValueError`，提示需要更多历史数据
- date_range 与 X 时间范围不匹配：抛出 `ValueError`，提示时间窗口脱节
- 模型训练失败：捕获异常，记录日志，继续其他模型
- 参数提取失败（异构模型）：根据模型类型分发，捕获异常并记录
- 文件写入失败：抛出异常，提示磁盘空间或权限问题

### 参数提取分发逻辑
```python
def _extract_parameters(model, model_type, dl_config=None):
    if model_type == "lightgbm":
        return model.get_params()  # LGBMClassifier 的 scikit-learn API
    elif model_type in ["gru", "lstm"]:
        if dl_config is None:
            raise ValueError(f"DLConfig required for {model_type}")
        return {
            "hidden_size": dl_config.hidden_size,
            "num_layers": dl_config.num_layers,
            "dropout": dl_config.dropout,
            "seq_len": dl_config.seq_len,
            "learning_rate": dl_config.learning_rate,
            "weight_decay": dl_config.weight_decay,
            "batch_size": dl_config.batch_size,
            "max_epochs": dl_config.max_epochs,
        }
    else:
        raise ValueError(f"Unknown model type: {model_type}")
```

### 融合信号计算
```python
def _calculate_fusion_score(predictions, metrics):
    """
    加权平均，权重 = 各模型的 Mean AUC
    """
    total_auc = sum(metrics[m]["mean_auc"] for m in predictions.keys())
    fusion = sum(
        predictions[m] * metrics[m]["mean_auc"] / total_auc
        for m in predictions.keys()
    )
    return fusion
```

### 特征重要性提取（LightGBM 专属）
```python
def _extract_feature_importance(model, top_k=3):
    """
    从 LightGBM 模型提取 Top K 特征重要性
    """
    importances = model.feature_importances_
    feature_names = model.feature_name_  # 需要在训练时设置
    top_indices = np.argsort(importances)[-top_k:][::-1]
    return [
        {
            "name": feature_names[i],
            "importance": float(importances[i])
        }
        for i in top_indices
    ]
```

## 输出示例

```markdown
# 量化预测模型对比报告

## 元数据
- **股票代码**: AAPL
- **数据周期**: 2024-01-01 ~ 2024-12-31
- **数据点数**: 252 个交易日
- **生成时间**: 2026-04-01 10:30:00

## 参数对比

### 数据处理
| 参数 | LightGBM | GRU | LSTM |
| --- | --- | --- | --- |
| 核心视角 | 截面特征、技术指标 | 时序演变、K线形态 | 时序演变、长短期记忆 |
| 历史回溯 | 无 | 15 天 | 15 天 |
| 归一化 | 无 | RobustScaler | RobustScaler |

### 网络结构
| 参数 | LightGBM | GRU | LSTM |
| --- | --- | --- | --- |
| 隐藏层大小 | N/A | 32 | 32 |
| 网络层数 | N/A | 1 | 1 |
| Dropout | 0.6 (subsample) | 0.4 | 0.4 |
| 参数量 | ~1000 | ~6000 | ~8000 |

### 训练配置
| 参数 | LightGBM | GRU | LSTM |
| --- | --- | --- | --- |
| 学习率 | 0.01 | 0.0005 | 0.0005 |
| 正则化 | L1/L2 | weight_decay | weight_decay |
| 批次大小 | N/A | 32 | 32 |
| 交叉验证 | TimeSeriesSplit(5) | TimeSeriesSplit(5) | TimeSeriesSplit(5) |

## 性能指标

| 指标 | LightGBM | GRU | LSTM |
| --- | --- | --- | --- |
| **Mean AUC** | 0.542 | 0.551 | 0.548 |
| **Mean Accuracy** | 0.521 | 0.535 | 0.532 |
| **Fold AUCs** | [0.53, 0.54, 0.55, 0.54, 0.53] | [0.54, 0.55, 0.56, 0.55, 0.54] | [0.53, 0.55, 0.56, 0.54, 0.53] |
| **训练耗时** | 2.34 秒 | 45.67 秒 | 52.11 秒 |

## 最新预测信号

| 模型 | 预测概率 | 信号 | 置信度 |
| --- | --- | --- | --- |
| LightGBM | 54.2% | 看涨 | 中等 |
| GRU | 51.8% | 看涨 | 低 |
| LSTM | 52.1% | 看涨 | 低 |
| **融合信号** | **52.7%** | **看涨** | **中等** |

**融合算法**：加权平均，权重 = 各模型的 Mean AUC
```
fusion_score = (54.2% × 0.542 + 51.8% × 0.551 + 52.1% × 0.548) / (0.542 + 0.551 + 0.548)
             = 52.7%
```

## 特征重要性（LightGBM）

当前主导因子（Top 3）：

| 特征 | 重要性 | 解释 |
| --- | --- | --- |
| RSI_14 | 24.5% | 相对强弱指数，反映超买/超卖状态 |
| Volume_Ratio | 18.9% | 成交量比率，反映市场参与度 |
| MACD_Signal | 15.6% | MACD 信号线，反映动量变化 |

## 综合评定

### LightGBM
- **优点**: 训练速度极快（2.34 秒），对异常值容忍度高
- **缺点**: 无法捕捉时序依赖，仅基于截面特征
- **推荐**: 作为基准信号，快速决策

### GRU
- **优点**: 参数少（6k），收敛稳定，不易过拟合，AUC 最高（0.551）
- **缺点**: 无法捕捉超长期记忆
- **推荐**: 时间序列主力预测器

### LSTM
- **优点**: 可捕捉长期依赖，参数量适中
- **缺点**: 参数多（8k），训练耗时最长（52.11 秒），易过拟合
- **推荐**: 辅助验证，用于长周期趋势确认

### 信号融合建议
- 当三个模型预测同向（都 > 0.55 或都 < 0.45）时，置信度最高
- 当融合信号与 LightGBM 基准信号一致时，可增加头寸规模
- 当深度学习模型与树模型分歧时，降低头寸规模或观望
```

## 测试策略

1. **单元测试**
   - 测试 `generate_comparison_report()` 返回结构正确
   - 测试 `format_comparison_markdown()` 输出有效 Markdown

2. **集成测试**
   - 在小数据集上运行完整流程
   - 验证输出文件格式和内容

3. **手动验证**
   - 在真实股票数据上运行
   - 检查参数表、指标表、预测信号的准确性

## 依赖和约束

- 依赖：`app/ml/model_registry.py`、`app/ml/features.py`、`app/ml/dl_config.py`
- 约束：需要至少 252 个交易日的历史数据
- 性能：完整流程预计 5-15 分钟（取决于数据量和硬件）

## 后续扩展

- 支持多个股票的批量对比
- 添加可视化图表（AUC 曲线、预测分布等）
- 集成到 FastAPI 后端作为 `/api/ml/compare` 端点
- 定期自动生成报告并存档
