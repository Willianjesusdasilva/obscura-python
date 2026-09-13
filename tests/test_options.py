import pytest

from obscura._process import _cache_dir, proxy_url
from obscura.sync_api import Error


def test_proxy_credentials_are_encoded():
    assert proxy_url({"server": "http://proxy:8080", "username": "a@b", "password": "p:x"}) == "http://a%40b:p%3Ax@proxy:8080"


def test_proxy_bypass_is_rejected():
    with pytest.raises(Error, match="bypass"):
        proxy_url({"server": "http://proxy:8080", "bypass": "localhost"})


def test_obscura_home_is_respected(monkeypatch, tmp_path):
    monkeypatch.setenv("OBSCURA_PYTHON_HOME", str(tmp_path))
    assert _cache_dir() == tmp_path / "binaries"
