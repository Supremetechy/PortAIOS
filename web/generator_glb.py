import numpy as np
import trimesh



# Create sphere mesh
mesh = trimesh.creation.icosphere(subdivisions=4, radius=1.0)
mesh.visual = trimesh.visual.ColorVisuals(mesh)


# Export GLB
mesh.export("AI_Avatar.glb")

print("✅ GLB without morph target exported.")
# Create smile morph (raise lower vertices)
vertices = mesh.vertices.copy()
smile = vertices.copy()

for i, v in enumerate(smile):
    if v[2] < 0:
        smile[i][2] += 0.1

# Create morph target as delta
delta = smile - vertices

# Normalize delta
#delta = delta / np.linalg.norm(delta, axis=1, keepdims=True)


# Add morph target
mesh.morph_targets = [delta]

mesh.export("AI_Avatar.glb")

print("✅ GLB with morph target exported.")

print("✅ GLB file created.")