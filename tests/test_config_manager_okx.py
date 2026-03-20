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
