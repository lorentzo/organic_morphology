
# Blender 3.5.1.

import bpy
import mathutils
import bmesh
import numpy as np

# NB: all scales are set to fit original blender primitives.

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

def select_activate_only(objects=[]):
    for obj in bpy.data.objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = None 
    for obj in objects:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

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

def recalculate_normals_bmesh(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.clear()
    obj.data.update()
    bm.free()

def add_subdivision_modifier(obj, subdiv_levels=2):
    mod = obj.modifiers.new("SubdivisionSurface", 'SUBSURF')
    mod.subdivision_type = 'CATMULL_CLARK'
    mod.levels = subdiv_levels
    mod.render_levels = subdiv_levels
    mod.show_only_control_edges = True
    # TODO: advanced options?

def add_remesh_modifier(obj, voxel_size=0.05, shade_smooth=False):
    mod = obj.modifiers.new("Remesh", 'REMESH')
    mod.mode = 'VOXEL'
    mod.voxel_size = voxel_size
    mod.adaptivity = 0
    mod.use_smooth_shade = shade_smooth
    # TODO: other options?

def main():

    # Parameters.
    target_collection = "proportional_vertex_growth"

    whole_object_scaling_factor_min_max = [1.1, 1.3]

    n_anim_vert = 30
    size_of_extrusion_min_max = [0.1, 0.6] # how many vertices will be moved in one extrusion
    extrude_strength_min_max = [0.2, 0.5]
    n_extrusions_per_keyframe_update = 3

    start_frame = 0
    delta_frame = 50 # distance between keyframes
    max_frames = 500
    growth_change_frame = max_frames / 2.0 # first part is growth, 2nd part is shrinkage

    # Algorithm.
    for base_object in bpy.data.collections[target_collection].all_objects:

        # Create kdtree from object vertices.
        n_verts = len(base_object.data.vertices)
        kd = mathutils.kdtree.KDTree(n_verts)
        for i, v in enumerate(base_object.data.vertices):
            kd.insert(v.co, i)
        kd.balance()

        # Animate.
        curr_frame = start_frame

        # Animate scaling of the whole object.
        original_obj_scale = mathutils.Vector(base_object.scale)
        scale_factor = lerp(whole_object_scaling_factor_min_max[0], whole_object_scaling_factor_min_max[1], mathutils.noise.random())
        base_object.keyframe_insert("scale", frame=curr_frame)
        base_object.scale = original_obj_scale * scale_factor
        base_object.keyframe_insert("scale", frame=growth_change_frame)
        base_object.scale = original_obj_scale
        base_object.keyframe_insert("scale", frame=max_frames)
        set_animation_fcurve(base_object.animation_data, option='BOUNCE', easing='EASE_IN_OUT')

        # Initialize all vert keyframes to curr_frame.
        vertex_last_keyframe = {}
        for v in base_object.data.vertices:
            v.keyframe_insert("co", frame=curr_frame)
            vertex_last_keyframe.update({v.index: curr_frame}) # at beginning, all vertices have keyframe at frame curr_frame       
        
        # Animate vertices.
        sign = 1
        # Take only subset of vertices which will be animated.
        vert_indices_anim = np.random.randint(0, n_verts, n_anim_vert)
        while True:
            curr_frame += delta_frame
            for i in range(n_extrusions_per_keyframe_update):
                # OPTION 1: use only subset of vertices for animation.
                #vi_tmp = np.random.randint(0, len(vert_indices_anim), 1)[0]
                #vi = vert_indices_anim[vi_tmp]
                # OPTION 2: use random mesh vertex for animation.
                vi = np.random.randint(0, n_verts, 1)[0]
                v = base_object.data.vertices[vi]
                # Compute distance of extrude op.
                t = mathutils.noise.random()
                neighbour_distace = lerp(size_of_extrusion_min_max[0], size_of_extrusion_min_max[1], t)
                # Determine extrude (growth) direction.
                if curr_frame < growth_change_frame:
                    # Direction of growth in first part is mostly positive.
                    if mathutils.noise.random() > 0.2:
                        sign = 1.0
                    else:
                        sign = -1.0
                else:
                    # Direction of growth in second part is mostly negative.
                    if mathutils.noise.random() > 0.2:
                        sign = -1.0
                    else:
                        sign = 1.0
                # Extrude shape and strength randomization.
                t = mathutils.noise.random()
                extrude_strength = lerp(extrude_strength_min_max[0], extrude_strength_min_max[1], t)
                a = lerp(0.1, 4.0, mathutils.noise.random())
                b = lerp(0.1, 4.0, mathutils.noise.random())
                c = lerp(0.1, 4.0, mathutils.noise.random())
                for (co, index, dist) in kd.find_range(v.co, neighbour_distace):
                    curr_vert = base_object.data.vertices[index]
                    # Perform movement.
                    #extrude_shape = shape_hann(dist, 1.0)
                    extrude_shape = shape1(dist, a=1.0)
                    #extrude_shape = shape2(dist, a=2.0, b=2.0)
                    #extrude_shape = shape3(dist, a=2.0, b=0.5)
                    #extrude_shape = shape4(dist, a=2.0, b=1.0, c=0.5)
                    #extrude_shape = shape5(dist, a=2.0, b=1.0, c=0.5)
                    #extrude_shape = lerp(0.1, 0.5, shape_gauss(dist, deviation=0.1, shift=0.0))
                    #extrude_shape = shape_lerp(dist, max_x=neighbour_distace, minv=0.1, maxv=0.5)
                    curr_vert.co += curr_vert.normal * sign * extrude_shape * extrude_strength
                    # Keyframe updated coordinates.
                    curr_vert.keyframe_insert("co", frame=curr_frame)
                    # Store keyframe.
                    vertex_last_keyframe[index] = curr_frame
                # Recalulate normals since mesh was deformed.
                #recalculate_normals_bmesh(base_object)

            if curr_frame > max_frames:
                break

        # Add interpolation type.
        set_animation_fcurve(base_object.data.animation_data, option='EXPO', easing='EASE_IN_OUT')

        # Finally, add subdivision or remesh to make animation mesh smooth.
        #add_subdivision_modifier(base_object, subdiv_levels=2)
        add_remesh_modifier(base_object, voxel_size=0.07, shade_smooth=False)

#
# Script entry point.
#
if __name__ == "__main__":
    main()