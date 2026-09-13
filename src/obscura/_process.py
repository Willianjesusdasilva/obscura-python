"""Owned, per-launch Obscura processes. Never changes the parent's environment."""

import math
import os
import shutil
import socket
import subprocess
import tempfile
import time
import json
import platform
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from playwright.sync_api import Error, TimeoutError

class ObscuraExecutableNotFound(Error):
    """Raised when no usable Obscura executable can be located."""


def _cache_dir() -> Path:
    configured = os.environ.get("OBSCURA_PYTHON_HOME")
    if configured:
        return Path(configured).expanduser() / "binaries"
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return root / "obscura-python" / "binaries"
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "obscura-python" / "binaries"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
        return root / "obscura-python" / "binaries"


def _asset_name() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Windows" and machine in {"amd64", "x86_64", "x64"}:
        return "obscura-x86_64-windows.zip"
    if system == "Linux" and machine in {"amd64", "x86_64", "x64"}:
        return "obscura-x86_64-linux.tar.gz"
    if system == "Linux" and machine in {"aarch64", "arm64"}:
        return "obscura-aarch64-linux.tar.gz"
    if system == "Darwin" and machine in {"amd64", "x86_64", "x64"}:
        return "obscura-x86_64-macos.tar.gz"
    if system == "Darwin" and machine in {"aarch64", "arm64"}:
        return "obscura-aarch64-macos.tar.gz"
    raise ObscuraExecutableNotFound(f"No Obscura binary is available for {system}/{machine}")


def ensure_executable() -> str:
    """Return a usable binary, downloading the matching official release if needed."""
    bundled = Path(__file__).with_name("bin") / ("obscura.exe" if os.name == "nt" else "obscura")
    explicit = os.environ.get("OBSCURA_EXECUTABLE")
    if explicit:
        resolved = shutil.which(explicit) or explicit
        if Path(resolved).is_file():
            return resolved
        raise ObscuraExecutableNotFound(f"OBSCURA_EXECUTABLE does not exist: {explicit}")
    if bundled.is_file():
        return str(bundled)
    path_binary = shutil.which("obscura")
    if path_binary:
        return path_binary

    asset = _asset_name()
    version = os.environ.get("OBSCURA_VERSION", "latest")
    destination = _cache_dir() / version / ("obscura.exe" if os.name == "nt" else "obscura")
    if destination.is_file():
        return str(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    lock = destination.with_suffix(destination.suffix + ".lock")
    acquired = False
    for _ in range(300):
        try:
            lock.mkdir()
            acquired = True
            break
        except FileExistsError:
            if destination.is_file():
                return str(destination)
            time.sleep(0.1)
    if not acquired:
        raise ObscuraExecutableNotFound("Timed out waiting for another Obscura download")
    try:
        if destination.is_file():
            return str(destination)
        repository = os.environ.get("OBSCURA_REPOSITORY", "h4ckf0r0day/obscura")
        api = f"https://api.github.com/repos/{repository}/releases/latest"
        with urllib.request.urlopen(api, timeout=20) as response:
            release = json.load(response)
        if version != "latest":
            tag = version if version.startswith("v") else f"v{version}"
            release_url = f"https://github.com/{repository}/releases/download/{tag}/{asset}"
        else:
            found = next((item for item in release.get("assets", []) if item.get("name") == asset), None)
            if not found:
                raise ObscuraExecutableNotFound(f"Release does not provide {asset}")
            release_url = found["browser_download_url"]
        with tempfile.TemporaryDirectory(prefix="obscura-download-") as temp:
            archive = Path(temp) / asset
            urllib.request.urlretrieve(release_url, archive)
            extract = Path(temp) / "extract"
            extract.mkdir()
            if asset.endswith(".zip"):
                with zipfile.ZipFile(archive) as package:
                    package.extractall(extract)
            else:
                with tarfile.open(archive, "r:gz") as package:
                    try:
                        package.extractall(extract, filter="data")
                    except TypeError:  # Python 3.10/3.11
                        package.extractall(extract)
            candidates = list(extract.rglob(destination.name))
            if not candidates:
                raise ObscuraExecutableNotFound("Downloaded Obscura archive has no executable")
            shutil.copy2(candidates[0], destination)
        if os.name != "nt":
            destination.chmod(destination.stat().st_mode | 0o111)
        return str(destination)
    except ObscuraExecutableNotFound:
        raise
    except Exception as exc:
        raise ObscuraExecutableNotFound(
            f"Could not download Obscura automatically: {exc}. "
            "Set OBSCURA_EXECUTABLE to a local binary to disable downloading."
        ) from exc
    finally:
        try:
            lock.rmdir()
        except OSError:
            pass


def proxy_url(proxy):
    if not proxy:
        return None
    if set(proxy) - {"server", "username", "password", "bypass"}:
        raise Error("Unknown Obscura proxy option")
    if proxy.get("bypass"):
        raise Error("Obscura does not support proxy bypass lists")
    server = proxy.get("server", "")
    parsed = urlsplit(server if "://" in server else "http://" + server)
    if parsed.scheme not in {"http", "https", "socks5"} or not parsed.hostname:
        raise Error("Obscura requires an HTTP, HTTPS or SOCKS5 proxy server")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise Error("Proxy server must not contain a path, query or fragment")
    authority = parsed.netloc
    if proxy.get("username") is not None or proxy.get("password") is not None:
        authority = authority.rsplit("@", 1)[-1]
        user = quote(proxy.get("username", ""), safe="")
        password = quote(proxy.get("password", ""), safe="")
        authority = f"{user}:{password}@{authority}"
    return urlunsplit((parsed.scheme, authority, "", "", ""))


class Server:
    def __init__(self, *, executable_path=None, headless=None, proxy=None,
                 timeout=None, env=None, slow_mo=None, obscura_args=None, **unsupported):
        active = [key for key, value in unsupported.items() if value is not None]
        if active:
            raise Error("Unsupported Obscura launch options: " + ", ".join(active))
        if headless is False:
            raise Error("Obscura is headless only; headless=False is unsupported")
        timeout = 30000 if timeout is None else timeout
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout < 0:
            raise Error("timeout must be a finite nonnegative number of milliseconds")
        self.deadline = None if timeout == 0 else time.monotonic() + timeout / 1000
        self.slow_mo = slow_mo
        self.obscura_args = list(obscura_args or [])
        self.env = dict(os.environ)
        if env is not None:
            self.env.update({k: str(v) for k, v in env.items()})
        if executable_path:
            self.executable = shutil.which(os.fspath(executable_path), path=self.env.get("PATH")) or os.fspath(executable_path)
            if not Path(self.executable).is_file():
                raise ObscuraExecutableNotFound(f"executable_path does not exist: {executable_path}")
        elif self.env.get("OBSCURA_EXECUTABLE"):
            self.executable = self.env["OBSCURA_EXECUTABLE"]
            if not Path(self.executable).is_file():
                raise ObscuraExecutableNotFound(f"OBSCURA_EXECUTABLE does not exist: {self.executable}")
        else:
            self.executable = ensure_executable()
        url = proxy_url(proxy)
        if url:
            self.env["OBSCURA_PROXY"] = url
        # OS allocation avoids a fixed port shared by simultaneous RPA jobs.
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            self.port = reservation.getsockname()[1]
        self.endpoint = f"ws://127.0.0.1:{self.port}/devtools/browser"
        self.process = None

    def start(self):
        try:
            self.process = subprocess.Popen(
                [self.executable, "serve", "--host", "127.0.0.1", "--port", str(self.port), *self.obscura_args],
                env=self.env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            raise Error(f"Could not start Obscura: {exc}") from exc

    def remaining_ms(self):
        if self.deadline is None:
            return 0
        remaining = (self.deadline - time.monotonic()) * 1000
        if remaining <= 0:
            raise TimeoutError("Timed out starting Obscura")
        return remaining

    def ready(self):
        if self.process.poll() is not None:
            raise Error(f"Obscura exited during startup (code {self.process.returncode})")
        self.remaining_ms()
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=0.01):
                return True
        except OSError:
            return False

    def stop(self, *_):
        viewer = getattr(self, "_frame_viewer", None)
        if viewer is not None:
            viewer.close()
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


class UnsupportedBrowser:
    def __getattr__(self, name):
        raise Error("Obscura supports chromium only, not Firefox or WebKit")


class BrowserTypeBase:
    name = "chromium"

    def __init__(self, chromium):
        self._chromium = chromium
        self._servers = []

    @property
    def executable_path(self):
        bundled = Path(__file__).with_name("bin") / ("obscura.exe" if os.name == "nt" else "obscura")
        return os.environ.get("OBSCURA_EXECUTABLE") or (str(bundled) if bundled.exists() else shutil.which("obscura") or "obscura")

    def _stop_servers(self):
        for server in self._servers:
            server.stop()
        self._servers.clear()

    def __getattr__(self, name):
        raise Error(f"Obscura does not support BrowserType.{name}")
