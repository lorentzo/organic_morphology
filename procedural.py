
# Blender 3.5.1.

import bpy
import mathutils
import bmesh
import numpy as np

# Help: https://blender.stackexchange.com/questions/40923/editing-a-mesh-in-proportional-mode-from-script
# https://www.youtube.com/watch?v=6qevtzXgk1k

# Gaussian.
def smooth_falloff(x, deviation, shift):
    return (1 / (deviation * np.sqrt(2 * np.pi))) * np.exp(-0.5 * (np.power(x - shift,2.0) / np.power(deviation,2.0)))

# Aglebraic.
def smooth_falloff2(x):
    return 1 / (np.power(1+np.sqrt(x), 3.0/2.0))

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

def main():

    target_collection = "grow_objects"
    for base_object in bpy.data.collections[target_collection].all_objects:

        # Create kdtree from object vertices.
        n_verts = len(base_object.data.vertices)
        kd = mathutils.kdtree.KDTree(n_verts)
        for i, v in enumerate(base_object.data.vertices):
            kd.insert(v.co, i)
        kd.balance()

        # Animate.
        curr_frame = 0
        delta_frame = 10
        max_frames = 500
        growth_change_frame = max_frames / 2.0

        # Scale whole object.
        original_obj_scale = mathutils.Vector(base_object.scale)
        scale_factor = 1.2
        base_object.keyframe_insert("scale", frame=curr_frame)
        base_object.scale = original_obj_scale * scale_factor
        base_object.keyframe_insert("scale", frame=growth_change_frame)
        base_object.scale = original_obj_scale
        base_object.keyframe_insert("scale", frame=max_frames)
        set_animation_fcurve(base_object.animation_data, option='BOUNCE', easing='EASE_IN_OUT')

        # Ini all vert keyframes to frame curr_frame.
        vertex_last_keyframe = {}
        for v in base_object.data.vertices:
            v.keyframe_insert("co", frame=curr_frame)
            vertex_last_keyframe.update({v.index: curr_frame}) # at beginning, all vertices have keyframe at frame curr_frame

        # Add movement and keyframes.
        curr_frame += delta_frame
        sign = 1
        while True:
            vi = np.random.randint(0, n_verts, 1)[0]
            v = base_object.data.vertices[vi]
            # Update coordinates.
            t = mathutils.noise.random()
            neighbour_distace = lerp(2.0, 4.0, t)
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
                falloff_deviation = 1
                falloff_shift = 0.0
                curr_vert.co += curr_vert.normal * smooth_falloff(dist, falloff_deviation, falloff_shift) * sign * lerp(1.5,3,mathutils.noise.random())
                # Keyframe updated coordinates.
                curr_vert.keyframe_insert("co", frame=curr_frame)
                # Store keyframe.
                vertex_last_keyframe[index] = curr_frame
            if mathutils.noise.random() > 0.6:
                curr_frame += delta_frame

            if curr_frame > max_frames:
                break

        # Add interpolation type.
        set_animation_fcurve(base_object.data.animation_data, option='BOUNCE', easing='EASE_IN_OUT')

#
# Script entry point.
#
if __name__ == "__main__":
    main()