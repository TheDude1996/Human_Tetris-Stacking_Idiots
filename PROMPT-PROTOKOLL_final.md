# Prompt-Protokoll final — Human Tetris Scan-Pipeline

Zusammenfassung aller Prompt-Protokolle zur Scan-Pipeline (Rohscan → Blender → Unity) in zeitlicher Reihenfolge. Quellen:

| Quelle | Inhalt |
|---|---|
| `PROMPT-PROTOKOLL website.md`, Abschnitt 18 | Pipeline-Grafik für die Website (08.10.2026) |
| `PROMPT-PROTOKOLL.md` im Repo `HumanTetrisUnity`, Einträge 12–14 | Anbindung der Scan-Ordner an das Spiel (02.11.2026) |
| `PROMPT-PROTOKOLL low poly script.md` | Low-Poly-Skript `ply_head_to_lowpoly_glb.py` (05.11.2026) |
| `PROMPT-PROTOKOLL pipeline tool V6-V8.md` | Pipeline-Tool V6 bis V8 (23.11.2026) |

Für die Entstehung der GUI-Versionen V1 bis V5 im Juli 2026 gibt es keine Prompt-Protokolle. Den Stand beschreiben `Uebergabedokument_2_1_Content-Pipeline.docx` (23.07.2026) und `GUI_Pipeline_Dokumentation_Final.docx` (29.07.2026).

## Zeitleiste

| Datum | Stand | Ablage |
|---|---|---|
| 21.–23.07.2026 | Konzept Content-Pipeline: eine Person pro Tetris-Form, S/Z und J/L per Spiegelung, Blender-Skripte für Cleanup und Textur-Export | `Projektplan_Uebergabedokument.docx`, `Uebergabedokument_2_1_Content-Pipeline.docx` |
| 24.–28.07.2026 | GUI `gui_app.py` / `PipelineTool.exe`, Versionen bis V3 | `GUI_FINAL_V2.zip`, `gui_pipeline_V3/` |
| 29.07.2026 | V4 und V5: Export als GLB statt FBX, Würfel-Skalierung, fester Dateiname `PlayerHead.glb`, Ordner `Playermodell_XXXX` mit `.pipeline_counter.json` | `Content_Pipeline_V4/`, `Content_Pipeline_V5/` |
| 08.10.2026 | Pipeline-Grafik für die Website | `pipeline.html` (Website) |
| 02.11.2026 | Spiel lädt die Köpfe zur Laufzeit aus dem Scan-Ordner | Repo `HumanTetrisUnity` |
| 05.11.2026 | Low-Poly-Skript, Köpfe 0001–0004 ersetzt | `ply_head_to_lowpoly_glb.py` |
| 23.11.2026 | V6 Final: nur Low-Poly-Skript, Spielernamen als `name.txt` | `Pipeline V6 Final/` (Commit `1af03be`) |
| 23.11.2026 | V7: nur neueste `.ply`, Name aus dem Dateinamen | `Pipeline V7/` (Commit `0da12f4`) |
| 23.11.2026 | V8: Auswahlliste der Dateien, Icon | `Pipeline V8/` (Commits `f871850`, `4d19658`) |

---

## 08.10.2026 — Pipeline-Grafik im Human-Tetris-Stil

Claude Sonnet 5.5. Quelle: `PROMPT-PROTOKOLL website.md`, Abschnitt 18.

| Nr. | Prompt (Wortlaut) | Ergebnis |
|---:|---|---|
| 1 | „verschönere die grafik im stiel der folgenden website“ | Inline-SVG des Ablaufs „ReconstructMe Scan → Blender Pipeline → Übertragung → Main Menu → Spielen“ im Website-Stil (dunkler Hintergrund, Neongrün, Cyan, Pink, nummerierte Karten) |
| 2 | „kannst du diese darstellung als rerines html bereitstellen“ | `pipeline.html` mit HTML und CSS, Glow- und Hover-Effekten |
| 3 | „die texte passen nicht in die kacheln... mach es so neben einander wie im beispiel obwn“ | Kacheln nebeneinander, Schrift und Abstände skalieren mit der Fensterbreite |
| 4 | „ich brauche ein prompt protokoll“ | Prompt-Protokoll |

---

## 02.11.2026 — Scan-Ordner im Spiel

Quelle: `PROMPT-PROTOKOLL.md` im Repo `HumanTetrisUnity`, Einträge 12–14.

### Spielerdaten aus dem Scan-Netzwerkordner

**Prompt:** „wir haben eine scan pipeline die an einen netzwerk ordnber ordner mit fortlaufender nummer übermittelt, in diesen ordner liegen jewils die player heads später sollen auch die sampels und highscores in diesen ordner zurück gesichert werden, es benötigt die option die daten zur runtime zu laden baue das“ / „C:\Users\sever\Desktop\putput nutze dien pfad zum testen der ordner strucktur“

**Umsetzung:** `PlayerDataManager.cs` mit `HumanTetris_config.json`: Köpfe werden zur Laufzeit per glTFast aus `<scansRoot>/Playermodell_XXXX/` geladen, Spielerauswahl im Hauptmenü, `sample.wav` und `highscore.json` werden in den Spielerordner zurückgeschrieben.

### Helligkeit und Auslieferung der Scans

**Prompt:** „das sind die gleichen modelle auf der website sind sie gut von der helligkeit versuche es über die konfiguration anzupassen ist es möglich den ordener puput in dem die scans liegen zusammen mit dem spiel auszuliefern? …“

**Umsetzung:** `headBrightness` und `headSelfLight` in der Konfiguration. Die Scans liegen im Projekt unter `Scans/` und werden beim Build neben die .exe kopiert.

### Kopfgröße

**Prompts:** „finde heraus wie viel größer man die köpfe skalieren kann ohne das sie aus den blöcken herausschauen“ / „zeig mal head size 0,95“ / „hinten fehlt die glas kante“ / „Richte diese 0,95 Kopfgröße noch fest in den Code ein und commite und pushen“

**Umsetzung:** Bis `headSize` 1,0 ragt kein Kopf aus dem Glas; Standard 0,95.

---

## 05.11.2026 — Low-Poly-Köpfe

Quelle: `PROMPT-PROTOKOLL low poly script.md`.

### 1. Neues Skript für Low-Poly-GLBs

**Prompt:** „hier sind die skripte mit denen die roh scans im .ply vormat verarbeitet werden um für human ttris genuzt zu werden, erstelle ein neues skript das mithilfe von blender die ply kopfscans in polygon reduzierte glb datein umwandelt“

**Umsetzung:** `ply_head_to_lowpoly_glb.py`: PLY importieren, Cleanup, optional Skalierung/Spiegelung, Decimate auf `--target-faces` (Standard 5.000 Dreiecke), UV-Unwrap, Farbe und optional Normal-Map vom High-Poly auf das Low-Poly backen, GLB mit eingebetteter Textur. Joel-Scan von 483.614 auf 5.000 Dreiecke in ca. 17 s.

### 2. Test in Spiel und Blender

**Prompts:** „öfnne mir das glb in muman tetris“ / „öfnne mir die low poly variante in blender“

**Umsetzung:** Testkopf im TestBuild fehlerfrei geladen und in Blender 5.2 geöffnet.

### 3. Alle vier Scans umwandeln

**Prompts:** „ok mach das mit allen 4 scans und lege sie entsprechend in playermodell nach aktueller names konvention ab“ / „starte das spiel“

**Umsetzung:** Joel → 0001, Joko → 0002, Kacpar → 0003, Severin → 0004, je 5.000 Dreiecke mit Normal-Map (ca. 4 statt 16–18 MB). `PlayerHead.glb`, `PlayerHead.png` und `PlayerHead_normal.png` in `TestBuild/Scans` und `HumanTetrisUnity/Scans`. Highscores blieben erhalten.

### 4. Prompt-Protokoll

**Prompt:** „erstlle ein kurzes prompt protokoll“

**Umsetzung:** `PROMPT-PROTOKOLL low poly script.md`.

---

## 23.11.2026 — Pipeline-Tool V6 bis V8

Claude Code, Claude Opus 5.5. Quelle: `PROMPT-PROTOKOLL pipeline tool V6-V8.md` (dort alle Prompts im Wortlaut).

| Nr. | Prompt (gekürzt) | Ergebnis |
|---:|---|---|
| 1 | „wir möchten die player nummern mit namen verknüpfen … sollen wir den namen in die datei oder als name nutzen“ | Empfehlung: fester Dateiname `name.txt`, Name als Inhalt (UTF-8) |
| 2 | „… engine ist unity, das pipline tool ist phyton“ | Spiel zeigt den Namen in Spielerkarte und Bestenliste |
| 3 | „… finde die aktuellste version des pipline tools nach upload datum … instaliere dafür phyton“ | V5 als neueste Version erkannt, Python 3.12.10 installiert, Feld „Spielername“ und „Namen nachtragen...“, `name.txt` pro Spieler-Ordner |
| 4 | „pack es auf dem desktop in einen ordenr piplive V6 Final“ | `Desktop/Pipeline V6 Final` |
| 5 | „… baue nochmal neu nur mit dem im ordner vorhandenen skript“ | GUI fest auf `ply_head_to_lowpoly_glb.py`, nur `.ply`, Optionen des Skripts |
| 6 | „lade den ordner ins repo hoch“ / „pushe und commite die änderungen am spiel“ | V6 Final auf `main`, Spiel auf `feature/grafik-audio-spielerdaten` |
| 7 | „… immer nur die neuste datei … name des .ply in den spielernamen …“ | Nur neueste `.ply`, Name aus dem Dateinamen, Schutz vor doppelter Verarbeitung |
| 8 | „ja pushe es auf main als V7“ | `Pipeline V7` |
| 9 | „… im dropdown beim input ordner auch die datein anwählen …“ | Auswahlliste aller `.ply`, neueste vorausgewählt |
| 10 | „ja pushe es als V8 auf main“ | `Pipeline V8` |
| 11 | „… pipeline.ico baue Dieses icon für die pipline ein es soll überall angezeigt werden“ | Icon in Exe, Titelleiste, Taskleiste und Dialogen |
| 12 | „kannst du v8 überschreiben“ | `Pipeline V8` mit Icon überschrieben |
| 13 | „erstelle ein kleines protokoll … und erstelle protokoll_final“ | `PROMPT-PROTOKOLL pipeline tool V6-V8.md` und dieses Protokoll |

---

## Endstand der Pipeline (V8)

- **Ordner:** `Pipeline V8/` mit `PipelineTool.exe`, `ply_head_to_lowpoly_glb.py`, `gui_app.py` (Quellcode), `PipelineTool.spec` (Bauanleitung) und `pipeline.ico`.
- **Ablauf:** Datei im Input-Ordner wählen (Standard: neueste `.ply`), Namen prüfen, „Pipeline starten“. Blender wandelt den Scan in einen Low-Poly-Kopf um.
- **Ergebnis pro Spieler:** `<Output>/Playermodell_XXXX/` mit `PlayerHead.glb` (5.000 Dreiecke, Textur eingebettet), `PlayerHead.png`, `PlayerHead_normal.png` und `name.txt`. Die Nummer kommt aus `.pipeline_counter.json` im Output-Ordner.
- **Im Spiel:** Der Output-Ordner ist der `scansRoot` aus `HumanTetris_config.json`. Das Spiel lädt den Kopf zur Laufzeit und zeigt den Namen aus `name.txt` in der Spielerkarte und in der Bestenliste.
- **Exe neu bauen:** `python -m PyInstaller --noconfirm PipelineTool.spec` im Ordner `Pipeline V8` (Python 3.12 mit PyInstaller; `pipeline.ico` muss daneben liegen).
- **Voraussetzung:** Blender 4.x oder 5.x; der Pfad zu `blender.exe` wird beim ersten Start unter „Einstellungen“ eingetragen.
