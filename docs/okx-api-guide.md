# OKX API 使用指南

## 概述

Finance Agent集成了OKX交易所API，支持实盘和模拟盘的账户管理和交易功能。

## 配置

### 环境变量

在`.env`文件中配置OKX API凭证：

```bash
# OKX模拟盘配置
OKX_DEMO_API_KEY=your-demo-api-key
OKX_DEMO_SECRET_KEY=your-demo-secret-key
OKX_DEMO_PASSPHRASE=your-demo-passphrase

# OKX实盘配置
OKX_LIVE_API_KEY=your-live-api-key
OKX_LIVE_SECRET_KEY=your-live-secret-key
OKX_LIVE_PASSPHRASE=your-live-passphrase

# 默认模式
OKX_DEFAULT_MODE=demo
```

### 获取API凭证

1. 登录OKX官网
2. 进入"API管理"页面
3. 创建API Key（分别为实盘和模拟盘创建）
4. 保存API Key、Secret Key和Passphrase

**注意：** 实盘和模拟盘的API凭证是完全独立的。

## API端点

### 账户管理

#### 获取账户余额

```bash
GET /api/okx/account/balance?mode=demo&currency=USDT
```

**参数：**
- `mode`: 交易模式（demo/live），默认demo
- `currency`: 币种（可选），不传则返回所有币种

**响应：**
```json
{
  "mode": "demo",
  "balances": [
    {
      "currency": "USDT",
      "available": "1000.5",
      "frozen": "100.0",
      "total": "1100.5"
    }
  ]
}
```

#### 获取持仓信息

```bash
GET /api/okx/account/positions?mode=demo&inst_type=SPOT
```

**参数：**
- `mode`: 交易模式（demo/live）
- `inst_type`: 产品类型（SPOT/MARGIN/SWAP/FUTURES/OPTION）

**响应：**
```json
{
  "mode": "demo",
  "positions": [
    {
      "inst_id": "BTC-USDT-SWAP",
      "position_side": "long",
      "position": "10",
      "available_position": "10",
      "average_price": "50000",
      "unrealized_pnl": "500",
      "leverage": "10"
    }
  ]
}
```

### 交易管理

#### 下单

```bash
POST /api/okx/trade/order
Content-Type: application/json

{
  "mode": "demo",
  "inst_id": "BTC-USDT",
  "side": "buy",
  "order_type": "limit",
  "size": "0.01",
  "price": "50000",
  "client_order_id": "my-order-1"
}
```

**参数：**
- `mode`: 交易模式
- `inst_id`: 产品ID（如BTC-USDT）
- `side`: 订单方向（buy/sell）
- `order_type`: 订单类型（market/limit/post_only/fok/ioc）
- `size`: 委托数量
- `price`: 委托价格（限价单必填）
- `client_order_id`: 客户端订单ID（可选）

**响应：**
```json
{
  "mode": "demo",
  "order_id": "123456",
  "client_order_id": "my-order-1",
  "status_code": "0"
}
```

#### 撤单

```bash
DELETE /api/okx/trade/order/123456?mode=demo&inst_id=BTC-USDT
```

**参数：**
- `order_id`: 订单ID（路径参数）
- `mode`: 交易模式
- `inst_id`: 产品ID

**响应：**
```json
{
  "mode": "demo",
  "order_id": "123456",
  "status_code": "0"
}
```

#### 查询订单详情

```bash
GET /api/okx/trade/order/123456?mode=demo&inst_id=BTC-USDT
```

**响应：**
```json
{
  "mode": "demo",
  "order": {
    "order_id": "123456",
    "inst_id": "BTC-USDT",
    "status": "filled",
    "side": "buy",
    "order_type": "limit",
    "size": "0.01",
    "filled_size": "0.01",
    "price": "50000",
    "average_price": "50000",
    "timestamp": "1710000000000"
  }
}
```

#### 查询历史订单

```bash
GET /api/okx/trade/orders/history?mode=demo&inst_type=SPOT&limit=10
```

**参数：**
- `mode`: 交易模式
- `inst_type`: 产品类型
- `inst_id`: 产品ID（可选）
- `limit`: 返回数量限制（1-100）

**响应：**
```json
{
  "mode": "demo",
  "orders": [...]
}
```

## 错误处理

### HTTP状态码

- `200`: 成功
- `400`: 请求错误（参数错误、业务错误）
- `401`: 认证错误（API密钥无效）
- `429`: 频率限制
- `500`: 服务器错误

### 错误响应格式

```json
{
  "detail": "[50113] Invalid Sign"
}
```

## Python客户端使用

### 基本使用

```python
from app.okx import get_okx_client

# 获取客户端
client = get_okx_client(mode="demo")

# 查询余额
balances = await client.get_account_balance()

# 下单
order = await client.place_order(
    inst_id="BTC-USDT",
    side="buy",
    order_type="limit",
    size="0.01",
    price="50000"
)

# 撤单
await client.cancel_order(
    inst_id="BTC-USDT",
    order_id=order['order_id']
)
```

### 错误处理

```python
from app.okx.exceptions import (
    OKXAuthError,
    OKXRateLimitError,
    OKXInsufficientBalanceError,
    OKXOrderError
)

try:
    order = await client.place_order(...)
except OKXAuthError as e:
    print(f"认证错误: {e}")
except OKXRateLimitError as e:
    print(f"频率限制: {e}")
except OKXInsufficientBalanceError as e:
    print(f"余额不足: {e}")
except OKXOrderError as e:
    print(f"订单错误: {e}")
```

## 最佳实践

1. **使用模拟盘测试**：在实盘交易前，先在模拟盘充分测试
2. **错误处理**：始终捕获并处理异常
3. **频率限制**：注意API调用频率，避免触发限制
4. **日志记录**：记录所有交易操作，便于审计
5. **凭证安全**：不要将API密钥提交到版本控制

## 常见问题

### Q: 如何切换实盘和模拟盘？

A: 通过`mode`参数控制：`mode=demo`使用模拟盘，`mode=live`使用实盘。

### Q: 签名错误怎么办？

A: 检查API Key、Secret Key和Passphrase是否正确，确保实盘和模拟盘的凭证不要混淆。

### Q: 如何处理频率限制？

A: 客户端已内置重试机制，会自动重试频率限制错误。如果频繁触发，需要降低调用频率。

### Q: 市价单和限价单的区别？

A: 市价单立即以市场价成交，不需要指定价格；限价单以指定价格挂单，可能不会立即成交。
