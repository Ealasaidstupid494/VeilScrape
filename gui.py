import os
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from scraper import scrape, check_tor_running, set_stop, clear_stop

CONFIG_FILE = os.path.expanduser("~/.veilscrape_config.json")

# ── Themes ────────────────────────────────────────────────────────────────────
THEMES = {
    "light": {
        "BG":        "#f0f0f0",
        "TOOLBAR":   "#d6e4f0",
        "TBTN":      "#e8f0f8",
        "HDR_BG":    "#c8daea",
        "HDR_FG":    "#003366",
        "ROW_ODD":   "#ffffff",
        "ROW_EVEN":  "#eef4fb",
        "ROW_HL":    "#fffacd",
        "BORDER":    "#a0b8cc",
        "ACCENT":    "#003366",
        "PANEL":     "#e8f0f8",
        "INPUT_BG":  "#ffffff",
        "INPUT_FG":  "#000000",
        "ERR":       "#cc0000",
        "OK":        "#006600",
        "WARN":      "#996600",
        "INFO":      "#003399",
        "LOG_BG":    "#ffffff",
        "LOG_FG":    "#000000",
        "STATUS_BG": "#c8daea",
        "WHITE":     "#ffffff",
        "MUTED":     "#666666",
    },
    "dark": {
        "BG":        "#0a0a0a",
        "TOOLBAR":   "#111111",
        "TBTN":      "#1a1a1a",
        "HDR_BG":    "#0d0d0d",
        "HDR_FG":    "#4fc3f7",
        "ROW_ODD":   "#0f0f0f",
        "ROW_EVEN":  "#141414",
        "ROW_HL":    "#1a1a00",
        "BORDER":    "#2a2a2a",
        "ACCENT":    "#4fc3f7",
        "PANEL":     "#0d0d0d",
        "INPUT_BG":  "#050505",
        "INPUT_FG":  "#00e5ff",
        "ERR":       "#ff4444",
        "OK":        "#00e676",
        "WARN":      "#ffcc00",
        "INFO":      "#4fc3f7",
        "LOG_BG":    "#020202",
        "LOG_FG":    "#00e676",
        "STATUS_BG": "#0d0d0d",
        "WHITE":     "#e0e0e0",
        "MUTED":     "#555555",
    }
}

FM      = "Arial"
FM_MONO = "Courier New"
F_TITLE = (FM, 10, "bold")
F_HDR   = (FM, 9, "bold")
F_ENTRY = (FM, 9)
F_BTN   = (FM, 8, "bold")
F_LOG   = (FM_MONO, 9)
F_TINY  = (FM, 8)
F_STAT  = (FM, 8)


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class VeilScrapeApp:
    def __init__(self, root):
        self.root       = root
        self.root.title("VeilScrape")
        self.root.geometry("1040x740")
        self.root.resizable(True, True)
        self.config     = load_config()
        self._scraping  = False
        self._spin_job  = None
        self._spin_idx  = 0
        self._log_rows  = []
        self._theme_name = self.config.get("theme", "light")
        self.T          = THEMES[self._theme_name]
        self._build()
        self.root.after(400, self._check_tor)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    @property
    def t(self):
        return self.T

    # ─────────────────────────────────────────── BUILD

    def _build(self):
        self.root.configure(bg=self.t["BG"])
        self._title_bar()
        self._toolbar()
        self._rule()
        self._column_bar()
        self._rule()
        self._table_area()
        self._rule()
        self._status_bar()

    def _rule(self):
        tk.Frame(self.root, bg=self.t["BORDER"], height=1).pack(fill="x")

    # ── Title bar

    def _title_bar(self):
        self._tbar_frame = tk.Frame(self.root, bg=self.t["HDR_BG"], height=34)
        self._tbar_frame.pack(fill="x")
        self._tbar_frame.pack_propagate(False)
        self._tbar_title = tk.Label(
            self._tbar_frame,
            text="  VeilScrape  |  Tor .onion Data Extractor  |  suadatbiniqbal",
            font=F_TITLE, bg=self.t["HDR_BG"], fg=self.t["ACCENT"])
        self._tbar_title.pack(side="left", padx=8, pady=7)
        self.tor_lbl = tk.Label(
            self._tbar_frame, text="[TOR: CHECKING]",
            font=F_STAT, bg=self.t["HDR_BG"], fg=self.t["MUTED"])
        self.tor_lbl.pack(side="right", padx=14)

    def _check_tor(self):
        if check_tor_running():
            self.tor_lbl.config(text="[TOR: ACTIVE]",  fg=self.t["OK"])
        else:
            self.tor_lbl.config(
                text="[TOR: OFFLINE -- sudo service tor start]",
                fg=self.t["ERR"])

    # ── Toolbar

    def _toolbar(self):
        self._tb_frame = tk.Frame(self.root, bg=self.t["TOOLBAR"], height=38)
        self._tb_frame.pack(fill="x")
        self._tb_frame.pack_propagate(False)

        def tbtn(text, cmd, primary=False):
            bg = self.t["ACCENT"] if primary else self.t["TBTN"]
            fg = self.t["BG"]     if primary else self.t["ACCENT"]
            b  = tk.Button(self._tb_frame, text=text, font=F_BTN,
                           bg=bg, fg=fg, relief="raised", bd=1,
                           cursor="hand2", activebackground=self.t["HDR_BG"],
                           command=cmd, padx=10, pady=3)
            b.pack(side="left", padx=2, pady=4)
            return b

        self.run_btn  = tbtn("  Run Scrape  ",  self._start, primary=True)
        self.stop_btn = tbtn("  Stop  ",        self._stop)
        self.stop_btn.config(state="disabled",
                             bg=self.t["TBTN"], fg=self.t["MUTED"])

        tk.Frame(self._tb_frame, bg=self.t["BORDER"],
                 width=1).pack(side="left", fill="y", padx=6, pady=6)

        tbtn("  Clear  ",       self._clear_log)
        tbtn("  Open Folder  ", self._open_folder)
        tbtn("  Recheck Tor  ", self._check_tor)

        tk.Frame(self._tb_frame, bg=self.t["BORDER"],
                 width=1).pack(side="left", fill="y", padx=6, pady=6)

        # Dark mode toggle
        self._dm_btn = tk.Button(
            self._tb_frame,
            text="Dark Mode" if self._theme_name == "light" else "Light Mode",
            font=F_BTN, bg=self.t["TBTN"], fg=self.t["ACCENT"],
            relief="raised", bd=1, cursor="hand2",
            activebackground=self.t["HDR_BG"],
            command=self._toggle_theme,
            padx=10, pady=3)
        self._dm_btn.pack(side="left", padx=2, pady=4)

        self.spin_lbl = tk.Label(self._tb_frame, text="",
                                 font=F_STAT, bg=self.t["TOOLBAR"],
                                 fg=self.t["ACCENT"], width=14)
        self.spin_lbl.pack(side="left", padx=6)

        self.status_lbl = tk.Label(self._tb_frame, text="Ready",
                                   font=F_STAT, bg=self.t["TOOLBAR"],
                                   fg=self.t["ACCENT"])
        self.status_lbl.pack(side="left", padx=6)

    # ── Input / filter bar

    def _column_bar(self):
        self._col_frame = tk.Frame(self.root, bg=self.t["PANEL"])
        self._col_frame.pack(fill="x")

        row1 = tk.Frame(self._col_frame, bg=self.t["PANEL"])
        row1.pack(fill="x", padx=10, pady=(7, 2))

        tk.Label(row1, text="Target URL:", font=F_HDR,
                 bg=self.t["PANEL"], fg=self.t["ACCENT"],
                 width=13, anchor="w").pack(side="left")
        self.url_var = tk.StringVar(
            value=self.config.get("last_url", "http://"))
        self._url_entry = tk.Entry(
            row1, textvariable=self.url_var,
            font=F_ENTRY, bg=self.t["INPUT_BG"], fg=self.t["INPUT_FG"],
            insertbackground=self.t["ACCENT"],
            relief="sunken", bd=1, width=52)
        self._url_entry.pack(side="left", ipady=4, padx=(0, 16))
        self._url_entry.bind("<FocusIn>",
            lambda e: self._url_entry.selection_range(0, "end"))

        tk.Label(row1, text="Output Folder:", font=F_HDR,
                 bg=self.t["PANEL"], fg=self.t["ACCENT"],
                 anchor="w").pack(side="left")
        self.folder_var = tk.StringVar(
            value=self.config.get("last_folder",
                                  os.path.expanduser("~/VeilScrape_output")))
        self._folder_entry = tk.Entry(
            row1, textvariable=self.folder_var,
            font=F_ENTRY, bg=self.t["INPUT_BG"], fg=self.t["INPUT_FG"],
            insertbackground=self.t["ACCENT"],
            relief="sunken", bd=1, width=26)
        self._folder_entry.pack(side="left", ipady=4, padx=(4, 4))
        tk.Button(row1, text="...", font=F_BTN,
                  bg=self.t["TBTN"], fg=self.t["ACCENT"],
                  relief="raised", bd=1, cursor="hand2",
                  command=self._browse,
                  padx=6, pady=2).pack(side="left")

        row2 = tk.Frame(self._col_frame, bg=self.t["PANEL"])
        row2.pack(fill="x", padx=10, pady=(2, 7))
        tk.Label(row2, text="Extract:", font=F_HDR,
                 bg=self.t["PANEL"], fg=self.t["ACCENT"],
                 width=13, anchor="w").pack(side="left")

        self.opts   = {}
        self._cbs   = []
        items = [("text","Text"),("links","Links"),("images","Images"),
                 ("videos","Videos"),("audio","Audio"),
                 ("files","Files"),("emails","Emails")]
        for key, lbl in items:
            v  = tk.BooleanVar(value=self.config.get(f"opt_{key}", True))
            self.opts[key] = v
            cb = tk.Checkbutton(
                row2, text=lbl, variable=v,
                font=F_TINY,
                bg=self.t["PANEL"], fg=self.t["ACCENT"],
                selectcolor=self.t["INPUT_BG"],
                activebackground=self.t["PANEL"],
                relief="flat", cursor="hand2",
                command=lambda k=key, val=v: self._save_opt(k, val))
            cb.pack(side="left", padx=8)
            self._cbs.append(cb)

    def _save_opt(self, key, var):
        self.config[f"opt_{key}"] = var.get()
        save_config(self.config)

    # ── Table

    def _table_area(self):
        self._table_outer = tk.Frame(self.root, bg=self.t["BG"])
        self._table_outer.pack(fill="both", expand=True)

        self._hdr_frame = tk.Frame(self._table_outer, bg=self.t["HDR_BG"])
        self._hdr_frame.pack(fill="x")
        for name, w in [("Time", 8), ("Level", 9), ("Message", 80)]:
            tk.Label(self._hdr_frame, text=name, font=F_HDR,
                     bg=self.t["HDR_BG"], fg=self.t["HDR_FG"],
                     width=w, anchor="w", padx=6, pady=4).pack(side="left")
            tk.Frame(self._hdr_frame, bg=self.t["BORDER"],
                     width=1).pack(side="left", fill="y", pady=2)

        body_wrap = tk.Frame(self._table_outer, bg=self.t["BG"])
        body_wrap.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(body_wrap, bg=self.t["ROW_ODD"],
                                highlightthickness=0)
        self._vsb   = tk.Scrollbar(body_wrap, orient="vertical",
                                   command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._vsb.set)
        self._vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.table_frame = tk.Frame(self.canvas, bg=self.t["ROW_ODD"])
        self._cw = self.canvas.create_window(
            (0, 0), window=self.table_frame, anchor="nw")
        self.table_frame.bind("<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
            lambda e: self.canvas.itemconfig(self._cw, width=e.width))
        self.canvas.bind_all("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(-1*(e.delta//120), "units"))

    def _add_row(self, ts, level, msg):
        idx = len(self._log_rows)
        bg  = self.t["ROW_HL"] if level in ("ERROR","DONE") \
              else (self.t["ROW_ODD"] if idx % 2 == 0 else self.t["ROW_EVEN"])
        fg_map = {
            "ERROR":   self.t["ERR"],
            "DONE":    self.t["OK"],
            "OK":      self.t["OK"],
            "WARN":    self.t["WARN"],
            "INFO":    self.t["INFO"],
            "SAVED":   self.t["WHITE"],
            "STOPPED": self.t["ERR"],
        }
        fg = fg_map.get(level, self.t["WHITE"])

        row = tk.Frame(self.table_frame, bg=bg)
        row.pack(fill="x")
        tk.Label(row, text=ts,    font=F_LOG, bg=bg, fg=fg,
                 width=8,  anchor="w", padx=6, pady=2).pack(side="left")
        tk.Frame(row, bg=self.t["BORDER"], width=1).pack(
            side="left", fill="y", pady=1)
        tk.Label(row, text=level, font=F_LOG, bg=bg, fg=fg,
                 width=9,  anchor="w", padx=6).pack(side="left")
        tk.Frame(row, bg=self.t["BORDER"], width=1).pack(
            side="left", fill="y", pady=1)
        tk.Label(row, text=msg,   font=F_LOG, bg=bg, fg=fg,
                 anchor="w", padx=6, wraplength=720,
                 justify="left").pack(side="left", fill="x", expand=True)
        self._log_rows.append(row)
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    # ── Status bar

    def _status_bar(self):
        self._sb_frame = tk.Frame(self.root, bg=self.t["STATUS_BG"], height=22)
        self._sb_frame.pack(fill="x", side="bottom")
        self._sb_frame.pack_propagate(False)
        self._sb_lbl = tk.Label(
            self._sb_frame,
            text="  VeilScrape  |  Educational use only  |  suadatbiniqbal",
            font=F_STAT, bg=self.t["STATUS_BG"], fg=self.t["ACCENT"], anchor="w")
        self._sb_lbl.pack(side="left", padx=8)
        self._row_lbl = tk.Label(
            self._sb_frame, text="Rows: 0",
            font=F_STAT, bg=self.t["STATUS_BG"], fg=self.t["ACCENT"])
        self._row_lbl.pack(side="right", padx=14)

    # ─────────────────────────────────────────── THEME

    def _toggle_theme(self):
        self._theme_name = "dark" if self._theme_name == "light" else "light"
        self.T = THEMES[self._theme_name]
        self.config["theme"] = self._theme_name
        save_config(self.config)
        # Destroy and rebuild UI
        for widget in self.root.winfo_children():
            widget.destroy()
        self._log_rows = []
        self._build()
        self.root.after(300, self._check_tor)

    # ─────────────────────────────────────────── ACTIONS

    def _browse(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.folder_var.set(folder)
            self.config["last_folder"] = folder
            save_config(self.config)

    def _log(self, msg):
        import time as _t
        ts = _t.strftime("%H:%M:%S")
        m  = msg.upper()
        if   "[ERROR]"   in m: level = "ERROR"
        elif "[DONE]"    in m: level = "DONE"
        elif "[OK]"      in m: level = "OK"
        elif "[WARN]"    in m: level = "WARN"
        elif "[INFO]"    in m or "[CHECK]" in m \
          or "[FIX]"     in m or "[TIP]"   in m \
          or "[FOLDER]"  in m: level = "INFO"
        elif "[SAVED]"   in m: level = "SAVED"
        elif "[STOPPED]" in m: level = "STOPPED"
        else:                   level = "LOG"
        self._add_row(ts, level, msg.strip())
        self._row_lbl.config(text=f"Rows: {len(self._log_rows)}")

    def _clear_log(self):
        for row in self._log_rows:
            row.destroy()
        self._log_rows.clear()
        self._row_lbl.config(text="Rows: 0")

    def _open_folder(self):
        folder = self.folder_var.get().strip()
        if os.path.exists(folder):
            os.system(f'xdg-open "{folder}"')
        else:
            messagebox.showinfo("Not Found", "Run a scrape first.")

    def _start(self):
        url    = self.url_var.get().strip()
        folder = self.folder_var.get().strip()
        if not url or url == "http://":
            messagebox.showerror("Error", "Enter a .onion URL.")
            return
        if not folder:
            messagebox.showerror("Error", "Select an output folder.")
            return
        selected = {k: v.get() for k, v in self.opts.items()}
        if not any(selected.values()):
            messagebox.showerror("Error", "Select at least one data type.")
            return
        self.config["last_url"]    = url
        self.config["last_folder"] = folder
        save_config(self.config)
        self._scraping = True
        self.run_btn.config(state="disabled", text="Running...",
                            bg=self.t["MUTED"])
        self.stop_btn.config(state="normal",  bg=self.t["ERR"],
                             fg=self.t["WHITE"])
        self.status_lbl.config(text="Scraping...", fg=self.t["ERR"])
        self._start_spinner()
        self._log(f"[START]  {url}")
        self._log(f"[START]  Extract: "
                  f"{', '.join(k.upper() for k,v in selected.items() if v)}")
        threading.Thread(target=self._run,
                         args=(url, folder, selected),
                         daemon=True).start()

    def _stop(self):
        set_stop()
        self._log("[STOPPED] Cancelled by user.")
        self.stop_btn.config(state="disabled",
                             bg=self.t["TBTN"], fg=self.t["MUTED"])
        self.status_lbl.config(text="Stopping...", fg=self.t["WARN"])

    def _run(self, url, folder, options):
        scrape(url, folder, options=options, log_callback=self._log)
        self._scraping = False
        self._stop_spinner()
        self.run_btn.config(state="normal", text="  Run Scrape  ",
                            bg=self.t["ACCENT"], fg=self.t["BG"])
        self.stop_btn.config(state="disabled",
                             bg=self.t["TBTN"], fg=self.t["MUTED"])
        self.status_lbl.config(text="Ready", fg=self.t["ACCENT"])
        self._check_tor()

    # ── Spinner

    _FRAMES = ["[      ]","[=     ]","[==    ]","[===   ]",
               "[====  ]","[===== ]","[======]","[ =====]",
               "[  ====]","[   ===]","[    ==]","[     =]"]

    def _start_spinner(self):
        self._spin_idx = 0
        self._tick_spinner()

    def _tick_spinner(self):
        if not self._scraping:
            self.spin_lbl.config(text="")
            return
        self.spin_lbl.config(text=self._FRAMES[self._spin_idx % len(self._FRAMES)])
        self._spin_idx += 1
        self._spin_job = self.root.after(90, self._tick_spinner)

    def _stop_spinner(self):
        self.spin_lbl.config(text="")
        if self._spin_job:
            self.root.after_cancel(self._spin_job)

    def _on_close(self):
        if self._scraping:
            if messagebox.askyesno("Quit", "Scrape is running. Stop and quit?"):
                set_stop()
                self.root.destroy()
        else:
            self.root.destroy()


def launch():
    root = tk.Tk()
    VeilScrapeApp(root)
    root.mainloop()