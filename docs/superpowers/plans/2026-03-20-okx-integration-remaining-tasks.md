# OKX交易API集成 - 剩余任务计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成OKX集成的完整MVP功能（配置管理、数据模型、客户端、账户API、交易API、路由层）

**Prerequisites:** Task 1-2已完成（SDK验证、错误处理模块）

---

## Task 3: 配置管理扩展

**Context:** 扩展ConfigManager以支持OKX配置的读取和更新

**Files:**
- Modify: `app/config_manager.py`
- Test: `tests/test_config_manager_okx.py`

**Steps:** [详见part2计划中的Task 3]

---

## Task 4: Pydantic数据模型

**Context:** 定义OKX API的请求和响应数据模型

**Files:**
- Modify: `app/api/models/schemas.py`
- Test: `tests/test_okx_schemas.py`

**Steps:** [详见part2计划中的Task 4]

---

## Task 5: OKXTradingClient初始化

**Context:** 创建OKXTradingClient类的基础结构和客户端工厂函数

**Files:**
- Create: `app/okx/trading_client.py`
- Modify: `app/okx/__init__.py`
- Test: `tests/test_okx_client_init.py`

**Steps:** [详见part2计划中的Task 5]

---

## Task 6: 账户余额查询API

**Context:** 实现获取账户余额的功能

**Files:**
- Modify: `app/okx/trading_client.py`
- Test: `tests/test_okx_client_balance.py`

- [ ] **Step 1: 编写余额查询测试**

Create `tests/test_okx_client_balance.py`:

```python
"""测试OKXTradingClient账户余额功能"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.okx.trading_client import OKXTradingClient


@pytest.fixture
def mock_client():
    """创建mock客户端"""
    with patch('app.okx.trading_client.OKXTradingClient._init_sdk_clients'):
        client = OKXTradingClient(
            api_key="test_key",
            secret_key="test_secret",
            passphrase="test_pass",
            is_demo=True
        )
        client.account_api = Mock()
        yield client


@pytest.mark.asyncio
async def test_get_account_balance_all_currencies(mock_client):
    """测试获取所有币种余额"""
    # Mock SDK响应
    mock_client.account_api.get_account_balance = AsyncMock(return_value={
        'code': '0',
        'data': [{
            'details': [
                {'ccy': 'USDT', 'availBal': '1000', 'frozenBal': '100', 'bal': '1100'},
                {'ccy': 'BTC', 'availBal': '0.5', 'frozenBal': '0', 'bal': '0.5'}
            ]
        }]
    })

    result = await mock_client.get_account_balance()

    assert len(result) == 2
    assert result[0]['currency'] == 'USDT'
    assert result[0]['available'] == '1000'
    assert result[0]['total'] == '1100'


@pytest.mark.asyncio
async def test_get_account_balance_single_currency(mock_client):
    """测试获取单个币种余额"""
    mock_client.account_api.get_account_balance = AsyncMock(return_value={
        'code': '0',
        'data': [{
            'details': [
                {'ccy': 'USDT', 'availBal': '1000', 'frozenBal': '100', 'bal': '1100'}
            ]
        }]
    })

    result = await mock_client.get_account_balance(currency='USDT')

    assert len(result) == 1
    assert result[0]['currency'] == 'USDT'
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_okx_client_balance.py -v
```

- [ ] **Step 3: 实现余额查询方法**

在 `app/okx/trading_client.py` 中添加：

```python
    async def get_account_balance(self, currency: Optional[str] = None) -> List[Dict]:
        """获取账户余额

        Args:
            currency: 币种，如BTC、USDT，不传则返回所有币种

        Returns:
            余额信息列表
        """
        return await self._call_with_retry(
            self._get_account_balance_impl, currency
        )

    async def _get_account_balance_impl(self, currency: Optional[str] = None) -> List[Dict]:
        """获取账户余额的实际实现"""
        params = {}
        if currency:
            params['ccy'] = currency

        response = await self.account_api.get_account_balance(**params)

        if response.get('code') != '0':
            from .exceptions import OKXError
            raise OKXError(
                f"Failed to get balance: {response.get('msg')}",
                code=response.get('code')
            )

        balances = []
        data = response.get('data', [])
        if data:
            details = data[0].get('details', [])
            for detail in details:
                balances.append({
                    'currency': detail.get('ccy'),
                    'available': detail.get('availBal'),
                    'frozen': detail.get('frozenBal'),
                    'total': detail.get('bal')
                })

        return balances
```

- [ ] **Step 4: 运行测试验证**

```bash
uv run pytest tests/test_okx_client_balance.py -v
```

- [ ] **Step 5: 提交**

```bash
git add app/okx/trading_client.py tests/test_okx_client_balance.py
git commit -m "feat(okx): add account balance query"
```

---

## Task 7: 持仓查询API

**Context:** 实现获取持仓信息的功能

**Files:**
- Modify: `app/okx/trading_client.py`
- Test: `tests/test_okx_client_positions.py`

- [ ] **Step 1: 编写持仓查询测试**

Create `tests/test_okx_client_positions.py`:

```python
"""测试OKXTradingClient持仓功能"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.okx.trading_client import OKXTradingClient


@pytest.fixture
def mock_client():
    with patch('app.okx.trading_client.OKXTradingClient._init_sdk_clients'):
        client = OKXTradingClient(
            api_key="test_key",
            secret_key="test_secret",
            passphrase="test_pass",
            is_demo=True
        )
        client.account_api = Mock()
        yield client


@pytest.mark.asyncio
async def test_get_positions(mock_client):
    """测试获取持仓"""
    mock_client.account_api.get_positions = AsyncMock(return_value={
        'code': '0',
        'data': [{
            'instId': 'BTC-USDT-SWAP',
            'posSide': 'long',
            'pos': '10',
            'availPos': '10',
            'avgPx': '50000',
            'upl': '500',
            'lever': '10'
        }]
    })

    result = await mock_client.get_positions()

    assert len(result) == 1
    assert result[0]['inst_id'] == 'BTC-USDT-SWAP'
    assert result[0]['position_side'] == 'long'
```

- [ ] **Step 2: 实现持仓查询方法**

在 `app/okx/trading_client.py` 中添加：

```python
    async def get_positions(self, inst_type: Optional[str] = None) -> List[Dict]:
        """获取持仓信息

        Args:
            inst_type: 产品类型 SPOT/MARGIN/SWAP/FUTURES/OPTION

        Returns:
            持仓列表
        """
        return await self._call_with_retry(
            self._get_positions_impl, inst_type
        )

    async def _get_positions_impl(self, inst_type: Optional[str] = None) -> List[Dict]:
        """获取持仓的实际实现"""
        params = {}
        if inst_type:
            params['instType'] = inst_type

        response = await self.account_api.get_positions(**params)

        if response.get('code') != '0':
            from .exceptions import OKXError
            raise OKXError(
                f"Failed to get positions: {response.get('msg')}",
                code=response.get('code')
            )

        positions = []
        for pos in response.get('data', []):
            positions.append({
                'inst_id': pos.get('instId'),
                'position_side': pos.get('posSide'),
                'position': pos.get('pos'),
                'available_position': pos.get('availPos'),
                'average_price': pos.get('avgPx'),
                'unrealized_pnl': pos.get('upl'),
                'leverage': pos.get('lever')
            })

        return positions
```

- [ ] **Step 3: 测试并提交**

```bash
uv run pytest tests/test_okx_client_positions.py -v
git add app/okx/trading_client.py tests/test_okx_client_positions.py
git commit -m "feat(okx): add positions query"
```

---

## Task 8: 下单API

**Context:** 实现下单功能（市价单、限价单）

**Files:**
- Modify: `app/okx/trading_client.py`
- Test: `tests/test_okx_client_order.py`

- [ ] **Step 1: 编写下单测试**

Create `tests/test_okx_client_order.py`:

```python
"""测试OKXTradingClient下单功能"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.okx.trading_client import OKXTradingClient


@pytest.fixture
def mock_client():
    with patch('app.okx.trading_client.OKXTradingClient._init_sdk_clients'):
        client = OKXTradingClient(
            api_key="test_key",
            secret_key="test_secret",
            passphrase="test_pass",
            is_demo=True
        )
        client.trade_api = Mock()
        yield client


@pytest.mark.asyncio
async def test_place_limit_order(mock_client):
    """测试限价单"""
    mock_client.trade_api.place_order = AsyncMock(return_value={
        'code': '0',
        'data': [{
            'ordId': '123456',
            'clOrdId': 'my-order-1',
            'sCode': '0'
        }]
    })

    result = await mock_client.place_order(
        inst_id='BTC-USDT',
        side='buy',
        order_type='limit',
        size='0.01',
        price='50000'
    )

    assert result['order_id'] == '123456'
    assert result['client_order_id'] == 'my-order-1'


@pytest.mark.asyncio
async def test_place_market_order(mock_client):
    """测试市价单"""
    mock_client.trade_api.place_order = AsyncMock(return_value={
        'code': '0',
        'data': [{
            'ordId': '123457',
            'clOrdId': '',
            'sCode': '0'
        }]
    })

    result = await mock_client.place_order(
        inst_id='BTC-USDT',
        side='sell',
        order_type='market',
        size='0.01'
    )

    assert result['order_id'] == '123457'
```

- [ ] **Step 2: 实现下单方法**

在 `app/okx/trading_client.py` 中添加：

```python
    async def place_order(
        self,
        inst_id: str,
        side: str,
        order_type: str,
        size: str,
        price: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """下单

        Args:
            inst_id: 产品ID，如 BTC-USDT
            side: 订单方向 buy/sell
            order_type: 订单类型 market/limit/post_only等
            size: 委托数量
            price: 委托价格（限价单必填）
            **kwargs: 其他参数

        Returns:
            订单信息
        """
        return await self._call_with_retry(
            self._place_order_impl, inst_id, side, order_type, size, price, **kwargs
        )

    async def _place_order_impl(
        self,
        inst_id: str,
        side: str,
        order_type: str,
        size: str,
        price: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """下单的实际实现"""
        params = {
            'instId': inst_id,
            'tdMode': 'cash',  # 现货交易模式
            'side': side,
            'ordType': order_type,
            'sz': size
        }

        if price:
            params['px'] = price

        params.update(kwargs)

        response = await self.trade_api.place_order(**params)

        if response.get('code') != '0':
            from .exceptions import OKXOrderError
            raise OKXOrderError(
                f"Failed to place order: {response.get('msg')}",
                code=response.get('code')
            )

        data = response.get('data', [{}])[0]
        return {
            'order_id': data.get('ordId'),
            'client_order_id': data.get('clOrdId', ''),
            'status_code': data.get('sCode')
        }
```

- [ ] **Step 3: 测试并提交**

```bash
uv run pytest tests/test_okx_client_order.py -v
git add app/okx/trading_client.py tests/test_okx_client_order.py
git commit -m "feat(okx): add place order functionality"
```

---

## Task 9: 撤单和订单查询API

**Context:** 实现撤单和订单查询功能

**Files:**
- Modify: `app/okx/trading_client.py`
- Test: `tests/test_okx_client_order_mgmt.py`

- [ ] **Step 1: 编写测试**

Create `tests/test_okx_client_order_mgmt.py`:

```python
"""测试订单管理功能"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.okx.trading_client import OKXTradingClient


@pytest.fixture
def mock_client():
    with patch('app.okx.trading_client.OKXTradingClient._init_sdk_clients'):
        client = OKXTradingClient(
            api_key="test_key",
            secret_key="test_secret",
            passphrase="test_pass",
            is_demo=True
        )
        client.trade_api = Mock()
        yield client


@pytest.mark.asyncio
async def test_cancel_order(mock_client):
    """测试撤单"""
    mock_client.trade_api.cancel_order = AsyncMock(return_value={
        'code': '0',
        'data': [{'ordId': '123456', 'sCode': '0'}]
    })

    result = await mock_client.cancel_order(
        inst_id='BTC-USDT',
        order_id='123456'
    )

    assert result['order_id'] == '123456'


@pytest.mark.asyncio
async def test_get_order_details(mock_client):
    """测试查询订单详情"""
    mock_client.trade_api.get_order = AsyncMock(return_value={
        'code': '0',
        'data': [{
            'ordId': '123456',
            'instId': 'BTC-USDT',
            'state': 'filled',
            'side': 'buy',
            'sz': '0.01',
            'fillSz': '0.01'
        }]
    })

    result = await mock_client.get_order_details(
        inst_id='BTC-USDT',
        order_id='123456'
    )

    assert result['order_id'] == '123456'
    assert result['status'] == 'filled'
```

- [ ] **Step 2: 实现方法**

在 `app/okx/trading_client.py` 中添加撤单和查询方法

- [ ] **Step 3: 测试并提交**

```bash
uv run pytest tests/test_okx_client_order_mgmt.py -v
git add app/okx/trading_client.py tests/test_okx_client_order_mgmt.py
git commit -m "feat(okx): add cancel order and order query"
```

---

## Task 10: API路由层 - 账户管理

**Context:** 创建FastAPI路由处理账户相关请求

**Files:**
- Create: `app/api/routes/okx.py`
- Test: `tests/test_okx_routes_account.py`

- [ ] **Step 1: 编写路由测试**

Create `tests/test_okx_routes_account.py`:

```python
"""测试OKX账户路由"""
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_get_balance():
    """测试获取余额接口"""
    response = client.get("/api/okx/account/balance?mode=demo")
    assert response.status_code == 200
    data = response.json()
    assert "mode" in data
    assert "balances" in data


def test_get_positions():
    """测试获取持仓接口"""
    response = client.get("/api/okx/account/positions?mode=demo")
    assert response.status_code == 200
    data = response.json()
    assert "mode" in data
    assert "positions" in data
```

- [ ] **Step 2: 创建路由文件**

Create `app/api/routes/okx.py`:

```python
"""OKX API路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.okx import get_okx_client
from app.okx.exceptions import OKXError, OKXAuthError, OKXRateLimitError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/okx/account/balance")
async def get_account_balance(
    mode: str = Query("demo", description="模式 (live/demo)"),
    currency: Optional[str] = Query(None, description="币种")
):
    """获取账户余额"""
    try:
        client = get_okx_client(mode)
        balances = await client.get_account_balance(currency)
        return {
            "mode": mode,
            "balances": balances
        }
    except OKXAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except OKXRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except OKXError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/okx/account/positions")
async def get_positions(
    mode: str = Query("demo", description="模式 (live/demo)"),
    inst_type: Optional[str] = Query(None, description="产品类型")
):
    """获取持仓信息"""
    try:
        client = get_okx_client(mode)
        positions = await client.get_positions(inst_type)
        return {
            "mode": mode,
            "positions": positions
        }
    except OKXAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except OKXRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except OKXError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 3: 注册路由到main.py**

在 `app/api/main.py` 中添加：

```python
from .routes import okx

app.include_router(okx.router, prefix="/api", tags=["okx"])
```

- [ ] **Step 4: 测试并提交**

```bash
uv run pytest tests/test_okx_routes_account.py -v
git add app/api/routes/okx.py app/api/main.py tests/test_okx_routes_account.py
git commit -m "feat(okx): add account management routes"
```

---

## Task 11: API路由层 - 交易管理

**Context:** 创建交易相关的API路由

**Files:**
- Modify: `app/api/routes/okx.py`
- Test: `tests/test_okx_routes_trade.py`

- [ ] **Step 1: 编写交易路由测试**
- [ ] **Step 2: 实现交易路由（下单、撤单、查询）**
- [ ] **Step 3: 测试并提交**

---

## Task 12: 集成测试和文档

**Context:** 编写端到端集成测试，更新文档

**Files:**
- Create: `tests/integration/test_okx_integration.py`
- Update: `README.md` or `docs/okx-integration.md`

- [ ] **Step 1: 编写集成测试**
- [ ] **Step 2: 运行完整测试套件**
- [ ] **Step 3: 更新文档**
- [ ] **Step 4: 最终提交**

---

## 执行说明

**总任务数：** 12个任务（Task 1-2已完成，剩余Task 3-12）

**执行顺序：**
1. Task 3-5: 基础模块（配置、模型、客户端初始化）
2. Task 6-7: 账户API（余额、持仓）
3. Task 8-9: 交易API（下单、撤单、查询）
4. Task 10-11: 路由层（账户路由、交易路由）
5. Task 12: 集成测试和文档

**Token预估：**
- Task 3-5: ~50k tokens
- Task 6-9: ~60k tokens
- Task 10-12: ~40k tokens
