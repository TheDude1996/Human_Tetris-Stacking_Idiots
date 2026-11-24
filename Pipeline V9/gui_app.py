"""
gui_app.py  (Pipeline V9)
---------------------------
Grafische Oberflaeche fuer ply_head_to_lowpoly_glb.py: wandelt PLY-Kopfscans in
polygonreduzierte GLB-Koepfe fuer Human Tetris (Unity) um. Laesst dich:
  - ReconstructMe per Knopf starten (Pfad zur .exe wird wie bei Blender gewaehlt
    und gespeichert); der Scan wird in ReconstructMe per Hand als .ply in den
    Input-Ordner gespeichert und hier automatisch erkannt
  - Input-Ordner (Rohscans, .ply) und Output-Ordner (Scan-Ordner des Spiels) waehlen
  - Den Pfad zu blender.exe einmalig hinterlegen (wird gespeichert)
  - Den Spielernamen eintragen (landet als name.txt im Spieler-Ordner)
  - Optionen setzen (Ziel-Dreiecke, Normal-Map, Spiegeln, Kantenlaenge, ...)
  - Den Lauf per Klick starten und live im Log-Fenster mitverfolgen

Das einzige Blender-Skript ist ply_head_to_lowpoly_glb.py; es muss im selben
Ordner wie die .exe (bzw. diese Datei) liegen.

Pro Lauf wird eine .ply verarbeitet: die in der Auswahlliste "Datei im
Input-Ordner" gewaehlte. Standard ist die neueste (nach Aenderungsdatum); ein
neuer Scan wird automatisch ausgewaehlt. Sie landet in einem eigenen
Unterordner im Output-Ordner, benannt "Playermodell_<Nummer>" (z.B.
Playermodell_0007). Darin liegen immer PlayerHead.glb (Textur eingebettet),
PlayerHead.png (und PlayerHead_normal.png mit Normal-Map) sowie name.txt.
Die Nummer steht in .pipeline_counter.json direkt im Output-Ordner und bleibt
daher auch nach einem Neustart der App erhalten -- die Zaehlung faengt nie
wieder bei 0 an.

Spielername: name.txt = erste Zeile ist der Name, UTF-8. Das Spiel zeigt ihn im
Spielermenue und in der Bestenliste an. Das Feld "Spielername" wird mit dem
Dateinamen der gewaehlten .ply vorbelegt ("Max_Mustermann.ply" -> "Max Mustermann")
und kann vor dem Start geaendert werden. Wurde die Datei schon verarbeitet, fragt
die App nach. Mit "Namen nachtragen..." bekommt ein vorhandener Spieler-Ordner
einen Namen.

Im Hintergrund laeuft pro Datei:

    blender.exe --background --python ply_head_to_lowpoly_glb.py -- --input <datei> --output <ordner> --rename PlayerHead [...]

Design: Farben und Karten wie Website und Spiel (dunkel, Neon-Gruen/Cyan/Pink).

Exe bauen:  python -m PyInstaller --noconfirm PipelineTool.spec
"""

import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

APP_TITLE = "Human Tetris – Scan zu Unity Pipeline V9"
CONFIG_FILENAME = "pipeline_gui_config.json"

# Liegt neben der .exe (bzw. neben dem Skript im Entwicklungsmodus)
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(BASE_DIR, CONFIG_FILENAME)

# Icon: in der .exe eingebettet (PyInstaller entpackt es nach sys._MEIPASS), sonst neben dieser Datei
ICON_NAME = "pipeline.ico"
ICON_PATH = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), ICON_NAME)

SCRIPT_NAME = "ply_head_to_lowpoly_glb.py"
SCRIPT_PATH = os.path.join(BASE_DIR, SCRIPT_NAME)

ALLOWED_INPUT_EXTENSIONS = (".ply",)  # das Skript liest nur PLY (mit Vertex-Colors)
OUTPUT_FILE_NAME = "PlayerHead"       # -> PlayerHead.glb / .png / _normal.png

# Diese Datei liegt direkt im gewaehlten Output-Ordner und merkt sich die
# naechste zu vergebende laufende Nummer. Da sie an den Ordner gebunden ist
# (nicht an die App), bleibt die Zaehlung auch nach einem Neustart der
# Anwendung oder einem Wechsel des Output-Ordners korrekt erhalten.
COUNTER_FILENAME = ".pipeline_counter.json"

# Name des Spielers im Spieler-Ordner (liest das Spiel, siehe PlayerDataManager.GetPlayerName)
NAME_FILENAME = "name.txt"
MAX_NAME_LENGTH = 32


# ----------------------------------------------------------------------
# Hilfsfunktionen
# ----------------------------------------------------------------------
def input_files(input_path):
    """Alle .ply im Input-Ordner, neueste zuerst (nach Aenderungsdatum).
    Ist direkt eine Datei angegeben, nur diese."""
    if os.path.isfile(input_path):
        return [input_path] if input_path.lower().endswith(ALLOWED_INPUT_EXTENSIONS) else []
    if not os.path.isdir(input_path):
        return []
    try:
        files = [
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.lower().endswith(ALLOWED_INPUT_EXTENSIONS)
        ]
        return sorted(files, key=os.path.getmtime, reverse=True)
    except OSError:
        return []


def newest_input_file(input_path):
    """Die neueste .ply im Input-Ordner, oder None."""
    files = input_files(input_path)
    return files[0] if files else None


def file_label(filepath, newest=False):
    """Anzeige in der Auswahlliste: "Max_Mustermann.ply  (23.11. 11:15)  [neueste]"."""
    try:
        stamp = time.strftime("%d.%m. %H:%M", time.localtime(os.path.getmtime(filepath)))
    except OSError:
        stamp = "?"
    return f"{os.path.basename(filepath)}  ({stamp})" + ("  [neueste]" if newest else "")


def name_from_file(filepath):
    """Vorschlag fuer den Spielernamen aus dem Dateinamen: "Max_Mustermann.ply" -> "Max Mustermann"."""
    stem = os.path.splitext(os.path.basename(filepath))[0]
    return clean_player_name(stem.replace("_", " "))


def _counter_path(output_root):
    return os.path.join(output_root, COUNTER_FILENAME)


def _load_next_counter(output_root):
    path = _counter_path(output_root)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return int(json.load(f).get("next", 1))
        except (OSError, json.JSONDecodeError, ValueError):
            pass
    return 1


def _save_next_counter(output_root, next_value):
    try:
        with open(_counter_path(output_root), "w", encoding="utf-8") as f:
            json.dump({"next": next_value}, f)
    except OSError:
        pass


def take_next_number(output_root):
    """Liest die naechste freie laufende Nummer fuer diesen Output-Ordner,
    erhoeht und speichert sie sofort -- dadurch bleibt die Nummerierung auch
    bei einem Absturz oder Neustart der App luecken- und ueberschneidungsfrei."""
    current = _load_next_counter(output_root)
    _save_next_counter(output_root, current + 1)
    return current


def clean_player_name(name):
    """Nur die erste Zeile, Leerraum zusammengefasst, hoechstens MAX_NAME_LENGTH Zeichen."""
    if not name or not name.strip():
        return ""
    first_line = name.strip().splitlines()[0]
    return " ".join(first_line.split())[:MAX_NAME_LENGTH].strip()


def write_player_name(player_dir, name):
    """Schreibt name.txt (UTF-8 ohne BOM). Leerer Name = vorhandene name.txt bleibt unveraendert.
    Gibt den geschriebenen Namen zurueck (oder "")."""
    name = clean_player_name(name)
    if not name:
        return ""
    path = os.path.join(player_dir, NAME_FILENAME)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(name + "\n")
    os.replace(tmp, path)  # atomar, das Spiel liest nie eine halbe Datei
    return name


def read_player_name(player_dir):
    try:
        with open(os.path.join(player_dir, NAME_FILENAME), "r", encoding="utf-8-sig") as f:
            return clean_player_name(f.readline())
    except OSError:
        return ""


def load_config():
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(data):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


# ----------------------------------------------------------------------
# Design (Farben wie Website und Spiel)
# ----------------------------------------------------------------------
BG = "#0A0B1A"        # Hintergrund
CARD = "#12142A"      # Karten
BORDER = "#2A2D4D"    # Rahmen
GREEN = "#A6FF00"     # Akzent Gruen
CYAN = "#4DE8FF"      # Akzent Cyan
PINK = "#FF1493"      # Akzent Pink
TEXT = "#E8EAF6"      # Text
MUTED = "#8A8FB8"     # gedaempfter Grautext
ERROR = "#FF4D6D"

FONT = "Segoe UI" if os.name == "nt" else "DejaVu Sans"
MONO = "Consolas" if os.name == "nt" else "DejaVu Sans Mono"


def open_in_explorer(path):
    """Ordner im Datei-Explorer oeffnen."""
    if os.name == "nt":
        os.startfile(path)  # noqa: S606 - nur lokale Ordner aus der eigenen Oberflaeche
    else:
        subprocess.Popen(["xdg-open", path])


class ScrollFrame(tk.Frame):
    """Senkrecht scrollbarer Bereich, damit die Oberflaeche auch auf kleinen Bildschirmen passt."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        # Mausrad nur, solange die Maus ueber diesem Bereich ist
        self.bind("<Enter>", lambda e: self.bind_all("<MouseWheel>", self._on_wheel))
        self.bind("<Leave>", lambda e: self.unbind_all("<MouseWheel>"))

    def _on_wheel(self, event):
        if isinstance(event.widget, tk.Text):
            return  # im Log selbst scrollen
        self.canvas.yview_scroll(int(-event.delta / 120) or (-1 if event.delta > 0 else 1), "units")


# ----------------------------------------------------------------------
# Oberflaeche
# ----------------------------------------------------------------------
class PipelineGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self._apply_icon()
        self.geometry("860x860")
        self.minsize(740, 560)
        self.configure(bg=BG)
        self._apply_style()

        c = load_config()
        self.blender_path_var = tk.StringVar(value=c.get("blender_path", ""))
        self.reconstructme_path_var = tk.StringVar(value=c.get("reconstructme_path", ""))
        self.input_var = tk.StringVar(value=c.get("input_path", ""))
        self.output_var = tk.StringVar(value=c.get("output_path", ""))
        self.player_name_var = tk.StringVar()  # bewusst nicht gespeichert: gilt nur fuer den naechsten Lauf

        # Standardwerte = so wurden die Low-Poly-Koepfe im Spiel erzeugt (5000 Dreiecke, Farbe + Normal-Map)
        self.target_faces_var = tk.StringVar(value=str(c.get("target_faces", "5000")))
        self.bake_normals_var = tk.BooleanVar(value=c.get("bake_normals", True))
        self.mirror_var = tk.BooleanVar(value=c.get("mirror", False))
        self.skip_cleanup_var = tk.BooleanVar(value=c.get("skip_cleanup", False))
        self.no_fill_holes_var = tk.BooleanVar(value=c.get("no_fill_holes", False))
        self.no_bake_var = tk.BooleanVar(value=c.get("no_bake", False))
        self.use_edge_length_var = tk.BooleanVar(value=c.get("use_edge_length", False))
        self.edge_length_var = tk.DoubleVar(value=c.get("edge_length", 0.3))
        self.bake_size_var = tk.StringVar(value=str(c.get("bake_size", "2048")))
        self.margin_var = tk.StringVar(value=str(c.get("margin", "8")))

        self.last_processed = c.get("last_processed", "")  # "<pfad>|<mtime>" der zuletzt verarbeiteten Datei
        self.newest_file = None    # neueste .ply beim letzten Pruefen (erkennt neue Scans)
        self.selected_file = None  # in der Auswahlliste gewaehlte .ply (wird verarbeitet)
        self.known_files = []      # Inhalt der Auswahlliste beim letzten Pruefen
        self.file_paths = {}       # Anzeige-Text -> Pfad
        self.file_choice_var = tk.StringVar()
        self._first_refresh = True  # beim Start ist die neueste Datei kein "neuer Scan"

        self.process = None
        self.reme_process = None   # gestartetes ReconstructMe
        self._build_ui()
        self.input_var.trace_add("write", lambda *_: self._update_scan_card())
        self.reconstructme_path_var.trace_add("write", lambda *_: self._update_scan_card())
        self.blender_path_var.trace_add("write", lambda *_: self._update_program_labels())
        self._update_scan_card()
        self._update_program_labels()
        self._watch_input()

    def _apply_icon(self):
        """pipeline.ico fuer Titelleiste, Taskleiste und alle Dialoge (default= gilt fuer jedes Fenster)."""
        try:
            self.iconbitmap(default=ICON_PATH)
        except tk.TclError:
            pass  # Icon fehlt: Standard-Icon, App laeuft trotzdem

    # ------------------------------------------------------------------
    # Design
    # ------------------------------------------------------------------
    def _apply_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")  # der einzige Standard-Stil, der eigene Farben vollstaendig zulaesst
        base = (FONT, 10)
        s.configure(".", background=CARD, foreground=TEXT, font=base, bordercolor=BORDER,
                    lightcolor=BORDER, darkcolor=BORDER, troughcolor=BG, focuscolor=CYAN,
                    fieldbackground=BG, insertcolor=TEXT, selectbackground=CYAN, selectforeground=BG)
        s.configure("TFrame", background=CARD)
        s.configure("TLabel", background=CARD, foreground=TEXT)
        s.configure("Muted.TLabel", foreground=MUTED, font=(FONT, 9))
        s.configure("Path.TLabel", foreground=CYAN, font=(MONO, 9))
        s.configure("Ok.TLabel", foreground=GREEN, font=(FONT, 9, "bold"))
        s.configure("Bad.TLabel", foreground=ERROR, font=(FONT, 9, "bold"))
        s.configure("Status.TLabel", background=BG, foreground=MUTED, font=(FONT, 10, "bold"))

        s.configure("TEntry", fieldbackground=BG, foreground=TEXT, padding=5)
        s.map("TEntry", bordercolor=[("focus", CYAN)], lightcolor=[("focus", CYAN)])

        s.configure("TButton", background=BORDER, foreground=TEXT, padding=(12, 6),
                    font=(FONT, 9, "bold"), borderwidth=0)
        s.map("TButton", background=[("disabled", CARD), ("pressed", CYAN), ("active", "#3A3E66")],
              foreground=[("disabled", MUTED), ("pressed", BG)])
        s.configure("Cyan.TButton", background=CYAN, foreground=BG, padding=(14, 8), font=(FONT, 10, "bold"))
        s.map("Cyan.TButton", background=[("disabled", BORDER), ("active", "#8FF2FF")],
              foreground=[("disabled", MUTED)])
        s.configure("Start.TButton", background=GREEN, foreground=BG, padding=(26, 12), font=(FONT, 13, "bold"))
        s.map("Start.TButton", background=[("disabled", BORDER), ("active", "#C6FF4D")],
              foreground=[("disabled", MUTED)])

        s.configure("TCheckbutton", background=CARD, foreground=TEXT, indicatorbackground=BG,
                    indicatorforeground=GREEN, indicatorrelief="flat")
        s.map("TCheckbutton", background=[("active", CARD)],
              indicatorbackground=[("selected", BG), ("active", BORDER)])

        s.configure("TCombobox", fieldbackground=BG, background=BORDER, foreground=TEXT,
                    arrowcolor=CYAN, padding=4)
        s.map("TCombobox", fieldbackground=[("readonly", BG)], foreground=[("readonly", TEXT)],
              selectbackground=[("readonly", BG)], selectforeground=[("readonly", TEXT)])
        self.option_add("*TCombobox*Listbox.background", CARD)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", CYAN)
        self.option_add("*TCombobox*Listbox.selectForeground", BG)
        self.option_add("*TCombobox*Listbox.font", base)

        s.configure("Horizontal.TScale", background=CYAN, troughcolor=BG)
        s.configure("Vertical.TScrollbar", background=BORDER, troughcolor=BG, arrowcolor=CYAN,
                    bordercolor=BG, lightcolor=BORDER, darkcolor=BORDER, gripcount=0)
        s.map("Vertical.TScrollbar", background=[("disabled", BG), ("active", CYAN)],
              arrowcolor=[("disabled", BORDER)])

        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        s.configure("TNotebook.Tab", background=BG, foreground=MUTED, padding=(18, 8),
                    font=(FONT, 10, "bold"), borderwidth=0)
        s.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", GREEN)])

    def _card(self, parent, number, title, accent):
        """Nummerierte Karte wie auf der Website: dunkle Flaeche, feiner Rahmen, farbiger Kopf."""
        outer = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        outer.pack(fill="x", padx=14, pady=7)
        head = tk.Frame(outer, bg=CARD)
        head.pack(fill="x", padx=14, pady=(12, 4))
        if number:
            tk.Label(head, text=number, bg=accent, fg=BG, font=(FONT, 10, "bold"), padx=7).pack(side="left")
        tk.Label(head, text=title.upper(), bg=CARD, fg=accent,
                 font=(FONT, 11, "bold")).pack(side="left", padx=(10 if number else 0, 0))
        body = tk.Frame(outer, bg=CARD)
        body.pack(fill="x", padx=14, pady=(2, 12))
        return body

    # ------------------------------------------------------------------
    # Aufbau
    # ------------------------------------------------------------------
    def _build_ui(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=24, pady=(18, 0))
        title = tk.Frame(header, bg=BG)
        title.pack(anchor="w")
        tk.Label(title, text="HUMAN", bg=BG, fg=TEXT, font=(FONT, 22, "bold")).pack(side="left")
        tk.Label(title, text=" TETRIS", bg=BG, fg=GREEN, font=(FONT, 22, "bold")).pack(side="left")
        tk.Label(header, text="SCAN  \u2192  BLENDER  \u2192  UNITY    \u00b7    PIPELINE V9",
                 bg=BG, fg=CYAN, font=(FONT, 9, "bold")).pack(anchor="w", pady=(0, 8))
        tk.Frame(header, bg=PINK, height=3).pack(fill="x")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=(10, 10))

        run_tab = ScrollFrame(notebook)
        settings_tab = ScrollFrame(notebook)
        notebook.add(run_tab, text="  AUSFUEHREN  ")
        notebook.add(settings_tab, text="  EINSTELLUNGEN  ")

        self._build_run_tab(run_tab.inner)
        self._build_settings_tab(settings_tab.inner)

    def _build_run_tab(self, parent):
        tk.Frame(parent, bg=BG, height=6).pack()

        # --- 01 Scan -------------------------------------------------------
        body = self._card(parent, "01", "Scan mit ReconstructMe", GREEN)
        top = tk.Frame(body, bg=CARD)
        top.pack(fill="x")
        self.reme_button = ttk.Button(top, text="ReconstructMe starten", style="Cyan.TButton",
                                      command=self._on_start_reconstructme)
        self.reme_button.pack(side="left")
        self.reme_status = ttk.Label(top, text="")
        self.reme_status.pack(side="left", padx=12)

        ttk.Label(body, text="Scan in ReconstructMe als .ply speichern, und zwar in diesen Input-Ordner:",
                  wraplength=640, justify="left").pack(anchor="w", pady=(12, 2))
        self.scan_target_label = ttk.Label(body, text="", style="Path.TLabel", wraplength=640, justify="left")
        self.scan_target_label.pack(anchor="w")
        btns = tk.Frame(body, bg=CARD)
        btns.pack(anchor="w", pady=(8, 0))
        ttk.Button(btns, text="Pfad kopieren", command=self._copy_input_path).pack(side="left")
        ttk.Button(btns, text="Ordner oeffnen", command=lambda: self._open_folder(self.input_var.get())).pack(
            side="left", padx=8)
        self.scan_alert = ttk.Label(body, text="", foreground=PINK, font=(FONT, 10, "bold"))
        self.scan_alert.pack(anchor="w", pady=(8, 0))
        ttk.Label(body, text="Tipp: Den kopierten Pfad im Speichern-Dialog von ReconstructMe oben in die "
                             "Adresszeile einfuegen. Dateiname = Spielername, z.B. Max_Mustermann.ply.",
                  style="Muted.TLabel", wraplength=640, justify="left").pack(anchor="w", pady=(8, 0))

        # --- 02 Ordner -----------------------------------------------------
        io = self._card(parent, "02", "Ordner", CYAN)
        self._folder_row(io, "Input-Ordner (Rohscans .ply):", self.input_var, row=0)
        ttk.Label(io, text="Datei im Input-Ordner:").grid(row=1, column=0, sticky="w", pady=6)
        self.file_combo = ttk.Combobox(io, textvariable=self.file_choice_var, state="readonly", width=46)
        self.file_combo.grid(row=1, column=1, sticky="we", padx=6, pady=6)
        self.file_combo.bind("<<ComboboxSelected>>", self._on_file_selected)
        ttk.Button(io, text="Aktualisieren", command=self._refresh_files).grid(row=1, column=2, sticky="we", pady=6)
        self._folder_row(io, "Output-Ordner (Scans des Spiels):", self.output_var, row=2)

        # --- 03 Spieler ----------------------------------------------------
        pl = self._card(parent, "03", "Spieler", PINK)
        ttk.Label(pl, text="Spielername:").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(pl, textvariable=self.player_name_var, width=32, font=(FONT, 11)).grid(
            row=0, column=1, sticky="we", padx=6, pady=6)
        ttk.Button(pl, text="Namen nachtragen...", command=self._on_set_name_clicked).grid(
            row=0, column=2, pady=6)
        pl.columnconfigure(1, weight=1)
        ttk.Label(
            pl,
            text="Verarbeitet wird die oben gewaehlte .ply (standardmaessig die neueste; ein neuer Scan wird "
                 "automatisch ausgewaehlt). Der Name wird aus ihrem Dateinamen vorgeschlagen (_ wird zu "
                 f"Leerzeichen) und kann geaendert werden; er landet als {NAME_FILENAME} im Spieler-Ordner "
                 "und wird im Spiel angezeigt.",
            style="Muted.TLabel", wraplength=640, justify="left",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 0))

        # --- 04 Optionen ---------------------------------------------------
        opt = self._card(parent, "04", "Optionen", GREEN)
        ttk.Label(opt, text="Ziel-Dreiecke:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(opt, textvariable=self.target_faces_var, width=10).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Checkbutton(opt, text="Normal-Map backen", variable=self.bake_normals_var).grid(
            row=0, column=2, sticky="w", pady=4)
        ttk.Checkbutton(opt, text="Spiegeln (--mirror-x)", variable=self.mirror_var).grid(
            row=1, column=0, sticky="w", pady=4)
        ttk.Checkbutton(opt, text="Cleanup ueberspringen", variable=self.skip_cleanup_var).grid(
            row=1, column=1, sticky="w", pady=4)
        ttk.Checkbutton(opt, text="Loecher nicht fuellen", variable=self.no_fill_holes_var).grid(
            row=1, column=2, sticky="w", pady=4)
        ttk.Checkbutton(opt, text="Kein Textur-Bake", variable=self.no_bake_var).grid(
            row=2, column=0, sticky="w", pady=4)
        ttk.Checkbutton(opt, text="Auf Kantenlaenge skalieren (m):", variable=self.use_edge_length_var).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.edge_length_value_label = ttk.Label(opt, text=f"{self.edge_length_var.get():.2f} m",
                                                 foreground=CYAN, font=(FONT, 10, "bold"))
        self.edge_length_value_label.grid(row=3, column=2, sticky="e", pady=(10, 0))
        ttk.Scale(opt, from_=0.1, to=2.0, orient="horizontal",
                  variable=self.edge_length_var, command=self._on_edge_length_changed,
                  ).grid(row=4, column=0, columnspan=3, sticky="we", pady=(2, 6))
        for col in range(3):
            opt.columnconfigure(col, weight=1)
        ttk.Label(opt, text="Ohne Haken bleibt die Originalgroesse (das Spiel skaliert die Koepfe ohnehin passend).",
                  style="Muted.TLabel", wraplength=640, justify="left",
                  ).grid(row=5, column=0, columnspan=3, sticky="w")

        # --- 05 Start ------------------------------------------------------
        action = tk.Frame(parent, bg=BG)
        action.pack(fill="x", padx=14, pady=(10, 4))
        self.run_button = ttk.Button(action, text="\u25B6  PIPELINE STARTEN", style="Start.TButton",
                                     command=self._on_run_clicked)
        self.run_button.pack(side="left")
        self.status_label = ttk.Label(action, text="Bereit.", style="Status.TLabel")
        self.status_label.pack(side="left", padx=16)

        # --- Log -----------------------------------------------------------
        log = self._card(parent, "", "Log", MUTED)
        self.log_text = tk.Text(log, height=10, wrap="word", state="disabled", bg=BG, fg=TEXT,
                                insertbackground=TEXT, relief="flat", bd=0, font=(MONO, 9),
                                highlightthickness=1, highlightbackground=BORDER, padx=8, pady=6)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_configure("ok", foreground=GREEN)
        self.log_text.tag_configure("err", foreground=ERROR)
        self.log_text.tag_configure("head", foreground=CYAN)
        self.log_text.tag_configure("cmd", foreground=MUTED)
        tk.Frame(parent, bg=BG, height=8).pack()

    def _build_settings_tab(self, parent):
        tk.Frame(parent, bg=BG, height=6).pack()

        prog = self._card(parent, "", "Programme", CYAN)
        self._program_row(prog, "Pfad zu blender.exe:", self.blender_path_var, self._pick_blender_exe, row=0)
        self.blender_check = ttk.Label(prog, text="")
        self.blender_check.grid(row=1, column=1, sticky="w", padx=6, pady=(0, 8))
        self._program_row(prog, "Pfad zu ReconstructMe:", self.reconstructme_path_var,
                          self._pick_reconstructme_exe, row=2)
        self.reme_check = ttk.Label(prog, text="")
        self.reme_check.grid(row=3, column=1, sticky="w", padx=6)
        ttk.Label(prog, text="Meist C:\\Program Files\\ReconstructMe\\ReconstructMe.exe. Wird nur fuer den Knopf "
                             "\"ReconstructMe starten\" gebraucht.",
                  style="Muted.TLabel", wraplength=640, justify="left").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(6, 0))

        adv = self._card(parent, "", "Erweiterte Optionen", GREEN)
        ttk.Label(adv, text="Bake-Aufloesung (px):").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(adv, textvariable=self.bake_size_var, width=10).grid(row=0, column=1, sticky="w", padx=6, pady=6)
        ttk.Label(adv, text="Bake-Margin (px):").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(adv, textvariable=self.margin_var, width=10).grid(row=1, column=1, sticky="w", padx=6, pady=6)

        tk.Label(parent, text=f"Alle Einstellungen werden in {CONFIG_FILENAME} neben der Anwendung gespeichert.  "
                              "Getestet mit Blender 4.x / 5.x.",
                 bg=BG, fg=MUTED, font=(FONT, 9), justify="left").pack(anchor="w", padx=16, pady=10)

    def _program_row(self, parent, label, variable, command, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6)
        ttk.Entry(parent, textvariable=variable, width=50).grid(row=row, column=1, sticky="we", padx=6, pady=6)
        ttk.Button(parent, text="Durchsuchen...", command=command).grid(row=row, column=2, sticky="we", pady=6)
        parent.columnconfigure(1, weight=1)

    def _on_edge_length_changed(self, _value=None):
        self.edge_length_value_label.configure(text=f"{self.edge_length_var.get():.2f} m")

    def _folder_row(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6)
        ttk.Entry(parent, textvariable=variable, width=48).grid(row=row, column=1, sticky="we", padx=6, pady=6)
        ttk.Button(parent, text="Ordner waehlen...",
                   command=lambda v=variable: self._pick_folder(v)).grid(row=row, column=2, sticky="we", pady=6)
        parent.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    # Anzeige aktualisieren
    # ------------------------------------------------------------------
    def _update_scan_card(self):
        folder = self.input_var.get().strip()
        if folder:
            self.scan_target_label.configure(text=folder, style="Path.TLabel")
        else:
            self.scan_target_label.configure(text="Noch kein Input-Ordner gewaehlt (siehe 02 Ordner).",
                                             style="Bad.TLabel")
        self._update_program_labels()

    def _update_program_labels(self):
        reme = self.reconstructme_path_var.get().strip()
        if self.reme_process is not None and self.reme_process.poll() is None:
            self.reme_status.configure(text="\u25CF ReconstructMe laeuft", style="Ok.TLabel")
        elif reme and os.path.isfile(reme):
            self.reme_status.configure(text="Bereit", style="Muted.TLabel")
        else:
            self.reme_status.configure(text="Pfad fehlt -- unter Einstellungen waehlen", style="Bad.TLabel")
        for var, label in ((self.blender_path_var, getattr(self, "blender_check", None)),
                           (self.reconstructme_path_var, getattr(self, "reme_check", None))):
            if label is None:
                continue
            path = var.get().strip()
            if not path:
                label.configure(text="Nicht gesetzt", style="Bad.TLabel")
            elif os.path.isfile(path):
                label.configure(text="\u2714 Gefunden", style="Ok.TLabel")
            else:
                label.configure(text="\u2718 Datei nicht gefunden", style="Bad.TLabel")

    def _set_status(self, text, color=MUTED):
        self.status_label.configure(text=text, foreground=color)

    # ------------------------------------------------------------------
    # Auswahl-Dialoge
    # ------------------------------------------------------------------
    def _pick_folder(self, variable):
        start = variable.get() if os.path.isdir(variable.get()) else None
        chosen = filedialog.askdirectory(title="Ordner waehlen", initialdir=start)
        if chosen:
            variable.set(os.path.normpath(chosen))

    def _pick_exe(self, variable, title, exe_name):
        filetypes = [(exe_name, exe_name), ("Programme", "*.exe"), ("Alle Dateien", "*.*")] if os.name == "nt" \
            else [("Alle Dateien", "*")]
        current = variable.get().strip()
        start = os.path.dirname(current) if current and os.path.isdir(os.path.dirname(current)) else None
        chosen = filedialog.askopenfilename(title=title, filetypes=filetypes, initialdir=start)
        if chosen:
            variable.set(os.path.normpath(chosen))
            self._save_current_config()

    def _pick_blender_exe(self):
        self._pick_exe(self.blender_path_var, "blender.exe auswaehlen", "blender.exe")

    def _pick_reconstructme_exe(self):
        self._pick_exe(self.reconstructme_path_var, "ReconstructMe auswaehlen", "ReconstructMe*.exe")

    def _copy_input_path(self):
        folder = self.input_var.get().strip()
        if not folder:
            messagebox.showerror(APP_TITLE, "Bitte zuerst einen Input-Ordner waehlen.")
            return
        self.clipboard_clear()
        self.clipboard_append(folder)
        self._set_status("Pfad kopiert.", CYAN)

    def _open_folder(self, folder):
        folder = folder.strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror(APP_TITLE, "Der Ordner existiert nicht (oder ist noch nicht gewaehlt).")
            return
        try:
            open_in_explorer(folder)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Ordner konnte nicht geoeffnet werden:\n{exc}")

    # ------------------------------------------------------------------
    # ReconstructMe
    # ------------------------------------------------------------------
    def _on_start_reconstructme(self):
        if self.reme_process is not None and self.reme_process.poll() is None:
            messagebox.showinfo(APP_TITLE, "ReconstructMe laeuft bereits.")
            return
        path = self.reconstructme_path_var.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showinfo(APP_TITLE, "Bitte zuerst ReconstructMe auswaehlen (die .exe).")
            self._pick_reconstructme_exe()
            path = self.reconstructme_path_var.get().strip()
            if not path or not os.path.isfile(path):
                return
        if not self.input_var.get().strip():
            messagebox.showwarning(APP_TITLE, "Noch kein Input-Ordner gewaehlt. Bitte unter 02 Ordner festlegen, "
                                              "damit klar ist, wohin der Scan gespeichert wird.")
        try:
            # eigenes Arbeitsverzeichnis: ReconstructMe findet so seine Konfiguration und Treiber-DLLs
            self.reme_process = subprocess.Popen([path], cwd=os.path.dirname(path))
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"ReconstructMe konnte nicht gestartet werden:\n{exc}")
            return
        self._log("ReconstructMe gestartet. Scan als .ply in den Input-Ordner speichern.", "head")
        self._update_program_labels()
        self._watch_reconstructme()

    def _watch_reconstructme(self):
        """Statusanzeige aktualisieren, solange ReconstructMe laeuft."""
        self._update_program_labels()
        if self.reme_process is not None and self.reme_process.poll() is None:
            self.after(1500, self._watch_reconstructme)

    # ------------------------------------------------------------------
    # Ausfuehrung
    # ------------------------------------------------------------------
    def _log(self, text, tag=None):
        if tag is None:
            if text.startswith("==="):
                tag = "ok" if "Erfolgreich" in text else ("err" if "Abgebrochen" in text else "head")
            elif text.startswith("\n==="):
                tag = "head"
            elif text.startswith("> "):
                tag = "cmd"
            elif "Fehler" in text or "ERROR" in text:
                tag = "err"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n", tag or ())
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    @staticmethod
    def _is_positive_int(value):
        return value.strip().isdigit() and int(value) > 0

    def _validate_inputs(self):
        if not self.blender_path_var.get() or not os.path.isfile(self.blender_path_var.get()):
            messagebox.showerror(APP_TITLE, "Bitte unter 'Einstellungen' zuerst den Pfad zu blender.exe waehlen.")
            return False
        if not os.path.isfile(SCRIPT_PATH):
            messagebox.showerror(APP_TITLE, f"{SCRIPT_NAME} fehlt. Es muss neben der Anwendung liegen:\n{BASE_DIR}")
            return False
        if not self.input_var.get():
            messagebox.showerror(APP_TITLE, "Bitte einen Input-Ordner waehlen.")
            return False
        if not self.output_var.get():
            messagebox.showerror(APP_TITLE, "Bitte einen Output-Ordner waehlen.")
            return False
        for label, var in (("Ziel-Dreiecke", self.target_faces_var),
                           ("Bake-Aufloesung", self.bake_size_var),
                           ("Bake-Margin", self.margin_var)):
            if not self._is_positive_int(var.get()):
                messagebox.showerror(APP_TITLE, f"'{label}' muss eine ganze Zahl groesser 0 sein.")
                return False
        return True

    def _build_command(self, input_path, output_dir):
        cmd = [
            self.blender_path_var.get(),
            "--background",
            "--python", SCRIPT_PATH,
            "--",
            "--input", input_path,
            "--output", output_dir,
            "--rename", OUTPUT_FILE_NAME,
            "--target-faces", self.target_faces_var.get().strip(),
            "--bake-size", self.bake_size_var.get().strip(),
            "--margin", self.margin_var.get().strip(),
        ]
        if self.bake_normals_var.get():
            cmd += ["--bake-normals"]
        if self.mirror_var.get():
            cmd += ["--mirror-x"]
        if self.skip_cleanup_var.get():
            cmd += ["--skip-cleanup"]
        if self.no_fill_holes_var.get():
            cmd += ["--no-fill-holes"]
        if self.no_bake_var.get():
            cmd += ["--no-bake"]
        if self.use_edge_length_var.get():
            cmd += ["--edge-length", f"{self.edge_length_var.get():.4f}"]
        return cmd

    @staticmethod
    def _file_key(filepath):
        try:
            return f"{os.path.abspath(filepath)}|{os.path.getmtime(filepath):.0f}"
        except OSError:
            return ""

    def _select_file(self, path):
        """Datei in der Auswahlliste waehlen und den Namen aus ihrem Dateinamen vorschlagen."""
        self.selected_file = path
        label = next((k for k, v in self.file_paths.items() if v == path), "")
        self.file_choice_var.set(label)
        self.player_name_var.set(name_from_file(path) if path else "")

    def _on_file_selected(self, _event=None):
        self._select_file(self.file_paths.get(self.file_choice_var.get()))

    def _refresh_files(self):
        """Auswahlliste neu einlesen. Kommt ein neuer Scan dazu (neue neueste Datei), wird er
        ausgewaehlt; sonst bleiben Auswahl und Aenderungen am Namensfeld erhalten."""
        files = input_files(self.input_var.get()) if self.input_var.get() else []
        newest = files[0] if files else None

        if files != self.known_files:
            self.known_files = files
            self.file_paths = {file_label(f, i == 0): f for i, f in enumerate(files)}
            self.file_combo.configure(values=list(self.file_paths.keys()))
            if self.selected_file in files:  # Anzeige-Text (Zeit, [neueste]) auffrischen
                self.file_choice_var.set(next(k for k, v in self.file_paths.items() if v == self.selected_file))

        if newest != self.newest_file:
            is_new_scan = newest is not None and not self._first_refresh and self.newest_file is not None \
                and os.path.dirname(newest) == os.path.dirname(self.newest_file)
            self.newest_file = newest
            self._select_file(newest)           # neuer Scan bzw. anderer Input-Ordner
            if is_new_scan and (self.process is None or self.process.poll() is not None):
                self._set_status(f"\u2605 Neuer Scan: {os.path.basename(newest)} -- Namen pruefen und starten",
                                 PINK)
                self.scan_alert.configure(text=f"\u2605 Neuer Scan erkannt: {os.path.basename(newest)}  "
                                               "\u2192 unten Namen pruefen und Pipeline starten")
                self.bell()
        elif self.selected_file not in files:
            self._select_file(newest)           # gewaehlte Datei wurde geloescht/umbenannt
        if not files:
            self.file_choice_var.set("- (keine .ply gefunden)")
        self._first_refresh = False

    def _watch_input(self):
        """Prueft alle 2 s den Input-Ordner."""
        self._refresh_files()
        self.after(2000, self._watch_input)

    def _confirm_name(self):
        """Name aus dem Feld; leer -> nachfragen. None = Abbruch."""
        name = clean_player_name(self.player_name_var.get())
        if not name and not messagebox.askyesno(
                APP_TITLE, "Kein Spielername eingetragen.\n\nOhne Namen fortfahren? "
                           "(Im Spiel steht dann nur die Spielernummer.)"):
            return None
        return name

    def _on_set_name_clicked(self):
        """Name fuer einen vorhandenen Spieler-Ordner setzen oder aendern."""
        start = self.output_var.get() if os.path.isdir(self.output_var.get()) else None
        folder = filedialog.askdirectory(title="Spieler-Ordner waehlen (z.B. Playermodell_0007)", initialdir=start)
        if not folder:
            return
        current = read_player_name(folder)
        name = simpledialog.askstring(
            APP_TITLE, f"Spielername fuer {os.path.basename(folder)}:",
            initialvalue=current or self.player_name_var.get(), parent=self)
        if name is None:
            return
        try:
            written = write_player_name(folder, name)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"{NAME_FILENAME} konnte nicht geschrieben werden:\n{exc}")
            return
        if written:
            self._log(f"{os.path.basename(folder)}/{NAME_FILENAME}: {written}", "ok")
        else:
            messagebox.showinfo(APP_TITLE, "Kein Name eingegeben, nichts geaendert.")

    def _on_run_clicked(self):
        if not self._validate_inputs():
            return

        self._save_current_config()

        newest = newest_input_file(self.input_var.get())
        if not newest:
            messagebox.showerror(APP_TITLE, "Keine .ply Datei im Input-Ordner gefunden.")
            return
        if newest != self.newest_file:
            # Neuer Scan seit der letzten Anzeige: wird ausgewaehlt, erst Namen pruefen lassen
            self._refresh_files()
            messagebox.showinfo(APP_TITLE, f"Neue Datei gefunden: {os.path.basename(newest)}\n"
                                           "Sie ist jetzt ausgewaehlt. Bitte den Spielernamen pruefen "
                                           "und erneut starten.")
            return

        chosen = self.selected_file
        if not chosen or not os.path.isfile(chosen):
            self._refresh_files()
            messagebox.showerror(APP_TITLE, "Die gewaehlte Datei gibt es nicht mehr. Bitte neu auswaehlen.")
            return

        key = self._file_key(chosen)
        if key and key == self.last_processed and not messagebox.askyesno(
                APP_TITLE, f"{os.path.basename(chosen)} wurde bereits verarbeitet.\n\n"
                           "Trotzdem nochmal verarbeiten? (Es entsteht ein weiterer Spieler-Ordner.)"):
            return

        name = self._confirm_name()
        if name is None:
            return
        self.last_processed = key
        self._save_current_config()
        files, names = [chosen], [name]

        output_root = self.output_var.get()
        os.makedirs(output_root, exist_ok=True)

        self.run_button.configure(state="disabled")
        self.scan_alert.configure(text="")
        self._set_status("\u25CF Laeuft...", CYAN)
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        thread = threading.Thread(target=self._run_all_files, args=(files, names, output_root), daemon=True)
        thread.start()

    def _run_all_files(self, files, names, output_root):
        """Verarbeitet jede Eingabedatei einzeln und legt sie in einen eigenen,
        fortlaufend nummerierten Unterordner ab (z.B. Playermodell_0007)."""
        total = len(files)
        overall_rc = 0

        for idx, filepath in enumerate(files, start=1):
            number = take_next_number(output_root)
            folder_name = f"Playermodell_{number:04d}"
            target_dir = os.path.join(output_root, folder_name)
            os.makedirs(target_dir, exist_ok=True)

            try:
                written = write_player_name(target_dir, names[idx - 1])
                if written:
                    self.after(0, self._log, f"Spielername: {written} -> {folder_name}/{NAME_FILENAME}")
            except OSError as exc:
                self.after(0, self._log, f"  {NAME_FILENAME} konnte nicht geschrieben werden: {exc}")

            self.after(0, self._log,
                       f"\n=== [{idx}/{total}] {os.path.basename(filepath)} -> {folder_name}/{OUTPUT_FILE_NAME}.glb ===")
            cmd = self._build_command(filepath, target_dir)
            self.after(0, self._log, "> " + " ".join(f'"{c}"' if " " in c else c for c in cmd))

            rc = self._run_single(cmd)
            if rc != 0:
                overall_rc = rc
                self.after(0, self._log, f"  Fehlercode {rc} -- fahre trotzdem mit der naechsten Datei fort.")

        self.after(0, self._on_process_finished, overall_rc)

    def _run_single(self, cmd):
        # PYTHONUNBUFFERED erzwingt, dass Blenders eingebetteter Python-Interpreter
        # print()-Ausgaben sofort statt gepuffert weitergibt.
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",  # verhindert Absturz des Log-Threads bei Sonderzeichen
                bufsize=1,
                env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),  # kein schwarzes Konsolenfenster
            )
            while True:
                try:
                    line = self.process.stdout.readline()
                except (UnicodeDecodeError, ValueError) as exc:
                    self.after(0, self._log, f"[Log-Lesefehler ignoriert: {exc}]")
                    continue
                if line == "" and self.process.poll() is not None:
                    break
                if line:
                    self.after(0, self._log, line.rstrip())
            return self.process.wait()
        except OSError as exc:
            self.after(0, self._log, f"Fehler beim Starten von Blender: {exc}")
            return -1

    def _on_process_finished(self, return_code):
        self.run_button.configure(state="normal")
        if return_code == 0:
            self._set_status("\u2714 Fertig.", GREEN)
            self._log("=== Erfolgreich abgeschlossen ===")
        else:
            self._set_status(f"\u2718 Fehler (Code {return_code}).", ERROR)
            self._log(f"=== Abgebrochen mit Fehlercode {return_code} ===")

    def _save_current_config(self):
        save_config({
            "blender_path": self.blender_path_var.get(),
            "reconstructme_path": self.reconstructme_path_var.get(),
            "input_path": self.input_var.get(),
            "output_path": self.output_var.get(),
            "target_faces": self.target_faces_var.get(),
            "bake_normals": self.bake_normals_var.get(),
            "mirror": self.mirror_var.get(),
            "skip_cleanup": self.skip_cleanup_var.get(),
            "no_fill_holes": self.no_fill_holes_var.get(),
            "no_bake": self.no_bake_var.get(),
            "use_edge_length": self.use_edge_length_var.get(),
            "edge_length": self.edge_length_var.get(),
            "bake_size": self.bake_size_var.get(),
            "margin": self.margin_var.get(),
            "last_processed": self.last_processed,
        })

    def destroy(self):
        self._save_current_config()
        super().destroy()


if __name__ == "__main__":
    if os.name == "nt":
        # Eigene App-Kennung: Windows zeigt dann in der Taskleiste pipeline.ico statt des Python-Icons
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HumanTetris.PipelineTool")
        except (AttributeError, OSError):
            pass
    app = PipelineGUI()
    app.mainloop()
