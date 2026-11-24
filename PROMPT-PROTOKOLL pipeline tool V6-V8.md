# Prompt-Protokoll — Pipeline-Tool V6 bis V8 (Spielernamen, Dateiauswahl, Icon)

Dieses Protokoll dokumentiert die Prompts aus dem Chat vom 23.11.2026 (Claude Code, Claude Opus 5.5) und die jeweils umgesetzten Änderungen am Pipeline-Tool. Die Änderungen am Spiel stehen zusätzlich in `PROMPT-PROTOKOLL.md` im Repo `HumanTetrisUnity` (Eintrag 36).

## 1. Spielernummern mit Namen verknüpfen

**Prompt:** „wir möchten die player nummern mit namen verknüpfen, die namen sollen als .txt in den playerordnern gespeichert werden, und im spieler menu sowie in der bestenliste ausgegeben werden, die .txt wird vom pipline tool mit in den ordner gelegt, sie wird wie folgt aussehen NAME.txt, sollen wir den namen in die datei oder als name nutzen“

**Umsetzung:** Empfehlung: fester Dateiname `name.txt`, der Name steht in der ersten Zeile (UTF-8). Dateinamen erlauben Zeichen wie `/ : ? *` nicht, Umlaute gehen je nach Tool kaputt, und der Pfad ist immer gleich.

## 2. Namen im Spiel anzeigen

**Prompt:** „C:\Users\severin.benthin\OneDrive - BE O365 MS-Cloud\Desktop\HumanTetrisUnity\HumanTetrisUnity , engine ist unity, das pipline tool ist phyton“

**Umsetzung:** Im Spiel liest `PlayerDataManager` die `name.txt` (ohne sie gilt der Dateiname einer anderen `.txt`, sonst bleibt die Nummer). Die Spielerkarte zeigt „Name  #0004“, die Bestenliste den Namen statt „P0004“ (gekürzt auf 8 Zeichen). Das Pipeline-Tool schrieb noch keine `name.txt`.

## 3. Aktuelle Pipeline-Version holen und umbauen

**Prompt:** „https://github.com/TheDude1996/Human_Tetris-Stacking_Idiots finde die aktuellste version des pipline tools nach upload datum lade es herunter und baue das phyton skript um instaliere dafür phyton auf diesem pc“

**Umsetzung:** Neueste Version nach Upload-Datum: `Content_Pipeline_V5` (29.07.2026, Commit `e52b3f4`). Im Repo lag nur die `PipelineTool.exe`; der Quellcode `gui_app.py` stammt aus der lokalen Kopie (die Exe dort ist bytegleich). Python 3.12.10 per winget installiert, dazu PyInstaller. Neues Feld „Spielername“ und Knopf „Namen nachtragen...“; die App schreibt `name.txt` (atomar, UTF-8) in jeden neuen `Playermodell_XXXX`-Ordner. Exe neu gebaut.

## 4. Ordner auf dem Desktop

**Prompt:** „pack es auf dem desktop in einen ordenr piplive V6 Final“

**Umsetzung:** Ordner `Desktop/Pipeline V6 Final` mit Exe, Blender-Skripten, `gui_app.py` und `PipelineTool.spec`.

## 5. Nur noch das Low-Poly-Skript

**Prompt:** „ich hab das einizg benötigte skript in den ordner gelegt baue nochmal neu nur mit dem im ordner vorhandenen skript“

**Umsetzung:** Oberfläche fest auf `ply_head_to_lowpoly_glb.py` umgebaut (Skript-Auswahl entfernt, nur `.ply`). Optionen des Skripts: Ziel-Dreiecke (5.000), Normal-Map (an), Spiegeln, Cleanup, Löcher füllen, kein Bake, optionale Kantenlänge. Ausgabe `PlayerHead.glb/.png/_normal.png` wie bei den vorhandenen Köpfen. Blender läuft ohne eigenes Konsolenfenster. Test mit einem Platzhalter für Blender (auf dem PC ist kein Blender installiert).

## 6. Hochladen

**Prompts:** „lade den ordner ins repo hoch“ / „pushe und commite die änderungen am spiel“

**Umsetzung:** `Pipeline V6 Final` auf `main` (Commit `1af03be`). Spieländerungen auf dem Branch `feature/grafik-audio-spielerdaten` (Commit `bd36b90`).

## 7. Nur die neueste Datei, Name aus dem Dateinamen

**Prompt:** „ich möche noch eine kleine änderung vornehmen, es soll immer nur die neuste datei aus dem input ordner gewählt werden, es soll standardmäßig der name des .ply in den spielernamen übernommen werden das feld zur änderung soll dennoch vorhanden bleiben,“

**Umsetzung:** Pro Lauf nur die neueste `.ply` (nach Änderungsdatum). Das Namensfeld wird mit dem Dateinamen vorbelegt (`Max_Mustermann.ply` → „Max Mustermann“) und bleibt änderbar. Der Input-Ordner wird alle 2 s geprüft; kommt kurz vor dem Start ein neuer Scan dazu, startet die App nicht, sondern lässt zuerst den Namen prüfen. Bereits verarbeitete Dateien lösen eine Rückfrage aus.

## 8. Hochladen als V7

**Prompt:** „ja pushe es auf main als V7“

**Umsetzung:** Fenstertitel „V7“, Ordner `Pipeline V7` auf `main` (Commit `0da12f4`).

## 9. Dateien im Input-Ordner auswählen

**Prompt:** „uns ist aufgefallen das es auch eine möglichkeit geben sollte mit der man im dropdown beim input ordner auch die datein anwählen kann die da drinn liegen,“

**Umsetzung:** Auswahlliste „Datei im Input-Ordner“ mit allen `.ply`, neueste zuerst, mit Datum und Markierung `[neueste]`, plus Knopf „Aktualisieren“. Standard bleibt die neueste; ein neuer Scan wird automatisch gewählt. Eine ältere Datei kann gewählt werden, ihr Dateiname wird als Name vorgeschlagen. Wird die gewählte Datei gelöscht, springt die Auswahl auf die neueste.

## 10. Hochladen als V8

**Prompt:** „ja pushe es als V8 auf main“

**Umsetzung:** Fenstertitel „V8“, Ordner `Pipeline V8` auf `main` (Commit `f871850`).

## 11. Icon

**Prompt:** „https://github.com/TheDude1996/Human_Tetris-Stacking_Idiots/blob/main/pipeline.ico baue Dieses icon für die pipline ein es soll überall angezeigt werden“

**Umsetzung:** Die `pipeline.ico` aus dem Repo enthielt nur eine Größe (256 × 242). Sie wurde transparent auf ein Quadrat erweitert und in den Größen 16–256 px gespeichert. Das Icon ist in die Exe eingebettet (Explorer, Verknüpfungen) und wird für alle Fenster gesetzt (Titelleiste, Taskleiste, Dialoge); eine eigene App-Kennung sorgt dafür, dass die Taskleiste nicht das Python-Icon zeigt. Per Screenshot geprüft.

## 12. V8 überschreiben

**Prompt:** „kannst du v8 überschreiben“

**Umsetzung:** `Pipeline V8` auf `main` mit der Icon-Version überschrieben (Commit `4d19658`).

## 13. Prompt-Protokoll

**Prompt:** „erstelle ein kleines protokoll zu den fpromts der pipline, fasse auch alle anderen promt protokolle zur pipeline aus dem repo zusammen und erstelle protokoll_final“

**Umsetzung:** Dieses Protokoll und `PROMPT-PROTOKOLL_final.md` (Zusammenfassung aller Pipeline-Protokolle).

## 14. V9.1: ReconstructMe-Anbindung und neues Design

**Prompts:** „Kann man aus 2 Anwendungen ein neues fester machen mit eigenen Eingabe Feldern und Design ?“ – „Pipeline Tool v8 von human Tetris repo, Reconstruct me ist ein fertige Software“ – „Mach den Pfad auswählbar wie bei Blender, wir speichern aus reconstruct me per Hand, in den Input Ordner, auch dieser sollte sich in der gui angeben lassen, Design so wie die Website und das Spiel“ – „Commite und Push das als v9.1“

**Umsetzung (Ordner `Pipeline V9.1`, Chat vom 24.11.2026, Claude Opus 5.5):**
- Neue Karte „01 Scan mit ReconstructMe“: Knopf „ReconstructMe starten“ (startet die fertige Software), Statusanzeige „ReconstructMe läuft“.
- Pfad zu ReconstructMe unter „Einstellungen → Programme“ wählbar wie bei Blender (Durchsuchen, wird in `pipeline_gui_config.json` gespeichert, Anzeige „Gefunden / nicht gefunden“).
- Der Input-Ordner bleibt unter „02 Ordner“ wählbar und wird in Karte 01 als Speicherziel angezeigt, mit „Pfad kopieren“ (zum Einfügen im Speichern-Dialog von ReconstructMe) und „Ordner öffnen“.
- Ein neu gespeicherter Scan wird wie bisher automatisch erkannt und ausgewählt; zusätzlich pinker Hinweis „Neuer Scan erkannt“ und ein Signalton.
- Design wie Website und Spiel: Hintergrund `#0A0B1A`, Karten `#12142A`, Rand `#2A2D4D`, Akzente Grün `#A6FF00`, Cyan `#4DE8FF`, Pink `#FF1493`; nummerierte Karten 01–04, grüner Start-Knopf, farbiges Log. Die Oberfläche ist scrollbar (passt auch auf kleine Bildschirme).
- Pipeline-Logik (Blender-Aufruf, Nummerierung, `name.txt`) unverändert gegenüber V8.
- Getestet unter Linux mit Platzhaltern für Blender und ReconstructMe. Die `PipelineTool.exe` muss unter Windows neu gebaut werden: `python -m PyInstaller --noconfirm PipelineTool.spec` im Ordner `Pipeline V9.1`. Hochgeladen als V9.1 auf `main`.
