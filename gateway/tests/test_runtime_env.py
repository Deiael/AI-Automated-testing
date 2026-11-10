from types import SimpleNamespace

from app.services.runtime_env import list_envs, resolve_env


def _proj(**kwargs):
    defaults = {
        "runtime_base_url": "https://httpbin.org",
        "runtime_headers": {"X-A": "1"},
        "runtime_variables": {"token": "t"},
        "runtime_envs": [],
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_legacy_single_url_becomes_default_env():
    p = _proj()
    envs = list_envs(p)
    assert len(envs) == 1
    assert envs[0]["base_url"] == "https://httpbin.org"
    got = resolve_env(p, None)
    assert got["headers"]["X-A"] == "1"
    assert got["variables"]["token"] == "t"


def test_named_env_override():
    p = _proj(
        runtime_envs=[
            {"id": "test", "name": "测试", "base_url": "https://test.local", "is_default": True, "timeout_sec": 15},
            {"id": "prod", "name": "生产", "base_url": "https://prod.local", "headers": {"X-Env": "prod"}},
        ]
    )
    prod = resolve_env(p, "prod")
    assert prod["base_url"] == "https://prod.local"
    assert prod["headers"]["X-Env"] == "prod"
    assert prod["headers"]["X-A"] == "1"
    default = resolve_env(p, None)
    assert default["id"] == "test"
    assert default["timeout_sec"] == 15
