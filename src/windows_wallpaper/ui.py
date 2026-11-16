from __future__ import annotations

import queue
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageTk

from . import __version__
from .app import WallpaperApp
from .ipc import IPC
from .overlay import STYLES, render_quote


class MainWindow:
    BG = "#0a0a0f"
    PANEL = "#12121a"
    PANEL_2 = "#181824"
    TEXT = "#eef2ff"
    MUTED = "#8b91a7"
    CYAN = "#00f0ff"
    MAGENTA = "#ff00aa"
    GREEN = "#00ff9f"

    def __init__(self, app: WallpaperApp):
        self.app = app
        self.root = tk.Tk()
        self.root.title("Windows Wallpaper")
        self.root.geometry("1120x760")
        self.root.minsize(900, 620)
        self.root.configure(bg=self.BG)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.status = tk.StringVar(value="Ready")
        self.tab = tk.StringVar(value="NOW PLAYING")
        self.preview_photo = None
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
        self.quote_style = tk.StringVar(value=getattr(app, "quote_style", "classic"))
        self.wallhaven_query = tk.StringVar(value="anime")
        self.reddit_subreddit = tk.StringVar(value="Animewallpaper")
        self.quote_rotation_interval = tk.StringVar(value=str(getattr(app, "quote_rotation_interval", 120)))
        self.quote_provider_values = {"Quotable": "quotable", "ZenQuotes": "zenquotes", "Goodreads · imported file": "goodreads", "Funny quotes": "funny", "Built-in fallback": "builtin"}
        self.favorites_only = tk.BooleanVar(value=False)
        self._configure_style()
        self._build()
        self.ipc = IPC()
        self.ipc.listen(lambda command: self.root.after(0, lambda: self._handle_command(command)))
        self._refresh_folders(); self._refresh_library(); self._refresh_history()
        self.root.after(200, self._drain_events)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=self.BG)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure("TLabel", background=self.BG, foreground=self.TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=self.BG, foreground=self.MUTED)
        style.configure("Title.TLabel", background=self.BG, foreground=self.TEXT, font=("Segoe UI", 23, "bold"))
        style.configure("Section.TLabel", background=self.BG, foreground=self.CYAN, font=("Segoe UI", 10, "bold"))
        style.configure("TButton", background=self.PANEL_2, foreground=self.TEXT, borderwidth=0, padding=(12, 8), font=("Segoe UI", 10))
        style.map("TButton", background=[("active", self.CYAN)], foreground=[("active", self.BG)])
        style.configure("Accent.TButton", background=self.CYAN, foreground=self.BG, font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", self.GREEN)])
        style.configure("TCheckbutton", background=self.BG, foreground=self.TEXT)
        style.configure("TLabelframe", background=self.BG, foreground=self.CYAN)
        style.configure("TLabelframe.Label", background=self.BG, foreground=self.CYAN)
        style.configure("TNotebook", background=self.BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.PANEL, foreground=self.MUTED, padding=(16, 9), font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", self.CYAN)], foreground=[("selected", self.BG)])
        style.configure("TEntry", fieldbackground=self.PANEL_2, foreground=self.TEXT, insertcolor=self.CYAN)
        style.configure("TCombobox", fieldbackground=self.PANEL_2, foreground=self.TEXT)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=22); outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer); header.pack(fill="x", pady=(0, 18))
        ttk.Label(header, text="WINDOWS WALLPAPER", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text=f"v{__version__}  /  OFFLINE-FIRST", style="Muted.TLabel").pack(side="right", pady=8)
        self._build_tabs(outer)
        footer = ttk.Frame(outer); footer.pack(fill="x", pady=(14, 0))
        self.status_dot = tk.Label(footer, text="●", bg=self.BG, fg=self.GREEN, font=("Segoe UI", 12)); self.status_dot.pack(side="left")
        ttk.Label(footer, textvariable=self.status, style="Muted.TLabel").pack(side="left", padx=(8, 0))
        ttk.Button(footer, text="Hide to background", command=self.hide).pack(side="right")

    def _build_tabs(self, parent) -> None:
        notebook = ttk.Notebook(parent); notebook.pack(fill="both", expand=True)
        now = ttk.Frame(notebook, padding=18); library = ttk.Frame(notebook, padding=18); sources = ttk.Frame(notebook, padding=18); quotes = ttk.Frame(notebook, padding=18); settings = ttk.Frame(notebook, padding=18)
        notebook.add(now, text="NOW PLAYING"); notebook.add(library, text="LIBRARY"); notebook.add(sources, text="SOURCES"); notebook.add(quotes, text="QUOTES"); notebook.add(settings, text="SETTINGS")
        self._build_now(now); self._build_library(library); self._build_sources(sources); self._build_quotes(quotes); self._build_settings(settings)

    def _build_now(self, parent) -> None:
        parent.columnconfigure(0, weight=3); parent.columnconfigure(1, weight=2); parent.rowconfigure(0, weight=1)
        preview_card = tk.Frame(parent, bg="#050508", highlightbackground=self.CYAN, highlightthickness=1); preview_card.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self.preview_label = tk.Label(preview_card, text="NO WALLPAPER SELECTED", bg="#050508", fg=self.MUTED, font=("Segoe UI", 13, "bold")); self.preview_label.pack(fill="both", expand=True, padx=10, pady=10)
        side = ttk.Frame(parent); side.grid(row=0, column=1, sticky="nsew")
        ttk.Label(side, text="CURRENT WALLPAPER", style="Section.TLabel").pack(anchor="w")
        self.now_title = ttk.Label(side, text="Nothing playing", font=("Segoe UI", 17, "bold"), wraplength=320); self.now_title.pack(anchor="w", pady=(8, 4))
        self.now_meta = ttk.Label(side, text="Add a folder or fetch an online source to begin.", style="Muted.TLabel", wraplength=320); self.now_meta.pack(anchor="w", pady=(0, 22))
        actions = ttk.Frame(side); actions.pack(fill="x", pady=(0, 18))
        ttk.Button(actions, text="‹ Previous", command=self.app.previous).pack(side="left", expand=True, fill="x")
        ttk.Button(actions, text="Next ›", style="Accent.TButton", command=self.app.next).pack(side="left", expand=True, fill="x", padx=(8, 0))
        ttk.Button(side, text="☆  Favorite current", command=self.app.favorite).pack(fill="x")
        ttk.Checkbutton(side, text="Pause rotation", variable=self.paused, command=lambda: self.app.set_paused(self.paused.get())).pack(anchor="w", pady=14)
        ttk.Label(side, text="RECENTLY PLAYED", style="Section.TLabel").pack(anchor="w")
        self.history = tk.Listbox(side, height=8, bg=self.PANEL, fg=self.TEXT, selectbackground=self.CYAN, selectforeground=self.BG, relief="flat", highlightthickness=0, font=("Segoe UI", 9)); self.history.pack(fill="both", expand=True, pady=(8, 0)); self.history.bind("<Double-Button-1>", self._apply_history)

    def _build_library(self, parent) -> None:
        parent.columnconfigure(0, weight=1); parent.columnconfigure(1, weight=2); parent.rowconfigure(1, weight=1)
        ttk.Label(parent, text="LIBRARY", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(parent, text="WALLPAPERS", style="Section.TLabel").grid(row=0, column=1, sticky="w")
        left = ttk.Frame(parent); left.grid(row=1, column=0, sticky="nsew", padx=(0, 18)); left.rowconfigure(0, weight=1)
        self.folders = tk.Listbox(left, bg=self.PANEL, fg=self.TEXT, selectbackground=self.CYAN, selectforeground=self.BG, relief="flat", highlightthickness=0); self.folders.grid(row=0, column=0, columnspan=2, sticky="nsew")
        ttk.Button(left, text="+ Add folder", command=self._add_folder).grid(row=1, column=0, sticky="ew", pady=(10, 0)); ttk.Button(left, text="Remove", command=self._remove_folder).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(10, 0))
        right = ttk.Frame(parent); right.grid(row=1, column=1, sticky="nsew"); right.rowconfigure(1, weight=1); right.columnconfigure(0, weight=1)
        filters = ttk.Frame(right); filters.grid(row=0, column=0, sticky="ew", pady=(0, 10)); ttk.Label(filters, text="Contains").pack(side="left"); ttk.Entry(filters, textvariable=self.pattern, width=20).pack(side="left", padx=8); ttk.Checkbutton(filters, text="Favorites only", variable=self.favorites_only, command=self._refresh_library).pack(side="left", padx=8); ttk.Button(filters, text="Scan library", command=self._apply_settings).pack(side="left")
        self.library_list = tk.Listbox(right, bg=self.PANEL, fg=self.TEXT, selectbackground=self.CYAN, selectforeground=self.BG, relief="flat", highlightthickness=0, font=("Segoe UI", 10)); self.library_list.grid(row=1, column=0, sticky="nsew"); self.library_list.bind("<Double-Button-1>", self._apply_library)

    def _build_sources(self, parent) -> None:
        ttk.Label(parent, text="ONLINE SOURCES", style="Section.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Fetch deliberately. Downloads are validated, attributed, and stored locally for offline rotation.", style="Muted.TLabel").pack(anchor="w", pady=(4, 18))
        grid = ttk.Frame(parent); grid.pack(fill="x");
        cards = [("BING DAILY", "Photo of the day archive", self.app.download_bing), ("WALLHAVEN", "Search safe anime and art", lambda: self.app.download_wallhaven(self.wallhaven_query.get())), ("REDDIT", "Pull direct images from a community", lambda: self.app.download_reddit(self.reddit_subreddit.get()))]
        for i, (title, desc, command) in enumerate(cards):
            card = tk.Frame(grid, bg=self.PANEL, highlightbackground=self.PANEL_2, highlightthickness=1); card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0)); grid.columnconfigure(i, weight=1)
            tk.Label(card, text=title, bg=self.PANEL, fg=self.CYAN, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(16, 4)); tk.Label(card, text=desc, bg=self.PANEL, fg=self.MUTED, wraplength=220, justify="left").pack(anchor="w", padx=16)
            if title == "WALLHAVEN": ttk.Entry(card, textvariable=self.wallhaven_query).pack(fill="x", padx=16, pady=12)
            elif title == "REDDIT": ttk.Entry(card, textvariable=self.reddit_subreddit).pack(fill="x", padx=16, pady=12)
            else: tk.Label(card, text="8 recent images", bg=self.PANEL, fg=self.MUTED).pack(anchor="w", padx=16, pady=12)
            ttk.Button(card, text="Fetch source", style="Accent.TButton", command=command).pack(fill="x", padx=16, pady=(0, 16))
        self.source_log = tk.Listbox(parent, height=10, bg=self.PANEL, fg=self.MUTED, relief="flat", highlightthickness=0); self.source_log.pack(fill="both", expand=True, pady=(22, 0))

    def _build_quotes(self, parent) -> None:
        parent.rowconfigure(0, weight=1); parent.columnconfigure(0, weight=1)
        canvas = tk.Canvas(parent, bg=self.BG, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.grid(row=0, column=0, sticky="nsew"); scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)
        content = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-event.delta / 120), "units"))
        parent = content
        parent.columnconfigure(0, weight=2); parent.columnconfigure(1, weight=1); parent.rowconfigure(1, weight=1)
        ttk.Label(parent, text="QUOTE STUDIO", style="Section.TLabel").grid(row=0, column=0, sticky="w"); ttk.Label(parent, text="Arrow through the controls and the preview moves immediately.", style="Muted.TLabel").grid(row=0, column=1, sticky="e")
        editor = ttk.Frame(parent); editor.grid(row=1, column=0, sticky="nsew", padx=(0, 20)); editor.columnconfigure(1, weight=1)
        ttk.Checkbutton(editor, text="Enable quote overlay", variable=self.quote_enabled).grid(row=0, column=0, columnspan=2, sticky="w", pady=(8, 12))
        ttk.Label(editor, text="Quote text").grid(row=1, column=0, sticky="nw"); self.quote_text_box = tk.Text(editor, height=6, bg=self.PANEL, fg=self.TEXT, insertbackground=self.CYAN, relief="flat", wrap="word"); self.quote_text_box.grid(row=1, column=1, sticky="ew", pady=4); self.quote_text_box.insert("1.0", self.app.quote_text)
        ttk.Label(editor, text="Author").grid(row=2, column=0, sticky="w", pady=4); self.quote_author = ttk.Entry(editor); self.quote_author.grid(row=2, column=1, sticky="ew", pady=4); self.quote_author.insert(0, self.app.quote_author)
        ttk.Label(editor, text="Choose providers\n(select one or more)").grid(row=3, column=0, sticky="nw", pady=4)
        self.quote_provider_list = tk.Listbox(editor, selectmode=tk.MULTIPLE, height=5, exportselection=False, bg=self.PANEL, fg=self.TEXT, selectbackground=self.CYAN, selectforeground=self.BG, relief="flat", highlightthickness=0)
        for label in self.quote_provider_values: self.quote_provider_list.insert(tk.END, label)
        selected_providers = set(getattr(self.app, "quote_providers", [self.app.quote_source]))
        for index, label in enumerate(self.quote_provider_values):
            if self.quote_provider_values[label] in selected_providers: self.quote_provider_list.selection_set(index)
        self.quote_provider_list.grid(row=3, column=1, sticky="ew", pady=4)
        ttk.Label(editor, text="Rotation time (seconds)").grid(row=4, column=0, sticky="w", pady=4); self._make_spinbox(editor, self.quote_rotation_interval, 10, 86400, 10).grid(row=4, column=1, sticky="w", pady=4)
        ttk.Label(editor, text="Tags (Quotable)").grid(row=5, column=0, sticky="w", pady=4); ttk.Entry(editor, textvariable=self.quote_tags).grid(row=5, column=1, sticky="ew", pady=4)
        buttons = ttk.Frame(editor); buttons.grid(row=6, column=1, sticky="ew", pady=10); ttk.Button(buttons, text="Fetch selected now", command=self._fetch_quote).pack(side="left"); ttk.Button(buttons, text="Apply to desktop now", style="Accent.TButton", command=self._apply_quote_now).pack(side="left", padx=8)
        options = ttk.LabelFrame(editor, text="Typography & placement · use arrows for live movement", padding=12); options.grid(row=7, column=0, columnspan=2, sticky="ew", pady=10)
        fields = [("Style", self.quote_style, tuple(STYLES)), ("Font size", self.quote_font_size, 14, 160, 2), ("Color", self.quote_color, "color"), ("Panel opacity", self.quote_bg_opacity, 0, 100, 5), ("Text width %", self.quote_width, 10, 95, 1), ("Horizontal %", self.quote_hpos, 0, 100, 1), ("Vertical %", self.quote_vpos, 0, 100, 1)]
        for i, field in enumerate(fields):
            r, c = divmod(i, 2); label, var = field[0], field[1]; ttk.Label(options, text=label).grid(row=r, column=c * 2, sticky="w", padx=(0, 8), pady=4)
            if len(field) == 3 and field[2] == "color": widget = self._make_color_picker(options)
            elif len(field) == 3 and field[2] is not None: widget = ttk.Combobox(options, textvariable=var, values=field[2], state="readonly")
            elif len(field) >= 5: widget = self._make_spinbox(options, var, field[2], field[3], field[4])
            else: widget = ttk.Entry(options, textvariable=var)
            widget.grid(row=r, column=c * 2 + 1, sticky="ew", padx=(0, 14), pady=4); options.columnconfigure(c * 2 + 1, weight=1)
            var.trace_add("write", lambda *_args: self._live_quote_preview())
        preview = tk.Frame(parent, bg="#050508", highlightbackground=self.MAGENTA, highlightthickness=1); preview.grid(row=1, column=1, sticky="nsew", pady=(8, 0)); self.quote_preview = tk.Label(preview, text="QUOTE PREVIEW\n\nChoose a wallpaper to preview the overlay.", bg="#050508", fg=self.MUTED, justify="center", wraplength=280); self.quote_preview.pack(fill="both", expand=True, padx=18, pady=18)

    def _make_color_picker(self, parent):
        frame = ttk.Frame(parent)
        self.color_swatch = tk.Button(frame, text="  ", width=4, bg=self.quote_color.get(), activebackground=self.quote_color.get(), relief="flat", command=self._choose_color)
        self.color_swatch.pack(side="left", padx=(0, 6))
        ttk.Button(frame, text="Choose color…", command=self._choose_color).pack(side="left")
        palette = ("#ffffff", "#eeeeee", "#00f0ff", "#00ff9f", "#ffd166", "#ff9f1c", "#ff6b6b", "#ff00aa", "#d7c6ff", "#6cff87", "#111827", "#000000")
        for color in palette:
            tk.Button(frame, width=2, height=1, bg=color, activebackground=color, relief="flat", command=lambda value=color: self._set_color(value)).pack(side="left", padx=1)
        return frame

    def _set_color(self, value: str) -> None:
        self.quote_color.set(value)
        self.color_swatch.configure(bg=value, activebackground=value)

    def _choose_color(self) -> None:
        chosen = colorchooser.askcolor(color=self.quote_color.get(), title="Choose quote color")
        if chosen and chosen[1]: self._set_color(chosen[1])

    def _make_spinbox(self, parent, variable, minimum, maximum, increment):
        widget = tk.Spinbox(parent, textvariable=variable, from_=minimum, to=maximum, increment=increment, width=8, command=self._live_quote_preview, bg=self.PANEL_2, fg=self.TEXT, insertbackground=self.CYAN, buttonbackground=self.PANEL_2, relief="flat", highlightthickness=1, highlightbackground=self.PANEL_2)
        widget.bind("<KeyRelease>", lambda _event: self._live_quote_preview()); widget.bind("<MouseWheel>", lambda _event: self._live_quote_preview())
        return widget

    def _live_quote_preview(self) -> None:
        if hasattr(self, "quote_preview"): self._render_quote_preview()

    def _build_settings(self, parent) -> None:
        ttk.Label(parent, text="SETTINGS", style="Section.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Small, explicit settings that keep the app predictable.", style="Muted.TLabel").pack(anchor="w", pady=(4, 18))
        box = ttk.LabelFrame(parent, text="Rotation", padding=16); box.pack(fill="x", pady=(0, 14))
        for i, (label, var) in enumerate((("Interval (seconds)", self.interval), ("Minimum width", self.min_width), ("Filename filter", self.pattern))):
            ttk.Label(box, text=label).grid(row=i, column=0, sticky="w", pady=7); ttk.Entry(box, textvariable=var, width=28).grid(row=i, column=1, sticky="w", padx=14, pady=7)
        ttk.Checkbutton(box, text="Prefer landscape images", variable=self.landscape).grid(row=3, column=0, columnspan=2, sticky="w", pady=7); ttk.Checkbutton(box, text="Pause rotation", variable=self.paused, command=lambda: self.app.set_paused(self.paused.get())).grid(row=4, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Button(parent, text="Save settings and rescan", style="Accent.TButton", command=self._apply_settings).pack(anchor="w")

    def _apply_settings(self) -> None:
        try:
            interval = max(30, int(self.interval.get())); min_width = max(0, int(self.min_width.get())); font_size = max(14, int(self.quote_font_size.get())); opacity = max(0, min(100, int(self.quote_bg_opacity.get()))); width = max(10, min(95, int(self.quote_width.get()))); hpos = max(0, min(100, int(self.quote_hpos.get()))); vpos = max(0, min(100, int(self.quote_vpos.get()))); quote_rotation_interval = max(10, int(self.quote_rotation_interval.get()))
            if not self._valid_color(self.quote_color.get()): raise ValueError("Color must be #RRGGBB")
            providers = [self.quote_provider_values[self.quote_provider_list.get(index)] for index in self.quote_provider_list.curselection()] or ["quotable"]
            self.app.interval = interval; self.app.min_width = min_width; self.app.landscape = self.landscape.get(); self.app.pattern = self.pattern.get().strip(); self.app.quote_enabled = self.quote_enabled.get(); self.app.quote_text = self.quote_text_box.get("1.0", "end").strip(); self.app.quote_author = self.quote_author.get().strip(); self.app.quote_providers = providers; self.app.quote_source = providers[0]; self.app.quote_rotation_interval = quote_rotation_interval; self.app.quote_tags = self.quote_tags.get().strip(); self.app.quote_font_size = font_size; self.app.quote_color = self.quote_color.get().strip(); self.app.quote_bg_opacity = opacity; self.app.quote_width = width; self.app.quote_hpos = hpos; self.app.quote_vpos = vpos; self.app.quote_style = self.quote_style.get(); self.app.save_settings(); self.app.wake_event.set(); self.app.quote_wake_event.set(); self.app.scan(); self._refresh_library(); self._render_quote_preview(); self.status.set("Settings saved · preview updated"); return True
        except ValueError as exc: messagebox.showerror("Invalid settings", f"Check the highlighted values. {exc}"); return False

    @staticmethod
    def _valid_color(value: str) -> bool:
        if len(value.strip()) != 7 or not value.strip().startswith("#"):
            return False
        try:
            int(value.strip()[1:], 16); return True
        except ValueError:
            return False

    def _render_quote_preview(self) -> None:
        source = self.app.current if self.app.current and self.app.current.exists() else None
        if source is None:
            rows = self.app.catalog.list_images(["local", "bing", "wallhaven", "reddit"], self.app.min_width, self.app.landscape, self.app.pattern)
            source = Path(rows[0]["path"]) if rows else None
        if source is None or not self.quote_text_box.get("1.0", "end").strip():
            self.quote_preview.configure(image="", text="QUOTE PREVIEW\n\nChoose a wallpaper and enter text."); return
        try:
            preview_path = self.app.paths.cache / "preview.jpg"
            render_quote(source, preview_path, self.quote_text_box.get("1.0", "end").strip(), self.quote_author.get().strip(), font_size=max(14, int(self.quote_font_size.get())), text_color=self.quote_color.get(), background_opacity=max(0, min(100, int(self.quote_bg_opacity.get()))), width_percent=max(10, min(95, int(self.quote_width.get()))), hpos=max(0, min(100, int(self.quote_hpos.get()))), vpos=max(0, min(100, int(self.quote_vpos.get()))), style=self.quote_style.get())
            image = Image.open(preview_path).convert("RGB"); image.thumbnail((420, 520)); self.quote_preview_photo = ImageTk.PhotoImage(image); self.quote_preview.configure(image=self.quote_preview_photo, text="")
        except (OSError, ValueError):
            self.quote_preview.configure(image="", text="Preview unavailable — check image and color settings.")

    def _fetch_quote(self) -> None:
        if self._apply_settings(): self.app.fetch_quote(); self.status.set("Fetching quote…")

    def _apply_quote_now(self) -> None:
        if self._apply_settings(): self.app.apply_current(); self.status.set("Quote overlay applied to the desktop")

    def _refresh_folders(self) -> None:
        self.folders.delete(0, tk.END)
        for folder in self.app.folders: self.folders.insert(tk.END, str(folder))

    def _refresh_library(self) -> None:
        if not hasattr(self, "library_list"): return
        self.library_list.delete(0, tk.END)
        rows = self._library_rows()
        for row in rows[:500]: self.library_list.insert(tk.END, f"{row['title'] or Path(row['path']).name}  ·  {row['source']}  ·  {row['width']}×{row['height']}")

    def _library_rows(self):
        return self.app.catalog.favorites() if self.favorites_only.get() else self.app.catalog.list_images(["local", "bing", "wallhaven", "reddit"], self.app.min_width, self.app.landscape, self.app.pattern)

    def _refresh_history(self) -> None:
        if not hasattr(self, "history"): return
        self.history.delete(0, tk.END)
        for row in self.app.catalog.history(12): self.history.insert(tk.END, Path(row[0]).name)

    def _add_folder(self) -> None:
        selected = filedialog.askdirectory(title="Choose a wallpaper folder")
        if selected: self.app.add_folder(Path(selected)); self._refresh_folders(); self._refresh_library()

    def _remove_folder(self) -> None:
        choice = self.folders.curselection()
        if choice: self.app.remove_folder(self.app.folders[choice[0]]); self._refresh_folders(); self._refresh_library()

    def _apply_history(self, _event=None) -> None:
        selection = self.history.curselection()
        rows = self.app.catalog.history(12)
        if selection and selection[0] < len(rows): self.app._apply(Path(rows[selection[0]][0]))

    def _apply_library(self, _event=None) -> None:
        selection = self.library_list.curselection()
        rows = self._library_rows()
        if selection and selection[0] < len(rows): self.app._apply(Path(rows[selection[0]]["path"]))

    def _update_now(self, path: str) -> None:
        p = Path(path)
        if not p.exists(): return
        try:
            image = Image.open(p).convert("RGB"); image.thumbnail((760, 560)); self.preview_photo = ImageTk.PhotoImage(image); self.preview_label.configure(image=self.preview_photo, text="")
        except Exception: return
        row = self.app.catalog.image(str(p)); source = row["source"] if row else "local"; title = (row["title"] if row else "") or p.name; origin = (row["origin_url"] if row else "") or "Local file"
        self.now_title.configure(text=title); self.now_meta.configure(text=f"{source.upper()}  ·  {p.name}\n{origin}")
        self._refresh_history(); self._refresh_library()

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.app.events.get_nowait(); self.status.set(str(value))
                if kind == "current": self._update_now(str(value)); self._render_quote_preview()
                elif kind == "quote": self.quote_text_box.delete("1.0", "end"); self.quote_text_box.insert("1.0", self.app.quote_text); self.quote_author.delete(0, "end"); self.quote_author.insert(0, self.app.quote_author); self._render_quote_preview()
                elif kind == "source_complete": self._refresh_library(); self._refresh_history(); info = value if isinstance(value, dict) else {}; text = f"{info.get('label', 'Source')} complete · {info.get('completed', 0)} added · {info.get('skipped', 0)} skipped"; self.status.set(text); self.source_log.insert(0, text); self.status_dot.configure(fg=self.GREEN)
                elif kind == "error": self.status_dot.configure(fg=self.MAGENTA); self.source_log.insert(0, f"Error: {value}")
                elif kind == "status": self.status_dot.configure(fg=self.GREEN)
        except queue.Empty: pass
        self.root.after(250, self._drain_events)

    def _handle_command(self, command: str | None) -> None:
        if command == "show": self.show()
        elif command == "next": self.app.next()
        elif command == "previous": self.app.previous()
        elif command == "pause": self.app.set_paused(True); self.paused.set(True)
        elif command == "resume": self.app.set_paused(False); self.paused.set(False)
        elif command == "quit": self.quit()

    def hide(self) -> None:
        self.root.withdraw(); self.status.set("Running in background · relaunch the app to restore")

    def show(self) -> None:
        self.root.deiconify(); self.root.lift(); self.root.focus_force()

    def quit(self) -> None:
        self.ipc.close(); self.root.destroy()

    def run(self) -> None:
        self.app.start()
        if self.app.current: self._update_now(str(self.app.current))
        self.root.mainloop()
