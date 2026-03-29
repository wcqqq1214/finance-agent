---
name: ml-deep-learning-expansion
description: 深度学习模块扩展设计 - 为美股七姐妹预测添加GRU/LSTM时序模型
type: design
date: 2026-03-30
---

# 深度学习模块扩展设计

## 项目背景

当前ML模块使用LightGBM处理二维表格特征，对美股"七姐妹"（AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA）的预测能力有限。金融数据具有典型的"极低信噪比"特征，需要引入时序建模能力来捕捉价格形态和跨资产联动效应。

## 设计目标

1. **分阶段实验**：先实现GRU baseline验证时序建模价值，再扩展到LSTM和STGNN
2. **可扩展架构**：为未来的模型融合和并行预测打好基础
3. **防数据穿越**：严格的Fold隔离归一化和测试集lookback机制
4. **向后兼容**：与现有LightGBM保持接口一致，支持统一调度

## 核心决策

- **模型选择**：单层GRU (hidden_size=32, dropout=0.4)，参数量约6k
- **窗口大小**：可配置（默认15天），支持10/15/20天实验
- **归一化**：RobustScaler（抗极值），特征分组处理
- **训练策略**：AdamW + 加权BCE + 早停（patience=10）+ 最佳权重回滚
- **最终目标**：并行架构，为CIO Agent提供多维度"专家意见"


## 架构设计

### 整体架构

```
用户请求
    ↓
app/tools/quant_tool.py (调用model_registry)
    ↓
model_registry.train_all_models()
    ↓
    ├─→ LightGBM (现有)
    │   └─→ model_trainer.train_lightgbm()
    │
    └─→ 深度学习模型 (新增)
        ├─→ dl_config.py (配置管理)
        ├─→ dl_dataset.py (数据预处理)
        ├─→ dl_models.py (GRU/LSTM定义)
        └─→ dl_trainer.py (训练循环)
    ↓
返回多模型预测结果
    ↓
CIO Agent (综合决策)
```

### 新增模块

```
app/ml/
├── dl_config.py          # 深度学习配置类（窗口大小、模型超参数）
├── dl_dataset.py         # 时序数据集构造器（滑动窗口 + Scaler）
├── dl_models.py          # 神经网络模型定义（GRU/LSTM）
├── dl_trainer.py         # 深度学习训练器（统一训练循环）
└── model_registry.py     # 模型注册表（统一调度LightGBM/GRU/LSTM）
```

### 设计原则

1. **向后兼容**：不修改现有的`features.py`、`model_trainer.py`等模块
2. **接口统一**：所有模型通过`model_registry.py`统一调用
3. **配置驱动**：通过`dl_config.py`控制所有超参数，避免硬编码
4. **防数据穿越**：在`dl_dataset.py`中严格实现Fold隔离的归一化


## 核心模块详细设计

### 1. 配置模块（dl_config.py）

#### DLConfig 配置类

```python
@dataclass
class DLConfig:
    # 数据处理配置
    seq_len: int = 15                    # 滑动窗口大小（默认15天）
    scaler_type: str = "robust"          # 归一化方法：robust/standard/minmax
    
    # 模型架构配置
    model_type: str = "gru"              # 模型类型：gru/lstm
    hidden_size: int = 32                # GRU/LSTM隐藏层大小
    num_layers: int = 1                  # RNN层数（固定为1）
    dropout: float = 0.4                 # Dropout比例
    
    # 训练配置
    batch_size: int = 32                 # 批次大小
    learning_rate: float = 5e-4          # 学习率
    weight_decay: float = 1e-4           # AdamW权重衰减
    max_epochs: int = 100                # 最大训练轮数
    early_stopping_patience: int = 10    # 早停耐心值
    
    # TimeSeriesSplit配置
    n_splits: int = 5                    # 时序交叉验证折数
    
    # 设备配置
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
```

#### 特征分组策略

**需要归一化的特征（COLUMNS_TO_SCALE）**：
- 价格类：`ret_1d`, `ret_3d`, `ret_5d`, `ret_10d`, `volatility_5d`, `volatility_10d`
- 技术指标：`volume_ratio_5d`, `gap`, `ma5_vs_ma20`, `rsi_14`
- 新闻计数：`n_articles`, `n_relevant`, `n_positive`, `n_negative`, `news_count_*`

**直接使用的特征（PASSTHROUGH_COLUMNS）**：
- 情绪得分：`sentiment_score`, `sentiment_score_*`, `sentiment_momentum_3d`
- 比例特征：`relevance_ratio`, `positive_ratio`, `negative_ratio`
- 类别特征：`day_of_week`

**设计理由**：
- `rsi_14`虽然有界（0-100），但绝对值远大于情绪特征（-1到1），会导致梯度倾斜，必须归一化
- 情绪特征已在小范围内，直接使用避免过度处理
- RobustScaler基于中位数和IQR，对金融数据的极值（黑天鹅事件）更鲁棒


### 2. 数据集模块（dl_dataset.py）

#### 核心设计：防止数据穿越

**关键问题1：标签对齐**
- 当前项目中，标签已在特征工程阶段做了`shift(-1)`
- `y[t]`存储的是`t+1`的涨跌（`close.shift(-1) > close`）
- 窗口`[t-14, t-13, ..., t]`的标签应取`y[t]`（即预测t+1）

**关键问题2：测试集冷启动**
- 深度学习需要连续的历史窗口（seq_len=15天）
- 如果测试集直接切分，前14天无法构造完整窗口，会丢失预测
- 解决方案：测试集特征向训练集末尾"借"seq_len-1天作为lookback

#### TimeSeriesDataset 类

```python
class TimeSeriesDataset(Dataset):
    def __init__(
        self,
        X: np.ndarray,           # 特征矩阵
        y: np.ndarray,           # 标签（已shift(-1)）
        seq_len: int = 15,       # 滑动窗口大小
        is_test: bool = False,   # 是否为测试集
    ):
```

**训练集逻辑**：
- X和y长度相同
- `__len__`: `len(X) - seq_len + 1`（前seq_len-1个样本无法构造完整窗口）
- `__getitem__`: 窗口`X[idx:idx+seq_len]`，标签`y[idx+seq_len-1]`

**测试集逻辑**：
- X比y长seq_len-1（包含lookback）
- `__len__`: `len(y)`（有效样本数）
- `__getitem__`: 窗口`X[idx:idx+seq_len]`，标签`y[idx]`

#### prepare_dl_data 函数

**功能**：为单个TimeSeriesSplit fold准备数据

**关键步骤**：
1. 训练集正常切分：`X_train = X.iloc[train_idx]`
2. 测试集扩展索引：`extended_test_idx = range(first_test_idx - lookback_len, first_test_idx) + test_idx`
3. Fold隔离归一化：Scaler只在训练集上fit，测试集用训练集参数transform
4. 特征分组处理：COLUMNS_TO_SCALE归一化，PASSTHROUGH_COLUMNS直接使用

**边界处理**：
- 如果`first_test_idx < lookback_len`，直接抛出异常
- 原因：训练集数据不足，无法提供历史回溯窗口，会导致数据穿越


### 3. 模型模块（dl_models.py）

#### GRUClassifier 架构

```python
class GRUClassifier(nn.Module):
    def __init__(
        self,
        input_size: int,        # 特征维度（约35）
        hidden_size: int = 32,  # GRU隐藏层大小
        dropout: float = 0.4,   # Dropout比例
    ):
```

**架构流程**：
```
Input (batch, seq_len, features) 
  → GRU (batch, seq_len, hidden_size)
  → 取最后时间步 (batch, hidden_size)
  → Dropout(0.4)
  → Linear (batch, 1)
  → 输出logits（不加Sigmoid）
```

**设计原则**：
- **单层GRU**：避免过拟合，适合低信噪比金融数据
- **hidden_size=32**：参数量约6k（input_size≈35时），适合5000行日频数据
- **强Dropout(0.4)**：防止记忆化历史K线，必须手动添加（单层GRU的dropout参数无效）
- **输出logits**：数值稳定，配合BCEWithLogitsLoss使用Log-Sum-Exp技巧

**参数量分析**：
- GRU参数：`3 * (input_size * hidden_size + hidden_size * hidden_size + hidden_size)`
- FC参数：`hidden_size * 1 + 1`
- 总计：约6000参数（input_size=35, hidden_size=32）

#### LSTMClassifier 架构

与GRU类似，但使用LSTM单元（多了cell state）。用于消融实验，对比GRU和LSTM在金融时序上的表现。

#### 为什么不使用Transformer

**删除理由**：
1. **数据饥渴**：Transformer需要海量数据学习时间关系，日频5000行数据会严重过拟合
2. **缺少归纳偏置**：GRU/LSTM天生假设"时间连续，当前依赖上一步"，Transformer需要暴力学习
3. **位置编码缺失**：标准Transformer需要位置编码，否则会把时序当成无序"词袋"
4. **维护成本高**：臃肿且难调，拖慢项目进度


### 4. 训练器模块（dl_trainer.py）

#### train_dl_model 函数

**接口设计**：
```python
def train_dl_model(
    X: pd.DataFrame,
    y: pd.Series,
    config: DLConfig | None = None,
) -> Tuple[nn.Module, Dict[str, float | str | List[float]]]:
```

**与LightGBM兼容**：
- 输入：`(X, y)` DataFrame和Series
- 输出：`(model, metrics)` 模型和评估指标
- metrics格式与`model_trainer.py`保持一致

#### 训练流程

**外层循环：TimeSeriesSplit**
```python
tss = TimeSeriesSplit(n_splits=5)
for fold_idx, (train_idx, test_idx) in enumerate(tss.split(X)):
    # 1. prepare_dl_data：Fold隔离归一化 + lookback
    # 2. 创建Dataset和DataLoader
    # 3. 创建模型和优化器
    # 4. 训练循环（内层）
    # 5. Fold评估
```

**内层循环：训练+早停**
```python
best_val_loss = float("inf")
patience_counter = 0
best_model_wts = copy.deepcopy(model.state_dict())  # 初始化最佳权重

for epoch in range(max_epochs):
    # 训练阶段
    model.train()
    for X_batch, y_batch in train_loader:
        optimizer.zero_grad()
        logits = model(X_batch)
        loss = criterion(logits, y_batch)
        loss.backward()
        optimizer.step()
    
    # 验证阶段
    model.eval()
    val_loss = compute_validation_loss()
    
    # 早停检查 + 最佳权重保存
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        patience_counter = 0
        best_model_wts = copy.deepcopy(model.state_dict())  # 保存最佳权重
    else:
        patience_counter += 1
        if patience_counter >= patience:
            break

# 核心：回滚到最佳权重
model.load_state_dict(best_model_wts)
```

**关键修复：早停陷阱**
- PyTorch不会自动保存最佳权重
- break时模型持有的是最后一次迭代的权重（通常已过拟合）
- 必须手动保存并回滚到`best_val_loss`时的权重

#### 加权BCE损失函数

**处理类别不平衡**：
```python
# 计算每个fold的正负样本比例
num_positives = (y_train == 1).sum()
num_negatives = (y_train == 0).sum()
pos_weight_val = num_negatives / max(num_positives, 1)
pos_weight = torch.tensor([pos_weight_val]).to(device)

# 创建加权损失函数
criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
```

**为什么不用Focal Loss**：
- Focal Loss强迫模型关注"难分类样本"
- 金融市场中，难分类样本往往是纯随机噪音或黑天鹅事件
- 使用Focal Loss会拟合噪音，破坏对正常量价趋势的捕捉

#### 优化器配置

```python
optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=5e-4,              # 保守学习率
    weight_decay=1e-4,    # L2正则化
)
```

**AdamW vs Adam**：
- AdamW将权重衰减从梯度更新中分离
- L2正则化效果更好，压制权重过大


### 5. 模型注册表（model_registry.py）

#### train_all_models 函数

**功能**：统一调度LightGBM和深度学习模型，为CIO Agent提供多维度预测

```python
def train_all_models(
    symbol: str,
    model_types: List[ModelType] | None = None,
    dl_config: DLConfig | None = None,
) -> Dict[str, Dict]:
```

**返回格式**：
```python
{
    "lightgbm": {
        "model": LGBMClassifier,
        "metrics": {"mean_auc": 0.58, "mean_accuracy": 0.56, ...},
        "prediction": 0.62,  # 看涨62%
    },
    "gru": {
        "model": nn.Module,
        "metrics": {"mean_auc": 0.60, "mean_accuracy": 0.57, ...},
        "prediction": 0.48,  # 看跌52%
    },
}
```

#### format_predictions_for_agent 函数

**为CIO Agent生成Markdown报告**：

```markdown
## 量化模型预测汇总

### LIGHTGBM 分析师
- **预测概率**: 62% 看涨
- **模型AUC**: 0.5800
- **模型准确率**: 0.5600
- **分析依据**: 基于截面因子和近期动量

### GRU 分析师
- **预测概率**: 48% 看跌
- **模型AUC**: 0.6000
- **模型准确率**: 0.5700
- **分析依据**: 基于过去15天的K线序列形态
```

**设计理念**：
- 不同模型扮演不同"量化分析师"角色
- CIO Agent综合多维度意见，结合实时新闻做最终决策
- 比单一融合概率更有逻辑性和可解释性

## 分阶段实施路线图

### 第一阶段：GRU Baseline（本次实现）

**目标**：验证时序建模价值

**任务清单**：
1. 实现`dl_config.py`：配置类和特征分组
2. 实现`dl_dataset.py`：时序数据集和归一化
3. 实现`dl_models.py`：GRUClassifier定义
4. 实现`dl_trainer.py`：训练循环和早停
5. 实现`model_registry.py`：多模型调度
6. 编写测试脚本：对比GRU和LightGBM的AUC

**验收标准**：
- GRU在美股七姐妹上的平均AUC > LightGBM
- 或至少在2-3只股票上显著优于LightGBM
- 无数据穿越（通过人工审查代码逻辑）

### 第二阶段：LSTM对比实验（后续优化）

**目标**：消融实验，对比GRU和LSTM

**任务清单**：
1. 训练LSTM模型（代码已预留接口）
2. 对比GRU vs LSTM的AUC和训练速度
3. 实验不同窗口大小（10/15/20天）

### 第三阶段：STGNN和模型融合（终极目标）

**目标**：捕捉七姐妹联动效应，实现完整并行架构

**任务清单**：
1. 实现跨股票特征工程（七姐妹横截面拼接）
2. 实现STGNN模型（基于PyTorch Geometric）
3. 构建动态相关性图（基于30天收益率皮尔逊系数）
4. 实现模型融合策略（加权平均或Stacking）
5. 集成到CIO Agent工具链

## 关键技术风险

1. **过拟合风险**：日频数据量小（5000行），需严格控制模型复杂度
2. **数据穿越风险**：必须严格审查Fold隔离和lookback逻辑
3. **训练时间**：深度学习比LightGBM慢10-20倍，需优化DataLoader
4. **设备依赖**：GPU加速可选但非必需，CPU训练时间约5-10分钟/股票

## 依赖项

**新增Python包**：
```
torch>=2.0.0
scikit-learn>=1.3.0  # 已有，用于Scaler
```

**现有依赖**：
- pandas, numpy（数据处理）
- lightgbm（对比baseline）
- app/ml/features.py（特征工程）

