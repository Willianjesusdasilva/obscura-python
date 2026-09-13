"""Small local window for viewing the headless CDP screencast."""

from __future__ import annotations

import base64
import queue
import threading


class FrameWindow:
    """Display ``Page.screencastFrame`` images in a native Tk window.

    The browser remains headless; this is only a frame viewer. Tk runs on its
    own thread so it does not block Playwright's sync or async event loop.
    """

    def __init__(self, *, title: str = "Obscura (headless preview)", max_fps: int = 30):
        self.title = title
        self.max_fps = max(1, int(max_fps))
        self._frames: queue.Queue[bytes] = queue.Queue(maxsize=2)
        self._thread: threading.Thread | None = None
        self._closed = threading.Event()

    def start(self) -> None:
        try:
            import tkinter as tk
        except ImportError as exc:
            raise RuntimeError("show_window=True requires Tkinter (python-tk)") from exc

        def run() -> None:
            root = tk.Tk()
            root.title(self.title)
            label = tk.Label(root, text="Aguardando frame...", bg="#202124")
            label.pack(fill="both", expand=True)
            root.protocol("WM_DELETE_WINDOW", lambda: (self._closed.set(), root.destroy()))

            def refresh() -> None:
                if self._closed.is_set():
                    try:
                        root.destroy()
                    except tk.TclError:
                        pass
                    return
                try:
                    frame = self._frames.get_nowait()
                except queue.Empty:
                    frame = None
                if frame is not None:
                    image = tk.PhotoImage(data=base64.b64encode(frame).decode("ascii"))
                    label.configure(image=image, text="")
                    label.image = image
                root.after(max(1, int(1000 / self.max_fps)), refresh)

            root.after(0, refresh)
            root.mainloop()

        self._thread = threading.Thread(target=run, name="obscura-frame-window", daemon=True)
        self._thread.start()

    def push(self, data: bytes) -> None:
        if self._closed.is_set():
            return
        try:
            self._frames.put_nowait(data)
        except queue.Full:
            try:
                self._frames.get_nowait()
            except queue.Empty:
                pass
            try:
                self._frames.put_nowait(data)
            except queue.Full:
                pass

    @property
    def closed(self) -> bool:
        return self._closed.is_set()

    def close(self) -> None:
        self._closed.set()
