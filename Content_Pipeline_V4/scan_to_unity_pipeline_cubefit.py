"""
scan_to_unity_pipeline_cubefit.py
-----------------------------------
Kombination aus scan_to_unity_pipeline.py und ply_to_cube_textured.py:

  - Grundaufbau/Cleanup-Schritte wie scan_to_unity_pipeline.py (wasserdicht
    machen, Loecher fuellen, lose Fragmente entfernen, optionale Spiegelung,
    UV-Unwrap + Vertex-Color-Bake, GLB-Export)
  - ABER: die Skalierung erfolgt wie in ply_to_cube_textured.py ueber eine
    feste Ziel-Kantenlaenge (--edge-length) statt einer Ziel-Koerperhoehe.
    Das Mesh wird gleichmaessig auf allen Achsen so skaliert, dass es exakt
    in diese Kantenlaenge passt -- verkleinert bei zu grossen und
    vergroessert bei zu kleinen Meshes, ist es bereits kleiner.

Anders als ply_to_cube_textured.py wird hier weiterhin die ORIGINAL-Geometrie
exportiert (keine Wuerfel-Cage), nur eben in dieser Kantenlaengen-Logik
skaliert. Fuer den "Foto auf Wuerfel backen"-Workflow bitte weiterhin
ply_to_cube_textured.py verwenden.

Nutzung (Kommandozeile):
  blender --background --python scan_to_unity_pipeline_cubefit.py -- \
      --input /scans/raw --output /scans/processed --edge-length 1.75

  blender --background --python scan_to_unity_pipeline_cubefit.py -- \
      --input /scans/processed/S.ply --output /scans/processed \
      --mirror-x --rename Z --skip-cleanup

Wichtige Flags:
  --edge-length 1.0   Ziel-Kantenlaenge in Metern. Das Mesh wird IMMER
                      gleichmaessig so skaliert, dass die groesste Ausdehnung
                      (X/Y/Z) genau hineinpasst -- verkleinert bei zu grossen
                      und vergroessert bei zu kleinen Meshes.
  --padding 0.05      Sicherheitsabstand als Anteil, damit das Mesh nicht
                      exakt an der Kante anliegt (Standard: 5%).
  --mirror-x          Mesh entlang X-Achse spiegeln (S->Z, J->L).
  --skip-cleanup      Cleanup-Schritte ueberspringen (z.B. bei Spiegelung
                      eines bereits bereinigten Meshes).
  --no-bake           Kein Textur-Bake, nur Cleanup/Skalierung + Export.

Kompatibilitaet: Getestet fuer Blender 5.2 LTS (color_attributes-API).
"""

import bpy
import bmesh
import sys
import os
import argparse
from mathutils import Vector


# ---------------------------------------------------------------------------
# Argumente
# ---------------------------------------------------------------------------

def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []

    p = argparse.ArgumentParser(description="Scan (PLY/STL) -> bereinigtes, kantenlaengen-skaliertes, texturiertes Unity-GLB")
    p.add_argument("--input", required=True, help="Datei oder Ordner mit .ply/.stl")
    p.add_argument("--output", required=True, help="Zielordner fuer die fertige .glb")
    p.add_argument("--edge-length", type=float, default=1.0,
                    help="Ziel-Kantenlaenge in Metern (Standard: 1.0). Das Mesh wird IMMER "
                         "gleichmaessig so skaliert, dass es genau hineinpasst.")
    p.add_argument("--padding", type=float, default=0.05,
                    help="Sicherheitsabstand als Anteil der Kantenlaenge (Standard: 0.05 = 5%%)")
    p.add_argument("--mirror-x", action="store_true",
                    help="Mesh entlang X-Achse spiegeln (S->Z, J->L)")
    p.add_argument("--rename", default=None,
                    help="Ausgabedateiname ohne Endung ueberschreiben")
    p.add_argument("--skip-cleanup", action="store_true",
                    help="Cleanup-Schritte (Loecher fuellen, wasserdicht machen) ueberspringen")
    p.add_argument("--bake-size", type=int, default=2048, help="Textur-Aufloesung")
    p.add_argument("--margin", type=int, default=8, help="Bake-Margin in Pixeln")
    p.add_argument("--no-bake", action="store_true",
                    help="Kein Textur-Bake, nur Cleanup/Skalierung + Export")
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
# 1. Cleanup (identisch zu scan_to_unity_pipeline.py)
# ---------------------------------------------------------------------------

def cleanup_mesh(obj):
    """Doppelte Vertices entfernen, lose Fragmente loeschen, Loecher fuellen,
    Normalen vereinheitlichen -- macht das Mesh wasserdicht und spielbereit."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")

    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0005)
    bpy.ops.mesh.normals_make_consistent(inside=False)

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
# 2. Skalierung (aus ply_to_cube_textured.py uebernommen: Kantenlaengen-Fit
#    statt Ziel-Koerperhoehe)
# ---------------------------------------------------------------------------

def compute_world_bounds(obj):
    mat = obj.matrix_world
    coords = [mat @ v.co for v in obj.data.vertices]
    xs = [c.x for c in coords]
    ys = [c.y for c in coords]
    zs = [c.z for c in coords]
    mn = Vector((min(xs), min(ys), min(zs)))
    mx = Vector((max(xs), max(ys), max(zs)))
    dims = mx - mn
    return dims


def scale_to_fit_edge_length(obj, edge_length, padding):
    """Skaliert das Mesh gleichmaessig (alle Achsen gleich) so, dass seine
    groesste Ausdehnung genau in einen Wuerfel mit der Kantenlaenge
    edge_length passt -- verkleinert grosse Meshes UND vergroessert kleine."""
    dims = compute_world_bounds(obj)
    max_dim = max(dims.x, dims.y, dims.z)
    if max_dim <= 0:
        print("  Warnung: Konnte Ausdehnung nicht bestimmen, Skalierung uebersprungen.")
        return 1.0

    target_inner = edge_length * (1 - padding)
    scale_factor = target_inner / max_dim

    if abs(scale_factor - 1.0) > 1e-6:
        obj.scale = (obj.scale.x * scale_factor, obj.scale.y * scale_factor, obj.scale.z * scale_factor)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        richtung = "verkleinert" if scale_factor < 1.0 else "vergroessert"
        print(f"  Mesh {richtung} um Faktor {scale_factor:.4f}, um in {edge_length} m zu passen.")
    else:
        print(f"  Mesh passt bereits exakt in {edge_length} m, keine Skalierung noetig.")

    return scale_factor


# ---------------------------------------------------------------------------
# 3. Spiegelung (identisch zu scan_to_unity_pipeline.py)
# ---------------------------------------------------------------------------

def mirror_x(obj):
    bpy.context.view_layer.objects.active = obj
    obj.scale.x *= -1
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    print("  Entlang X-Achse gespiegelt.")


# ---------------------------------------------------------------------------
# 4. UV + Textur-Bake (identisch zu scan_to_unity_pipeline.py, color_attributes-API)
# ---------------------------------------------------------------------------

def get_color_attribute_name(obj):
    """Vertex-Color-Schicht ueber die color_attributes-API ermitteln
    (Blender 4.0+/5.x; die alte vertex_colors-API ist dort immer leer)."""
    color_attrs = getattr(obj.data, "color_attributes", None)
    if color_attrs and len(color_attrs) > 0:
        return color_attrs[0].name
    legacy = getattr(obj.data, "vertex_colors", None)
    if legacy and len(legacy) > 0:
        return legacy[0].name
    return None


def ensure_uv_map(obj):
    if not obj.data.uv_layers:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
        bpy.ops.object.mode_set(mode="OBJECT")


def build_vertex_color_material(obj, color_attr_name):
    mat = bpy.data.materials.new(name=f"{obj.name}_baked")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)
    # Base Color auf reines Weiss setzen (sonst multiplizieren manche Export-Formate
    # den Standard-Grauwert ~0.8 auf die Textur, was sie abdunkelt) und
    # Rauheit/Spiegelung so setzen, dass kein kuenstlicher Glanz entsteht --
    # eine Foto-Textur soll komplett matt/diffus wirken.
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Roughness"].default_value = 1.0
    specular_input = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if specular_input:
        specular_input.default_value = 0.0
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (500, 0)
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    vcol = nodes.new("ShaderNodeVertexColor")
    vcol.location = (-200, 0)
    vcol.layer_name = color_attr_name
    links.new(vcol.outputs["Color"], bsdf.inputs["Base Color"])

    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    return mat


def bake_to_texture(obj, mat, name, bake_size, margin, output_dir):
    image = bpy.data.images.new(name=f"{name}_baked", width=bake_size, height=bake_size)
    image.colorspace_settings.name = "sRGB"  # explizit, verhindert Gamma-/Dunkel-Artefakte
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

def export_glb(obj, output_path):
    """Exportiert als glTF-Binary (.glb) -- eine einzige Binaerdatei mit
    Geometrie, Material und eingebetteter Textur, kein separates .png noetig."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_yup=True,
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

    scale_to_fit_edge_length(obj, args.edge_length, args.padding)

    if args.mirror_x:
        mirror_x(obj)

    color_attr_name = get_color_attribute_name(obj)
    if not args.no_bake and color_attr_name:
        ensure_uv_map(obj)
        mat = build_vertex_color_material(obj, color_attr_name)
        bake_to_texture(obj, mat, base_name, args.bake_size, args.margin, args.output)
    elif not args.no_bake:
        print("  Hinweis: Keine Vertex-Colors (color_attributes) gefunden, ueberspringe Textur-Bake.")

    glb_path = os.path.join(args.output, f"{base_name}.glb")
    export_glb(obj, glb_path)
    print(f"  Fertig: {glb_path}")


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
