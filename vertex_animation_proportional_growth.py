
# Blender 3.5.1.

import bpy
import mathutils
import bmesh
import numpy as np

# NB: all scales are set to fit original blender primitives.

# Help: https://blender.stackexchange.com/questions/40923/editing-a-mesh-in-proportional-mode-from-script
# https://www.youtube.com/watch?v=6qevtzXgk1k

# Gaussian.
def smooth_falloff(x, deviation, shift):
    return (1 / (deviation * np.sqrt(2 * np.pi))) * np.exp(-0.5 * (np.power(x - shift,2.0) / np.power(deviation,2.0)))

# Aglebraic.
def smooth_falloff2(x):
    return 1 / (np.power(1+np.sqrt(x), 3.0/2.0))

# Hann
def hann(x, L):
    if np.abs(x) <= L / 2.0:
        return (1.0 / L) * np.power(np.cos((np.pi * x) / L), 2.0)
    else:
        return 0.0

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
    size_of_extrusion_min_max = [0.75, 0.96] # how many vertices will be moved in one extrusion
    strength_of_extrusion_min_max = [0.35, 0.46]

    start_frame = 0
    delta_frame = 10 # distance between keyframes
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
            if mathutils.noise.random() > 0.3:
                curr_frame += delta_frame
            # OPTION 1: use only subset of vertices for animation.
            vi_tmp = np.random.randint(0, len(vert_indices_anim), 1)[0]
            vi = vert_indices_anim[vi_tmp]
            # OPTION 2: use random mesh vertex for animation.
            #vi = np.random.randint(0, n_verts, 1)[0]
            v = base_object.data.vertices[vi]
            # Update coordinates.
            t = mathutils.noise.random()
            neighbour_distace = lerp(size_of_extrusion_min_max[0], size_of_extrusion_min_max[1], t)
            # Growth direction.
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
            for (co, index, dist) in kd.find_range(v.co, neighbour_distace):
                curr_vert = base_object.data.vertices[index]
                # Perform movement.
                falloff_deviation = 0.1
                falloff_shift = 0.0
                strength_of_extrusion = lerp(strength_of_extrusion_min_max[0], strength_of_extrusion_min_max[1], 1.0-dist/neighbour_distace)
                smooth_falloff_val = hann(dist, 1.0) #smooth_falloff(dist, falloff_deviation, falloff_shift)
                curr_vert.co += curr_vert.normal * smooth_falloff_val * sign * strength_of_extrusion
                # Keyframe updated coordinates.
                curr_vert.keyframe_insert("co", frame=curr_frame)
                # Store keyframe.
                vertex_last_keyframe[index] = curr_frame
            # Recalulate normals since mesh was deformed.
            #recalculate_normals_bmesh(base_object)

            if curr_frame > max_frames:
                break

        # Add interpolation type.
        set_animation_fcurve(base_object.data.animation_data, option='BOUNCE', easing='EASE_IN_OUT')

        # Finally, add subdivision or remesh to make animation mesh smooth.
        add_subdivision_modifier(base_object, subdiv_levels=2)
        #add_remesh_modifier(base_object, voxel_size=0.05, shade_smooth=False)

#
# Script entry point.
#
if __name__ == "__main__":
    main()