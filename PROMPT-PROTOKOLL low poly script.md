# Prompt-Protokoll — Human Tetris Scan-Pipeline (Low-Poly-Köpfe)

Dieses Protokoll dokumentiert die Prompts aus dem vorliegenden Chat (05.11.2026) und die jeweils umgesetzten Änderungen.

## 1. Neues Skript für Low-Poly-GLBs

**Prompt:** „hier sind die skripte mit denen die roh scans im .ply vormat verarbeitet werden um für human ttris genuzt zu werden, erstelle ein neues skript das mithilfe von blender die ply kopfscans in polygon reduzierte glb datein umwandelt“

**Umsetzung:** `ply_head_to_lowpoly_glb.py` wurde angelegt. Ablauf: PLY importieren, Cleanup (doppelte Vertices, lose Fragmente, Löcher), optional Skalierung/Spiegelung, Ursprung setzen, Kopie per Decimate auf `--target-faces` (Standard 5.000 Dreiecke) reduzieren, UV-Unwrap, Farben (und optional Normal-Map mit `--bake-normals`) vom High-Poly-Scan auf das Low-Poly backen, nur das Low-Poly als GLB mit eingebetteter Textur exportieren. Unbekannte GUI-Argumente werden ignoriert, damit das Skript im PipelineTool nutzbar ist. Test mit Blender 5.2: Joel-Scan von 483.614 auf 5.000 Dreiecke in ca. 17 s.

## 2. Low-Poly-Kopf im Spiel testen

**Prompt:** „öfnne mir das glb in muman tetris“

**Umsetzung:** Das Test-GLB wurde als `TestBuild/Scans/Playermodell_0005/PlayerHead.glb` abgelegt und `HumanTetris.exe` gestartet. Das Spiel-Log bestätigte das fehlerfreie Laden über glTFast.

## 3. Low-Poly-Kopf in Blender ansehen

**Prompt:** „öfnne mir die low poly variante in blender“

**Umsetzung:** Blender 5.2 wurde mit leerer Szene gestartet, das GLB importiert und die Ansicht auf Material-Vorschau gestellt.

## 4. Alle vier Scans umwandeln und einsortieren

**Prompt:** „ok mach das mit allen 4 scans und lege sie entsprechend in playermodell nach aktueller names konvention ab“

**Umsetzung:** Zuordnung über die Mesh-Namen der bestehenden GLBs geprüft (Joel → 0001, Joko → 0002, Kacpar → 0003, Severin → 0004). Alle vier Scans mit Normal-Map auf je 5.000 Dreiecke reduziert (GLB jeweils ca. 4 statt 16–18 MB). `PlayerHead.glb` und `PlayerHead.png` in `TestBuild/Scans` und `HumanTetrisUnity/Scans` ersetzt, `PlayerHead_normal.png` ergänzt. Highscores und `.pipeline_counter.json` blieben unverändert, die High-Poly-Originale liegen weiterhin in `putput`. Der Testordner `Playermodell_0005` wurde entfernt (in einen temporären Ordner verschoben). Nichts wurde ins Git-Repo committet.

## 5. Spiel starten

**Prompt:** „starte das spiel“

**Umsetzung:** `HumanTetris.exe` aus dem TestBuild gestartet. Das Log zeigte bis dahin geladene Köpfe für 0004 und 0001 und keine Fehler.

## 6. Prompt-Protokoll

**Prompt:** „erstlle ein kurzes prompt protokoll“

**Umsetzung:** Dieses Protokoll wurde als `PROMPT-PROTOKOLL.md` im Ordner `pipeline tool` angelegt, im Format des Protokolls der Website.
