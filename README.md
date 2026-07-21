Human Tetris — Kinect-Scan Edition

Ein Tetris-Klon in Unity, bei dem die Blöcke echte 3D-Scans von Menschen sind, die Tetromino-Formen nachstellen. Gesteuert wird per Kinect-Bewegungserkennung, und die Melodie entsteht live aus einer Spieler-Audioaufnahme.

Features
🧩 Tetromino-Steine als 3D-Scans echter Personen (STL, per ReconstructMe + Kinect erstellt)
🎮 Steuerung per Kinect v1 Skeleton-Tracking (kein Controller nötig)
🎨 Automatische Farbeinfärbung pro Steinart (klassisches Tetris-Farbschema)
🎵 Prozeduraler Melodie-Sampler: 2-Sekunden-Sprachaufnahme wird per Pitch-Shifting zur Tetris-Melodie ("Korobeiniki")
🧹 Automatisierte Mesh-Bereinigungs-Pipeline (Lochreparatur, Decimation, Normalisierung)
Tech Stack

Unity · C# · Kinect for Windows SDK v1.8 · ReconstructMe · Python / PyMeshLab

Projektstruktur
/scans/           Rohe & bereinigte STL-Scans der Tetrisformen
/tools/           Python-Skripte zur Mesh-Automatisierung (PyMeshLab)
/Assets/Scripts/  Unity-Spiellogik, Kinect-Input, Melodie-Sampler
Status

🚧 In aktiver Konzeptions-/Prototypenphase — Architektur & Kernfeatures geplant, erste Skripte (Mesh-Cleanup, Melodie-Sampler) implementiert.
