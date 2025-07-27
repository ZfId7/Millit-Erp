from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopoDS import TopoDS_Shape, TopoDS_Face
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
from OCP.TColgp import TColgp_Array1OfPnt
from OCP.gp import gp_Pnt
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf

import os
import json


def extract_triangles(shape):
    # Mesh the shape with a suitable deflection
    BRepMesh_IncrementalMesh(shape, 0.1)

    vertices = []
    triangles = []

    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    index = 0

    while exp.More():
        face = TopoDS_Face(exp.Current())
        location = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation(face, location)

        if triangulation is not None:
            nodes = triangulation.Nodes()
            tris = triangulation.Triangles()
            offset = len(vertices) // 3

            for i in range(1, nodes.Length() + 1):
                pnt = nodes.Value(i)
                vertices.extend([pnt.X(), pnt.Y(), pnt.Z()])

            for i in range(1, tris.Length() + 1):
                tri = tris.Value(i)
                t1, t2, t3 = tri.Get()
                triangles.extend([
                    vertices[3 * (t1 - 1)], vertices[3 * (t1 - 1) + 1], vertices[3 * (t1 - 1) + 2],
                    vertices[3 * (t2 - 1)], vertices[3 * (t2 - 1) + 1], vertices[3 * (t2 - 1) + 2],
                    vertices[3 * (t3 - 1)], vertices[3 * (t3 - 1) + 1], vertices[3 * (t3 - 1) + 2],
                ])

        exp.Next()

    return vertices, triangles


def parse_step(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"STEP file not found: {filepath}")

    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)

    if status != IFSelect_RetDone:
        raise ValueError("Failed to read STEP file")

    reader.TransferRoots()
    shape = reader.OneShape()

    vertices, triangles = extract_triangles(shape)

    shape_data = {
        "version": 3,
        "parts": [
            {
                "id": "/Imported/Shape",
                "type": "shapes",
                "subtype": "solid",
                "name": os.path.basename(filepath),
                "shape": {
                    "vertices": vertices,
                    "triangles": triangles,
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
                "renderback": False,
                "accuracy": None,
                "bb": None
            }
        ],
        "loc": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
        "name": "Imported",
        "id": "/Imported",
        "normal_len": 0,
        "bb": None
    }

    return shape_data
