
# Blender 3.5.1.

import bpy
import mathutils
import bmesh
import numpy as np

# TODO:
#* fix animation

def shape3(x, a = 2.0, b = 0.5):
    return 1.0 - np.power(np.abs(np.sin(np.pi * x / a)), b)

def hann(x, L):
    if np.abs(x) <= L / 2.0:
        return (1.0 / L) * np.power(np.cos((np.pi * x) / L), 2.0)
    else:
        return 0.0

def lerp(a, b, t):
    return (1.0 - t) * a + t * b

def extrude_all_faces_no_transform(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    bmesh.ops.extrude_face_region(
        bm, 
        geom=bm.faces[:], 
        edges_exclude=set(), 
        use_keep_orig=True, 
        use_normal_flip=False, 
        use_normal_from_adjacent=False, 
        use_dissolve_ortho_edges=False, 
        use_select_history=False)

    bm.to_mesh(obj.data)
    bm.clear()
    obj.data.update()
    bm.free()

def extrude_all_faces_no_transform2(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    bmesh.ops.extrude_discrete_faces(
        bm, 
        faces=bm.faces, 
        use_normal_flip=False, 
        use_select_history=False)

    bm.to_mesh(obj.data)
    bm.clear()
    obj.data.update()
    bm.free()

def extrude_all_edges_no_transform(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    bmesh.ops.extrude_edge_only(
        bm, 
        edges=bm.edges, 
        use_normal_flip=False, 
        use_select_history=False)

    bm.to_mesh(obj.data)
    bm.clear()
    obj.data.update()
    bm.free()

def extrude_with_transform(obj, face_idx, extrude_vec):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    ret = bmesh.ops.extrude_face_region(
        bm, 
        geom=[bm.faces[face_idx]], 
        edges_exclude=set(), 
        use_keep_orig=True, 
        use_normal_flip=False, 
        use_normal_from_adjacent=False, 
        use_dissolve_ortho_edges=False, 
        use_select_history=False)

    verts = [e for e in ret['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec = extrude_vec, verts=verts)

    updated_vertex_indices = []
    for v in verts:
        updated_vertex_indices.append(v.index)

    bm.to_mesh(obj.data)
    bm.clear()
    obj.data.update()
    bm.free()

    return updated_vertex_indices
    
def keyframe_vertices(obj, vertex_indices, curr_frame):
    for vi in vertex_indices:
        obj.data.vertices[vi].keyframe_insert("co", frame=curr_frame)

def keyframe_vertices_all(obj, curr_frame):
    for v in obj.data.vertices:
        v.keyframe_insert("co", frame=curr_frame)

def main():

    # Parameters.
    target_collection = "proportional_faces_movement"
    n_extrusions = 10
    extrusion_radius = 0.5
    delta_frame = 10
    
    for base_object in bpy.data.collections[target_collection].all_objects:

        # Create kdtree from object faces.
        n_faces = len(base_object.data.polygons)
        kd = mathutils.kdtree.KDTree(n_faces)
        for f in base_object.data.polygons:
            kd.insert(f.center, f.index)
        kd.balance()

        # Extrude.
        curr_frame = 0
        keyframe_vertices_all(base_object, curr_frame)
        for i in range(n_extrusions):
            fi = np.random.randint(0, n_faces, 1)[0]
            f = base_object.data.polygons[fi]
            for (pos, index, dist) in kd.find_range(f.center, extrusion_radius):
                #extrusion_amount = hann(dist, 1.0)
                #extrusion_amount = lerp(0.1, 0.8, 1.0-dist/extrusion_radius)
                extrusion_amount = shape3(dist, a = 2.0, b = 0.5)
                extrude_vec = base_object.data.polygons[index].normal * extrusion_amount
                updated_vertex_indices = extrude_with_transform(base_object, index, extrude_vec)
                keyframe_vertices(base_object, updated_vertex_indices, curr_frame)
                curr_frame += delta_frame

#
# Script entry point.
#
if __name__ == "__main__":
    main()