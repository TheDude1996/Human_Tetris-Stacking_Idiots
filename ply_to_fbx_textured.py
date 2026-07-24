"""
ply_to_fbx_textured.py
-----------------------
Wandelt PLY-Dateien mit Vertex-Colors (z.B. aus ReconstructMe) automatisch in
FBX-Dateien mit gebackener Bild-Textur um. Läuft als Blender-Skript im
Hintergrund (--background), damit es sich z.B. an eure mesh_cleanup_batch.py
anschliessen laesst.

Ablauf pro Datei:
  1. PLY importieren
  2. UV-Unwrap erzeugen (Smart UV Project), falls keine UVs vorhanden
  3. Material mit Vertex-Color-Node aufbauen
  4. Vertex-Colors in eine Bild-Textur backen
  5. FBX + PNG-Textur exportieren

Nutzung (Beispiel, Kommandozeile):
  blender --background --python ply_to_fbx_textured.py -- \
      --input /scans/processed --output /scans/unity_ready --bake-size 2048

Einzeldatei statt ganzem Ordner:
  blender --background --python ply_to_fbx_textured.py -- \
      --input /scans/processed/I.ply --output /scans/unity_ready

Voraussetzungen:
  - Blender 3.x, 4.x oder 5.x (getestet mit Cycles als Bake-Engine, inkl. 5.2 LTS)
  - Die PLY-Datei muss Vertex-Colors enthalten (ReconstructMe-Standardexport)

Kompatibilitaet: Vertex-Farben werden ueber die color_attributes-API
ausgelesen (die alte vertex_colors-API wurde in Blender 4.0 entfernt bzw.
ist seitdem immer leer, auch wenn das Mesh Farben besitzt).
"""

import bpy
import sys
import os
import argparse


def parse_args():
    # Alles nach "--" sind unsere eigenen Argumente, Blender ignoriert den Rest
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="PLY -> FBX mit gebackener Textur")
    parser.add_argument("--input", required=True,
                         help="Pfad zu einer .ply-Datei ODER einem Ordner voller .ply-Dateien")
    parser.add_argument("--output", required=True,
                         help="Zielordner fuer .fbx + .png")
    parser.add_argument("--bake-size", type=int, default=2048,
                         help="Aufloesung der gebackenen Textur (Standard: 2048)")
    parser.add_argument("--margin", type=int, default=8,
                         help="Bake-Margin in Pixeln, verhindert Naht-Artefakte (Standard: 8)")
    return parser.parse_args(argv)


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
    # Neu importiertes Objekt ist danach aktiv selektiert
    obj = bpy.context.selected_objects[0]
    return obj


def ensure_uv_map(obj):
    if not obj.data.uv_layers:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
        bpy.ops.object.mode_set(mode="OBJECT")


def get_color_attribute_name(obj):
    """Ermittelt den Namen der Vertex-Color-Schicht ueber die
    color_attributes-API (Blender 4.0+/5.x). Fallback auf die alte
    vertex_colors-API fuer sehr alte Blender-Versionen."""
    color_attrs = getattr(obj.data, "color_attributes", None)
    if color_attrs and len(color_attrs) > 0:
        return color_attrs[0].name
    legacy = getattr(obj.data, "vertex_colors", None)
    if legacy and len(legacy) > 0:
        return legacy[0].name
    return None


def build_vertex_color_material(obj, color_attr_name):
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
    vcol.layer_name = color_attr_name
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

    # Cycles wird nur fuer den Bake-Vorgang benoetigt
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

    # Nach dem Backen: Material auf die gebackene Textur umstellen,
    # damit Unity beim Import direkt die richtige Albedo-Textur bekommt.
    links = mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    links.new(img_node.outputs["Color"], bsdf.inputs["Base Color"])

    return image_path


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


def process_file(filepath, output_dir, bake_size, margin):
    name = os.path.splitext(os.path.basename(filepath))[0]
    print(f"\n=== Verarbeite {name} ===")

    reset_scene()
    obj = import_ply(filepath)

    color_attr_name = get_color_attribute_name(obj)
    if not color_attr_name:
        print(f"  Warnung: {name} hat keine Vertex-Colors (color_attributes), "
              f"ueberspringe Textur-Bake.")
    else:
        ensure_uv_map(obj)
        mat = build_vertex_color_material(obj, color_attr_name)
        bake_to_texture(obj, mat, name, bake_size, margin, output_dir)

    fbx_path = os.path.join(output_dir, f"{name}.fbx")
    export_fbx(obj, fbx_path)
    print(f"  Fertig: {fbx_path}")


def main():
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)
    ply_files = find_ply_files(args.input)

    if not ply_files:
        print("Keine .ply-Dateien gefunden.")
        return

    for filepath in ply_files:
        process_file(filepath, args.output, args.bake_size, args.margin)

    print(f"\nAlle {len(ply_files)} Datei(en) verarbeitet -> {args.output}")


if __name__ == "__main__":
    main()
