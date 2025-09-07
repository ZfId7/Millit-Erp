# File: modules/assembly/parser/step_parser.py
# Purpose: Parse a STEP file into a multi-part JSON payload compatible with three-cad-viewer
# Notes:
# - Emits one "part" per SOLID with basic metrics (bbox, volume) and a mesh hash for grouping
# - Keeps the same top-level schema your viewer already expects (version=3, parts=[...])
# - Designed as a drop-in replacement for your existing step_parser.py

from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_SOLID, TopAbs_FACE
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop_VolumeProperties
from OCC.Core.TopoDS import topods

import os
import json
import hashlib
import traceback


# -----------------------------
# Mesh extraction (faces → triangles)
# -----------------------------
def extract_triangles(shape):
    """Triangulate a TopoDS_Shape (typically a SOLID) and return (vertices, triangles).
    Vertices are a flat float list [x0,y0,z0, ...]; triangles are 0-based indices.
    """
    # Mesh generation: 0.001 is a decent default for small/med parts; adjust if needed
    BRepMesh_IncrementalMesh(shape, 0.02)

    vertices = []
    triangles = []

    exp = TopExp_Explorer(shape, TopAbs_FACE)
    face_idx = 0
    tri_face_count = 0

    while exp.More():
        face_shape = exp.Current()
        try:
            face = topods.Face(face_shape)
            location = TopLoc_Location()
            triangulation = BRep_Tool.Triangulation(face, location)

            if triangulation is None:
                # No triangulation for this face (can happen on bad geometry)
                pass
            else:
                tri_face_count += 1
                nodes = triangulation.Nodes()
                tris = triangulation.Triangles()
                offset = len(vertices) // 3

                # Add vertices
                for i in range(1, nodes.Length() + 1):
                    pnt = nodes.Value(i)
                    vertices.extend([pnt.X(), pnt.Y(), pnt.Z()])

                # Add triangle indices (convert to 0-based, add offset)
                for i in range(1, tris.Length() + 1):
                    tri = tris.Value(i)
                    t1, t2, t3 = tri.Get()
                    triangles.extend([t1 - 1 + offset, t2 - 1 + offset, t3 - 1 + offset])

        except Exception:
            # Keep going even if one face fails
            traceback.print_exc()
        finally:
            face_idx += 1
            exp.Next()

    return vertices, triangles


# -----------------------------
# Geometry helpers for metrics
# -----------------------------

def _bbox(shape):
    box = Bnd_Box()
    # useTriangulation=True for speed; set to False for exact (slower)
    brepbndlib_Add(shape, box, True)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax, "zmin": zmin, "zmax": zmax}


def _volume(shape):
    props = GProp_GProps()
    try:
        brepgprop_VolumeProperties(shape, props)
        return float(props.Mass())  # volume in model units
    except Exception:
        traceback.print_exc()
        return None

def _pad_bb(bb, pad=0.03):
    """Pad a bbox by a % to keep camera near plane off the geometry."""
    if not bb:
        return None
    dx = (bb["xmax"] - bb["xmin"]) * pad or 1e-6
    dy = (bb["ymax"] - bb["ymin"]) * pad or 1e-6
    dz = (bb["zmax"] - bb["zmin"]) * pad or 1e-6
    return {
        "xmin": bb["xmin"] - dx, "xmax": bb["xmax"] + dx,
        "ymin": bb["ymin"] - dy, "ymax": bb["ymax"] + dy,
        "zmin": bb["zmin"] - dz, "zmax": bb["zmax"] + dz,
    }


def _hash_mesh(verts, tris):
    """Quick-and-stable mesh signature to group identical solids into quantities.
    Uses counts and a sampled subset for speed.
    """
    h = hashlib.sha1()
    h.update(f"v{len(verts)}-t{len(tris)}".encode())
    # sample some vertices/triangles to stabilize hash without being huge
    for i in range(0, min(len(verts), 1200), 12):
        h.update(f"{verts[i]:.6f}".encode())
    for i in range(0, min(len(tris), 1200), 12):
        h.update(str(tris[i]).encode())
    return h.hexdigest()


# -----------------------------
# STEP → Shapes JSON (multi-solid)
# -----------------------------

def parse_step(filepath):
    """Read a STEP file and return the viewer JSON with one entry per SOLID.
    filepath may be absolute or relative to your static/uploads path.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"STEP file not found: {filepath}")

    # 1) Read STEP
    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)
    if status != IFSelect_RetDone:
        # Debug aid: dump first lines to help diagnose malformed files
        try:
            with open(filepath, 'r', errors='replace') as f:
                _ = f.readlines()[:10]
        except Exception:
            pass
        raise ValueError("Failed to read STEP file (IFSelect_RetDone != RetDone)")

    reader.TransferRoots()
    shape = reader.OneShape()
    if shape.IsNull():
        raise ValueError("Parsed shape is null")

    # 2) Extract each SOLID under the root shape
    parts = []
    solid_ex = TopExp_Explorer(shape, TopAbs_SOLID)

    color_palette = [
        "#e8b024", "#4cc9f0", "#72e06a", "#ff6b6b", "#c77dff",
        "#ffd166", "#06d6a0", "#bdb2ff", "#bde0fe", "#ffc6ff"
    ]
    count = 0

    while solid_ex.More():
        solid = solid_ex.Current()

        # Triangulate solid
        verts, tris = extract_triangles(solid)

        # Metrics
        bb = _bbox(solid)
        vol = _volume(solid)
        mesh_hash = _hash_mesh(verts, tris)

        # Build part entry
        parts.append({
            "id": f"/Imported/Solid_{count}",
            "type": "shapes",
            "subtype": "solid",
            "name": f"Solid_{count}",
            "shape": {
                "vertices": verts,
                "triangles": tris,
                "normals": [],
                "edges": [],
                "obj_vertices": [],
                "face_types": [],
                "edge_types": [],
                "triangles_per_face": [],
                "segments_per_edge": []
            },
            "state": [1, 1],
            "color": color_palette[count % len(color_palette)],
            "alpha": 1.0,
            "texture": None,
            "loc": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
            "renderback": True,
            "accuracy": None,
            "bb": bb,
            "metrics": {
                "volume": vol,
                "mesh_hash": mesh_hash
            }
        })

        count += 1
        solid_ex.Next()

    # If no solids were found, fall back to meshing the root (prevents empty result)
    if not parts:
        verts, tris = extract_triangles(shape)
        bb = _bbox(shape)
        vol = _volume(shape)
        mesh_hash = _hash_mesh(verts, tris)
        parts.append({
            "id": "/Imported/Shape",
            "type": "shapes",
            "subtype": "solid",
            "name": os.path.basename(filepath),
            "shape": {
                "vertices": verts,
                "triangles": tris,
                "normals": [],
                "edges": [],
                "obj_vertices": [],
                "face_types": [],
                "edge_types": [],
                "triangles_per_face": [],
                "segments_per_edge": []
            },
            "state": [1, 1],
            "color": "#e8b024",
            "alpha": 1.0,
            "texture": None,
            "loc": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
            "renderback": True,
            "accuracy": None,
            "bb": bb,
            "metrics": {
                "volume": vol,
                "mesh_hash": mesh_hash
            }
        })
    overall_bb = _bbox(shape)
    padded_bb = _pad_bb(overall_bb, 0.03)
    
    shapes = {
        "version": 3,
        "parts": parts,
        "loc": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
        "name": os.path.basename(filepath),
        "id": "/Imported",
        "normal_len": 0,
        "bb": padded_bb
    }

    return shapes
