# Obscura Python SDK documentation

Languages: [Português do Brasil](README.pt-BR.md) · English

`obscura-python` is a Python integration layer for the Rust Obscura browser. It
reuses Playwright Python's API and objects and connects to Obscura through CDP.
It does not embed or rewrite the browser engine in Python.

## Install

```bash
pip install obscura-python
# or
uv add obscura-python
```

The package requires Python 3.10+ and depends on Playwright as a protocol
client. It does not run `playwright install chromium`. When a browser is first
launched, the SDK downloads the matching Obscura release from
`h4ckf0r0day/obscura` and stores it in its own data directory:

- Windows: `%LOCALAPPDATA%\\obscura-python\\binaries`
- Linux: `~/.local/share/obscura-python/binaries`
- macOS: `~/Library/Application Support/obscura-python/binaries`

Set `OBSCURA_PYTHON_HOME` to choose another root. The download requires
internet access once per Obscura version and platform.

## Async API

Change only the import in supported Playwright code:

```python
from obscura.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()
    await page.goto("https://example.com")
    print(await page.title())
    await browser.close()
```

`Page`, `Browser`, `BrowserContext`, `Locator`, `Frame`, `Request`, `Response`,
Playwright errors, and assertions are re-exported from Playwright. Therefore
methods such as `locator()`, `click()`, `fill()`, `evaluate()`,
`wait_for_selector()`, `content()`, screenshots, contexts, and cookies retain
Playwright's normal calling convention when implemented by Obscura's CDP
surface.

## Sync API

```python
from obscura.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com")
    print(page.title())
    browser.close()
```

## Launch options

```python
browser = await p.chromium.launch(
    executable_path="/opt/obscura",
    proxy={"server": "http://proxy:8080", "username": "user", "password": "pass"},
    timeout=30_000,
    env={"OBSCURA_SCRIPT_DEADLINE_MS": "60000"},
    obscura_args=["--stealth"],
)
```

Every launch gets a free loopback port and an independent OS process. A
`connect_over_cdp()` connection attaches to an existing process and does not
own or terminate that process. `headless=False`, Chromium launch `args`,
`channel`, Firefox, and WebKit are rejected explicitly when unsupported.

`OBSCURA_REPOSITORY=owner/repository` changes the release source. Use a fork
only when it publishes the same platform asset names as the upstream project.

## CLI

The package installs `obscura-python`, which forwards arguments to the Rust
CLI and downloads the binary first when necessary:

```bash
obscura-python fetch https://example.com --dump text
obscura-python serve --port 9222
```

## RPA and workers

The SDK has no singleton or fixed port. Each Celery task, subprocess, or worker
can launch its own browser and proxy. Keep one browser per task when cookies
or credentials must remain isolated, and always close it or leave the
`async_playwright()` context so cleanup runs.

## Releases and development

The repository is [Willianjesusdasilva/obscura-python](https://github.com/Willianjesusdasilva/obscura-python).
Tests run with `pytest`; build artifacts with `uv build`. Pushing a `v*` tag
runs tests, builds the wheel and source archive, and publishes to PyPI through
GitHub Actions Trusted Publishing.

The browser binaries are released by the Obscura Rust project. The Python SDK
does not compile V8 or download Rust source dependencies on the user's
machine; it downloads the already compiled release artifact.
