# Obscura Python SDK

Documentação completa: [English](docs/README.md) · [Português do Brasil](docs/README.pt-BR.md)

Playwright-like Python entry points for the Rust Obscura browser fork. The SDK
uses Playwright's own Python objects and CDP client; it does not download
Chromium.

Complete documentation: [English](DOCUMENTATION.md) · [Português do Brasil](DOCUMENTATION.pt-BR.md)

Install from this directory with `pip install -e .`. On first use, the SDK
downloads the matching release from `h4ckf0r0day/obscura` into its own
`obscura-python` data directory. Set `OBSCURA_REPOSITORY` to use another
repository, such as your own fork, when it has compatible release assets.
Set `OBSCURA_PYTHON_HOME` to choose the local root.
`OBSCURA_EXECUTABLE`, `executable_path`, or a binary on `PATH` can override
that download.

The package also installs the `obscura-python` command, which forwards CLI
arguments to the Rust executable:

```bash
pip install obscura-python
obscura-python fetch https://example.com --dump text
```

With uv, install it as a tool:

```bash
uv tool install obscura-python
obscura-python --version
```

Releases are published by GitHub Actions. Create a tag such as `v0.1.0` after
configuring the repository as a Trusted Publisher for the `obscura-python`
project on PyPI; the workflow builds and uploads the wheel and source archive
without storing a PyPI token in GitHub.

For a local checkout use `uv tool install ./python`, or add it to a project
with `uv add ./python`. The first execution may require internet access to
download the Rust browser binary; set `OBSCURA_EXECUTABLE` for offline use.

```python
from obscura.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(proxy={"server": "http://127.0.0.1:8080"})
    page = await browser.new_page()
    await page.goto("https://example.com")
    print(await page.title())
    await browser.close()
```

## Janela de visualização (headless)

O engine continua sem janela e recebe comandos por CDP, mas o SDK pode mostrar
os frames recebidos em uma janela Tkinter. Isso é útil para depurar um fluxo de
RPA sem trocar a API Playwright:

```python
from obscura.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(show_window=True, window_title="Meu robô", frame_rate=30)
    page = browser.contexts[0].pages[0]
    page.goto("https://example.com")
    input("Pressione Enter para fechar... ")
    browser.close()
```

`show_window=True` apenas exibe o screencast `Page.startScreencast`; não torna o
processo do navegador headed e não altera a automação. O recurso depende de
Tkinter estar disponível na instalação do Python.

Each launch chooses a free loopback port and starts an independent process.
`connect_over_cdp()` connects to an external process and never terminates it.
Obscura is headless only; unsupported launch options produce explicit errors.
