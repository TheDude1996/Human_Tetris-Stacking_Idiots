"""
scan_to_unity_pipeline.py
--------------------------
Eigenstaendiges Blender-Skript fuer den kompletten Weg vom Rohscan (PLY mit
Vertex-Colors, z.B. aus ReconstructMe) bis zum fertigen, texturierten
Unity-Asset (FBX). Deckt ab:

  1. Cleanup:      wasserdicht machen, Loecher fuellen, lose Fragmente entfernen
  2. Skalierung:    auf Ziel-Koerperhoehe normalisieren (bis Kalibrierungsobjekt-
                    Erkennung existiert, siehe Abschnitt 7 im Uebergabedokument)
  3. Spiegelung:    optional entlang der X-Achse (fuer S->Z bzw. J->L)
  4. UV + Bake:     Smart-UV-Unwrap + Vertex-Colors in Bild-Textur backen
  5. Export:        FBX mit eingebetteter Textur, fertig fuer Unity-Import

Nutzung (Kommandozeile):

  # Einzelne Form, normaler Cleanup + Bake + Export
  blender --background --python scan_to_unity_pipeline.py -- \
      --input /scans/raw/S_2026-07-22_take1.stl \
      --output /scans/processed \
      --target-height 1.75

  # Ganzer Ordner
  blender --background --python scan_to_unity_pipeline.py -- \
      --input /scans/raw --output /scans/processed --target-height 1.75

  # Eine bereits bereinigte Form spiegeln, um eine zweite zu erzeugen
  # (z.B. S.ply -> Z.fbx), ohne sie erneut zu scannen:
  blender --background --python scan_to_unity_pipeline.py -- \
      --input /scans/processed/S.ply \
      --output /scans/processed \
      --mirror-x --rename Z --skip-cleanup

Wichtige Flags:
  --input           Datei oder Ordner mit .ply/.stl Rohscans
  --output          Zielordner fuer die fertigen .fbx (+ .png Texturen)
  --target-height   Ziel-Koerperhoehe in Metern zur Skalierung (Standard: 1.75)
  --mirror-x        Spiegelt das Mesh an der X-Achse (fuer S->Z, J->L)
  --rename NAME     Ueberschreibt den Ausgabedateinamen (nuetzlich bei Spiegelung)
  --skip-cleanup    Ueberspringt Cleanup-Schritte (z.B. wenn Input schon bereinigt ist)
  --bake-size N     Aufloesung der gebackenen Textur (Standard: 2048)
  --no-bake         Kein Textur-Bake, nur Cleanup + Export (falls keine Vertex-Colors)

Hinweis Kalibrierung: Solange die Kalibrierungsobjekt-Erkennung (offener Punkt
Abschnitt 7) nicht implementiert ist, skaliert dieses Skript ersatzweise auf
eine feste Ziel-Koerperhoehe (Bounding-Box in Z). Sobald ihr ein Referenzobjekt
festlegt, kann calibrate_scale() leicht auf "Objekt bekannter Groesse im
Scan finden" umgestellt werden.
"""

import bpy
import bmesh
import sys
import os
import argparse


# ---------------------------------------------------------------------------
# Argumente
# ---------------------------------------------------------------------------

def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []

    p = argparse.ArgumentParser(description="Scan (PLY/STL) -> bereinigtes, texturiertes Unity-FBX")
    p.add_argument("--input", required=True, help="Datei oder Ordner mit .ply/.stl")
    p.add_argument("--output", required=True, help="Zielordner fuer .fbx (+ .png)")
    p.add_argument("--target-height", type=float, default=1.75,
                    help="Ziel-Koerperhoehe in Metern (Standard: 1.75)")
    p.add_argument("--mirror-x", action="store_true",
                    help="Mesh entlang X-Achse spiegeln (S->Z, J->L)")
    p.add_argument("--rename", default=None,
                    help="Ausgabedateiname ohne Endung ueberschreiben")
    p.add_argument("--skip-cleanup", action="store_true",
                    help="Cleanup-Schritte (Loecher fuellen, wasserdicht machen) ueberspringen")
    p.add_argument("--bake-size", type=int, default=2048, help="Textur-Aufloesung")
    p.add_argument("--margin", type=int, default=8, help="Bake-Margin in Pixeln")
    p.add_argument("--no-bake", action="store_true",
                    help="Kein Textur-Bake, nur Cleanup + Export")
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def find_scan_files(input_path):
    exts = (".ply", ".stl")
    if os.path.isdir(input_path):
        return sorted(
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.lower().endswith(exts)
        )
    if os.path.isfile(input_path) and input_path.lower().endswith(exts):
        return [input_path]
    raise ValueError(f"Keine .ply/.stl Datei gefunden unter: {input_path}")


def import_scan(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".ply":
        bpy.ops.wm.ply_import(filepath=filepath)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=filepath)
    else:
        raise ValueError(f"Nicht unterstuetztes Format: {ext}")
    return bpy.context.selected_objects[0]


# ---------------------------------------------------------------------------
# 1. Cleanup
# ---------------------------------------------------------------------------

def cleanup_mesh(obj):
    """Doppelte Vertices entfernen, lose Fragmente loeschen, Loecher fuellen,
    Normalen vereinheitlichen -- macht das Mesh wasserdicht und spielbereit."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")

    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0005)
    bpy.ops.mesh.normals_make_consistent(inside=False)

    # Loecher schliessen (Randkanten -> Face fuellen)
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.mesh.select_non_manifold()
    bpy.ops.mesh.fill_holes(sides=0)

    bpy.ops.object.mode_set(mode="OBJECT")

    # Groesste zusammenhaengende Insel behalten, kleine Fragmente
    # (Scan-Artefakte, Rauschen) verwerfen.
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    islands = []
    visited = set()
    for v in bm.verts:
        if v.index in visited:
            continue
        stack = [v]
        island = set()
        while stack:
            cur = stack.pop()
            if cur.index in island:
                continue
            island.add(cur.index)
            for e in cur.link_edges:
                other = e.other_vert(cur)
                if other.index not in island:
                    stack.append(other)
        visited |= island
        islands.append(island)

    if len(islands) > 1:
        largest = max(islands, key=len)
        bpy.ops.mesh.select_all(action="DESELECT")
        for v in bm.verts:
            v.select = v.index not in largest
        bmesh.update_edit_mesh(obj.data)
        bpy.ops.mesh.delete(type="VERT")

    bpy.ops.object.mode_set(mode="OBJECT")


def is_watertight(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    non_manifold = [e for e in bm.edges if not e.is_manifold]
    bm.free()
    return len(non_manifold) == 0


# ---------------------------------------------------------------------------
# 2. Skalierung
# ---------------------------------------------------------------------------

def calibrate_scale(obj, target_height_m):
    """Ersatz fuer die noch fehlende Kalibrierungsobjekt-Erkennung:
    skaliert das Mesh so, dass seine Bounding-Box-Hoehe (Z) der
    Ziel-Koerperhoehe entspricht."""
    bbox = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not bbox:
        return
    z_values = [v.z for v in bbox]
    current_height = max(z_values) - min(z_values)
    if current_height <= 0:
        print("  Warnung: Konnte Hoehe nicht bestimmen, Skalierung uebersprungen.")
        return

    factor = target_height_m / current_height
    obj.scale = (obj.scale.x * factor, obj.scale.y * factor, obj.scale.z * factor)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    print(f"  Skaliert um Faktor {factor:.4f} -> Hoehe {target_height_m} m")


# ---------------------------------------------------------------------------
# 3. Spiegelung
# ---------------------------------------------------------------------------

def mirror_x(obj):
    bpy.context.view_layer.objects.active = obj
    obj.scale.x *= -1
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # Normalen nach der Spiegelung neu ausrichten
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    print("  Entlang X-Achse gespiegelt.")


# ---------------------------------------------------------------------------
# 4. UV + Textur-Bake
# ---------------------------------------------------------------------------

def ensure_uv_map(obj):
    if not obj.data.uv_layers:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
        bpy.ops.object.mode_set(mode="OBJECT")


def build_vertex_color_material(obj):
    mat = bpy.data.materials.new(name=f"{obj.name}_baked")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (500, 0)
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    vcol = nodes.new("ShaderNodeVertexColor")
    vcol.location = (-200, 0)
    if obj.data.vertex_colors:
        vcol.layer_name = obj.data.vertex_colors[0].name
    links.new(vcol.outputs["Color"], bsdf.inputs["Base Color"])

    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    return mat


def bake_to_texture(obj, mat, name, bake_size, margin, output_dir):
    image = bpy.data.images.new(name=f"{name}_baked", width=bake_size, height=bake_size)
    image_path = os.path.join(output_dir, f"{name}.png")

    nodes = mat.node_tree.nodes
    img_node = nodes.new("ShaderNodeTexImage")
    img_node.image = image
    img_node.select = True
    nodes.active = img_node

    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.context.scene.cycles.bake_type = "DIFFUSE"
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.use_pass_color = True
    bpy.context.scene.render.bake.margin = margin

    bpy.ops.object.bake(type="DIFFUSE")

    image.filepath_raw = image_path
    image.file_format = "PNG"
    image.save()

    links = mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    links.new(img_node.outputs["Color"], bsdf.inputs["Base Color"])
    return image_path


# ---------------------------------------------------------------------------
# 5. Export
# ---------------------------------------------------------------------------

def export_fbx(obj, output_path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        path_mode="COPY",
        embed_textures=True,
    )


# ---------------------------------------------------------------------------
# Hauptablauf pro Datei
# ---------------------------------------------------------------------------

def process_file(filepath, args):
    base_name = args.rename or os.path.splitext(os.path.basename(filepath))[0]
    print(f"\n=== Verarbeite {base_name} ({os.path.basename(filepath)}) ===")

    reset_scene()
    obj = import_scan(filepath)

    if not args.skip_cleanup:
        cleanup_mesh(obj)
        if is_watertight(obj):
            print("  Cleanup ok: Mesh ist wasserdicht.")
        else:
            print("  Warnung: Mesh ist nach Cleanup noch nicht vollstaendig wasserdicht "
                  "(manuelle Nachbearbeitung in Blender empfohlen).")
        calibrate_scale(obj, args.target_height)

    if args.mirror_x:
        mirror_x(obj)

    if not args.no_bake and obj.data.vertex_colors:
        ensure_uv_map(obj)
        mat = build_vertex_color_material(obj)
        bake_to_texture(obj, mat, base_name, args.bake_size, args.margin, args.output)
    elif not args.no_bake:
        print("  Hinweis: Keine Vertex-Colors gefunden, ueberspringe Textur-Bake.")

    fbx_path = os.path.join(args.output, f"{base_name}.fbx")
    export_fbx(obj, fbx_path)
    print(f"  Fertig: {fbx_path}")


def main():
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)
    files = find_scan_files(args.input)

    if not files:
        print("Keine Scan-Dateien gefunden.")
        return

    if len(files) > 1 and args.rename:
        print("Warnung: --rename wird bei mehreren Dateien ignoriert.")
        args.rename = None

    for filepath in files:
        process_file(filepath, args)

    print(f"\nAlle {len(files)} Datei(en) verarbeitet -> {args.output}")


if __name__ == "__main__":
    main()
