"""Replace `playwright.sync_api` with `obscura.sync_api` for supported flows."""

import time
from playwright import sync_api as _api
from ._process import BrowserTypeBase, ObscuraExecutableNotFound, Server, UnsupportedBrowser

__all__ = [name for name in dir(_api) if not name.startswith("_")]
globals().update({name: getattr(_api, name) for name in __all__})


class BrowserType(BrowserTypeBase):
    def launch(self, *, args=None, obscura_args=None, **kwargs) -> _api.Browser:
        if args:
            raise _api.Error("Obscura does not support Chromium launch args; use obscura_args")
        if obscura_args is not None and not all(isinstance(arg, str) for arg in obscura_args):
            raise _api.Error("obscura_args must be a sequence of strings")
        kwargs["obscura_args"] = obscura_args
        server = Server(**kwargs)
        try:
            server.start()
            while not server.ready():
                time.sleep(0.025)
            browser = self._chromium.connect_over_cdp(
                server.endpoint, timeout=server.remaining_ms(), slow_mo=server.slow_mo,
            )
            browser.on("disconnected", server.stop)
            self._servers.append(server)
            return browser
        except BaseException:
            server.stop()
            raise

    def connect_over_cdp(self, endpoint_url, **kwargs) -> _api.Browser:
        return self._chromium.connect_over_cdp(endpoint_url, **kwargs)


class Playwright:
    def __init__(self, native):
        self._native = native
        self.chromium = BrowserType(native.chromium)
        self.firefox = UnsupportedBrowser()
        self.webkit = UnsupportedBrowser()

    def __getattr__(self, name):
        return getattr(self._native, name)

    def stop(self):
        try:
            self._native.stop()
        finally:
            self.chromium._stop_servers()


class _ContextManager:
    def __init__(self):
        self._manager = _api.sync_playwright()
        self._playwright = None

    def start(self) -> Playwright:
        self._playwright = Playwright(self._manager.start())
        return self._playwright

    def __enter__(self) -> Playwright:
        return self.start()

    def __exit__(self, *args):
        self._playwright.stop()


def sync_playwright() -> _ContextManager:
    return _ContextManager()
