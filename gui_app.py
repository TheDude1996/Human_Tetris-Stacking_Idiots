"""
gui_app.py
----------
Grafische Oberflaeche fuer die Scan-zu-Unity-Pipeline. Laesst dich:
  - Input-Ordner (Rohscans) per Dialog auswaehlen
  - Output-Ordner (fertige .fbx/.png) per Dialog auswaehlen
  - Das Blender-Skript auswaehlen (scan_to_unity_pipeline.py, ply_to_fbx_textured.py
    oder ein eigenes ueber "Durchsuchen...")
  - Den Pfad zu blender.exe einmalig hinterlegen (wird gespeichert)
  - Optionen setzen (Zielhoehe, Spiegeln, Bake-Aufloesung, ...)
  - Den Lauf per Klick starten und live im Log-Fenster mitverfolgen

Jede Eingabedatei wird einzeln verarbeitet und landet in einem eigenen
Unterordner im Output-Ordner, benannt "Playermodell_<Nummer>" (z.B.
Playermodell_0007). Die erzeugten Dateien (.fbx/.png) darin heissen ebenso
"Playermodell_0007.fbx" usw. statt beim urspruenglichen Scan-Dateinamen zu
bleiben. Diese Nummer wird in einer kleinen .pipeline_counter.json direkt
im Output-Ordner gespeichert und bleibt daher auch nach einem Neustart der
App erhalten -- die Zaehlung faengt nie wieder bei 0 an.

Diese Datei ist die Basis fuer die .exe (siehe Packen-Anleitung im Chat).
Sie ruft im Hintergrund exakt denselben Kommandozeilen-Aufruf auf, den du
bisher manuell getippt hast:

    blender.exe --background --python <skript>.py -- --input <ordner> --output <ordner> [...]
"""

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "Scan zu Unity Pipeline"
CONFIG_FILENAME = "pipeline_gui_config.json"

# Liegt neben der .exe (bzw. neben dem Skript im Entwicklungsmodus)
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(BASE_DIR, CONFIG_FILENAME)

BUILTIN_SCRIPTS = {
    "scan_to_unity_pipeline.py (Cleanup + Bake + Export)": "scan_to_unity_pipeline.py",
    "ply_to_fbx_textured.py (nur Bake + Export)": "ply_to_fbx_textured.py",
}
CUSTOM_SCRIPT_LABEL = "Eigenes Skript auswaehlen..."

ALLOWED_INPUT_EXTENSIONS = (".ply", ".stl")

# Diese Datei liegt direkt im gewaehlten Output-Ordner und merkt sich die
# naechste zu vergebende laufende Nummer. Da sie an den Ordner gebunden ist
# (nicht an die App), bleibt die Zaehlung auch nach einem Neustart der
# Anwendung oder einem Wechsel des Output-Ordners korrekt erhalten.
COUNTER_FILENAME = ".pipeline_counter.json"


def list_input_files(input_path):
    """Findet alle .ply/.stl Dateien in einem Ordner (oder gibt eine
    einzelne Datei zurueck, falls direkt eine Datei uebergeben wurde)."""
    if os.path.isdir(input_path):
        return sorted(
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.lower().endswith(ALLOWED_INPUT_EXTENSIONS)
        )
    if os.path.isfile(input_path) and input_path.lower().endswith(ALLOWED_INPUT_EXTENSIONS):
        return [input_path]
    return []


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


class PipelineGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x620")
        self.minsize(680, 560)

        self.config_data = load_config()
        self.script_path_var = tk.StringVar(value=self.config_data.get("script_path", ""))
        self.blender_path_var = tk.StringVar(value=self.config_data.get("blender_path", ""))
        self.input_var = tk.StringVar(value=self.config_data.get("input_path", ""))
        self.output_var = tk.StringVar(value=self.config_data.get("output_path", ""))

        self.target_height_var = tk.StringVar(value=self.config_data.get("target_height", "1.75"))
        self.bake_size_var = tk.StringVar(value=self.config_data.get("bake_size", "2048"))
        self.margin_var = tk.StringVar(value=self.config_data.get("margin", "8"))
        self.mirror_var = tk.BooleanVar(value=self.config_data.get("mirror", False))
        self.skip_cleanup_var = tk.BooleanVar(value=self.config_data.get("skip_cleanup", False))
        self.no_bake_var = tk.BooleanVar(value=self.config_data.get("no_bake", False))

        self.process = None
        self._build_ui()
        self._restore_script_dropdown()

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------
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

        # --- Skript-Auswahl -------------------------------------------------
        script_frame = ttk.LabelFrame(parent, text="Blender-Skript")
        script_frame.pack(fill="x", **pad)

        self.script_combo = ttk.Combobox(
            script_frame,
            values=list(BUILTIN_SCRIPTS.keys()) + [CUSTOM_SCRIPT_LABEL],
            state="readonly",
        )
        self.script_combo.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        self.script_combo.bind("<<ComboboxSelected>>", self._on_script_selected)

        self.script_path_label = ttk.Label(script_frame, textvariable=self.script_path_var, foreground="#555")
        self.script_path_label.pack(fill="x", padx=8, pady=(0, 8))

        # --- Input-Ordner -----------------------------------------------
        io_frame = ttk.LabelFrame(parent, text="Ordner")
        io_frame.pack(fill="x", **pad)

        self._folder_row(io_frame, "Input-Ordner (Rohscans):", self.input_var, row=0)
        self._folder_row(io_frame, "Output-Ordner (fertige Dateien):", self.output_var, row=1)

        # --- Optionen kurz sichtbar auf dem Run-Tab -----------------------
        opt_frame = ttk.LabelFrame(parent, text="Optionen")
        opt_frame.pack(fill="x", **pad)

        ttk.Checkbutton(opt_frame, text="Spiegeln (--mirror-x)", variable=self.mirror_var).grid(
            row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Checkbutton(opt_frame, text="Cleanup ueberspringen", variable=self.skip_cleanup_var).grid(
            row=0, column=1, sticky="w", padx=8, pady=4)
        ttk.Checkbutton(opt_frame, text="Kein Textur-Bake", variable=self.no_bake_var).grid(
            row=0, column=2, sticky="w", padx=8, pady=4)

        # --- Start-Button + Log ------------------------------------------
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill="x", padx=8, pady=(4, 0))

        self.run_button = ttk.Button(action_frame, text="Pipeline starten", command=self._on_run_clicked)
        self.run_button.pack(side="left")

        self.status_label = ttk.Label(action_frame, text="Bereit.")
        self.status_label.pack(side="left", padx=12)

        log_frame = ttk.LabelFrame(parent, text="Log")
        log_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.log_text = tk.Text(log_frame, height=14, wrap="word", state="disabled", bg="#111", fg="#ddd")
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

        adv_frame = ttk.LabelFrame(parent, text="Erweiterte Pipeline-Optionen")
        adv_frame.pack(fill="x", **pad)

        ttk.Label(adv_frame, text="Ziel-Koerperhoehe (m):").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(adv_frame, textvariable=self.target_height_var, width=10).grid(row=0, column=1, sticky="w", pady=6)

        ttk.Label(adv_frame, text="Bake-Aufloesung (px):").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(adv_frame, textvariable=self.bake_size_var, width=10).grid(row=1, column=1, sticky="w", pady=6)

        ttk.Label(adv_frame, text="Bake-Margin (px):").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(adv_frame, textvariable=self.margin_var, width=10).grid(row=2, column=1, sticky="w", pady=6)

        ttk.Label(
            parent,
            text="Hinweis: Diese Einstellungen werden lokal in\n"
                 f"{CONFIG_FILENAME} neben der Anwendung gespeichert.",
            foreground="#666",
            justify="left",
        ).pack(anchor="w", padx=8, pady=12)

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

    def _on_script_selected(self, _event=None):
        label = self.script_combo.get()
        if label == CUSTOM_SCRIPT_LABEL:
            chosen = filedialog.askopenfilename(
                title="Blender-Skript (.py) auswaehlen",
                filetypes=[("Python-Skript", "*.py"), ("Alle Dateien", "*.*")],
            )
            if chosen:
                self.script_path_var.set(chosen)
            else:
                self.script_combo.set("")
        else:
            script_name = BUILTIN_SCRIPTS[label]
            # Eingebaute Skripte werden im selben Ordner wie diese Anwendung erwartet
            self.script_path_var.set(os.path.join(BASE_DIR, script_name))

    def _restore_script_dropdown(self):
        current = self.script_path_var.get()
        for label, script_name in BUILTIN_SCRIPTS.items():
            if current.endswith(script_name):
                self.script_combo.set(label)
                return
        if current:
            self.script_combo.set(CUSTOM_SCRIPT_LABEL)

    # ------------------------------------------------------------------
    # Ausfuehrung
    # ------------------------------------------------------------------
    def _log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _validate_inputs(self):
        if not self.blender_path_var.get() or not os.path.isfile(self.blender_path_var.get()):
            messagebox.showerror(APP_TITLE, "Bitte unter 'Einstellungen' zuerst den Pfad zu blender.exe waehlen.")
            return False
        if not self.script_path_var.get() or not os.path.isfile(self.script_path_var.get()):
            messagebox.showerror(APP_TITLE, "Bitte ein gueltiges Blender-Skript auswaehlen.")
            return False
        if not self.input_var.get():
            messagebox.showerror(APP_TITLE, "Bitte einen Input-Ordner waehlen.")
            return False
        if not self.output_var.get():
            messagebox.showerror(APP_TITLE, "Bitte einen Output-Ordner waehlen.")
            return False
        return True

    def _build_command(self, input_path, output_dir, rename_name):
        cmd = [
            self.blender_path_var.get(),
            "--background",
            "--python", self.script_path_var.get(),
            "--",
            "--input", input_path,
            "--output", output_dir,
            "--rename", rename_name,
        ]
        # Diese Zusatz-Flags versteht nur scan_to_unity_pipeline.py; bei
        # ply_to_fbx_textured.py werden sie einfach nicht mitgeschickt, wenn
        # nicht gesetzt/relevant. scan_to_unity_pipeline.py ignoriert unbekannte
        # Flags nicht -- deshalb nur anhaengen, wenn das passende Skript aktiv ist.
        script_name = os.path.basename(self.script_path_var.get())

        if script_name == "scan_to_unity_pipeline.py":
            if self.target_height_var.get():
                cmd += ["--target-height", self.target_height_var.get()]
            if self.mirror_var.get():
                cmd += ["--mirror-x"]
            if self.skip_cleanup_var.get():
                cmd += ["--skip-cleanup"]
            if self.no_bake_var.get():
                cmd += ["--no-bake"]

        if self.bake_size_var.get():
            cmd += ["--bake-size", self.bake_size_var.get()]
        if self.margin_var.get():
            cmd += ["--margin", self.margin_var.get()]

        return cmd

    def _on_run_clicked(self):
        if not self._validate_inputs():
            return

        self._save_current_config()

        files = list_input_files(self.input_var.get())
        if not files:
            messagebox.showerror(
                APP_TITLE,
                "Keine .ply/.stl Dateien im Input-Ordner gefunden.",
            )
            return

        output_root = self.output_var.get()
        os.makedirs(output_root, exist_ok=True)

        self.run_button.configure(state="disabled")
        self.status_label.configure(text="Laeuft...")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        thread = threading.Thread(target=self._run_all_files, args=(files, output_root), daemon=True)
        thread.start()

    def _run_all_files(self, files, output_root):
        """Verarbeitet jede Eingabedatei einzeln und legt sie in einen eigenen,
        fortlaufend nummerierten Unterordner ab (z.B. Playermodell_0007)."""
        total = len(files)
        overall_rc = 0

        for idx, filepath in enumerate(files, start=1):
            number = take_next_number(output_root)
            folder_name = f"Playermodell_{number:04d}"
            target_dir = os.path.join(output_root, folder_name)
            os.makedirs(target_dir, exist_ok=True)

            self.after(0, self._log, f"\n=== [{idx}/{total}] {os.path.basename(filepath)} -> {folder_name} ===")
            cmd = self._build_command(filepath, target_dir, folder_name)
            self.after(0, self._log, "> " + " ".join(f'"{c}"' if " " in c else c for c in cmd))

            rc = self._run_single(cmd)
            if rc != 0:
                overall_rc = rc
                self.after(0, self._log, f"  Fehlercode {rc} -- fahre trotzdem mit der naechsten Datei fort.")

        self.after(0, self._on_process_finished, overall_rc)

    def _run_single(self, cmd):
        # PYTHONUNBUFFERED erzwingt, dass Blenders eingebetteter Python-Interpreter
        # print()-Ausgaben sofort statt gepuffert weitergibt -- sonst kommt in der
        # Pipe (anders als im Terminal) oft alles erst ganz am Ende oder in falscher
        # Reihenfolge an.
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
            "script_path": self.script_path_var.get(),
            "blender_path": self.blender_path_var.get(),
            "input_path": self.input_var.get(),
            "output_path": self.output_var.get(),
            "target_height": self.target_height_var.get(),
            "bake_size": self.bake_size_var.get(),
            "margin": self.margin_var.get(),
            "mirror": self.mirror_var.get(),
            "skip_cleanup": self.skip_cleanup_var.get(),
            "no_bake": self.no_bake_var.get(),
        })

    def destroy(self):
        self._save_current_config()
        super().destroy()


if __name__ == "__main__":
    app = PipelineGUI()
    app.mainloop()
