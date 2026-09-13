"""Small isolated process for viewing the headless browser frames."""

from __future__ import annotations

import base64
import multiprocessing as mp
import queue


def _run_window(frames, title: str, max_fps: int) -> None:
    import tkinter as tk
    root = tk.Tk()
    root.title(title)
    label = tk.Label(root, text="Aguardando frame...", bg="#202124")
    label.pack(fill="both", expand=True)

    def refresh() -> None:
        try:
            frame = frames.get_nowait()
        except queue.Empty:
            frame = None
        if frame is None:
            root.destroy()
            return
        image = tk.PhotoImage(data=base64.b64encode(frame).decode("ascii"))
        label.configure(image=image, text="")
        label.image = image
        root.after(max(1, int(1000 / max_fps)), refresh)

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.after(0, refresh)
    root.mainloop()


class FrameWindow:
    """Display frames in a native window without making the browser headed."""

    def __init__(self, *, title: str = "Obscura (headless preview)", max_fps: int = 30):
        self.title = title
        self.max_fps = max(1, int(max_fps))
        self._frames = mp.Queue(maxsize=2)
        self._process: mp.Process | None = None
        self._closed = False

    def start(self) -> None:
        self._process = mp.Process(
            target=_run_window, args=(self._frames, self.title, self.max_fps),
            name="obscura-frame-window", daemon=True,
        )
        self._process.start()

    def push(self, data: bytes) -> None:
        if self._closed:
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
        return self._closed or (self._process is not None and not self._process.is_alive())

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._frames.put_nowait(None)
        except (queue.Full, ValueError):
            pass
        if self._process is not None:
            self._process.join(timeout=2)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=1)
        self._frames.close()
