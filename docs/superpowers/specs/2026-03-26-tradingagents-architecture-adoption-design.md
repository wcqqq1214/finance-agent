---
name: TradingAgents 架构借鉴与改进方案
description: 从 TradingAgents 项目借鉴数据提供商抽象层、LLM 工厂模式和 BM25 记忆系统的渐进式改进设计
type: architecture
date: 2026-03-26
---

# TradingAgents 架构借鉴与改进方案

## 1. 概述

### 1.1 背景

TradingAgents 是一个高 star 的多智能体金融交易框架，与我们的 finance-agent 项目在架构上有诸多相似之处。通过分析其设计模式，我们识别出三个可以借鉴的核心架构：

1. **数据提供商抽象层**：供应商无关的数据接口，支持配置级切换
2. **LLM 提供商工厂模式**：统一的 LLM 客户端接口，支持多提供商
3. **BM25 离线记忆系统**：无 API 调用的关键词检索记忆

### 1.2 改进策略

采用**渐进式改进**方案（方案 A）：
- 保持现有 MCP 架构和 LangGraph 编排不变
- 引入低风险、高价值的基础设施改进
- 实施周期：1-2 周
- 风险等级：低

### 1.3 核心设计原则

1. **向后兼容**：现有代码继续工作，新功能通过配置开启
2. **MCP 优先**：保留 MCP 服务器作为主要数据源
3. **配置驱动**：所有切换通过配置文件，不改代码
4. **渐进迁移**：可以逐个 agent 迁移到新抽象层

## 2. 整体架构设计

### 2.1 架构层次

```
┌─────────────────────────────────────────────────┐
│  Agent Layer (Quant/News/Social/CIO)           │
│  - 保持现有 agent 逻辑不变                        │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  NEW: Data Provider Abstraction                 │
│  - 统一接口：get_stock_data(), get_news()等      │
│  - 配置驱动：config["data_vendors"]              │
│  - 支持：MCP/yfinance/Polygon/Alpha Vantage     │
│  - 运行时降级：MCP 失败自动切换 yfinance          │
│  - Redis 缓存：历史数据 7 天 TTL                 │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  NEW: LLM Provider Factory                      │
│  - 工厂函数：create_llm(provider, model)         │
│  - 支持：OpenAI/Anthropic/Google                │
│  - 提供商特定配置：reasoning_effort/thinking等   │
│  - Agent 专用优化：Quant 用推理模型              │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  NEW: BM25 Memory System                        │
│  - 离线检索，无 API 调用                          │
│  - 存储历史决策和反思                             │
│  - 补充现有 ChromaDB RAG                         │
│  - 混合检索：BM25 + ChromaDB RRF 融合           │
└─────────────────────────────────────────────────┘
```

### 2.2 与现有架构的关系

**保持不变**：
- LangGraph 多 agent 编排（`app/graph_multi.py`）
- MCP 服务器（`mcp_servers/market_data/`, `mcp_servers/news_search/`）
- FastAPI 后端和 Next.js 前端
- ChromaDB RAG 系统

**新增模块**：
- `app/dataflows/` - 数据提供商抽象层
- `app/llm_clients/` - LLM 提供商工厂
- `app/memory/` - BM25 记忆系统

**重构模块**：
- `app/llm_config.py` → 迁移到工厂模式
- `app/tools/finance_tools.py` → 通过抽象层调用

### 2.3 实施路线图

**阶段 1（第 1 周）**：
1. 实现数据提供商抽象层基础框架
2. 实现 MCP 和 yfinance 适配器
3. 集成 Redis 缓存层

**阶段 2（第 2 周）**：
1. 实现 LLM 提供商工厂模式
2. 重构现有 `llm_config.py`
3. 配置 Agent 专用模型

**阶段 3（第 2 周）**：
1. 实现 BM25 记忆系统
2. 实现混合检索（BM25 + ChromaDB）
3. 集成到 CIO Agent


## 3. 数据提供商抽象层设计

### 3.1 目录结构

```
app/dataflows/
├── __init__.py
├── base.py              # 异步 ABC 抽象基类
├── models.py            # Pydantic 数据模型（标准化契约）
├── config.py            # 配置管理
├── interface.py         # 带降级和缓存的路由器
├── cache.py             # Redis 缓存层
├── providers/
│   ├── __init__.py
│   ├── mcp_provider.py      # MCP 服务器适配器（主要）
│   ├── yfinance_provider.py # yfinance 直接调用
│   ├── polygon_provider.py  # Polygon API
│   └── alpha_vantage_provider.py
└── utils.py
```

### 3.2 Pydantic 数据模型（标准化契约）

**核心思想**：所有数据提供商必须返回标准化的 Pydantic 模型，Agent 层完全不关心底层数据源格式。

**`app/dataflows/models.py`**：

```python
from pydantic import BaseModel, Field, field_serializer
from typing import List, Optional
from datetime import datetime
from enum import Enum

class StockCandle(BaseModel):
    """标准化的 OHLCV 数据"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    @field_serializer('timestamp')
    def serialize_timestamp(self, dt: datetime, _info):
        return dt.isoformat()

class TechnicalIndicator(BaseModel):
    """技术指标数据"""
    timestamp: datetime
    indicator_name: str  # "SMA_20", "MACD", "RSI_14"
    value: float
    metadata: Optional[dict] = None  # 额外信息（如 MACD 的 signal line）
    
    @field_serializer('timestamp')
    def serialize_timestamp(self, dt: datetime, _info):
        return dt.isoformat()

class NewsArticle(BaseModel):
    """新闻文章"""
    title: str
    url: str
    published_at: datetime
    source: str
    summary: Optional[str] = None
    sentiment: Optional[float] = Field(None, ge=-1.0, le=1.0)  # -1 到 1
    
    @field_serializer('published_at')
    def serialize_published_at(self, dt: datetime, _info):
        return dt.isoformat()

class FundamentalsData(BaseModel):
    """基本面数据"""
    symbol: str
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    revenue: Optional[float] = None
    profit_margin: Optional[float] = None
    updated_at: datetime
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, dt: datetime, _info):
        return dt.isoformat()
```

**关键优势**：
- yfinance 返回的 `Open/High/Low/Close` 和 Polygon 返回的 `o/h/l/c` 都被标准化为 `open/high/low/close`
- 时间戳格式统一为 `datetime` 对象
- Agent 层代码完全解耦，不受数据源变化影响

### 3.3 异步抽象基类

**`app/dataflows/base.py`**：

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from app.dataflows.models import (
    StockCandle, TechnicalIndicator, NewsArticle, FundamentalsData
)

class ProviderError(Exception):
    """数据提供商错误基类"""
    pass

class ProviderTimeoutError(ProviderError):
    """超时错误"""
    pass

class ProviderRateLimitError(ProviderError):
    """限流错误（429）"""
    pass

class BaseDataProvider(ABC):
    """所有数据提供商必须实现的异步接口"""
    
    def __init__(self, config: dict):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def get_stock_data(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[StockCandle]:
        """
        获取 OHLCV 数据（异步）
        
        必须返回标准化的 StockCandle 列表
        提供商负责将原始数据转换为标准格式
        """
        pass
    
    @abstractmethod
    async def get_technical_indicators(
        self, 
        symbol: str, 
        indicators: List[str],  # ["SMA_20", "MACD", "RSI_14"]
        start_date: datetime,
        end_date: datetime
    ) -> List[TechnicalIndicator]:
        """获取技术指标（异步）"""
        pass
    
    @abstractmethod
    async def get_news(
        self, 
        query: str, 
        limit: int = 10,
        start_date: Optional[datetime] = None
    ) -> List[NewsArticle]:
        """搜索新闻（异步）"""
        pass
    
    @abstractmethod
    async def get_fundamentals(
        self, 
        symbol: str
    ) -> FundamentalsData:
        """获取基本面数据（异步）"""
        pass
    
    async def health_check(self) -> bool:
        """健康检查（用于降级决策）"""
        try:
            return True
        except Exception:
            return False
```

**关键特性**：
- 全异步接口（`async def`），支持高并发
- 返回类型强制为 Pydantic 模型
- 定义了三种异常类型，用于降级决策


### 3.4 Redis 缓存层

**`app/dataflows/cache.py`**：

```python
import json
import hashlib
from typing import Optional, Any, List
from datetime import timedelta
import redis.asyncio as redis
from pydantic import BaseModel

class CacheConfig:
    """缓存配置"""
    # 历史数据：长 TTL（7 天）
    STOCK_DATA_TTL = timedelta(days=7)
    # 技术指标：中等 TTL（1 天）
    INDICATORS_TTL = timedelta(days=1)
    # 新闻：短 TTL（1 小时）
    NEWS_TTL = timedelta(hours=1)
    # 基本面：中等 TTL（1 天）
    FUNDAMENTALS_TTL = timedelta(days=1)

class DataCache:
    """异步 Redis 缓存层"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    def _make_key(self, prefix: str, **kwargs) -> str:
        """生成缓存键"""
        params_str = json.dumps(kwargs, sort_keys=True, default=str)
        hash_suffix = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"dataflow:{prefix}:{hash_suffix}"
    
    async def get(self, prefix: str, **kwargs) -> Optional[List[BaseModel]]:
        """从缓存获取数据"""
        key = self._make_key(prefix, **kwargs)
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def set(
        self, 
        prefix: str, 
        data: List[BaseModel], 
        ttl: timedelta,
        **kwargs
    ):
        """写入缓存（Pydantic V2）"""
        key = self._make_key(prefix, **kwargs)
        json_data = json.dumps([item.model_dump() for item in data], default=str)
        await self.redis.setex(key, int(ttl.total_seconds()), json_data)
    
    async def invalidate(self, prefix: str, **kwargs):
        """清除缓存"""
        key = self._make_key(prefix, **kwargs)
        await self.redis.delete(key)
```

**缓存策略**：
- 历史数据（OHLCV）：7 天 TTL，因为历史数据不会变化
- 技术指标：1 天 TTL，每日收盘后重新计算
- 新闻：1 小时 TTL，新闻时效性强
- 基本面：1 天 TTL，财报数据更新频率低

### 3.5 带降级和缓存的路由器

**`app/dataflows/interface.py`**：

```python
import logging
from typing import List, Optional
from datetime import datetime
from app.dataflows.base import (
    BaseDataProvider, ProviderError, ProviderTimeoutError, ProviderRateLimitError
)
from app.dataflows.models import StockCandle, TechnicalIndicator, NewsArticle, FundamentalsData
from app.dataflows.cache import DataCache, CacheConfig
from app.dataflows.config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

_PROVIDER_REGISTRY = {
    "mcp": MCPDataProvider,
    "yfinance": YFinanceProvider,
    "polygon": PolygonProvider,
}

class DataFlowRouter:
    """
    带自动降级和缓存的数据路由器
    
    特性：
    1. 运行时异常自动降级到备用数据源
    2. Redis 缓存层（历史数据长 TTL）
    3. 异步接口支持高并发
    """
    
    def __init__(self, config: dict = None, enable_cache: bool = True):
        self.config = config or DEFAULT_CONFIG
        self._providers = {}
        self.cache = DataCache(self.config.get("redis_url")) if enable_cache else None
    
    def _get_provider(self, vendor_name: str) -> BaseDataProvider:
        """延迟加载提供商实例"""
        if vendor_name not in self._providers:
            provider_class = _PROVIDER_REGISTRY[vendor_name]
            self._providers[vendor_name] = provider_class(self.config)
        return self._providers[vendor_name]
    
    def _get_vendor_with_fallback(self, tool_name: str, category: str) -> tuple[str, Optional[str]]:
        """
        获取主提供商和备用提供商
        
        Returns:
            (primary_vendor, fallback_vendor)
        """
        # 1. 工具级配置
        primary = self.config["tool_vendors"].get(tool_name)
        # 2. 类别级配置
        if not primary:
            primary = self.config["data_vendors"][category]
        
        # 3. 确定备用提供商
        fallback = None
        if primary == "mcp":
            fallback = "yfinance"
        elif primary == "yfinance":
            fallback = self.config.get("fallback_vendor", "polygon")
        
        return primary, fallback
    
    async def _call_with_fallback(
        self,
        method_name: str,
        category: str,
        *args,
        **kwargs
    ):
        """
        调用提供商方法，失败时自动降级
        """
        primary_vendor, fallback_vendor = self._get_vendor_with_fallback(method_name, category)
        
        # 尝试主提供商
        try:
            provider = self._get_provider(primary_vendor)
            method = getattr(provider, method_name)
            result = await method(*args, **kwargs)
            logger.info(f"✓ {method_name} succeeded with {primary_vendor}")
            return result
        
        except (ProviderTimeoutError, ProviderRateLimitError, ProviderError) as e:
            logger.warning(f"✗ {method_name} failed with {primary_vendor}: {e}")
            
            # 如果有备用提供商，尝试降级
            if fallback_vendor:
                logger.info(f"↻ Falling back to {fallback_vendor}...")
                try:
                    fallback_provider = self._get_provider(fallback_vendor)
                    fallback_method = getattr(fallback_provider, method_name)
                    result = await fallback_method(*args, **kwargs)
                    logger.info(f"✓ {method_name} succeeded with fallback {fallback_vendor}")
                    return result
                except Exception as fallback_error:
                    logger.error(f"✗ Fallback {fallback_vendor} also failed: {fallback_error}")
                    raise fallback_error
            else:
                raise e
    
    async def get_stock_data(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[StockCandle]:
        """获取股票数据（带缓存和降级）"""
        # 1. 尝试从缓存读取
        if self.cache:
            cached = await self.cache.get(
                "stock_data",
                symbol=symbol,
                start=start_date.isoformat(),
                end=end_date.isoformat()
            )
            if cached:
                logger.info(f"✓ Cache hit for {symbol} stock data")
                return [StockCandle(**item) for item in cached]
        
        # 2. 缓存未命中，调用提供商（带降级）
        result = await self._call_with_fallback(
            "get_stock_data",
            "stock_data",
            symbol, start_date, end_date
        )
        
        # 3. 写入缓存
        if self.cache and result:
            await self.cache.set(
                "stock_data",
                result,
                CacheConfig.STOCK_DATA_TTL,
                symbol=symbol,
                start=start_date.isoformat(),
                end=end_date.isoformat()
            )
        
        return result
    
    # get_technical_indicators, get_news, get_fundamentals 类似实现...
```

**关键特性**：
1. **运行时降级**：MCP 超时自动切换 yfinance，对用户透明
2. **智能缓存**：历史数据 7 天 TTL，新闻 1 小时 TTL
3. **异步高并发**：支持并发获取多只股票数据
4. **日志追踪**：每次调用记录提供商和结果


## 4. LLM 提供商工厂模式设计

### 4.1 目录结构

```
app/llm_clients/
├── __init__.py
├── base.py              # ABC 抽象基类
├── factory.py           # 工厂函数
├── config.py            # LLM 配置
├── providers/
│   ├── __init__.py
│   ├── openai_client.py
│   ├── anthropic_client.py
│   └── google_client.py
└── utils.py
```

### 4.2 抽象基类

**`app/llm_clients/base.py`**：

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Type
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

class BaseLLMClient(ABC):
    """所有 LLM 提供商必须实现的接口"""
    
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        streaming: bool = True,
        max_retries: int = 3,
        temperature: float = 0.7,
        **kwargs
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.streaming = streaming
        self.max_retries = max_retries
        self.temperature = temperature
        self.extra_kwargs = kwargs
    
    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        """返回 LangChain 兼容的 LLM 实例"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """返回提供商名称（用于日志）"""
        pass
    
    def get_structured_llm(self, schema: Type[BaseModel]) -> BaseChatModel:
        """
        返回绑定了结构化输出的 LLM 实例
        
        子类可以覆盖此方法来处理提供商特定的结构化输出问题
        """
        llm = self.get_llm()
        return llm.with_structured_output(schema)
    
    def supports_streaming(self) -> bool:
        """是否支持流式输出"""
        return True
    
    def _filter_unsupported_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """过滤模型不支持的参数（子类可覆盖）"""
        return params
```

### 4.3 OpenAI 客户端（支持 o 系列特殊处理）

**`app/llm_clients/providers/openai_client.py`**：

```python
import os
import logging
from typing import Optional, Dict, Any, Type
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from app.llm_clients.base import BaseLLMClient

logger = logging.getLogger(__name__)

class OpenAIClient(BaseLLMClient):
    """OpenAI LLM 客户端（支持 o 系列特殊处理）"""
    
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        reasoning_effort: Optional[str] = None,  # "low", "medium", "high"
        **kwargs
    ):
        super().__init__(model, api_key, base_url, **kwargs)
        self.reasoning_effort = reasoning_effort
        self._is_o_series = model.startswith(("o1", "o3"))
    
    def _filter_unsupported_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        o 系列模型特殊处理：
        - 不支持 temperature（固定为 1）
        - 不支持 streaming
        - 不支持 max_tokens（使用 max_completion_tokens）
        """
        if self._is_o_series:
            filtered = params.copy()
            
            if "temperature" in filtered:
                logger.warning(f"Model {self.model} does not support temperature, removing...")
                filtered.pop("temperature")
            
            if "streaming" in filtered:
                logger.warning(f"Model {self.model} does not support streaming, disabling...")
                filtered["streaming"] = False
            
            if "max_tokens" in filtered:
                filtered["max_completion_tokens"] = filtered.pop("max_tokens")
            
            return filtered
        
        return params
    
    def get_llm(self) -> ChatOpenAI:
        """返回 LangChain ChatOpenAI 实例"""
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        
        llm_kwargs = {
            "model": self.model,
            "api_key": api_key,
            "temperature": self.temperature,
            "streaming": self.streaming,
            "max_retries": self.max_retries,
        }
        
        if self.base_url:
            llm_kwargs["base_url"] = self.base_url
        
        # o 系列支持 reasoning_effort
        if self.reasoning_effort and self._is_o_series:
            llm_kwargs["model_kwargs"] = {
                "reasoning_effort": self.reasoning_effort
            }
        
        # 过滤不支持的参数
        llm_kwargs = self._filter_unsupported_params(llm_kwargs)
        
        return ChatOpenAI(**llm_kwargs)
    
    def supports_streaming(self) -> bool:
        """o 系列不支持流式输出"""
        return not self._is_o_series
    
    def get_structured_llm(self, schema: Type[BaseModel]) -> ChatOpenAI:
        """OpenAI 的结构化输出使用 Native JSON Schema"""
        llm = self.get_llm()
        return llm.with_structured_output(schema, method="json_schema")
    
    def get_provider_name(self) -> str:
        return "OpenAI"
```

### 4.4 Anthropic 客户端

**`app/llm_clients/providers/anthropic_client.py`**：

```python
import os
import logging
from typing import Optional, Dict, Any, Type
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel
from app.llm_clients.base import BaseLLMClient

logger = logging.getLogger(__name__)

class AnthropicClient(BaseLLMClient):
    """Anthropic Claude 客户端"""
    
    def __init__(
        self,
        model: str = "claude-opus-4-6",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        extended_thinking: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(model, api_key, base_url, **kwargs)
        self.extended_thinking = extended_thinking
    
    def get_llm(self) -> ChatAnthropic:
        """返回 LangChain ChatAnthropic 实例"""
        api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
        
        llm_kwargs = {
            "model": self.model,
            "anthropic_api_key": api_key,
            "temperature": self.temperature,
            "streaming": self.streaming,
            "max_retries": self.max_retries,
        }
        
        # Claude 4.6+ 支持 extended thinking
        if self.extended_thinking and self.extended_thinking.get("enabled"):
            llm_kwargs["model_kwargs"] = {
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": self.extended_thinking.get("budget_tokens", 10000)
                }
            }
        
        return ChatAnthropic(**llm_kwargs)
    
    def get_structured_llm(self, schema: Type[BaseModel]) -> ChatAnthropic:
        """
        Anthropic 的结构化输出处理
        
        使用 tool calling（更可靠），失败时回退到 JSON mode
        """
        llm = self.get_llm()
        
        try:
            return llm.with_structured_output(schema, method="function_calling")
        except Exception as e:
            logger.warning(f"Function calling failed, falling back to JSON mode: {e}")
            return llm.with_structured_output(schema, method="json_mode")
    
    def get_provider_name(self) -> str:
        return "Anthropic"
```

### 4.5 Google 客户端

**`app/llm_clients/providers/google_client.py`**：

```python
import os
from typing import Optional, Type
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from app.llm_clients.base import BaseLLMClient

class GoogleClient(BaseLLMClient):
    """Google Gemini 客户端"""
    
    def __init__(
        self,
        model: str = "gemini-3.1-pro",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        thinking_level: Optional[str] = None,
        **kwargs
    ):
        super().__init__(model, api_key, base_url, **kwargs)
        self.thinking_level = thinking_level
    
    def get_llm(self) -> ChatGoogleGenerativeAI:
        """返回 LangChain ChatGoogleGenerativeAI 实例"""
        api_key = self.api_key or os.getenv("GOOGLE_API_KEY")
        
        llm_kwargs = {
            "model": self.model,
            "google_api_key": api_key,
            "temperature": self.temperature,
            "streaming": self.streaming,
            "max_retries": self.max_retries,
        }
        
        # Gemini 3.x 支持 thinking_level
        if self.thinking_level:
            llm_kwargs["model_kwargs"] = {
                "thinking_level": self.thinking_level
            }
        
        return ChatGoogleGenerativeAI(**llm_kwargs)
    
    def get_provider_name(self) -> str:
        return "Google"
```


### 4.6 LLM 配置系统

**`app/llm_clients/config.py`**：

```python
import os
from typing import Dict, Any, Optional

class LLMConfig:
    """LLM 配置"""
    
    # 默认配置
    DEFAULT_PROVIDER = "openai"
    DEFAULT_MODEL = "gpt-4o"
    
    # 全局默认参数
    DEFAULT_STREAMING = True
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_TEMPERATURE = 0.7
    
    # Agent 角色到模型的映射
    AGENT_MODEL_MAPPING = {
        "quant": {
            "provider": "openai",
            "model": "o1",  # o 系列推理模型
            "reasoning_effort": "high",
            "streaming": False,  # o 系列不支持流式
            "temperature": None,  # o 系列不支持 temperature
        },
        "news": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "extended_thinking": {"enabled": True, "budget_tokens": 10000},
            "streaming": True,
            "temperature": 0.7,
        },
        "social": {
            "provider": "google",
            "model": "gemini-3.1-flash",
            "thinking_level": "minimal",
            "streaming": True,
            "temperature": 0.5,
        },
        "cio": {
            "provider": "anthropic",
            "model": "claude-opus-4-6",
            "extended_thinking": {"enabled": True, "budget_tokens": 20000},
            "streaming": True,
            "temperature": 0.8,
        },
    }
    
    @classmethod
    def get_agent_config(cls, agent_type: str) -> Dict[str, Any]:
        """获取 Agent 专用配置（带默认值）"""
        config = cls.AGENT_MODEL_MAPPING.get(agent_type, {}).copy()
        
        # 填充默认值
        config.setdefault("provider", cls.DEFAULT_PROVIDER)
        config.setdefault("model", cls.DEFAULT_MODEL)
        config.setdefault("streaming", cls.DEFAULT_STREAMING)
        config.setdefault("max_retries", cls.DEFAULT_MAX_RETRIES)
        config.setdefault("temperature", cls.DEFAULT_TEMPERATURE)
        
        return config
```

**Agent 模型分配策略**：
- **Quant Agent**: OpenAI o1（高推理能力，适合解释 SHAP 归因和复杂特征）
- **News Agent**: Claude Sonnet 4.6（长上下文，适合处理大量召回文档）
- **Social Agent**: Gemini 3.1 Flash（速度优先，社交情绪分析不需要深度推理）
- **CIO Agent**: Claude Opus 4.6（最强综合能力，extended thinking 20000 tokens）

### 4.7 工厂函数

**`app/llm_clients/factory.py`**：

```python
from typing import Optional, Dict, Any
from app.llm_clients.base import BaseLLMClient
from app.llm_clients.config import LLMConfig
from app.llm_clients.providers.openai_client import OpenAIClient
from app.llm_clients.providers.anthropic_client import AnthropicClient
from app.llm_clients.providers.google_client import GoogleClient

def create_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    agent_type: Optional[str] = None,
    **kwargs
) -> BaseLLMClient:
    """
    LLM 客户端工厂函数
    
    Args:
        provider: LLM 提供商（"openai", "anthropic", "google"）
        model: 模型名称
        agent_type: Agent 类型（"quant", "news", "social", "cio"）
                   如果指定，会使用 Agent 专用配置
        **kwargs: 提供商特定参数
    
    Returns:
        BaseLLMClient 实例
    
    Examples:
        # 方式 1：直接指定提供商和模型
        client = create_llm_client(provider="openai", model="gpt-4o")
        
        # 方式 2：使用 Agent 预设配置
        client = create_llm_client(agent_type="quant")
        
        # 方式 3：覆盖 Agent 配置
        client = create_llm_client(
            agent_type="cio",
            extended_thinking={"enabled": True, "budget_tokens": 30000}
        )
    """
    # 如果指定了 agent_type，使用预设配置
    if agent_type:
        agent_config = LLMConfig.get_agent_config(agent_type)
        provider = provider or agent_config["provider"]
        model = model or agent_config["model"]
        # 合并 Agent 配置和用户参数
        for key, value in agent_config.items():
            if key not in ("provider", "model") and key not in kwargs:
                kwargs[key] = value
    
    # 使用默认值
    provider = provider or LLMConfig.DEFAULT_PROVIDER
    provider_config = LLMConfig.get_provider_config(provider)
    model = model or provider_config.get("default_model")
    
    # 路由到具体提供商
    if provider == "openai":
        return OpenAIClient(model=model, **kwargs)
    elif provider == "anthropic":
        return AnthropicClient(model=model, **kwargs)
    elif provider == "google":
        return GoogleClient(model=model, **kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

def create_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    agent_type: Optional[str] = None,
    **kwargs
):
    """
    便捷函数：直接返回 LangChain LLM 实例
    
    Returns:
        BaseChatModel: 可直接用于 LangGraph 的 LLM
    """
    client = create_llm_client(provider, model, agent_type, **kwargs)
    return client.get_llm()
```

### 4.8 使用示例

**基础使用**：
```python
from app.llm_clients.factory import create_llm

# 自动处理 o 系列特殊性
quant_llm = create_llm(agent_type="quant")
# 内部自动：streaming=False, temperature 被移除

# 流式输出（其他 Agent）
news_llm = create_llm(agent_type="news")
# 内部自动：streaming=True, max_retries=3
```

**结构化输出**：
```python
from pydantic import BaseModel
from app.llm_clients.factory import create_llm_client

class QuantReport(BaseModel):
    symbol: str
    recommendation: str
    confidence: float

# 创建客户端
client = create_llm_client(agent_type="quant")

# 获取结构化输出 LLM
structured_llm = client.get_structured_llm(QuantReport)

# 调用
result = structured_llm.invoke("Analyze AAPL")
# result 是 QuantReport 实例，字段保证存在
```

**在 graph_multi.py 中集成**：
```python
from app.llm_clients.factory import create_llm

# 为不同 Agent 分配不同模型
quant_llm = create_llm(agent_type="quant")  # o1 with high reasoning
news_llm = create_llm(agent_type="news")    # Claude Sonnet
cio_llm = create_llm(agent_type="cio")      # Claude Opus with extended thinking

# 在 LangGraph 中使用
def quant_agent_node(state: AgentState):
    response = quant_llm.invoke([...])
    return {"quant_report": response.content}
```

