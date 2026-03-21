# Reddit Ticker 别名匹配优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 Reddit 情绪抓取的文本匹配逻辑，使用别名字典和正则词边界匹配，消除误匹配和漏匹配问题。

**Architecture:** 新增 JSON 配置文件存储 ticker 别名，新增正则编译缓存函数，改造现有过滤函数使用词边界正则匹配。

**Tech Stack:** Python 3.13, pytest, re (正则表达式), functools.lru_cache, logging

---

## File Structure

**New Files:**
- `app/social/reddit/ticker_aliases.json` - 别名配置文件（Magnificent Seven + BTC + ETH）

**Modified Files:**
- `app/social/reddit/tools.py` - 新增别名加载和正则编译函数，改造过滤函数
- `tests/test_social_reddit_subreddit_routing.py` - 新增 10 个测试用例

---

### Task 1: 创建别名配置文件

**Files:**
- Create: `app/social/reddit/ticker_aliases.json`

- [ ] **Step 1: 创建配置文件**

创建 `app/social/reddit/ticker_aliases.json`，内容如下：

```json
{
  "NVDA": {
    "aliases": ["NVDA", "Nvidia", "Nvidia Corp"],
    "type": "stock"
  },
  "AAPL": {
    "aliases": ["AAPL", "Apple"],
    "type": "stock"
  },
  "MSFT": {
    "aliases": ["MSFT", "Microsoft", "Microsoft Corp"],
    "type": "stock"
  },
  "GOOGL": {
    "aliases": ["GOOGL", "GOOG", "Google", "Alphabet"],
    "type": "stock"
  },
  "AMZN": {
    "aliases": ["AMZN", "Amazon"],
    "type": "stock"
  },
  "TSLA": {
    "aliases": ["TSLA", "Tesla"],
    "type": "stock"
  },
  "META": {
    "aliases": ["META", "Meta", "Facebook", "FB"],
    "type": "stock"
  },
  "BTC": {
    "aliases": ["BTC", "Bitcoin"],
    "type": "crypto"
  },
  "ETH": {
    "aliases": ["ETH", "Ethereum"],
    "type": "crypto"
  }
}
```

- [ ] **Step 2: 验证 JSON 格式和结构**

运行：`uv run python -c "import json; data = json.load(open('app/social/reddit/ticker_aliases.json')); assert 'NVDA' in data; assert 'aliases' in data['NVDA']; assert 'type' in data['NVDA']; print('✓ JSON format and structure valid')"`

预期：输出 "✓ JSON format and structure valid"

- [ ] **Step 3: 提交配置文件**

```bash
git add app/social/reddit/ticker_aliases.json
git commit -m "feat(reddit): add ticker aliases config for Magnificent Seven + BTC/ETH"
```

---

### Task 2: 添加别名加载函数

**Files:**
- Modify: `app/social/reddit/tools.py:26-27` (添加 import 和 logger)
- Modify: `app/social/reddit/tools.py:68` (插入新函数)
- Test: `tests/test_social_reddit_subreddit_routing.py`

- [ ] **Step 1: 编写别名加载测试（失败测试）**

在 `tests/test_social_reddit_subreddit_routing.py` 末尾添加：

```python
def test_load_ticker_aliases():
    """测试别名配置加载"""
    from app.social.reddit.tools import _load_ticker_aliases

    aliases = _load_ticker_aliases()

    # 验证配置结构
    assert isinstance(aliases, dict)
    assert "NVDA" in aliases
    assert "aliases" in aliases["NVDA"]
    assert "type" in aliases["NVDA"]

    # 验证 NVDA 别名
    nvda_aliases = aliases["NVDA"]["aliases"]
    assert "NVDA" in nvda_aliases
    assert "Nvidia" in nvda_aliases
    assert "Nvidia Corp" in nvda_aliases

    # 验证 META 包含曾用名
    meta_aliases = aliases["META"]["aliases"]
    assert "FB" in meta_aliases
    assert "Facebook" in meta_aliases
```

- [ ] **Step 2: 运行测试验证失败**

运行：`uv run pytest tests/test_social_reddit_subreddit_routing.py::test_load_ticker_aliases -v`

预期：FAIL with "ImportError: cannot import name '_load_ticker_aliases'"

- [ ] **Step 3: 添加所需的 import 和 logger**

在 `app/social/reddit/tools.py` 第 10 行（`import re` 之后）添加：

```python
import json
import logging
from functools import lru_cache
from pathlib import Path
```

在第 26 行（`_URL_RE` 定义之前）添加：

```python
logger = logging.getLogger(__name__)
```

注：`from typing import Dict, Any, Optional` 已在第 12 行存在，无需添加。

- [ ] **Step 4: 实现别名加载函数**

在 `app/social/reddit/tools.py` 中，找到 `_asset_to_subreddits` 函数（当前在第 55 行），在其之前插入：

```python
@lru_cache(maxsize=1)
def _load_ticker_aliases() -> Dict[str, Dict[str, Any]]:
    """加载 ticker 别名配置（带缓存）。

    使用 lru_cache 确保配置文件只加载一次，避免重复 I/O。

    Returns:
        字典，键为 ticker（大写），值为配置对象：
        {
            "aliases": List[str],  # 别名列表
            "type": str            # "stock" 或 "crypto"
        }

    Raises:
        FileNotFoundError: 配置文件不存在
        json.JSONDecodeError: 配置文件格式错误
    """
    config_path = Path(__file__).parent / "ticker_aliases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
```

- [ ] **Step 5: 运行测试验证通过**

运行：`uv run pytest tests/test_social_reddit_subreddit_routing.py::test_load_ticker_aliases -v`

预期：PASS

- [ ] **Step 6: 提交别名加载函数**

```bash
git add app/social/reddit/tools.py tests/test_social_reddit_subreddit_routing.py
git commit -m "feat(reddit): add ticker aliases loader with caching"
```

---

### Task 3: 添加正则编译缓存函数

**Files:**
- Modify: `app/social/reddit/tools.py:95` (插入新函数，在 `_load_ticker_aliases` 之后)
- Test: `tests/test_social_reddit_subreddit_routing.py`

- [ ] **Step 1: 编写正则编译测试（失败测试）**

在 `tests/test_social_reddit_subreddit_routing.py` 末尾添加：

```python
def test_compile_ticker_regex():
    """测试正则表达式编译和缓存"""
    from app.social.reddit.tools import _compile_ticker_regex
    import re

    # 测试正常编译
    regex = _compile_ticker_regex("NVDA")
    assert regex is not None
    assert isinstance(regex, re.Pattern)

    # 测试匹配行为
    assert regex.search("NVDA is bullish")
    assert regex.search("$NVDA to the moon")
    assert regex.search("Nvidia earnings")
    assert regex.search("nvidia") is not None  # 大小写不敏感
    assert not regex.search("NVDAX")  # 词边界阻止误匹配

    # 测试缓存（同一对象）
    regex2 = _compile_ticker_regex("NVDA")
    assert regex is regex2


def test_compile_ticker_regex_fallback():
    """测试配置加载失败时的降级行为"""
    from app.social.reddit.tools import _compile_ticker_regex
    from unittest.mock import patch

    # Mock 配置加载失败
    with patch("app.social.reddit.tools._load_ticker_aliases", side_effect=FileNotFoundError):
        regex = _compile_ticker_regex("UNKNOWN")
        assert regex is not None
        # 应该回退到只匹配 ticker 本身
        assert regex.search("UNKNOWN")
        assert not regex.search("UnknownCompany")
```

- [ ] **Step 2: 运行测试验证失败**

运行：`uv run pytest tests/test_social_reddit_subreddit_routing.py::test_compile_ticker_regex -v`

预期：FAIL with "ImportError: cannot import name '_compile_ticker_regex'"

- [ ] **Step 3: 实现正则编译函数**

在 `app/social/reddit/tools.py` 中，找到 `_load_ticker_aliases` 函数，在其之后插入：

```python
@lru_cache(maxsize=128)
def _compile_ticker_regex(asset: str) -> Optional[re.Pattern]:
    """编译并缓存 ticker 的正则表达式。

    Args:
        asset: 资产代码（如 "NVDA"）

    Returns:
        编译后的正则表达式对象，如果别名列表为空则返回 None
    """
    asset_upper = asset.upper()

    try:
        aliases_config = _load_ticker_aliases()
        ticker_config = aliases_config.get(asset_upper, {})
        aliases = ticker_config.get("aliases", [asset_upper])
    except Exception as e:
        logger.warning(f"Failed to load ticker aliases for {asset_upper}: {e}, falling back to simple matching")
        aliases = [asset_upper]

    # 验证别名列表非空
    if not aliases:
        logger.warning(f"Empty alias list for {asset_upper}")
        return None

    # 构建正则表达式：\$?\b(NVDA|Nvidia|Nvidia Corp)\b
    escaped_aliases = [re.escape(alias) for alias in aliases]
    pattern = r'\$?\b(' + '|'.join(escaped_aliases) + r')\b'
    return re.compile(pattern, re.IGNORECASE)
```

- [ ] **Step 4: 运行测试验证通过**

运行：`uv run pytest tests/test_social_reddit_subreddit_routing.py::test_compile_ticker_regex tests/test_social_reddit_subreddit_routing.py::test_compile_ticker_regex_fallback -v`

预期：PASS (2 tests)

- [ ] **Step 5: 提交正则编译函数**

```bash
git add app/social/reddit/tools.py tests/test_social_reddit_subreddit_routing.py
git commit -m "feat(reddit): add regex compiler with caching and fallback"
```

---

### Task 4: 改造过滤函数

**Files:**
- Modify: `app/social/reddit/tools.py:69-92` (替换 `_filter_posts_by_asset` 函数)
- Test: `tests/test_social_reddit_subreddit_routing.py`

- [ ] **Step 1: 编写过滤函数测试（失败测试）**

在 `tests/test_social_reddit_subreddit_routing.py` 末尾添加：

```python
def test_filter_with_ticker_exact_match():
    """测试 ticker 精确匹配"""
    from app.social.reddit.tools import _filter_posts_by_asset
    from app.social.reddit.json_client import RedditPost

    posts = [
        RedditPost(title="NVDA is bullish", selftext="", score=100, permalink="/r/test/1"),
        RedditPost(title="NVDAX is different", selftext="", score=50, permalink="/r/test/2"),
        RedditPost(title="Other stock", selftext="", score=30, permalink="/r/test/3"),
    ]

    filtered = _filter_posts_by_asset(posts, "NVDA")

    assert len(filtered) == 1
    assert filtered[0]["title"] == "NVDA is bullish"


def test_filter_with_company_name():
    """测试公司名匹配"""
    from app.social.reddit.tools import _filter_posts_by_asset
    from app.social.reddit.json_client import RedditPost

    posts = [
        RedditPost(title="Nvidia earnings beat", selftext="", score=100, permalink="/r/test/1"),
        RedditPost(title="Nvidia Corp announced", selftext="", score=80, permalink="/r/test/2"),
        RedditPost(title="AMD news", selftext="", score=50, permalink="/r/test/3"),
    ]

    filtered = _filter_posts_by_asset(posts, "NVDA")

    assert len(filtered) == 2
    assert any("Nvidia earnings" in p["title"] for p in filtered)
    assert any("Nvidia Corp" in p["title"] for p in filtered)


def test_filter_with_cashtag():
    """测试 Cashtag 格式（$NVDA）"""
    from app.social.reddit.tools import _filter_posts_by_asset
    from app.social.reddit.json_client import RedditPost

    posts = [
        RedditPost(title="$NVDA to the moon 🚀", selftext="", score=200, permalink="/r/test/1"),
        RedditPost(title="$TSLA vs $NVDA", selftext="", score=150, permalink="/r/test/2"),
        RedditPost(title="Other ticker", selftext="", score=50, permalink="/r/test/3"),
    ]

    filtered = _filter_posts_by_asset(posts, "NVDA")

    assert len(filtered) == 2


def test_filter_no_false_positive():
    """测试词边界防止误匹配"""
    from app.social.reddit.tools import _filter_posts_by_asset
    from app.social.reddit.json_client import RedditPost

    posts = [
        RedditPost(title="NVDA is good", selftext="", score=100, permalink="/r/test/1"),
        RedditPost(title="NVDAX is different", selftext="", score=50, permalink="/r/test/2"),
        RedditPost(title="mynvda.com", selftext="", score=30, permalink="/r/test/3"),
    ]

    filtered = _filter_posts_by_asset(posts, "NVDA")

    assert len(filtered) == 1
    assert filtered[0]["title"] == "NVDA is good"


def test_filter_case_insensitive():
    """测试大小写不敏感"""
    from app.social.reddit.tools import _filter_posts_by_asset
    from app.social.reddit.json_client import RedditPost

    posts = [
        RedditPost(title="nvidia is great", selftext="", score=100, permalink="/r/test/1"),
        RedditPost(title="NVIDIA announced", selftext="", score=80, permalink="/r/test/2"),
        RedditPost(title="Nvidia Corp", selftext="", score=60, permalink="/r/test/3"),
    ]

    filtered = _filter_posts_by_asset(posts, "NVDA")

    assert len(filtered) == 3


def test_filter_with_possessive():
    """测试所有格形式（Nvidia's）"""
    from app.social.reddit.tools import _filter_posts_by_asset
    from app.social.reddit.json_client import RedditPost

    posts = [
        RedditPost(title="Nvidia's earnings beat expectations", selftext="", score=100, permalink="/r/test/1"),
        RedditPost(title="NVDA's stock price", selftext="", score=80, permalink="/r/test/2"),
    ]

    filtered = _filter_posts_by_asset(posts, "NVDA")

    assert len(filtered) == 2


def test_filter_selftext_matching():
    """测试 selftext 字段匹配"""
    from app.social.reddit.tools import _filter_posts_by_asset
    from app.social.reddit.json_client import RedditPost

    posts = [
        RedditPost(title="Stock discussion", selftext="I think NVDA will go up", score=100, permalink="/r/test/1"),
        RedditPost(title="Market analysis", selftext="Nvidia is strong", score=80, permalink="/r/test/2"),
        RedditPost(title="Other", selftext="AMD news", score=50, permalink="/r/test/3"),
    ]

    filtered = _filter_posts_by_asset(posts, "NVDA")

    assert len(filtered) == 2


def test_filter_empty_aliases():
    """测试空别名列表处理"""
    from app.social.reddit.tools import _filter_posts_by_asset
    from app.social.reddit.json_client import RedditPost
    from unittest.mock import patch

    posts = [
        RedditPost(title="Some post", selftext="", score=100, permalink="/r/test/1"),
    ]

    # Mock 返回空别名列表
    with patch("app.social.reddit.tools._compile_ticker_regex", return_value=None):
        filtered = _filter_posts_by_asset(posts, "UNKNOWN")
        assert len(filtered) == 0


def test_regex_caching():
    """测试正则表达式缓存机制"""
    from app.social.reddit.tools import _compile_ticker_regex

    # 清除缓存
    _compile_ticker_regex.cache_clear()

    # 第一次调用
    regex1 = _compile_ticker_regex("NVDA")
    cache_info1 = _compile_ticker_regex.cache_info()

    # 第二次调用（应该命中缓存）
    regex2 = _compile_ticker_regex("NVDA")
    cache_info2 = _compile_ticker_regex.cache_info()

    assert regex1 is regex2  # 同一对象
    assert cache_info2.hits == cache_info1.hits + 1  # 缓存命中次数增加
```

- [ ] **Step 2: 运行测试验证失败**

运行：`uv run pytest tests/test_social_reddit_subreddit_routing.py::test_filter_with_ticker_exact_match -v`

预期：FAIL（旧实现会匹配 NVDAX）

- [ ] **Step 3: 替换过滤函数实现**

在 `app/social/reddit/tools.py` 中，找到 `_filter_posts_by_asset` 函数（当前在第 69-92 行），完全替换为：

```python
def _filter_posts_by_asset(
    posts: List[RedditPost],
    asset: str
) -> List[RedditPost]:
    """使用别名字典和正则词边界过滤帖子。

    匹配规则：
    1. 通过 _compile_ticker_regex() 获取缓存的正则表达式
    2. 正则模式：\$?\b(alias1|alias2|...)\b
       - \$? : 可选的美元符号前缀（支持 $NVDA 格式）
       - \b  : 词边界，避免误匹配（NVDA 不会匹配 NVDAX）
       - re.IGNORECASE : 忽略大小写
    3. 在帖子的 title 和 selftext 中搜索匹配

    注意：与旧实现的行为变化
    - 旧实现：将文本转为大写后匹配（title.upper()）
    - 新实现：使用 re.IGNORECASE，保持原文本不变
    - 影响：无功能差异，但正则匹配更高效

    Args:
        posts: Reddit 帖子列表（RedditPost TypedDict 实例）
        asset: 资产代码（如 "NVDA"）

    Returns:
        匹配的帖子列表
    """
    # 获取编译后的正则表达式（带缓存）
    regex = _compile_ticker_regex(asset)
    if regex is None:
        # 别名列表为空，无法匹配
        return []

    filtered = []
    for post in posts:
        title = post.get("title") or ""
        selftext = post.get("selftext") or ""
        combined_text = f"{title} {selftext}"

        match = regex.search(combined_text)
        if match:
            filtered.append(post)

    return filtered
```

- [ ] **Step 4: 运行所有过滤测试验证通过**

运行：`uv run pytest tests/test_social_reddit_subreddit_routing.py -k "test_filter" -v`

预期：PASS (10 tests)

- [ ] **Step 5: 提交过滤函数改造**

```bash
git add app/social/reddit/tools.py tests/test_social_reddit_subreddit_routing.py
git commit -m "feat(reddit): refactor filter to use regex word boundaries and aliases"
```

---

### Task 5: 运行完整测试套件

**Files:**
- Test: `tests/test_social_reddit_subreddit_routing.py`
- Test: `tests/test_social_reddit_ingest.py`

- [ ] **Step 1: 运行 Reddit 路由测试**

运行：`uv run pytest tests/test_social_reddit_subreddit_routing.py -v`

预期：PASS (所有测试)

- [ ] **Step 2: 运行 Reddit 集成测试**

运行：`uv run pytest tests/test_social_reddit_ingest.py -v`

预期：PASS（确保改动不影响现有功能）

- [ ] **Step 3: 运行所有 social 模块测试**

运行：`uv run pytest tests/test_social*.py -v`

预期：PASS (所有测试)

---

### Task 6: 手动验证真实场景

**Files:**
- Test: Manual verification

- [ ] **Step 1: 测试 NVDA 别名匹配**

创建临时测试脚本 `test_manual.py`：

```python
from app.social.reddit.tools import _filter_posts_by_asset
from app.social.reddit.json_client import RedditPost

posts = [
    RedditPost(title="NVDA earnings beat", selftext="", score=100, permalink="/r/test/1"),
    RedditPost(title="$NVDA to the moon", selftext="", score=90, permalink="/r/test/2"),
    RedditPost(title="Nvidia announced new GPUs", selftext="", score=80, permalink="/r/test/3"),
    RedditPost(title="Nvidia Corp reported", selftext="", score=70, permalink="/r/test/4"),
    RedditPost(title="NVDAX is different", selftext="", score=60, permalink="/r/test/5"),
    RedditPost(title="AMD news", selftext="", score=50, permalink="/r/test/6"),
]

filtered = _filter_posts_by_asset(posts, "NVDA")

print(f"Matched {len(filtered)} posts:")
for p in filtered:
    print(f"  - {p['title']}")

# 预期输出：
# Matched 4 posts:
#   - NVDA earnings beat
#   - $NVDA to the moon
#   - Nvidia announced new GPUs
#   - Nvidia Corp reported
```

运行：`uv run python test_manual.py`

预期：输出 4 个匹配的帖子，不包含 NVDAX 和 AMD

- [ ] **Step 2: 测试 META 曾用名（FB）**

修改 `test_manual.py`：

```python
from app.social.reddit.tools import _filter_posts_by_asset
from app.social.reddit.json_client import RedditPost

posts = [
    RedditPost(title="META earnings", selftext="", score=100, permalink="/r/test/1"),
    RedditPost(title="$FB still bullish", selftext="", score=90, permalink="/r/test/2"),
    RedditPost(title="Facebook rebranded", selftext="", score=80, permalink="/r/test/3"),
    RedditPost(title="Meta announced", selftext="", score=70, permalink="/r/test/4"),
]

filtered = _filter_posts_by_asset(posts, "META")

print(f"Matched {len(filtered)} posts:")
for p in filtered:
    print(f"  - {p['title']}")

# 预期输出：所有 4 个帖子都匹配
```

运行：`uv run python test_manual.py`

预期：输出 4 个匹配的帖子

- [ ] **Step 3: 清理临时文件**

```bash
rm test_manual.py
```

---

### Task 7: 更新文档和提交最终版本

**Files:**
- Modify: `docs/superpowers/specs/2026-03-21-reddit-ticker-alias-matching-design.md`

- [ ] **Step 1: 更新设计文档状态**

在 `docs/superpowers/specs/2026-03-21-reddit-ticker-alias-matching-design.md` 第 4 行，将状态从"待审核"改为"已实现"：

```markdown
**状态**: 已实现
```

- [ ] **Step 2: 提交文档更新**

```bash
git add docs/superpowers/specs/2026-03-21-reddit-ticker-alias-matching-design.md
git commit -m "docs: mark Reddit ticker alias matching spec as implemented"
```

- [ ] **Step 3: 创建最终总结提交**

```bash
git log --oneline -7
```

预期：看到 7 个提交记录（配置文件、加载函数、编译函数、过滤函数、文档更新等）

---

## 完成标准

- ✅ 所有测试通过（10 个新测试 + 现有测试）
- ✅ 配置文件包含 9 个资产（Magnificent Seven + BTC + ETH）
- ✅ 正则表达式使用词边界，避免误匹配
- ✅ 支持 Cashtag 格式（$NVDA）
- ✅ 支持大小写不敏感匹配
- ✅ 支持所有格形式（Nvidia's）
- ✅ 配置加载失败时优雅降级
- ✅ 正则编译使用缓存优化性能
- ✅ 手动验证真实场景通过
- ✅ 文档状态更新为"已实现"

## 注意事项

1. **TDD 原则**：每个功能都先写失败测试，再实现代码
2. **频繁提交**：每完成一个子功能就提交，保持提交粒度小
3. **向后兼容**：`_filter_posts_by_asset` 函数签名不变，现有调用方无需修改
4. **性能优化**：使用 `@lru_cache` 确保配置和正则只加载/编译一次
5. **错误处理**：配置加载失败时记录日志并降级，不中断服务
