# Prompt-Protokoll — Human Tetris

Dieses Protokoll dokumentiert die Prompts aus dem vorliegenden Chat und die jeweils umgesetzten Änderungen. Eine vollständige Historie der Website-Erstellung vor diesem Gespräch liegt hier nicht vor.

## 1. Versionswechsel zur 90er-Seite

**Prompt:** „der 90er version button soll immer auf die index90 führen da dort alle inhalte in einer website sind“

**Umsetzung:** Die Versionswechsel auf der Start-, Spiel- und About-Seite wurden als direkte Links zu `index90.html` eingerichtet.

## 2. Auffälligeres Website-Design

**Prompt:** „mach die website richtig krass und flashy“

**Umsetzung:** Die modernen Seiten erhielten ein Neon-Arcade-Design mit dunklem Hintergrund, leuchtenden Akzentfarben, Animationen, Hover-Effekten und responsiven Layouts. Auf der Spielseite wurden vorhandene Screenshots statt Bildplatzhaltern eingebunden.

## 3. 90er-Version im Original belassen

**Prompt:** „belasse die 90er variante im orginal“

**Umsetzung:** `index90.html` wurde auf den ursprünglichen Inhalt und Aufbau zurückgesetzt. Eine gezielte CSS-Ausnahme verhindert, dass die neuen globalen Styles das ursprüngliche Erscheinungsbild dieser Seite überschreiben.

## 4. Joel-Version in die 90er-Seite übernehmen

**Prompt:** „nimm die index aus dem ordener joel und aktualiesiere die index 90 entsprechend tausche auch die assets mi denen aus dem ordner joel“

**Umsetzung:** Die Inhalte und der Bildvergleich aus `joel/index.html` wurden in `index90.html` übernommen. Die benötigten Bilder wurden in den Hauptordner `assets` konsolidiert.

## 5. Cursor und Bilder für die moderne Version

**Prompt:** „ziehe den cursor auch auf die neue website um nutze auf der neuen version auch die bilder aus der index 90“

**Umsetzung:** Der Joel-Cursor wurde auf die moderne Website übertragen und die modernen Start-/About-Seiten verwenden die Kinect- und Tiefenvergleichsbilder aus der 90er-Version.

## 6. Asset-Ordner aufräumen

**Prompt:** „räume die asset ordner auf und lege alle benötigten bilder in den haupt asset ordner“

**Umsetzung:** Benötigte Bilder und Cursor wurden im Hauptordner `assets` gesammelt. Byte-identische Duplikate wurden aus `joel/assets` entfernt und die Asset-Pfade aktualisiert.

## 7. Joel-Ordner entfernen

**Prompt:** „kann der ordner joel jetzt sicher entfernt werden ?“ / „mache das“

**Umsetzung:** Das Stylesheet für die 90er-Seite wurde als `style90.css` in den Hauptordner verschoben. Danach wurden verbliebene Verweise geprüft und der nicht mehr benötigte Ordner `joel` entfernt.

## 8. Moderne Technik-Unterseite

**Prompt:** „wir brauchen eine weiter unterseite der modernen variante sie soll Technik heißen“

**Umsetzung:** `technik.html` wurde mit einer Erklärung zur Kinect-Tiefenerfassung angelegt und in die Navigation der modernen Seiten aufgenommen.

## 9. Scan- und Modellierungsworkflow

**Prompt:** „füge auf der technik seite einen absatz zum scannen der spieler mit reconstruct me und bfleder workflow“

**Umsetzung:** Die Technikseite beschreibt den Scan der Spielenden mit ReconstructMe und Kinect sowie die anschließende Bereinigung und Vorbereitung des Modells in Blender.

## 10. Laterale Teamstruktur

**Prompt:** „auf der about us seite wird das team vorgestellt und sehr kleinteilig aufgeteilt, bitte spiegel in der auflistung unsere latarale führungs strucktur wieder“

**Umsetzung:** Die Teamdarstellung wurde von einzelnen Fachrollen auf gemeinsame Entscheidungsfindung, vernetzte Arbeit und geteilte Verantwortung umgestellt.

## 11. Erklärungstext entfernen

**Prompt:** „entferne den geschollenen text unter Zusammenarbeit auf Augenhöhe — Ein Team. Eine gemeinsame Richtung.“

**Umsetzung:** Der erklärende Absatz wurde entfernt; Überschrift und Teamkarten blieben bestehen.

## 12. Viertes Teamfeld

**Prompt:** „denk dir ein 4 feld aus damit jeder der mitglieder sein bild in eine kachel bekommen kann“

**Umsetzung:** Eine vierte gleichberechtigte Teamkachel „Neue Perspektiven“ wurde ergänzt und das Raster auf vier Kacheln erweitert.

## 13. Drehbare GLB-Modelle

**Prompt:** „bereite die about us seite so vor das in die 4 untern boxen drehbare glb modelle abgelegt werden können, vergib auch namen für die 4 felder so das ich später nur die datein mit korrktem namen in assets ablegen muss“

**Umsetzung:** Vier interaktive Modellplätze mit eindeutigen Dateinamen (`team-richtung.glb`, `team-gestaltung.glb`, `team-umsetzung.glb`, `team-impulse.glb`) wurden vorbereitet.

## 14. Externe Daten vermeiden

**Prompt:** „es dürfen keine externen daten geladen werden finde eine möglichkeit das ohne cdn zu machen“

**Umsetzung:** Der 3D-Viewer wurde lokal unter `assets/vendor` eingebunden. Eine Content-Security-Policy beschränkt die About-Seite auf lokale Ressourcen.

## 15. Erstes GLB-Modell einsetzen

**Prompt:** „ich habe eine glb in assets abgelegt passe den namen an und prüfe ob das modell lädt“

**Umsetzung:** `Playermodell_0025.glb` wurde nach Auswahl der ersten Teamkachel zu `team-richtung.glb` umbenannt und das Laden im Browser geprüft.

## 16. GLB-Hinweis entfernen

**Prompt:** „bitte entferne den info text zu den glb datein …“

**Umsetzung:** Der allgemeine Hinweistext zu den Modell-Dateinamen wurde von der About-Seite entfernt; die Dateinamen bleiben in den leeren Modellkacheln sichtbar.

## 17. Bilder nach ihrer Position benennen

**Prompt:** „da ich später die bilder auf der website noch austauschen möchte kannst du bitte alle bilder so bennnen wie ihre position auf der website ist? benenne die aktuellen datein um damit sie weiterhin als platzhalter fungieren ich sie aber später einfacher tauschen kannn“

**Umsetzung:** Die verwendeten Bilder und Cursor wurden nach ihrem Website-Einsatz umbenannt, zum Beispiel `start-hero-banner.png`, `gameplay-motion-tracking.png` und `cursor-slider-90er.png`. Alle Referenzen in HTML und CSS wurden aktualisiert. Nicht mehr eingebundene ältere Kinect-Bilder wurden beibehalten.

## 18. Prompt-Protokoll: Pipeline-Grafik im Human-Tetris-Stil

**Datum:** 08.10.2026  
**Modell:** Claude Sonnet 5.5

| Nr. | Prompt (Wortlaut) | Eingabe | Ergebnis |
|---:|---|---|---|
| 1 | „verschönere die grafik im stiel der folgenden website“ | Zwei Screenshots: (1) Ablaufdiagramm „ReconstructMe Scan → Blender Pipeline → Übertragung → Main Menu → Spielen“, (2) Human-Tetris-Website als Stilvorlage | Inline-SVG-Grafik mit dunklem Hintergrund, Neongrün, Cyan, Pink, nummerierten Karten und grün gefülltem Schlusskasten „Spielen“ |
| 2 | „kannst du diese darstellung als rerines html bereitstellen“ | – | `pipeline.html` mit HTML und CSS, Glow- und Hover-Effekten sowie Farbvariablen |
| 3 | „die texte passen nicht in die kacheln... mach es so neben einander wie im beispiel obwn“ | – | `pipeline.html` überarbeitet: Kacheln nebeneinander; Schrift, Abstände und Pfeile skalieren mit der Fensterbreite; lange Wörter werden getrennt |
| 4 | „ich brauche ein prompt protokoll“ | – | Dieses Prompt-Protokoll |

### Verwendete Stilvorgaben

- Hintergrund `#0A0B1A`, Karten `#12142A`, Rand `#2A2D4D`
- Akzentfarben: Grün `#A6FF00`, Cyan `#4DE8FF`, Pink `#FF1493`
- Fette Überschriften mit enger Laufweite und gedämpfter Grautext
- Letzter Schritt als grün gefüllter Kasten in Button-Optik

### Anmerkungen

- Prompt 1 war knapp formuliert; der Stil ergab sich aus dem Screenshot der Website.
- Prompt 3 behob das Darstellungsproblem aus Prompt 2: Texte liefen über die Kachelränder.
- Das Briefumschlag-Symbol zwischen Schritt 2 und 3 aus dem Beispielbild wurde bewusst weggelassen.

## Ergebnis

Die modernen Seiten verwenden das überarbeitete Arcade-Design und umfassen jetzt eine Technik-Unterseite sowie eine About-Seite mit vier vorbereiteten Team-Modellplätzen. Die separate 90er-Seite behält ihre Gestaltung und nutzt die konsolidierten Assets aus dem Hauptordner.

## Prompt 5: Texte vermenschlichen (About us)

**Prompt:**
> Das sind website texte die copilot erstellt hat.... sie klingen sehr stark nach ki, bitte vermenschliche die texte behalte die groben absätze bei damit ich die texte auf der website ändern kann

**Eingabe:** Von Copilot erstellte Texte der Seite „About us“ (Team, Idee, Motivation, Zusammenarbeit 01–04).

**Ergebnis:** Überarbeitete Texte, lockerer und konkreter, Struktur und Zwischenüberschriften unverändert.

---

## Prompt 6: Texte weiter verbessern, Überschriften vorschlagen

**Prompt:**
> mach bitte diese texte auch besser schlage auch gerne andere überschriften vor

**Ergebnis:** Kürzere, konkretere Version der About-us-Texte mit je ein bis zwei alternativen Überschriften. Hinweis, dass einige Aussagen (z. B. „Feste Rollen gibt es kaum“, Beispiel mit dem L-Stein) vom Team geprüft werden sollen.

---

## Prompt 7: Texte der Seite „Spiel“

**Prompt:**
> für diese texte auch im stiel der ersten alternative

**Eingabe:** Texte der Seite „Spiel“ (Hero, „Direkt aus dem Spiel“, Spielprinzip, Steuerung, Erlebnis, „Ready. Set. Pose!“).

**Ergebnis:** Texte im gleichen Stil wie in Prompt 6, mit Alternativen für Überschriften und Button. Die doppelten Inhalte bei „Steuerung“ und „Der Controller bist du“ wurden unterschiedlich formuliert. Zu prüfen: „Ausfallschritt“, „Stell dich vor die Kinect“ und die Bewegung „nach oben“.

---

## Prompt 8: Protokoll für Markdown

**Prompt:**
> protokolire bitte die promps so das ich einfach in mein markdownfile koopieren kann

