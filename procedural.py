
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

def lerp(t, a, b):
    return (1.0 - t) * a + t * b

def select_activate_only(objects=[]):
    for obj in bpy.data.objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = None 
    for obj in objects:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj


# GUI selection.
selected_object = bpy.context.selected_objects[0] 
print("Selected object:", selected_object.name)

# Create kdtree.
n_verts = len(selected_object.data.vertices)
kd = mathutils.kdtree.KDTree(n_verts)
for i, v in enumerate(selected_object.data.vertices):
    kd.insert(v.co, i)
kd.balance()

# Animate.
max_movements = 50
curr_frame = 0
delta_frame = 10
# Take n random vert indices.
rand_vert_indices = np.random.randint(0, n_verts, max_movements)
vertex_last_keyframe = {}
for i in rand_vert_indices:
    vertex_last_keyframe.update({i: 0})
# Ini all vert keyframes.
for v in selected_object.data.vertices:
    v.keyframe_insert("co", frame=0)
for vi in rand_vert_indices:
    v = selected_object.data.vertices[vi]
    # Update coordinates.
    search_dist = 2
    deviation = np.abs(mathutils.noise.noise(v.co)) * 3
    for (co, index, dist) in kd.find_range(v.co, search_dist):
        curr_vert = selected_object.data.vertices[index]
        # Keyframe ini coordinates.
        if not index in vertex_last_keyframe: 
            curr_vert.keyframe_insert("co", frame=curr_frame)
        # Perform movement.
        curr_vert.select = True
        curr_vert.co += curr_vert.normal * smooth_falloff(dist, 1, 0) * lerp(0.5,3,mathutils.noise.random())
        # Keyframe updated coordinates.
        curr_vert.keyframe_insert("co", frame=curr_frame+delta_frame)
        # Store keyframe.
        vertex_last_keyframe[index] = curr_frame+delta_frame
    if mathutils.noise.random() > 0.6:
        curr_frame += delta_frame
    


#for i_key_frame in range(n_key_frames):
#for v in selected_object.data.vertices:
    #selected_object.data.vertices[v.index].keyframe_insert("co", frame=curr_frame)
    #if mathutils.noise.random() > 0.5:
"""
v = selected_object.data.vertices[4]
co_find = v.co
for (co, index, dist) in kd.find_range(co_find, 2):
    selected_object.data.vertices[index].select = True
    print(co)
"""     
                    
        #selected_object.data.vertices[v.index].keyframe_insert("co", frame=curr_frame)
    #curr_frame += delta_frame