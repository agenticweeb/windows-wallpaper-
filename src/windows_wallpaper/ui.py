from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .app import WallpaperApp
from . import __version__


class MainWindow:
    def __init__(self, app: WallpaperApp):
        self.app = app
        self.root = tk.Tk()
        self.root.title("Windows Wallpaper")
        self.root.geometry("760x560")
        self.root.minsize(620, 430)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.status = tk.StringVar(value="Ready")
        self.interval = tk.StringVar(value=str(app.interval))
        self.min_width = tk.StringVar(value=str(app.min_width))
        self.pattern = tk.StringVar(value=app.pattern)
        self.landscape = tk.BooleanVar(value=app.landscape)
        self.paused = tk.BooleanVar(value=app.paused)
        self._build()
        self._refresh_folders()
        self.root.after(200, self._drain_events)
        self.root.after(2000, self._refresh_history)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=16); outer.pack(fill="both", expand=True)
        heading = ttk.Frame(outer); heading.pack(fill="x")
        ttk.Label(heading, text="Windows Wallpaper", font=("Segoe UI", 20, "bold")).pack(side="left")
        ttk.Label(heading, text=f"v{__version__}", foreground="#666").pack(side="right", pady=8)
        ttk.Label(outer, text="A small, offline-friendly wallpaper manager with the Variety workflow.").pack(anchor="w", pady=(0, 14))
        panes = ttk.PanedWindow(outer, orient="horizontal"); panes.pack(fill="both", expand=True)
        left = ttk.Frame(panes, padding=(0, 0, 12, 0)); right = ttk.Frame(panes, padding=(12, 0, 0, 0)); panes.add(left, weight=1); panes.add(right, weight=1)
        ttk.Label(left, text="Wallpaper folders", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.folders = tk.Listbox(left, height=10, selectmode="browse")
        self.folders.pack(fill="both", expand=True, pady=8)
        buttons = ttk.Frame(left); buttons.pack(fill="x")
        ttk.Button(buttons, text="Add folder", command=self._add_folder).pack(side="left")
        ttk.Button(buttons, text="Remove", command=self._remove_folder).pack(side="left", padx=6)
        ttk.Button(left, text="Download Bing wallpapers", command=self.app.download_bing).pack(fill="x", pady=(10, 0))
        ttk.Label(right, text="Rotation", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        controls = ttk.Frame(right); controls.pack(fill="x", pady=8)
        ttk.Label(controls, text="Interval (seconds)").grid(row=0, column=0, sticky="w", pady=4); ttk.Entry(controls, textvariable=self.interval, width=12).grid(row=0, column=1, sticky="e", pady=4)
        ttk.Label(controls, text="Minimum width").grid(row=1, column=0, sticky="w", pady=4); ttk.Entry(controls, textvariable=self.min_width, width=12).grid(row=1, column=1, sticky="e", pady=4)
        ttk.Label(controls, text="Filename contains").grid(row=2, column=0, sticky="w", pady=4); ttk.Entry(controls, textvariable=self.pattern, width=12).grid(row=2, column=1, sticky="e", pady=4)
        ttk.Checkbutton(controls, text="Prefer landscape images", variable=self.landscape).grid(row=3, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Button(right, text="Apply settings and scan", command=self._apply_settings).pack(fill="x", pady=(2, 12))
        action = ttk.Frame(right); action.pack(fill="x")
        ttk.Button(action, text="Previous", command=self.app.previous).pack(side="left", expand=True, fill="x")
        ttk.Button(action, text="Next", command=self.app.next).pack(side="left", expand=True, fill="x", padx=5)
        ttk.Button(action, text="Favorite", command=self.app.favorite).pack(side="left", expand=True, fill="x")
        ttk.Checkbutton(right, text="Pause rotation", variable=self.paused, command=lambda: self.app.set_paused(self.paused.get())).pack(anchor="w", pady=10)
        ttk.Label(right, text="Recent history", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.history = tk.Listbox(right, height=8); self.history.pack(fill="both", expand=True, pady=8)
        footer = ttk.Frame(outer); footer.pack(fill="x", pady=(12, 0))
        ttk.Label(footer, textvariable=self.status, relief="sunken", anchor="w").pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Quit", command=self.quit).pack(side="right", padx=(8, 0))

    def _refresh_folders(self) -> None:
        self.folders.delete(0, tk.END)
        for folder in self.app.folders: self.folders.insert(tk.END, str(folder))

    def _refresh_history(self) -> None:
        self.history.delete(0, tk.END)
        for row in self.app.catalog.history(12): self.history.insert(tk.END, Path(row[0]).name)
        self.root.after(2000, self._refresh_history)

    def _add_folder(self) -> None:
        selected = filedialog.askdirectory(title="Choose a wallpaper folder")
        if selected: self.app.add_folder(Path(selected)); self._refresh_folders()

    def _remove_folder(self) -> None:
        choice = self.folders.curselection()
        if choice: self.app.remove_folder(self.app.folders[choice[0]]); self._refresh_folders()

    def _apply_settings(self) -> None:
        try:
            self.app.set_interval(int(self.interval.get()))
            self.app.min_width = max(0, int(self.min_width.get()))
            self.app.landscape = self.landscape.get()
            self.app.pattern = self.pattern.get().strip()
            self.app.save_settings(); self.app.scan()
        except ValueError: messagebox.showerror("Invalid settings", "Interval and minimum width must be numbers.")

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.app.events.get_nowait()
                if kind == "error": self.status.set(str(value))
                elif kind == "current": self.status.set(f"Current: {Path(str(value)).name}")
                elif kind == "state": self.paused.set(bool(value)); self.status.set("Rotation paused" if value else "Rotation running")
                else: self.status.set(str(value))
        except queue.Empty: pass
        self.root.after(200, self._drain_events)

    def hide(self) -> None:
        self.root.withdraw()

    def quit(self) -> None:
        self.root.destroy()

    def show(self) -> None:
        self.root.deiconify(); self.root.lift(); self.root.focus_force()

    def run(self) -> None:
        self.app.start(); self.root.mainloop()
