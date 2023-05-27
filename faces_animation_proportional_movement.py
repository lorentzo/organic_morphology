
# Blender 3.5.1.

import bpy
import mathutils
import bmesh
import numpy as np

# Shaping functions:
# https://realtimevfx.com/t/collection-of-useful-curve-shaping-functions/3704

# t = {0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5}
def shape1(x, a=0.5):
    return 1.0 - np.power(np.abs(x), a)

def shape2(x, a=2.0, b=2.0):
    return np.power(np.cos(np.pi * x / 2.0), 2.0)

def shape3(x, a = 2.0, b = 0.5):
    return 1.0 - np.power(np.abs(np.sin(np.pi * x / a)), b)

def shape4(x, a=2.0, b=1.0, c=0.5):
    return np.power(np.minimum(np.cos(np.pi * x / a), b - np.abs(x)), c)

def shape5(x, a=2.0, b=1.0, c=0.5):
    return 1.0 - np.power(np.maximum(0.0, np.abs(x) * a - b), c)

# Gaussian.
def shape_gauss(x, deviation, shift):
    return (1 / (deviation * np.sqrt(2 * np.pi))) * np.exp(-0.5 * (np.power(x - shift,2.0) / np.power(deviation,2.0)))

# Aglebraic.
def shape_alg(x):
    return 1 / (np.power(1+np.sqrt(x), 3.0/2.0))

# Hann
def shape_hann(x, L):
    if np.abs(x) <= L / 2.0:
        return (1.0 / L) * np.power(np.cos((np.pi * x) / L), 2.0)
    else:
        return 0.0

def shape_lerp(x, max_x, minv, maxv):
    xt = 1.0 - x / max_x
    return lerp(minv, maxv, xt)

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

def extrude_with_transform(obj, face_idx, extrude_vec, curr_keyframe, delta_keyframe):

    # Create bmesh structure from original mesh.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    # Using bmesh create extrusion for face_idx.
    # Store geometry which is created.
    ret = bmesh.ops.extrude_face_region(
        bm, 
        geom=[bm.faces[face_idx]], 
        edges_exclude=set(), 
        use_keep_orig=True, 
        use_normal_flip=False, 
        use_normal_from_adjacent=False, 
        use_dissolve_ortho_edges=False, 
        use_select_history=False)

    # Obtain created vertices of created geometry.
    verts = [e for e in ret['geom'] if isinstance(e, bmesh.types.BMVert)]

    # Store indices of created vertices.
    updated_vertex_indices = []
    for v in verts:
        updated_vertex_indices.append(v.index)

    # Update original mesh.
    bm.to_mesh(obj.data)
    obj.data.update()
    
    # Set initial keyframes for created vertices using original mesh.
    keyframe_vertices(obj, updated_vertex_indices, curr_keyframe-delta_keyframe)

    # Use bmesh for translation of created vertices.
    bmesh.ops.translate(bm, vec = extrude_vec, verts=verts)

    # Update original mesh.
    bm.to_mesh(obj.data)
    obj.data.update()

    # Set final keyframes for created vertices using original mesh.
    keyframe_vertices(obj, updated_vertex_indices, curr_keyframe)

    bm.clear()
    bm.free()

    return updated_vertex_indices
    
def keyframe_vertices(obj, vertex_indices, curr_frame):
    for vi in vertex_indices:
        obj.data.vertices[vi].keyframe_insert("co", frame=curr_frame)

def keyframe_vertices_all(obj, curr_frame):
    for v in obj.data.vertices:
        v.keyframe_insert("co", frame=curr_frame)

# https://behreajj.medium.com/scripting-curves-in-blender-with-python-c487097efd13
def set_animation_fcurve(animation_data, option='LINEAR', easing='EASE_IN_OUT'):
    # Animation data must be given!
    # animation_data: object.data.animation_data.action.fcurves
    # animation_data: object.animation_data.action.fcurves
    fcurves = animation_data.action.fcurves
    for fcurve in fcurves:
        for kf in fcurve.keyframe_points:
            # Options: ['CONSTANT', 'LINEAR', 'BEZIER', 'SINE',
            # 'QUAD', 'CUBIC', 'QUART', 'QUINT', 'EXPO', 'CIRC',
            # 'BACK', 'BOUNCE', 'ELASTIC']
            kf.interpolation = option
            # Options: ['AUTO', 'EASE_IN', 'EASE_OUT', 'EASE_IN_OUT']
            kf.easing = easing

def main():

    # Parameters.
    target_collection = "proportional_faces_movement"
    n_extrusions = 10
    extrusion_radius = 0.5
    delta_frame = 50
    max_frames = 500
    
    for base_object in bpy.data.collections[target_collection].all_objects:

        # Create kdtree from object faces.
        n_faces = len(base_object.data.polygons)
        kd = mathutils.kdtree.KDTree(n_faces)
        for f in base_object.data.polygons:
            kd.insert(f.center, f.index)
        kd.balance()

        # Extrude.
        curr_frame = 0
        #keyframe_vertices_all(base_object, curr_frame)
        while True:
            if not first_run and mathutils.noise.random() > 0.5:
                curr_frame += delta_frame
            fi = np.random.randint(0, n_faces, 1)[0]
            f = base_object.data.polygons[fi]
            a = lerp(0.1, 4.0, mathutils.noise.random())
            b = lerp(0.1, 4.0, mathutils.noise.random())
            c = lerp(0.1, 4.0, mathutils.noise.random())
            extrusion_strength = lerp(0.1, 2.0, mathutils.noise.random())
            for (pos, index, dist) in kd.find_range(f.center, extrusion_radius):
                #extrude_shape = shape1(dist, a=a)
                extrude_shape = shape2(dist, a=a, b=b)
                #extrude_shape = shape3(dist, a=a, b=b)
                #extrude_shape = shape5(dist, a=a, b=b, c=c)
                extrude_vec = base_object.data.polygons[index].normal * extrude_shape * extrusion_strength
                extrude_with_transform(base_object, index, extrude_vec, curr_frame, delta_frame)
            if curr_frame > max_frames:
                break

        # Add interpolation type.
        set_animation_fcurve(base_object.data.animation_data, option='BOUNCE', easing='EASE_IN_OUT')
            

#
# Script entry point.
#
if __name__ == "__main__":
    main()