"""Replace `playwright.async_api` with `obscura.async_api` for supported flows."""

import asyncio
from playwright import async_api as _api
from ._process import BrowserTypeBase, ObscuraExecutableNotFound, Server, UnsupportedBrowser
from ._viewer import FrameWindow

# Real Playwright types, exceptions and assertions, without private API patches.
__all__ = [name for name in dir(_api) if not name.startswith("_")]
globals().update({name: getattr(_api, name) for name in __all__})


class BrowserType(BrowserTypeBase):
    async def launch(self, *, args=None, obscura_args=None, show_window=False,
                     window_title="Obscura (headless preview)", frame_rate=30, **kwargs) -> _api.Browser:
        if args:
            raise _api.Error("Obscura does not support Chromium launch args; use obscura_args")
        if obscura_args is not None and not all(isinstance(arg, str) for arg in obscura_args):
            raise _api.Error("obscura_args must be a sequence of strings")
        kwargs["obscura_args"] = obscura_args
        server = Server(**kwargs)
        try:
            server.start()
            while not server.ready():
                await asyncio.sleep(0.025)
            browser = await self._chromium.connect_over_cdp(
                server.endpoint, timeout=server.remaining_ms(), slow_mo=server.slow_mo,
            )
            if show_window:
                viewer = FrameWindow(title=window_title, max_fps=frame_rate)
                viewer.start()
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else await context.new_page()

                async def pump_frames():
                    interval = 1 / max(1, int(frame_rate))
                    while not viewer.closed:
                        try:
                            viewer.push(await page.screenshot(type="png"))
                        except Exception:
                            viewer.close()
                            return
                        await asyncio.sleep(interval)

                server._frame_task = asyncio.create_task(pump_frames())
                def close_viewer():
                    viewer.close()
                    task = getattr(server, "_frame_task", None)
                    if task:
                        task.cancel()

                browser.on("disconnected", close_viewer)
                server._frame_viewer = viewer
            browser.on("disconnected", server.stop)
            self._servers.append(server)
            return browser
        except BaseException:
            server.stop()
            raise

    async def connect_over_cdp(self, endpoint_url, **kwargs) -> _api.Browser:
        return await self._chromium.connect_over_cdp(endpoint_url, **kwargs)


class Playwright:
    def __init__(self, native):
        self._native = native
        self.chromium = BrowserType(native.chromium)
        self.firefox = UnsupportedBrowser()
        self.webkit = UnsupportedBrowser()

    def __getattr__(self, name):
        return getattr(self._native, name)

    async def stop(self):
        try:
            await self._native.stop()
        finally:
            self.chromium._stop_servers()


class _ContextManager:
    def __init__(self):
        self._manager = _api.async_playwright()
        self._playwright = None

    async def start(self) -> Playwright:
        self._playwright = Playwright(await self._manager.start())
        return self._playwright

    async def __aenter__(self) -> Playwright:
        return await self.start()

    async def __aexit__(self, *args):
        await self._playwright.stop()


def async_playwright() -> _ContextManager:
    return _ContextManager()
