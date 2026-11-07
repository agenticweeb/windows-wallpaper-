from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .app import WallpaperApp
from . import __version__
from .ipc import IPC


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
        self.quote_enabled = tk.BooleanVar(value=app.quote_enabled)
        self.quote_source = tk.StringVar(value=app.quote_source)
        self.quote_tags = tk.StringVar(value=app.quote_tags)
        self.quote_font_size = tk.StringVar(value=str(app.quote_font_size))
        self.quote_color = tk.StringVar(value=app.quote_color)
        self.quote_bg_opacity = tk.StringVar(value=str(app.quote_bg_opacity))
        self.quote_width = tk.StringVar(value=str(app.quote_width))
        self.quote_hpos = tk.StringVar(value=str(app.quote_hpos))
        self.quote_vpos = tk.StringVar(value=str(app.quote_vpos))
        self.wallhaven_query = tk.StringVar(value="anime")
        self.reddit_subreddit = tk.StringVar(value="Animewallpaper")
        self.ipc = IPC()
        self._build()
        self.ipc.listen(lambda command: self.root.after(0, lambda: self._handle_command(command)))
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
        source_box = ttk.LabelFrame(left, text="Online sources", padding=8); source_box.pack(fill="x", pady=(10, 0))
        ttk.Label(source_box, text="Wallhaven search").pack(anchor="w"); ttk.Entry(source_box, textvariable=self.wallhaven_query).pack(fill="x", pady=(2, 4))
        ttk.Button(source_box, text="Download from Wallhaven", command=lambda: self.app.download_wallhaven(self.wallhaven_query.get())).pack(fill="x")
        ttk.Label(source_box, text="Reddit community").pack(anchor="w", pady=(6, 0)); ttk.Entry(source_box, textvariable=self.reddit_subreddit).pack(fill="x", pady=(2, 4))
        ttk.Button(source_box, text="Download from Reddit", command=lambda: self.app.download_reddit(self.reddit_subreddit.get())).pack(fill="x")
        ttk.Label(source_box, text="Wallhaven accepts search tags such as anime, cyberpunk, nature.", foreground="#666", wraplength=220).pack(anchor="w", pady=(6, 0))
        ttk.Label(right, text="Rotation", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        controls = ttk.Frame(right); controls.pack(fill="x", pady=8)
        ttk.Label(controls, text="Interval (seconds)").grid(row=0, column=0, sticky="w", pady=4); ttk.Entry(controls, textvariable=self.interval, width=12).grid(row=0, column=1, sticky="e", pady=4)
        ttk.Label(controls, text="Minimum width").grid(row=1, column=0, sticky="w", pady=4); ttk.Entry(controls, textvariable=self.min_width, width=12).grid(row=1, column=1, sticky="e", pady=4)
        ttk.Label(controls, text="Filename contains").grid(row=2, column=0, sticky="w", pady=4); ttk.Entry(controls, textvariable=self.pattern, width=12).grid(row=2, column=1, sticky="e", pady=4)
        ttk.Checkbutton(controls, text="Prefer landscape images", variable=self.landscape).grid(row=3, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Button(right, text="Apply settings and scan", command=self._apply_settings).pack(fill="x", pady=(2, 12))
        quote_box = ttk.LabelFrame(right, text="Quotes & text overlay", padding=8); quote_box.pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(quote_box, text="Render quote onto the wallpaper copy", variable=self.quote_enabled).grid(row=0, column=0, columnspan=4, sticky="w")
        self.quote_text_box = tk.Text(quote_box, height=3, width=36, wrap="word"); self.quote_text_box.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 4)); self.quote_text_box.insert("1.0", app.quote_text)
        ttk.Label(quote_box, text="Author").grid(row=2, column=0, sticky="w"); self.quote_author = ttk.Entry(quote_box, width=18); self.quote_author.grid(row=2, column=1, columnspan=3, sticky="ew"); self.quote_author.insert(0, app.quote_author)
        ttk.Label(quote_box, text="Source").grid(row=3, column=0, sticky="w", pady=(4, 0)); ttk.Combobox(quote_box, textvariable=self.quote_source, values=("quotable", "zenquotes", "custom"), state="readonly", width=12).grid(row=3, column=1, sticky="w", pady=(4, 0)); ttk.Button(quote_box, text="Fetch quote", command=self._fetch_quote).grid(row=3, column=2, columnspan=2, sticky="e", pady=(4, 0))
        ttk.Label(quote_box, text="Tags").grid(row=4, column=0, sticky="w"); ttk.Entry(quote_box, textvariable=self.quote_tags, width=15).grid(row=4, column=1, columnspan=3, sticky="ew")
        for col, (label, var) in enumerate((("Size", self.quote_font_size), ("Color", self.quote_color), ("Opacity", self.quote_bg_opacity), ("Width", self.quote_width))):
            ttk.Label(quote_box, text=label).grid(row=5, column=col, sticky="w"); ttk.Entry(quote_box, textvariable=var, width=7).grid(row=6, column=col, sticky="ew", padx=(0, 4))
        ttk.Label(quote_box, text="Horizontal %").grid(row=7, column=0, sticky="w"); ttk.Entry(quote_box, textvariable=self.quote_hpos, width=7).grid(row=8, column=0, sticky="ew")
        ttk.Label(quote_box, text="Vertical %").grid(row=7, column=1, sticky="w"); ttk.Entry(quote_box, textvariable=self.quote_vpos, width=7).grid(row=8, column=1, sticky="ew")
        ttk.Label(quote_box, text="Edit quotes in %APPDATA%\\WindowsWallpaper\\config\\quotes.txt as `quote | author`.", foreground="#666", wraplength=320).grid(row=9, column=0, columnspan=4, sticky="w", pady=(5, 0))
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

    def _fetch_quote(self) -> None:
        self._apply_settings()
        self.app.fetch_quote()

    def _apply_settings(self) -> None:
        try:
            self.app.set_interval(int(self.interval.get()))
            self.app.min_width = max(0, int(self.min_width.get()))
            self.app.landscape = self.landscape.get()
            self.app.pattern = self.pattern.get().strip()
            self.app.quote_enabled = self.quote_enabled.get()
            self.app.quote_text = self.quote_text_box.get("1.0", "end").strip()
            self.app.quote_author = self.quote_author.get().strip()
            self.app.quote_source = self.quote_source.get()
            self.app.quote_tags = self.quote_tags.get().strip()
            self.app.quote_font_size = max(14, int(self.quote_font_size.get()))
            self.app.quote_color = self.quote_color.get().strip() or "#ffffff"
            self.app.quote_bg_opacity = max(0, min(100, int(self.quote_bg_opacity.get())))
            self.app.quote_width = max(10, min(95, int(self.quote_width.get())))
            self.app.quote_hpos = max(0, min(100, int(self.quote_hpos.get())))
            self.app.quote_vpos = max(0, min(100, int(self.quote_vpos.get())))
            self.app.save_settings(); self.app.scan()
        except ValueError: messagebox.showerror("Invalid settings", "Interval and minimum width must be numbers.")

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.app.events.get_nowait()
                if kind == "error": self.status.set(str(value))
                elif kind == "current": self.status.set(f"Current: {Path(str(value)).name}")
                elif kind == "state": self.paused.set(bool(value)); self.status.set("Rotation paused" if value else "Rotation running")
                elif kind == "quote":
                    self.quote_text_box.delete("1.0", "end"); self.quote_text_box.insert("1.0", self.app.quote_text); self.quote_author.delete(0, "end"); self.quote_author.insert(0, self.app.quote_author); self.status.set("Quote updated")
                else: self.status.set(str(value))
        except queue.Empty: pass
        self.root.after(200, self._drain_events)

    def hide(self) -> None:
        self.root.withdraw()
        self.status.set("Running in the background. Relaunch Windows Wallpaper to restore this window.")

    def _handle_command(self, command: str | None) -> None:
        if command == "show":
            self.show()
        elif command == "next":
            self.app.next()
        elif command == "previous":
            self.app.previous()
        elif command == "pause":
            self.app.set_paused(True)
        elif command == "resume":
            self.app.set_paused(False)
        elif command == "quit":
            self.quit()

    def quit(self) -> None:
        self.ipc.close()
        self.root.destroy()

    def show(self) -> None:
        self.root.deiconify(); self.root.lift(); self.root.focus_force()

    def run(self) -> None:
        self.app.start(); self.root.mainloop()
