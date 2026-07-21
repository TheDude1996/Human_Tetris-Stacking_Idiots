"""
Automatisierte Mesh-Aufbereitung für Tetris-Scan-STLs
=======================================================

Was das Skript macht (pro STL-Datei im Eingabeordner):
1. Doppelte Vertices/Faces entfernen (typisches Kinect-Rauschen)
2. Nicht referenzierte Vertices entfernen
3. Löcher schließen (Kinect-Scans haben oft Lücken an Armen/Beinen)
4. Kleine, isolierte "Schmutz-Inseln" entfernen (Rauschpartikel im Scan)
5. Polygonzahl auf ein Ziel für Echtzeit-Nutzung reduzieren (Decimation)
6. Normalen neu berechnen (nötig nach Decimation/Reparatur)
7. Auf eine einheitliche Größe skalieren + zentrieren (damit alle 7
   Tetris-Formen ins gleiche Unity-Raster passen)
8. Als sauberes STL exportieren

Installation:
    pip install pymeshlab --break-system-packages

Nutzung:
    python mesh_cleanup_batch.py --input ./raw_scans --output ./clean_scans

Optional:
    --target-faces 15000      Ziel-Polygonzahl (Default: 15000)
    --target-height 2.0       Zielhöhe in Metern nach Skalierung (Default: 2.0)
    --max-hole-size 300       Maximale Lochgröße, die geschlossen wird
"""

import argparse
import sys
from pathlib import Path

import pymeshlab


def clean_mesh(input_path: Path, output_path: Path, target_faces: int,
               target_height: float, max_hole_size: int) -> None:
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(str(input_path))

    faces_before = ms.current_mesh().face_number()

    # 1+2) Rauschen/Duplikate entfernen
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_unreferenced_vertices()

    # 3) Kleine Rausch-Inseln entfernen, bevor Löcher geschlossen werden
    #    (verhindert, dass winzige losgelöste Fragmente mitgeschleppt werden)
    ms.meshing_remove_connected_component_by_diameter()

    # 4) Löcher schließen (typisch bei Kinect-Scans an Achseln, zwischen Beinen etc.)
    ms.meshing_close_holes(maxholesize=max_hole_size)

    # 5) Decimation auf Ziel-Polygonzahl (nur falls nötig)
    if ms.current_mesh().face_number() > target_faces:
        ms.meshing_decimation_quadric_edge_collapse(
            targetfacenum=target_faces,
            preservenormal=True,
            preservetopology=True,
        )

    # 6) Normalen neu berechnen
    ms.compute_normal_per_vertex()
    ms.compute_normal_per_face()

    # 7) Skalieren + zentrieren, damit alle Figuren im gleichen Tetris-Raster
    #    dieselbe effektive Größe haben
    bbox = ms.current_mesh().bounding_box()
    current_height = bbox.dim_y()  # Y = vertikale Achse bei Kinect-Scans
    if current_height > 0:
        scale_factor = target_height / current_height
        ms.compute_matrix_from_translation_rotation_scale(
            scalex=scale_factor, scaley=scale_factor, scalez=scale_factor
        )

    # Zentrieren auf Ursprung (Mittelpunkt der Bounding Box)
    bbox = ms.current_mesh().bounding_box()
    center = bbox.center()
    ms.compute_matrix_from_translation_rotation_scale(
        translationx=-center[0], translationy=-bbox.min()[1], translationz=-center[2]
    )

    faces_after = ms.current_mesh().face_number()

    ms.save_current_mesh(str(output_path))
    print(f"  {input_path.name}: {faces_before} -> {faces_after} Faces")


def main():
    parser = argparse.ArgumentParser(description="Batch-Aufbereitung von Scan-STLs")
    parser.add_argument("--input", required=True, help="Ordner mit Roh-STLs")
    parser.add_argument("--output", required=True, help="Zielordner für saubere STLs")
    parser.add_argument("--target-faces", type=int, default=15000)
    parser.add_argument("--target-height", type=float, default=2.0)
    parser.add_argument("--max-hole-size", type=int, default=300)
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    stl_files = sorted(input_dir.glob("*.stl"))
    if not stl_files:
        print(f"Keine .stl-Dateien in {input_dir} gefunden.")
        sys.exit(1)

    print(f"Verarbeite {len(stl_files)} Datei(en)...")
    for stl_file in stl_files:
        out_file = output_dir / stl_file.name
        try:
            clean_mesh(stl_file, out_file, args.target_faces,
                       args.target_height, args.max_hole_size)
        except Exception as e:
            print(f"  FEHLER bei {stl_file.name}: {e}")

    print("Fertig.")


if __name__ == "__main__":
    main()
