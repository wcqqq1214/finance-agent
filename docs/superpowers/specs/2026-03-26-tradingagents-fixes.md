# 设计文档修复清单

## Critical Issues 修复

### 1. DataFlowRouter 异常处理
**问题**: 缺少通用异常处理
**修复**: 在 `_call_with_fallback` 中添加 `Exception` 捕获

```python
except (ProviderTimeoutError, ProviderRateLimitError, ProviderError) as e:
    # ... 现有代码
except Exception as e:  # 新增：捕获所有其他异常
    logger.error(f"✗ Unexpected error with {primary_vendor}: {e}")
    if fallback_vendor:
        # 尝试降级
```

### 2. Cache 返回类型修复
**问题**: `cache.get()` 返回 dict 而非 Pydantic 模型
**修复**: 明确缓存存储 JSON dict，调用方负责重建模型

```python
# cache.py - 保持不变，返回 List[dict]
async def get(self, prefix: str, **kwargs) -> Optional[List[dict]]:
    """从缓存获取数据（返回 dict 列表）"""
    # ... 现有实现
```

### 3. Provider Registry Import
**问题**: 缺少 import 语句
**修复**: 在 `interface.py` 顶部添加

```python
from app.dataflows.providers.mcp_provider import MCPDataProvider
from app.dataflows.providers.yfinance_provider import YFinanceProvider
from app.dataflows.providers.polygon_provider import PolygonProvider
```

### 4. Memory 异步一致性
**问题**: BaseMemory.search() 未定义为 async
**修复**: BM25Memory 保持同步，HybridMemory 定义为 async

```python
# base.py
class BaseMemory(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 3) -> List[MemorySearchResult]:
        """检索相关记忆（同步）"""
        pass

# hybrid_memory.py
class HybridMemory(BaseMemory):
    async def search_async(self, query: str, top_k: int = 3) -> List[MemorySearchResult]:
        """异步混合检索"""
        # ChromaDB 调用
```

## Major Issues 修复

### 5. LLMConfig.get_provider_config()
**问题**: 方法缺失
**修复**: 添加方法定义

```python
@classmethod
def get_provider_config(cls, provider: str) -> Dict[str, Any]:
    """获取提供商配置"""
    return {
        "openai": {"default_model": "gpt-4o"},
        "anthropic": {"default_model": "claude-opus-4-6"},
        "google": {"default_model": "gemini-3.1-pro"},
    }.get(provider, {})
```

### 6. Pydantic 数据验证
**问题**: StockCandle 缺少逻辑验证
**修复**: 添加 model_validator

```python
from pydantic import model_validator

class StockCandle(BaseModel):
    # ... 字段定义

    @model_validator(mode='after')
    def validate_ohlc(self) -> 'StockCandle':
        if self.high < self.low:
            raise ValueError("high must be >= low")
        if self.high < self.open or self.high < self.close:
            raise ValueError("high must be >= open and close")
        if self.volume < 0:
            raise ValueError("volume must be >= 0")
        return self
```

### 7. RRF 实现完整性
**问题**: 只返回 BM25 结果
**修复**: 从两个来源构建结果

```python
# 构建结果（从两个来源）
results = []
result_map = {r.situation: r for r in bm25_results}

for key in sorted_keys:
    if key in result_map:
        results.append(MemorySearchResult(
            situation=key,
            recommendation=result_map[key].recommendation,
            score=scores[key],
            metadata=result_map[key].metadata
        ))
    else:
        # 从 ChromaDB 结果中查找
        for doc, metadata in zip(chroma_results['documents'][0], chroma_results['metadatas'][0]):
            if doc == key:
                results.append(MemorySearchResult(
                    situation=doc,
                    recommendation=metadata.get('recommendation', ''),
                    score=scores[key],
                    metadata=metadata
                ))
                break
```

### 8. 配置验证
**问题**: 无配置验证
**修复**: 添加验证函数

```python
def validate_config(config: dict) -> None:
    """验证配置有效性"""
    for category, vendor in config["data_vendors"].items():
        if vendor not in _PROVIDER_REGISTRY:
            raise ValueError(f"Invalid vendor '{vendor}' for category '{category}'")
```

### 9. Agent 类型映射
**问题**: 命名不一致
**修复**: 在文档中明确映射关系

```markdown
## Agent 类型映射

| Agent 类型 | graph_multi.py 节点名 | 说明 |
|-----------|---------------------|------|
| "quant"   | Quant_Agent         | 量化分析 |
| "news"    | News_Agent          | 新闻分析 |
| "social"  | Social_Agent        | 社交情绪 |
| "cio"     | CIO_Agent           | 最终决策 |
```

### 10. 结构化输出错误处理
**问题**: OpenAI 缺少 fallback
**修复**: 添加 try-except

```python
def get_structured_llm(self, schema: Type[BaseModel]) -> ChatOpenAI:
    llm = self.get_llm()
    try:
        return llm.with_structured_output(schema, method="json_schema")
    except Exception as e:
        logger.warning(f"json_schema failed, falling back to json_mode: {e}")
        return llm.with_structured_output(schema, method="json_mode")
```

