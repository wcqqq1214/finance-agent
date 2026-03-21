# OKX交易API集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 集成OKX交易所API，支持实盘和模拟盘的账户管理、交易执行和行情查询功能

**Architecture:** Client-Routes分层架构。OKXTradingClient封装SDK调用，FastAPI routes提供RESTful接口，ConfigManager管理配置，支持实盘/模拟盘双模式切换

**Tech Stack:** FastAPI, python-okx SDK, Pydantic, pytest, tenacity (重试机制)

---

## 文件结构规划

### 新增文件
```
app/okx/
├── __init__.py                 # 模块初始化，导出get_okx_client等
├── trading_client.py           # OKXTradingClient类，封装SDK调用
└── exceptions.py               # OKX错误类型定义

app/api/routes/
└── okx.py                      # OKX API路由（账户、交易、行情、系统）

tests/
├── test_okx_client.py          # OKXTradingClient单元测试
└── test_okx_routes.py          # OKX routes集成测试
```

### 修改文件
```
app/config_manager.py           # 扩展：get_okx_settings, update_okx_settings
app/api/models/schemas.py       # 扩展：OKX相关Pydantic模型
app/api/routes/settings.py      # 扩展：OKX设置管理接口
app/api/main.py                 # 注册OKX router
.env                            # 添加OKX配置
pyproject.toml                  # 添加依赖：python-okx, tenacity
```

---

## Task 1: SDK验证与选择（Phase 0）

**Files:**
- Create: `app/okx/sdk_poc.py` (临时POC文件)
- Modify: `.env`

- [ ] **Step 1: 安装python-okx SDK**

```bash
cd /home/wcqqq21/finance-agent
uv add python-okx tenacity
```

Expected: 依赖成功添加到pyproject.toml

- [ ] **Step 2: 添加OKX模拟盘配置到.env**

在 `.env` 文件末尾添加：

```bash
# OKX Demo Trading API (模拟盘)
OKX_DEMO_API_KEY=923cc63f-d44d-4726-9767-c2237538a36e
OKX_DEMO_SECRET_KEY=5C45AEA155CD0A29B91C26B510D95AB9
OKX_DEMO_PASSPHRASE=200312142058Wcq.

# OKX Live Trading API (实盘 - 暂时留空)
OKX_LIVE_API_KEY=
OKX_LIVE_SECRET_KEY=
OKX_LIVE_PASSPHRASE=

# Default mode
OKX_DEFAULT_MODE=demo
```

- [ ] **Step 3: 编写SDK POC代码验证API结构**

Create `app/okx/sdk_poc.py`:

```python
"""OKX SDK概念验证代码"""
import os
from dotenv import load_dotenv

load_dotenv()

# 测试导入python-okx包
try:
    import okx
    print(f"✓ python-okx version: {okx.__version__ if hasattr(okx, '__version__') else 'unknown'}")
except ImportError as e:
    print(f"✗ Failed to import python-okx: {e}")
    exit(1)

# 测试初始化客户端
api_key = os.getenv("OKX_DEMO_API_KEY")
secret_key = os.getenv("OKX_DEMO_SECRET_KEY")
passphrase = os.getenv("OKX_DEMO_PASSPHRASE")

print(f"\nTesting with demo credentials:")
print(f"API Key: {api_key[:10]}...")

# 根据实际SDK API调整以下代码
# 这里需要查阅python-okx文档确定正确的初始化方式
try:
    # 示例：可能的初始化方式
    # client = okx.Account(api_key, secret_key, passphrase, flag="1")
    print("✓ SDK initialization structure identified")
    print("TODO: Update this POC with actual SDK API calls")
except Exception as e:
    print(f"✗ SDK initialization failed: {e}")

print("\n=== SDK Verification Complete ===")
print("Next: Update trading_client.py with verified SDK API")
```

- [ ] **Step 4: 运行POC验证SDK**

```bash
uv run python app/okx/sdk_poc.py
```

Expected: 输出SDK版本信息和初始化结构

- [ ] **Step 5: 根据SDK文档更新POC代码**

查阅python-okx文档，更新sdk_poc.py中的初始化代码，确保能成功调用：
- 账户API（获取余额）
- 交易API（查询订单）
- 行情API（获取ticker）

- [ ] **Step 6: 提交SDK验证结果**

```bash
git add .env app/okx/sdk_poc.py pyproject.toml
git commit -m "chore: add OKX SDK and verify API structure"
```

---

## Task 2: 错误处理模块

**Files:**
- Create: `app/okx/exceptions.py`
- Test: `tests/test_okx_exceptions.py`

- [ ] **Step 1: 编写错误类型定义**

Create `app/okx/exceptions.py`:

```python
"""OKX API错误类型定义"""
from typing import Optional


class OKXError(Exception):
    """OKX API错误基类"""

    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code
        super().__init__(self.message)

    def __str__(self):
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class OKXAuthError(OKXError):
    """认证错误（API密钥无效、签名错误等）"""
    pass


class OKXRateLimitError(OKXError):
    """频率限制错误"""
    pass


class OKXInsufficientBalanceError(OKXError):
    """余额不足错误"""
    pass


class OKXOrderError(OKXError):
    """订单相关错误（下单失败、撤单失败等）"""
    pass


class OKXConfigError(OKXError):
    """配置错误（缺少API密钥等）"""
    pass
```

- [ ] **Step 2: 编写错误类型测试**

Create `tests/test_okx_exceptions.py`:

```python
"""测试OKX错误类型"""
import pytest
from app.okx.exceptions import (
    OKXError,
    OKXAuthError,
    OKXRateLimitError,
    OKXInsufficientBalanceError,
    OKXOrderError,
    OKXConfigError,
)


def test_okx_error_basic():
    """测试基础错误"""
    error = OKXError("Test error")
    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.code is None


def test_okx_error_with_code():
    """测试带错误码的错误"""
    error = OKXError("Test error", code="50000")
    assert str(error) == "[50000] Test error"
    assert error.code == "50000"


def test_okx_auth_error():
    """测试认证错误"""
    error = OKXAuthError("Invalid API key", code="50101")
    assert isinstance(error, OKXError)
    assert str(error) == "[50101] Invalid API key"


def test_okx_rate_limit_error():
    """测试频率限制错误"""
    error = OKXRateLimitError("Rate limit exceeded")
    assert isinstance(error, OKXError)


def test_okx_insufficient_balance_error():
    """测试余额不足错误"""
    error = OKXInsufficientBalanceError("Insufficient balance")
    assert isinstance(error, OKXError)


def test_okx_order_error():
    """测试订单错误"""
    error = OKXOrderError("Order failed")
    assert isinstance(error, OKXError)


def test_okx_config_error():
    """测试配置错误"""
    error = OKXConfigError("Missing API key")
    assert isinstance(error, OKXError)
```

- [ ] **Step 3: 运行测试验证错误类型**

```bash
uv run pytest tests/test_okx_exceptions.py -v
```

Expected: 所有测试通过

- [ ] **Step 4: 提交错误处理模块**

```bash
git add app/okx/exceptions.py tests/test_okx_exceptions.py
git commit -m "feat(okx): add error type definitions"
```

---

## Task 3: 配置管理扩展

**Files:**
- Modify: `app/config_manager.py`
- Test: `tests/test_config_manager_okx.py`

- [ ] **Step 1: 编写ConfigManager扩展测试**

Create `tests/test_config_manager_okx.py`:

```python
"""测试ConfigManager的OKX配置功能"""
import pytest
import os
from app.config_manager import ConfigManager


@pytest.fixture
def config_manager(tmp_path, monkeypatch):
    """创建临时ConfigManager"""
    env_file = tmp_path / ".env"
    manager = ConfigManager(env_path=env_file)

    # 设置测试环境变量
    monkeypatch.setenv("OKX_DEMO_API_KEY", "test_demo_key")
    monkeypatch.setenv("OKX_DEMO_SECRET_KEY", "test_demo_secret")
    monkeypatch.setenv("OKX_DEMO_PASSPHRASE", "test_demo_pass")

    return manager


def test_get_okx_settings_demo(config_manager):
    """测试获取demo模式配置"""
    settings = config_manager.get_okx_settings("demo")

    assert settings["mode"] == "demo"
    assert settings["api_key"] == "test_demo_key"
    assert settings["secret_key"] == "test_demo_secret"
    assert settings["passphrase"] == "test_demo_pass"


def test_get_okx_settings_live(config_manager, monkeypatch):
    """测试获取live模式配置"""
    monkeypatch.setenv("OKX_LIVE_API_KEY", "test_live_key")
    monkeypatch.setenv("OKX_LIVE_SECRET_KEY", "test_live_secret")
    monkeypatch.setenv("OKX_LIVE_PASSPHRASE", "test_live_pass")

    settings = config_manager.get_okx_settings("live")

    assert settings["mode"] == "live"
    assert settings["api_key"] == "test_live_key"


def test_update_okx_settings(config_manager):
    """测试更新OKX配置"""
    updated = config_manager.update_okx_settings(
        mode="demo",
        api_key="new_key",
        secret_key="new_secret",
        passphrase="new_pass"
    )

    assert updated["api_key"] == "new_key"
    assert updated["secret_key"] == "new_secret"
    assert updated["passphrase"] == "new_pass"

    # 验证环境变量已更新
    assert os.getenv("OKX_DEMO_API_KEY") == "new_key"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_config_manager_okx.py -v
```

Expected: 测试失败，提示方法不存在

- [ ] **Step 3: 扩展ConfigManager添加OKX方法**

在 `app/config_manager.py` 末尾添加：

```python
    def get_okx_settings(self, mode: str = "demo") -> Dict[str, Optional[str]]:
        """获取OKX配置

        Args:
            mode: 模式 (live/demo)

        Returns:
            OKX配置字典
        """
        prefix = f"OKX_{mode.upper()}_"
        return {
            "api_key": os.getenv(f"{prefix}API_KEY"),
            "secret_key": os.getenv(f"{prefix}SECRET_KEY"),
            "passphrase": os.getenv(f"{prefix}PASSPHRASE"),
            "mode": mode,
        }

    def update_okx_settings(
        self,
        mode: str,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        passphrase: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """更新OKX配置

        Args:
            mode: 模式 (live/demo)
            api_key: API密钥
            secret_key: Secret密钥
            passphrase: API密码

        Returns:
            更新后的配置
        """
        prefix = f"OKX_{mode.upper()}_"
        updates = {}
        if api_key:
            updates[f"{prefix}API_KEY"] = api_key
        if secret_key:
            updates[f"{prefix}SECRET_KEY"] = secret_key
        if passphrase:
            updates[f"{prefix}PASSPHRASE"] = passphrase

        if updates:
            self._update_env_file(updates)

            # 更新运行时环境
            for key, value in updates.items():
                os.environ[key] = value

        return self.get_okx_settings(mode)
```

- [ ] **Step 4: 运行测试验证实现**

```bash
uv run pytest tests/test_config_manager_okx.py -v
```

Expected: 所有测试通过

- [ ] **Step 5: 提交配置管理扩展**

```bash
git add app/config_manager.py tests/test_config_manager_okx.py
git commit -m "feat(config): add OKX configuration management"
```

---

## Task 4: Pydantic数据模型

**Files:**
- Modify: `app/api/models/schemas.py`
- Test: `tests/test_okx_schemas.py`

- [ ] **Step 1: 编写数据模型测试**

Create `tests/test_okx_schemas.py`:

```python
"""测试OKX Pydantic模型"""
import pytest
from pydantic import ValidationError
from app.api.models.schemas import (
    OKXOrderRequest,
    OKXBalance,
    OKXPosition,
    OKXOrderResponse,
    OKXTicker,
)


def test_okx_order_request_valid():
    """测试有效的下单请求"""
    order = OKXOrderRequest(
        inst_id="BTC-USDT",
        side="buy",
        order_type="limit",
        size="0.01",
        price="50000"
    )
    assert order.inst_id == "BTC-USDT"
    assert order.side == "buy"
    assert order.price == "50000"


def test_okx_order_request_market_order():
    """测试市价单（无需price）"""
    order = OKXOrderRequest(
        inst_id="BTC-USDT",
        side="sell",
        order_type="market",
        size="0.01"
    )
    assert order.price is None


def test_okx_balance():
    """测试余额模型"""
    balance = OKXBalance(
        currency="USDT",
        available="1000.5",
        frozen="100.0",
        total="1100.5"
    )
    assert balance.currency == "USDT"
    assert balance.total == "1100.5"


def test_okx_position():
    """测试持仓模型"""
    position = OKXPosition(
        inst_id="BTC-USDT-SWAP",
        position_side="long",
        position="10",
        available_position="10",
        average_price="50000",
        unrealized_pnl="500",
        leverage="10"
    )
    assert position.inst_id == "BTC-USDT-SWAP"
    assert position.position_side == "long"


def test_okx_order_response():
    """测试订单响应模型"""
    response = OKXOrderResponse(
        order_id="123456",
        client_order_id="my-order-1",
        inst_id="BTC-USDT",
        status="live",
        side="buy",
        order_type="limit",
        size="0.01",
        filled_size="0",
        price="50000",
        average_price=None,
        timestamp="2026-03-20T10:00:00Z"
    )
    assert response.order_id == "123456"
    assert response.status == "live"


def test_okx_ticker():
    """测试ticker模型"""
    ticker = OKXTicker(
        inst_id="BTC-USDT",
        last="50000",
        bid="49990",
        ask="50010",
        volume_24h="1234.56",
        high_24h="51000",
        low_24h="49000",
        timestamp="2026-03-20T10:00:00Z"
    )
    assert ticker.inst_id == "BTC-USDT"
    assert ticker.last == "50000"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_okx_schemas.py -v
```

Expected: 测试失败，提示模型不存在

- [ ] **Step 3: 在schemas.py中添加OKX模型**

在 `app/api/models/schemas.py` 末尾添加：

```python
# OKX相关模型

class OKXOrderRequest(BaseModel):
    """OKX下单请求"""
    inst_id: str
    side: str  # buy/sell
    order_type: str  # market/limit/post_only/fok/ioc
    size: str
    price: Optional[str] = None
    client_order_id: Optional[str] = None
    reduce_only: Optional[bool] = False


class OKXBalance(BaseModel):
    """OKX账户余额"""
    currency: str
    available: str
    frozen: str
    total: str


class OKXPosition(BaseModel):
    """OKX持仓信息"""
    inst_id: str
    position_side: str  # long/short/net
    position: str
    available_position: str
    average_price: str
    unrealized_pnl: str
    leverage: str


class OKXOrderResponse(BaseModel):
    """OKX订单响应"""
    order_id: str
    client_order_id: str
    inst_id: str
    status: str  # live/partially_filled/filled/canceled
    side: str
    order_type: str
    size: str
    filled_size: str
    price: Optional[str]
    average_price: Optional[str]
    timestamp: str


class OKXTicker(BaseModel):
    """OKX Ticker数据"""
    inst_id: str
    last: str
    bid: str
    ask: str
    volume_24h: str
    high_24h: str
    low_24h: str
    timestamp: str
```

- [ ] **Step 4: 运行测试验证模型**

```bash
uv run pytest tests/test_okx_schemas.py -v
```

Expected: 所有测试通过

- [ ] **Step 5: 提交数据模型**

```bash
git add app/api/models/schemas.py tests/test_okx_schemas.py
git commit -m "feat(models): add OKX Pydantic schemas"
```

---

## Task 5: OKXTradingClient核心类（第1部分：初始化）

**Files:**
- Create: `app/okx/trading_client.py`
- Create: `app/okx/__init__.py`
- Test: `tests/test_okx_client_init.py`

- [ ] **Step 1: 编写客户端初始化测试**

Create `tests/test_okx_client_init.py`:

```python
"""测试OKXTradingClient初始化"""
import pytest
from unittest.mock import Mock, patch
from app.okx.trading_client import OKXTradingClient


def test_client_init_demo():
    """测试模拟盘客户端初始化"""
    with patch('app.okx.trading_client.OKXTradingClient._init_sdk_clients'):
        client = OKXTradingClient(
            api_key="test_key",
            secret_key="test_secret",
            passphrase="test_pass",
            is_demo=True
        )

        assert client.api_key == "test_key"
        assert client.secret_key == "test_secret"
        assert client.passphrase == "test_pass"
        assert client.is_demo is True


def test_client_init_live():
    """测试实盘客户端初始化"""
    with patch('app.okx.trading_client.OKXTradingClient._init_sdk_clients'):
        client = OKXTradingClient(
            api_key="live_key",
            secret_key="live_secret",
            passphrase="live_pass",
            is_demo=False
        )

        assert client.is_demo is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_okx_client_init.py -v
```

Expected: 测试失败，提示类不存在

- [ ] **Step 3: 创建OKXTradingClient基础结构**

Create `app/okx/trading_client.py`:

```python
"""OKX交易客户端"""
import logging
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .exceptions import OKXRateLimitError

logger = logging.getLogger(__name__)


class OKXTradingClient:
    """OKX交易客户端，封装OKX SDK调用"""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        passphrase: str,
        is_demo: bool = False
    ):
        """初始化客户端

        Args:
            api_key: API密钥
            secret_key: Secret密钥
            passphrase: API密码
            is_demo: 是否为模拟盘
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.is_demo = is_demo

        # 初始化SDK客户端
        self._init_sdk_clients()

        logger.info(f"[OKX-{'DEMO' if is_demo else 'LIVE'}] Client initialized")

    def _init_sdk_clients(self):
        """初始化OKX SDK客户端

        注意：此方法需要根据实际SDK API调整
        参考sdk_poc.py中验证的初始化方式
        """
        # TODO: 根据SDK POC结果实现
        # 示例：
        # import okx
        # self.account_api = okx.Account(...)
        # self.trade_api = okx.Trade(...)
        # self.market_api = okx.MarketData(...)
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry_if=retry_if_exception_type(OKXRateLimitError),
        reraise=True
    )
    async def _call_with_retry(self, func, *args, **kwargs):
        """带重试的API调用

        Args:
            func: 要调用的函数
            *args, **kwargs: 函数参数

        Returns:
            函数返回值
        """
        try:
            return await func(*args, **kwargs)
        except OKXRateLimitError as e:
            logger.warning(
                f"[OKX-{'DEMO' if self.is_demo else 'LIVE'}] "
                f"Rate limit hit, retrying... {e}"
            )
            raise
```

- [ ] **Step 4: 创建模块初始化文件**

Create `app/okx/__init__.py`:

```python
"""OKX模块"""
from typing import Dict, Optional
from .trading_client import OKXTradingClient
from .exceptions import OKXConfigError
from app.config_manager import config_manager

_client_cache: Dict[str, OKXTradingClient] = {}


def get_okx_client(mode: str = "demo", force_refresh: bool = False) -> OKXTradingClient:
    """获取OKX客户端实例（单例模式）

    Args:
        mode: 模式 (live/demo)
        force_refresh: 强制刷新客户端

    Returns:
        OKXTradingClient实例

    Raises:
        OKXConfigError: 配置缺失或无效
    """
    if mode not in ["live", "demo"]:
        raise OKXConfigError(f"Invalid mode: {mode}")

    # 强制刷新时清除缓存
    if force_refresh and mode in _client_cache:
        del _client_cache[mode]

    # 检查缓存
    if mode in _client_cache:
        return _client_cache[mode]

    # 通过ConfigManager读取配置
    settings = config_manager.get_okx_settings(mode)
    api_key = settings.get("api_key")
    secret_key = settings.get("secret_key")
    passphrase = settings.get("passphrase")

    if not all([api_key, secret_key, passphrase]):
        raise OKXConfigError(f"Missing OKX {mode} configuration")

    # 创建客户端
    client = OKXTradingClient(
        api_key=api_key,
        secret_key=secret_key,
        passphrase=passphrase,
        is_demo=(mode == "demo")
    )

    # 缓存
    _client_cache[mode] = client
    return client


def clear_client_cache(mode: Optional[str] = None):
    """清除客户端缓存

    Args:
        mode: 要清除的模式，None表示清除所有
    """
    global _client_cache
    if mode:
        _client_cache.pop(mode, None)
    else:
        _client_cache.clear()


__all__ = [
    "OKXTradingClient",
    "get_okx_client",
    "clear_client_cache",
]
```

- [ ] **Step 5: 运行测试验证初始化**

```bash
uv run pytest tests/test_okx_client_init.py -v
```

Expected: 所有测试通过

- [ ] **Step 6: 提交客户端基础结构**

```bash
git add app/okx/trading_client.py app/okx/__init__.py tests/test_okx_client_init.py
git commit -m "feat(okx): add OKXTradingClient base structure"
```

---

由于计划文档较长，我将分段继续写入。让我先保存当前进度。

