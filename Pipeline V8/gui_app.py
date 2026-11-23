"""
gui_app.py  (Pipeline V8)
---------------------------
Grafische Oberflaeche fuer ply_head_to_lowpoly_glb.py: wandelt PLY-Kopfscans in
polygonreduzierte GLB-Koepfe fuer Human Tetris (Unity) um. Laesst dich:
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

APP_TITLE = "Scan zu Unity Pipeline V8"
CONFIG_FILENAME = "pipeline_gui_config.json"

# Liegt neben der .exe (bzw. neben dem Skript im Entwicklungsmodus)
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(BASE_DIR, CONFIG_FILENAME)

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
# Oberflaeche
# ----------------------------------------------------------------------
class PipelineGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x700")
        self.minsize(680, 620)

        c = load_config()
        self.blender_path_var = tk.StringVar(value=c.get("blender_path", ""))
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

        self.process = None
        self._build_ui()
        self._watch_input()

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        run_tab = ttk.Frame(notebook)
        settings_tab = ttk.Frame(notebook)
        notebook.add(run_tab, text="Ausfuehren")
        notebook.add(settings_tab, text="Einstellungen")

        self._build_run_tab(run_tab)
        self._build_settings_tab(settings_tab)

    def _build_run_tab(self, parent):
        pad = {"padx": 8, "pady": 6}

        # --- Skript (fest) -------------------------------------------------
        script_frame = ttk.LabelFrame(parent, text="Blender-Skript")
        script_frame.pack(fill="x", **pad)
        found = os.path.isfile(SCRIPT_PATH)
        ttk.Label(
            script_frame,
            text=f"{SCRIPT_NAME} (Kopfscan -> Low-Poly-GLB)" + ("" if found else "  --  NICHT GEFUNDEN!"),
            foreground="#000" if found else "#c00",
        ).pack(anchor="w", padx=8, pady=(8, 0))
        ttk.Label(script_frame, text=SCRIPT_PATH, foreground="#555").pack(anchor="w", padx=8, pady=(0, 8))

        # --- Ordner --------------------------------------------------------
        io_frame = ttk.LabelFrame(parent, text="Ordner")
        io_frame.pack(fill="x", **pad)
        self._folder_row(io_frame, "Input-Ordner (Rohscans .ply):", self.input_var, row=0)
        ttk.Label(io_frame, text="Datei im Input-Ordner:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.file_combo = ttk.Combobox(io_frame, textvariable=self.file_choice_var, state="readonly", width=46)
        self.file_combo.grid(row=1, column=1, sticky="we", padx=4, pady=6)
        self.file_combo.bind("<<ComboboxSelected>>", self._on_file_selected)
        ttk.Button(io_frame, text="Aktualisieren", command=self._refresh_files).grid(row=1, column=2, padx=8, pady=6)
        self._folder_row(io_frame, "Output-Ordner (Scans des Spiels):", self.output_var, row=2)

        # --- Spielername ---------------------------------------------------
        name_frame = ttk.LabelFrame(parent, text="Spieler")
        name_frame.pack(fill="x", **pad)
        ttk.Label(name_frame, text="Spielername:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(name_frame, textvariable=self.player_name_var, width=32).grid(
            row=0, column=1, sticky="we", padx=4, pady=6)
        ttk.Button(name_frame, text="Namen nachtragen...", command=self._on_set_name_clicked).grid(
            row=0, column=2, padx=8, pady=6)
        name_frame.columnconfigure(1, weight=1)
        ttk.Label(
            name_frame,
            text="Verarbeitet wird die oben gewaehlte .ply (standardmaessig die neueste; ein neuer Scan wird "
                 "automatisch ausgewaehlt). Der Name wird aus ihrem Dateinamen vorgeschlagen (_ wird zu "
                 f"Leerzeichen) und kann geaendert werden; er landet als {NAME_FILENAME} im Spieler-Ordner "
                 "und wird im Spiel angezeigt.",
            foreground="#666", wraplength=560, justify="left",
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 6))

        # --- Optionen ------------------------------------------------------
        opt_frame = ttk.LabelFrame(parent, text="Optionen")
        opt_frame.pack(fill="x", **pad)

        ttk.Label(opt_frame, text="Ziel-Dreiecke:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(opt_frame, textvariable=self.target_faces_var, width=10).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Checkbutton(opt_frame, text="Normal-Map backen", variable=self.bake_normals_var).grid(
            row=0, column=2, sticky="w", padx=8, pady=4)

        ttk.Checkbutton(opt_frame, text="Spiegeln (--mirror-x)", variable=self.mirror_var).grid(
            row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Checkbutton(opt_frame, text="Cleanup ueberspringen", variable=self.skip_cleanup_var).grid(
            row=1, column=1, sticky="w", padx=8, pady=4)
        ttk.Checkbutton(opt_frame, text="Loecher nicht fuellen", variable=self.no_fill_holes_var).grid(
            row=1, column=2, sticky="w", padx=8, pady=4)
        ttk.Checkbutton(opt_frame, text="Kein Textur-Bake", variable=self.no_bake_var).grid(
            row=2, column=0, sticky="w", padx=8, pady=4)

        ttk.Checkbutton(opt_frame, text="Auf Kantenlaenge skalieren (m):", variable=self.use_edge_length_var).grid(
            row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(10, 0))
        self.edge_length_value_label = ttk.Label(opt_frame, text=f"{self.edge_length_var.get():.2f} m")
        self.edge_length_value_label.grid(row=3, column=2, sticky="e", padx=8, pady=(10, 0))
        ttk.Scale(
            opt_frame, from_=0.1, to=2.0, orient="horizontal",
            variable=self.edge_length_var, command=self._on_edge_length_changed,
        ).grid(row=4, column=0, columnspan=3, sticky="we", padx=8, pady=(0, 6))
        for col in range(3):
            opt_frame.columnconfigure(col, weight=1)
        ttk.Label(
            opt_frame,
            text="Ohne Haken bleibt die Originalgroesse (das Spiel skaliert die Koepfe ohnehin passend).",
            foreground="#666", wraplength=560, justify="left",
        ).grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 6))

        # --- Start-Button + Log -------------------------------------------
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill="x", padx=8, pady=(4, 0))
        self.run_button = ttk.Button(action_frame, text="Pipeline starten", command=self._on_run_clicked)
        self.run_button.pack(side="left")
        self.status_label = ttk.Label(action_frame, text="Bereit.")
        self.status_label.pack(side="left", padx=12)

        log_frame = ttk.LabelFrame(parent, text="Log")
        log_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.log_text = tk.Text(log_frame, height=10, wrap="word", state="disabled", bg="#111", fg="#ddd")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_settings_tab(self, parent):
        pad = {"padx": 8, "pady": 6}

        blender_frame = ttk.LabelFrame(parent, text="Blender-Programm")
        blender_frame.pack(fill="x", **pad)
        ttk.Label(blender_frame, text="Pfad zu blender.exe:").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        ttk.Entry(blender_frame, textvariable=self.blender_path_var, width=55).grid(
            row=0, column=1, sticky="we", padx=4, pady=8)
        ttk.Button(blender_frame, text="Durchsuchen...", command=self._pick_blender_exe).grid(
            row=0, column=2, padx=8, pady=8)
        blender_frame.columnconfigure(1, weight=1)

        adv_frame = ttk.LabelFrame(parent, text="Erweiterte Optionen")
        adv_frame.pack(fill="x", **pad)
        ttk.Label(adv_frame, text="Bake-Aufloesung (px):").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(adv_frame, textvariable=self.bake_size_var, width=10).grid(row=0, column=1, sticky="w", pady=6)
        ttk.Label(adv_frame, text="Bake-Margin (px):").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(adv_frame, textvariable=self.margin_var, width=10).grid(row=1, column=1, sticky="w", pady=6)

        ttk.Label(
            parent,
            text="Hinweis: Diese Einstellungen werden lokal in\n"
                 f"{CONFIG_FILENAME} neben der Anwendung gespeichert.\n"
                 "Getestet mit Blender 4.x / 5.x.",
            foreground="#666", justify="left",
        ).pack(anchor="w", padx=8, pady=12)

    def _on_edge_length_changed(self, _value=None):
        self.edge_length_value_label.configure(text=f"{self.edge_length_var.get():.2f} m")

    def _folder_row(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(parent, textvariable=variable, width=48).grid(row=row, column=1, sticky="we", padx=4, pady=6)
        ttk.Button(parent, text="Ordner waehlen...",
                   command=lambda v=variable: self._pick_folder(v)).grid(row=row, column=2, padx=8, pady=6)
        parent.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    # Auswahl-Dialoge
    # ------------------------------------------------------------------
    def _pick_folder(self, variable):
        chosen = filedialog.askdirectory(title="Ordner waehlen")
        if chosen:
            variable.set(chosen)

    def _pick_blender_exe(self):
        filetypes = [("blender.exe", "blender.exe"), ("Alle Dateien", "*.*")] if os.name == "nt" \
            else [("Alle Dateien", "*")]
        chosen = filedialog.askopenfilename(title="blender.exe auswaehlen", filetypes=filetypes)
        if chosen:
            self.blender_path_var.set(chosen)

    # ------------------------------------------------------------------
    # Ausfuehrung
    # ------------------------------------------------------------------
    def _log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
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
            self.newest_file = newest
            self._select_file(newest)           # neuer Scan bzw. anderer Input-Ordner
        elif self.selected_file not in files:
            self._select_file(newest)           # gewaehlte Datei wurde geloescht/umbenannt
        if not files:
            self.file_choice_var.set("- (keine .ply gefunden)")

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
            self._log(f"{os.path.basename(folder)}/{NAME_FILENAME}: {written}")
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
        self.status_label.configure(text="Laeuft...")
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
            self.status_label.configure(text="Fertig.")
            self._log("=== Erfolgreich abgeschlossen ===")
        else:
            self.status_label.configure(text=f"Fehler (Code {return_code}).")
            self._log(f"=== Abgebrochen mit Fehlercode {return_code} ===")

    def _save_current_config(self):
        save_config({
            "blender_path": self.blender_path_var.get(),
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
    app = PipelineGUI()
    app.mainloop()
