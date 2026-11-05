"""
ply_head_to_lowpoly_glb.py
----------------------------
Wandelt hochaufgeloeste PLY-Kopfscans (mit Vertex-Colors, z.B. aus
ReconstructMe) in POLYGON-REDUZIERTE GLB-Dateien fuer Human-Tetris/Unity um.

Die Detail- und Farbinformation des Rohscans geht dabei nicht verloren:
Sie wird vom Original-Mesh (High-Poly) auf das reduzierte Mesh (Low-Poly)
gebacken ("Selected to Active") -- als Farbtextur und optional zusaetzlich
als Normal-Map.

Ablauf pro Datei:
  1. PLY importieren
  2. Cleanup (optional): doppelte Vertices zusammenfuehren, lose Fragmente
     entfernen (nur groesste Insel bleibt), Loecher fuellen, Normalen
     vereinheitlichen
  3. Skalierung (optional, --edge-length) wie in scan_to_unity_pipeline_cubefit.py
  4. Spiegelung (optional, --mirror-x)
  5. Ursprung setzen (--origin center|bottom|keep)
  6. Kopie des Meshes per Decimate-Modifier auf --target-faces Dreiecke reduzieren
  7. Low-Poly UV-entfalten (Smart UV Project) und glatt schattieren
  8. Vertex-Colors des High-Poly-Scans auf die Low-Poly-Textur backen
     (+ optional Normal-Map mit --bake-normals)
  9. Nur das Low-Poly-Mesh als GLB (Textur eingebettet) exportieren

Nutzung (Kommandozeile):
  blender --background --python ply_head_to_lowpoly_glb.py -- \
      --input C:/Users/sever/Desktop/input --output C:/Users/sever/Desktop/putput

  # Einzeldatei, 3000 Dreiecke, mit Normal-Map, auf 0.3 m skaliert
  blender --background --python ply_head_to_lowpoly_glb.py -- \
      --input C:/scans/Joel.ply --output C:/scans/out \
      --target-faces 3000 --bake-normals --edge-length 0.3 --rename Kopf_Joel

Wichtige Flags:
  --target-faces 5000   Ziel-Anzahl Dreiecke des reduzierten Meshes (Standard: 5000)
  --ratio 0.01          Alternativ: Reduktionsverhaeltnis (0..1). Ueberschreibt --target-faces.
  --bake-normals        Zusaetzlich Normal-Map vom High-Poly backen (mehr Detail bei
                        wenig Polygonen; wird im GLB mit eingebettet).
  --edge-length 0.3     Mesh gleichmaessig so skalieren, dass die groesste Ausdehnung
                        in diese Kantenlaenge (Meter) passt. Ohne Angabe: Originalgroesse.
  --origin center       Ursprung: center (Mitte der Bounding-Box, Standard),
                        bottom (unten mittig), keep (unveraendert).
  --skip-cleanup        Cleanup-Schritte ueberspringen.
  --no-fill-holes       Loecher (z.B. offener Hals) NICHT schliessen.
  --no-bake             Keine Textur backen (nur reduziertes Mesh exportieren).
  --draco               Draco-Mesh-Kompression im GLB (Unity braucht dafuer das
                        Draco-Paket fuer glTFast).

Unbekannte Argumente (z.B. --target-height aus der GUI) werden ignoriert statt
abzubrechen, damit das Skript in PipelineTool.exe wie die anderen Skripte
ausgewaehlt werden kann.

Kompatibilitaet: Blender 4.x / 5.x (color_attributes-API), getestet mit 5.2 LTS.
"""

import bpy
import bmesh
import sys
import os
import math
import argparse
from mathutils import Vector


# ---------------------------------------------------------------------------
# Argumente
# ---------------------------------------------------------------------------

def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []

    p = argparse.ArgumentParser(description="PLY-Kopfscan -> polygonreduziertes, texturiertes GLB")
    p.add_argument("--input", required=True, help="Datei oder Ordner mit .ply")
    p.add_argument("--output", required=True, help="Zielordner fuer die fertige .glb")
    p.add_argument("--target-faces", type=int, default=5000,
                    help="Ziel-Anzahl Dreiecke nach der Reduktion (Standard: 5000)")
    p.add_argument("--ratio", type=float, default=None,
                    help="Reduktionsverhaeltnis 0..1 (ueberschreibt --target-faces)")
    p.add_argument("--bake-size", type=int, default=2048, help="Textur-Aufloesung (Standard: 2048)")
    p.add_argument("--margin", type=int, default=8, help="Bake-Margin in Pixeln (Standard: 8)")
    p.add_argument("--bake-normals", action="store_true",
                    help="Zusaetzlich eine Normal-Map vom High-Poly-Scan backen")
    p.add_argument("--no-bake", action="store_true", help="Keine Textur backen")
    p.add_argument("--edge-length", type=float, default=None,
                    help="Ziel-Kantenlaenge in Metern (gleichmaessige Skalierung). "
                         "Ohne Angabe bleibt die Originalgroesse erhalten.")
    p.add_argument("--padding", type=float, default=0.0,
                    help="Sicherheitsabstand als Anteil der Kantenlaenge (Standard: 0)")
    p.add_argument("--origin", choices=["center", "bottom", "keep"], default="center",
                    help="Lage des Objekt-Ursprungs (Standard: center)")
    p.add_argument("--mirror-x", action="store_true", help="Mesh entlang X-Achse spiegeln")
    p.add_argument("--skip-cleanup", action="store_true", help="Cleanup ueberspringen")
    p.add_argument("--no-fill-holes", action="store_true",
                    help="Loecher beim Cleanup nicht schliessen")
    p.add_argument("--draco", action="store_true", help="Draco-Kompression beim GLB-Export")
    p.add_argument("--rename", default=None, help="Ausgabedateiname ohne Endung ueberschreiben")

    args, unknown = p.parse_known_args(argv)
    if unknown:
        print(f"Hinweis: Ignoriere unbekannte Argumente: {' '.join(unknown)}")
    return args


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def find_ply_files(input_path):
    if os.path.isdir(input_path):
        return sorted(
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.lower().endswith(".ply")
        )
    if os.path.isfile(input_path) and input_path.lower().endswith(".ply"):
        return [input_path]
    raise ValueError(f"Kein .ply gefunden unter: {input_path}")


def import_ply(filepath):
    bpy.ops.wm.ply_import(filepath=filepath)
    return bpy.context.selected_objects[0]


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def world_bounds(obj):
    """Achsenparallele Bounding-Box in Weltkoordinaten (min, max)."""
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    mx = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return mn, mx


def get_color_attribute_name(obj):
    color_attrs = getattr(obj.data, "color_attributes", None)
    if color_attrs and len(color_attrs) > 0:
        return color_attrs[0].name
    legacy = getattr(obj.data, "vertex_colors", None)
    if legacy and len(legacy) > 0:
        return legacy[0].name
    return None


# ---------------------------------------------------------------------------
# 1. Cleanup
# ---------------------------------------------------------------------------

def cleanup_mesh(obj, fill_holes=True):
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)

    # Groesste zusammenhaengende Insel behalten (Scan-Rauschen/Fragmente weg)
    bm.verts.ensure_lookup_table()
    n = len(bm.verts)
    island_id = [-1] * n
    sizes = []
    for start in range(n):
        if island_id[start] != -1:
            continue
        iid = len(sizes)
        island_id[start] = iid
        stack = [bm.verts[start]]
        count = 0
        while stack:
            v = stack.pop()
            count += 1
            for e in v.link_edges:
                o = e.other_vert(v)
                if island_id[o.index] == -1:
                    island_id[o.index] = iid
                    stack.append(o)
        sizes.append(count)

    if len(sizes) > 1:
        keep = max(range(len(sizes)), key=sizes.__getitem__)
        doomed = [v for v in bm.verts if island_id[v.index] != keep]
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
        print(f"  {len(sizes) - 1} lose Fragment(e) entfernt ({len(doomed)} Vertices).")

    if fill_holes:
        boundary = [e for e in bm.edges if e.is_boundary]
        if boundary:
            res = bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
            new_faces = res.get("faces", [])
            if new_faces:
                # Grosse N-Gons (z.B. Halsoeffnung) triangulieren, damit
                # Decimate und UV-Unwrap sauber damit umgehen koennen.
                bmesh.ops.triangulate(bm, faces=new_faces)
            print(f"  {len(new_faces)} Loch/Loecher geschlossen.")

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


# ---------------------------------------------------------------------------
# 2. Skalierung / Spiegelung / Ursprung
# ---------------------------------------------------------------------------

def scale_to_fit_edge_length(obj, edge_length, padding):
    mn, mx = world_bounds(obj)
    max_dim = max(mx - mn)
    if max_dim <= 0:
        print("  Warnung: Ausdehnung 0, Skalierung uebersprungen.")
        return
    f = edge_length * (1 - padding) / max_dim
    activate(obj)
    obj.scale = tuple(c * f for c in obj.scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    print(f"  Skaliert um Faktor {f:.4f} (groesste Ausdehnung -> {edge_length * (1 - padding):.3f} m).")


def mirror_x(obj):
    activate(obj)
    obj.scale.x *= -1
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    print("  Entlang X-Achse gespiegelt.")


def set_origin(obj, mode):
    if mode == "keep":
        return
    mn, mx = world_bounds(obj)
    pivot = (mn + mx) / 2
    if mode == "bottom":
        pivot.z = mn.z  # Blender Z-up -> wird im GLB zu Y-up (Unten = Kinn/Hals)
    activate(obj)
    obj.location -= pivot
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)


# ---------------------------------------------------------------------------
# 3. Polygon-Reduktion
# ---------------------------------------------------------------------------

def make_lowpoly(src, name, target_faces, ratio):
    low = src.copy()
    low.data = src.data.copy()
    low.name = f"{name}_lowpoly"
    low.data.name = f"{name}_lowpoly"
    bpy.context.collection.objects.link(low)

    before = tri_count(low)
    if ratio is None:
        ratio = target_faces / before if before > 0 else 1.0
    ratio = max(0.0001, min(1.0, ratio))

    if ratio < 1.0:
        activate(low)
        mod = low.modifiers.new(name="Decimate", type="DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)

    print(f"  Polygon-Reduktion: {before:,} -> {tri_count(low):,} Dreiecke (Ratio {ratio:.5f}).")
    return low


def unwrap_and_smooth(obj):
    activate(obj)
    for uv in list(obj.data.uv_layers):
        obj.data.uv_layers.remove(uv)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.01)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.shade_smooth()


# ---------------------------------------------------------------------------
# 4. Materialien + Bake (High-Poly -> Low-Poly)
# ---------------------------------------------------------------------------

def build_source_material(obj, color_attr_name):
    mat = bpy.data.materials.new(name=f"{obj.name}_source")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    vcol = nodes.new("ShaderNodeVertexColor")
    vcol.layer_name = color_attr_name
    links.new(vcol.outputs["Color"], bsdf.inputs["Base Color"])
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def build_lowpoly_material(obj, name, bake_size, with_normals):
    mat = bpy.data.materials.new(name=f"{name}_baked")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)
    # Matt/diffus wie in den anderen Pipeline-Skripten
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Roughness"].default_value = 1.0
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec:
        spec.default_value = 0.0
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (500, 0)
    mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    color_img = bpy.data.images.new(f"{name}_color", bake_size, bake_size)
    color_img.colorspace_settings.name = "sRGB"
    color_node = nodes.new("ShaderNodeTexImage")
    color_node.location = (-300, 100)
    color_node.image = color_img

    normal_node = None
    if with_normals:
        normal_img = bpy.data.images.new(f"{name}_normal", bake_size, bake_size)
        normal_img.colorspace_settings.name = "Non-Color"
        normal_node = nodes.new("ShaderNodeTexImage")
        normal_node.location = (-300, -200)
        normal_node.image = normal_img

    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return mat, bsdf, color_node, normal_node


def setup_bake(src, low, margin):
    mn, mx = world_bounds(src)
    size = max(mx - mn)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 4  # reiner Farb-/Normal-Bake braucht kaum Samples
    bake = scene.render.bake
    bake.use_selected_to_active = True
    bake.use_cage = False
    bake.cage_extrusion = size * 0.02      # Strahlen starten 2% ausserhalb des Low-Poly
    bake.max_ray_distance = size * 0.05    # ... und suchen max. 5% nach innen
    bake.margin = margin

    bpy.ops.object.select_all(action="DESELECT")
    src.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low  # Low-Poly = Bake-Ziel


def bake_color(mat, color_node):
    bake = bpy.context.scene.render.bake
    bake.use_pass_direct = False
    bake.use_pass_indirect = False
    bake.use_pass_color = True
    mat.node_tree.nodes.active = color_node
    bpy.ops.object.bake(type="DIFFUSE")


def bake_normals(mat, normal_node):
    bake = bpy.context.scene.render.bake
    bake.normal_space = "TANGENT"
    mat.node_tree.nodes.active = normal_node
    bpy.ops.object.bake(type="NORMAL")


def save_image(image, path):
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()


def wire_baked_textures(mat, bsdf, color_node, normal_node):
    links, nodes = mat.node_tree.links, mat.node_tree.nodes
    links.new(color_node.outputs["Color"], bsdf.inputs["Base Color"])
    if normal_node:
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.location = (0, -200)
        nmap.space = "TANGENT"
        links.new(normal_node.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])


def strip_color_attributes(obj):
    """Vertex-Colors vom Low-Poly entfernen, sonst multipliziert Unity/glTF
    (COLOR_0) sie zusaetzlich auf die gebackene Textur."""
    attrs = obj.data.color_attributes
    for a in list(attrs):
        attrs.remove(a)


# ---------------------------------------------------------------------------
# 5. Export
# ---------------------------------------------------------------------------

def export_glb(obj, output_path, draco):
    activate(obj)
    kwargs = dict(
        filepath=output_path,
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_yup=True,
        export_apply=True,
    )
    if draco:
        kwargs["export_draco_mesh_compression_enable"] = True
    bpy.ops.export_scene.gltf(**kwargs)


# ---------------------------------------------------------------------------
# Hauptablauf
# ---------------------------------------------------------------------------

def process_file(filepath, args):
    name = args.rename or os.path.splitext(os.path.basename(filepath))[0]
    print(f"\n=== Verarbeite {name} ({os.path.basename(filepath)}) ===")

    reset_scene()
    src = import_ply(filepath)
    print(f"  Import: {len(src.data.vertices):,} Vertices, {tri_count(src):,} Dreiecke.")

    if not args.skip_cleanup:
        cleanup_mesh(src, fill_holes=not args.no_fill_holes)

    if args.edge_length is not None:
        scale_to_fit_edge_length(src, args.edge_length, args.padding)
    if args.mirror_x:
        mirror_x(src)
    set_origin(src, args.origin)

    low = make_lowpoly(src, name, args.target_faces, args.ratio)
    unwrap_and_smooth(low)

    color_attr = get_color_attribute_name(src)
    if args.no_bake:
        print("  --no-bake: Textur-Bake uebersprungen.")
    elif not color_attr:
        print("  Hinweis: Keine Vertex-Colors gefunden, Textur-Bake uebersprungen.")
    else:
        build_source_material(src, color_attr)
        mat, bsdf, color_node, normal_node = build_lowpoly_material(
            low, name, args.bake_size, args.bake_normals)
        setup_bake(src, low, args.margin)

        bake_color(mat, color_node)
        save_image(color_node.image, os.path.join(args.output, f"{name}.png"))
        if normal_node:
            bake_normals(mat, normal_node)
            save_image(normal_node.image, os.path.join(args.output, f"{name}_normal.png"))

        wire_baked_textures(mat, bsdf, color_node, normal_node)
        strip_color_attributes(low)

    # High-Poly entfernen, damit garantiert nur das Low-Poly exportiert wird
    bpy.data.objects.remove(src, do_unlink=True)

    glb_path = os.path.join(args.output, f"{name}.glb")
    export_glb(low, glb_path, args.draco)
    print(f"  Fertig: {glb_path}  ({tri_count(low):,} Dreiecke)")


def main():
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)
    files = find_ply_files(args.input)

    if not files:
        print("Keine .ply-Dateien gefunden.")
        return

    if len(files) > 1 and args.rename:
        print("Warnung: --rename wird bei mehreren Dateien ignoriert.")
        args.rename = None

    failed = []
    for filepath in files:
        try:
            process_file(filepath, args)
        except Exception as exc:  # eine kaputte Datei soll nicht den ganzen Batch stoppen
            print(f"  FEHLER bei {os.path.basename(filepath)}: {exc}")
            failed.append(filepath)

    print(f"\n{len(files) - len(failed)}/{len(files)} Datei(en) verarbeitet -> {args.output}")
    if failed:
        print("Fehlgeschlagen: " + ", ".join(os.path.basename(f) for f in failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
