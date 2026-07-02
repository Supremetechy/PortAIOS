import bpy
import os
from mathutils import Vector

# Clear scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Create head (UV Sphere)
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1)
head = bpy.context.active_object
head.name = "AI_Avatar_Head"

# Smooth shading
bpy.ops.object.shade_smooth()

# Add Basis shape key
head.shape_key_add(name="Basis")

# -----------------------
# FUNCTION TO CREATE SHAPE KEY
# -----------------------
def create_shape_key(name, transform_func):
    key = head.shape_key_add(name=name)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    
    for v in head.data.vertices:
        key.data[v.index].co = transform_func(v.co.copy())
    
    bpy.ops.object.mode_set(mode='OBJECT')

# -----------------------
# FACIAL EXPRESSIONS
# -----------------------

# Smile
def smile(co):
    if co.z < 0.2 and abs(co.x) < 0.6:
        co.z += 0.1
    return co

create_shape_key("Smile", smile)

# Frown
def frown(co):
    if co.z < 0.2 and abs(co.x) < 0.6:
        co.z -= 0.1
    return co

create_shape_key("Frown", frown)

# Surprise
def surprise(co):
    if co.z < -0.2:
        co.z -= 0.15
    return co

create_shape_key("Surprise", surprise)

# Angry
def angry(co):
    if co.y > 0.3:
        co.z -= 0.1
    return co

create_shape_key("Angry", angry)

# Sad
def sad(co):
    if co.z < 0.2:
        co.z -= 0.05
    return co

create_shape_key("Sad", sad)

# -----------------------
# WINKS
# -----------------------

def wink_left(co):
    if co.x < 0:
        co.z -= 0.2
    return co

create_shape_key("Wink_Left", wink_left)

def wink_right(co):
    if co.x > 0:
        co.z -= 0.2
    return co

create_shape_key("Wink_Right", wink_right)

# -----------------------
# VISEMES (Speech Shapes)
# -----------------------

def viseme_A(co):
    if co.z < 0:
        co.z -= 0.15
    return co

create_shape_key("Viseme_A", viseme_A)

def viseme_O(co):
    if co.z < 0:
        co.x *= 0.8
        co.z -= 0.1
    return co

create_shape_key("Viseme_O", viseme_O)

def viseme_E(co):
    if co.z < 0:
        co.x *= 1.1
    return co

create_shape_key("Viseme_E", viseme_E)

def viseme_M(co):
    if co.z < 0:
        co.z += 0.1
    return co

create_shape_key("Viseme_M", viseme_M)

# -----------------------
# EXPORT TO GLB
# -----------------------

desktop = os.path.join(os.path.expanduser("~"), "Desktop")
filepath = os.path.join(desktop, "AI_Avatar.glb")

bpy.ops.export_scene.gltf(
    filepath=filepath,
    export_format='GLB',
    export_apply=True,
    export_morph=True,
)

print("✅ GLB Exported to:", filepath)