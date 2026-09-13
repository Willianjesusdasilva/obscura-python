# Documentação do Obscura Python SDK

Idiomas: Português do Brasil · [English](README.md)

O `obscura-python` é uma camada Python para o navegador Obscura escrito em
Rust. Ele reutiliza a API e os objetos do Playwright Python e se conecta ao
Obscura por CDP. O engine não é reescrito nem incorporado ao Python.

## Instalação

```bash
pip install obscura-python
# ou
uv add obscura-python
```

O pacote requer Python 3.10+ e usa Playwright como cliente de protocolo. Ele
não executa `playwright install chromium`. Na primeira abertura de um browser,
baixa a release correspondente de `h4ckf0r0day/obscura` e salva em um diretório
próprio:

- Windows: `%LOCALAPPDATA%\\obscura-python\\binaries`
- Linux: `~/.local/share/obscura-python/binaries`
- macOS: `~/Library/Application Support/obscura-python/binaries`

Use `OBSCURA_PYTHON_HOME` para escolher outra raiz. É necessário acesso à
internet uma vez por versão e plataforma.

## API assíncrona

Nos fluxos compatíveis com Playwright, troque apenas o import:

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
erros e asserções são reexportados do Playwright. Métodos como `locator()`,
`click()`, `fill()`, `evaluate()`, `wait_for_selector()`, `content()`,
screenshots, contexts e cookies mantêm a convenção do Playwright quando
estiverem disponíveis na superfície CDP do Obscura.

## API síncrona

```python
from obscura.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com")
    print(page.title())
    browser.close()
```

## Opções de inicialização

```python
browser = await p.chromium.launch(
    executable_path="C:\\obscura\\obscura.exe",
    proxy={"server": "http://proxy:8080", "username": "usuario", "password": "senha"},
    timeout=30_000,
    env={"OBSCURA_SCRIPT_DEADLINE_MS": "60000"},
    obscura_args=["--stealth"],
)
```

Cada abertura recebe uma porta loopback livre e um processo independente. Uma
conexão feita com `connect_over_cdp()` usa um processo existente e não o encerra.
`headless=False`, `args` do Chromium, `channel`, Firefox e WebKit geram erro
explícito quando não são suportados.

`OBSCURA_REPOSITORY=organizacao/repositorio` altera a origem das releases. Use
um fork somente se ele publicar os mesmos nomes de artefatos por plataforma.

## Linha de comando

O pacote instala `obscura-python`, que encaminha argumentos para a CLI Rust e
baixa o binário antes de executar quando necessário:

```bash
obscura-python fetch https://example.com --dump text
obscura-python serve --port 9222
```

## RPA e workers

O SDK não usa singleton nem porta fixa. Cada task do Celery, subprocesso ou
worker pode abrir seu próprio browser e proxy. Mantenha um browser por task
quando cookies ou credenciais precisarem ficar isolados e sempre feche o
browser ou saia do contexto `async_playwright()` para executar a limpeza.

## Releases e desenvolvimento

O repositório é
[Willianjesusdasilva/obscura-python](https://github.com/Willianjesusdasilva/obscura-python).
Execute os testes com `pytest` e gere artefatos com `uv build`. Um push de uma
tag `v*` executa os testes, gera wheel e source archive e publica no PyPI por
Trusted Publishing do GitHub Actions.

Os binários são publicados pelo projeto Obscura Rust. O SDK Python não compila
V8 nem baixa o código-fonte e dependências Rust na máquina do usuário; ele baixa
o artefato compilado da release.
