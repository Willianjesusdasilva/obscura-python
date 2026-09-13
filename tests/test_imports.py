def test_async_imports():
    from obscura.async_api import Browser, BrowserContext, Error, Locator, Page, TimeoutError, async_playwright
    assert all((Browser, BrowserContext, Error, Locator, Page, TimeoutError, async_playwright))


def test_sync_import():
    from obscura.sync_api import sync_playwright
    assert callable(sync_playwright)
