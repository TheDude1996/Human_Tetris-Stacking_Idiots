"""
ply_to_cube_textured.py
-------------------------
Wandelt PLY-Scans (mit Vertex-Colors) in einen texturierten WUERFEL um, statt
die Original-Koerperform zu exportieren. Gedacht fuer Human-Tetris: jede
gescannte Pose "steckt" am Ende in einem Standard-Wuerfel, dessen Textur
das Foto der Person zeigt -- perfekt zum 1:1 Bekleben eines Unity-Cube.

Ablauf pro Datei:
  1. PLY importieren (Vertex-Colors)
  2. Bounding-Box des Scans berechnen, leicht vergroessert einen Wuerfel
     ("Cage") drumherum bauen -- das ist das "zu einem Wuerfel druecken"
  3. Den Wuerfel mit einer klassischen 6-Flaechen-UV entfalten (Smart UV
     Project mit niedrigem Winkel-Limit -> 6 saubere quadratische Inseln)
  4. Textur von der Scan-Oberflaeche auf den Wuerfel backen
     (Blender-Feature "Selected to Active": Rays gehen vom Wuerfel nach
     innen zur Scan-Oberflaeche -- Standard-Technik fuer Cage-Baking)
  5. Nur den Wuerfel (nicht den Original-Scan) als FBX mit eingebetteter
     Textur exportieren

Nutzung (Kommandozeile):
  blender --background --python ply_to_cube_textured.py -- \
      --input /scans/processed --output /scans/unity_ready

Einzeldatei:
  blender --background --python ply_to_cube_textured.py -- \
      --input /scans/processed/S.ply --output /scans/unity_ready --rename Playermodell_0001

Wichtige Flags:
  --cube-mode uniform|fit   uniform (Standard) = echter Wuerfel, gleich lange
                            Kanten (laengste Scan-Dimension bestimmt die Kantenlaenge).
                            fit = Quader entlang der tatsaechlichen Scan-Proportionen.
  --padding 0.05            Vergroessert den Wuerfel um 5% ueber die Bounding-Box
                            hinaus, damit der Scan sicher komplett darin liegt.
  --cage-extrusion 0        0 = automatisch 5% der groessten Wuerfelkante.
                            Schiebt die Bake-Strahlen etwas nach aussen, bevor
                            sie nach innen zur Scan-Oberflaeche geschossen werden.

Kompatibilitaet: Getestet fuer Blender 5.2 LTS (color_attributes-API).
"""

import bpy
import sys
import os
import argparse
from mathutils import Vector


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []

    p = argparse.ArgumentParser(description="PLY-Scan -> texturierter Wuerfel (FBX)")
    p.add_argument("--input", required=True, help="Datei oder Ordner mit .ply")
    p.add_argument("--output", required=True, help="Zielordner fuer .fbx (+ .png)")
    p.add_argument("--bake-size", type=int, default=2048, help="Textur-Aufloesung (Standard: 2048)")
    p.add_argument("--margin", type=int, default=8, help="Bake-Margin in Pixeln zwischen UV-Inseln")
    p.add_argument("--rename", default=None, help="Ausgabedateiname (ohne Endung) ueberschreiben")
    p.add_argument("--cube-mode", choices=["uniform", "fit"], default="uniform",
                    help="uniform = echter Wuerfel (Standard), fit = Quader nach Scan-Proportionen")
    p.add_argument("--padding", type=float, default=0.05,
                    help="Zusaetzlicher Rand um die Bounding-Box, als Anteil (Standard: 0.05 = 5%%)")
    p.add_argument("--cage-extrusion", type=float, default=0.0,
                    help="Bake-Cage-Extrusion in Blender-Einheiten. 0 = automatisch 5%% der Wuerfelkante.")
    return p.parse_args(argv)


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


def build_source_material(obj, color_attr_name):
    """Material fuer den Original-Scan: Base Color kommt aus den
    Vertex-Colors. Wird beim Bake als Farbquelle abgetastet."""
    mat = bpy.data.materials.new(name=f"{obj.name}_source")
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


def compute_world_bounds(obj):
    mat = obj.matrix_world
    coords = [mat @ v.co for v in obj.data.vertices]
    xs = [c.x for c in coords]
    ys = [c.y for c in coords]
    zs = [c.z for c in coords]
    mn = Vector((min(xs), min(ys), min(zs)))
    mx = Vector((max(xs), max(ys), max(zs)))
    center = (mn + mx) / 2
    dims = mx - mn
    return center, dims


def create_bake_cube(center, dims, cube_mode, padding):
    padded = Vector((dims.x * (1 + padding), dims.y * (1 + padding), dims.z * (1 + padding)))

    if cube_mode == "uniform":
        side = max(padded.x, padded.y, padded.z)
        size_x = size_y = size_z = side
    else:
        size_x, size_y, size_z = padded.x, padded.y, padded.z

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    cube_obj = bpy.context.object
    cube_obj.scale = (size_x, size_y, size_z)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    return cube_obj, max(size_x, size_y, size_z)


def unwrap_cube_to_six_faces(cube_obj):
    """Klassische 6-Flaechen-Entfaltung: jede Wuerfelseite wird eine eigene,
    quadratische UV-Insel -- genau das Layout, das sich in Unity leicht auf
    einen Cube-Mesh legen laesst."""
    bpy.context.view_layer.objects.active = cube_obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.0, island_margin=0.03)
    bpy.ops.object.mode_set(mode="OBJECT")


def build_cube_material_with_image(cube_obj, image):
    mat = bpy.data.materials.new(name=f"{cube_obj.name}_baked")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (500, 0)
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    img_node = nodes.new("ShaderNodeTexImage")
    img_node.location = (-200, 0)
    img_node.image = image
    img_node.select = True
    nodes.active = img_node
    links.new(img_node.outputs["Color"], bsdf.inputs["Base Color"])

    cube_obj.data.materials.append(mat)
    return mat, img_node


def bake_source_to_cube(source_obj, cube_obj, img_node, bake_size, margin, cage_extrusion, cube_side):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.bake_type = "DIFFUSE"
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_color = True
    scene.render.bake.margin = margin
    scene.render.bake.use_selected_to_active = True

    # Rays starten etwas ausserhalb der Wuerfeloberflaeche und schiessen nach
    # innen zur Scan-Oberflaeche -- Standardtechnik beim Cage-Baking.
    scene.render.bake.cage_extrusion = cage_extrusion if cage_extrusion > 0 else cube_side * 0.05
    scene.render.bake.max_ray_distance = 0  # 0 = unbegrenzt

    bpy.ops.object.select_all(action="DESELECT")
    source_obj.select_set(True)
    cube_obj.select_set(True)
    bpy.context.view_layer.objects.active = cube_obj  # Wuerfel ist "aktiv" = Bake-Ziel

    bpy.ops.object.bake(type="DIFFUSE")


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


def process_file(filepath, args):
    name = args.rename or os.path.splitext(os.path.basename(filepath))[0]
    print(f"\n=== Verarbeite {name} ({os.path.basename(filepath)}) ===")

    reset_scene()
    source_obj = import_ply(filepath)

    color_attr_name = get_color_attribute_name(source_obj)
    if not color_attr_name:
        print(f"  Warnung: {name} hat keine Vertex-Colors (color_attributes), "
              f"kann keine Textur backen. Ueberspringe Datei.")
        return
    build_source_material(source_obj, color_attr_name)

    center, dims = compute_world_bounds(source_obj)
    cube_obj, cube_side = create_bake_cube(center, dims, args.cube_mode, args.padding)
    unwrap_cube_to_six_faces(cube_obj)

    image = bpy.data.images.new(name=f"{name}_baked", width=args.bake_size, height=args.bake_size)
    mat, img_node = build_cube_material_with_image(cube_obj, image)

    bake_source_to_cube(source_obj, cube_obj, img_node, args.bake_size, args.margin,
                         args.cage_extrusion, cube_side)

    image_path = os.path.join(args.output, f"{name}.png")
    image.filepath_raw = image_path
    image.file_format = "PNG"
    image.save()

    # Nach dem Backen: Bild-Textur bleibt im Material verknuepft, damit
    # Unity beim FBX-Import direkt die richtige Albedo-Textur bekommt.
    fbx_path = os.path.join(args.output, f"{name}.fbx")
    export_fbx(cube_obj, fbx_path)
    print(f"  Fertig: {fbx_path}  (Textur: {image_path})")


def main():
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)
    ply_files = find_ply_files(args.input)

    if not ply_files:
        print("Keine .ply-Dateien gefunden.")
        return

    if len(ply_files) > 1 and args.rename:
        print("Warnung: --rename wird bei mehreren Dateien ignoriert.")
        args.rename = None

    for filepath in ply_files:
        process_file(filepath, args)

    print(f"\nAlle {len(ply_files)} Datei(en) verarbeitet -> {args.output}")


if __name__ == "__main__":
    main()
