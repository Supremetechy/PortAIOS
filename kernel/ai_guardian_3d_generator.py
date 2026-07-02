"""
AI Guardian 3D Model Generator
Creates a holographic humanoid avatar with morph targets for:
- Lip-sync visemes (A, E, I, O, U, M, F, L, etc.)
- Facial expressions (smile, frown, surprise, thinking)
- Hand gestures (stop, wave, point, thinking pose)
"""

from __future__ import annotations
import io
import json
import struct
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np

try:
    import trimesh
except ImportError:
    trimesh = None

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = _REPO_ROOT / "models" / "ai_guardian.glb"


class AIGuardian3DGenerator:
    """Generate a stylized holographic humanoid avatar"""
    
    def __init__(self):
        self.scale = 1.0
        
    def create_holographic_humanoid(self) -> trimesh.Trimesh:
        """Create a stylized humanoid mesh with holographic aesthetic"""
        
        # HEAD (sphere with slight elongation)
        head = trimesh.creation.icosphere(subdivisions=3, radius=0.15)
        head.vertices *= [1.0, 1.1, 0.95]  # slight elongation
        head.apply_translation([0, 1.65, 0])
        
        # TORSO (tapered cylinder)
        torso = trimesh.creation.cylinder(radius=0.2, height=0.6, sections=16)
        torso_verts = torso.vertices.copy()
        # Taper: wider at shoulders, narrower at waist
        for i, v in enumerate(torso_verts):
            y_factor = (v[1] + 0.3) / 0.6  # 0 at bottom, 1 at top
            scale_factor = 0.7 + 0.3 * y_factor
            torso_verts[i] = [v[0] * scale_factor, v[1], v[2] * scale_factor]
        torso.vertices = torso_verts
        torso.apply_translation([0, 1.2, 0])
        
        # PELVIS (smaller cylinder)
        pelvis = trimesh.creation.cylinder(radius=0.18, height=0.15, sections=16)
        pelvis.apply_translation([0, 0.825, 0])
        
        # ARMS (cylinders with slight taper)
        def create_arm(x_side: float) -> trimesh.Trimesh:
            upper_arm = trimesh.creation.cylinder(radius=0.05, height=0.35, sections=12)
            upper_arm.apply_translation([x_side * 0.25, 1.35, 0])
            
            lower_arm = trimesh.creation.cylinder(radius=0.045, height=0.35, sections=12)
            lower_arm.apply_translation([x_side * 0.25, 0.875, 0])
            
            # Hand (small sphere)
            hand = trimesh.creation.icosphere(subdivisions=2, radius=0.06)
            hand.apply_translation([x_side * 0.25, 0.65, 0])
            
            return upper_arm + lower_arm + hand
        
        left_arm = create_arm(-1.0)
        right_arm = create_arm(1.0)
        
        # LEGS
        def create_leg(x_side: float) -> trimesh.Trimesh:
            upper_leg = trimesh.creation.cylinder(radius=0.07, height=0.45, sections=12)
            upper_leg.apply_translation([x_side * 0.1, 0.525, 0])
            
            lower_leg = trimesh.creation.cylinder(radius=0.06, height=0.45, sections=12)
            lower_leg.apply_translation([x_side * 0.1, 0.075, 0])
            
            # Foot (small box)
            foot = trimesh.creation.box(extents=[0.08, 0.05, 0.15])
            foot.apply_translation([x_side * 0.1, -0.125, 0.05])
            
            return upper_leg + lower_leg + foot
        
        left_leg = create_leg(-1.0)
        right_leg = create_leg(1.0)
        
        # Combine all parts
        avatar = head + torso + pelvis + left_arm + right_arm + left_leg + right_leg
        
        # Center and scale
        avatar.apply_translation([0, -0.85, 0])  # feet at origin
        
        return avatar
    
    def add_facial_region_markers(self, mesh: trimesh.Trimesh) -> Dict[str, np.ndarray]:
        """Identify facial regions for morphing"""
        vertices = mesh.vertices
        
        # Find head region (upper vertices)
        head_mask = vertices[:, 1] > 0.7  # above shoulders
        
        # Face region (front half of head)
        face_mask = head_mask & (vertices[:, 2] > 0)
        
        # Mouth region (lower front of face)
        mouth_center_y = vertices[head_mask, 1].min() + 0.1
        mouth_mask = face_mask & (vertices[:, 1] < mouth_center_y) & (vertices[:, 1] > mouth_center_y - 0.08)
        
        # Eye regions
        eye_y = vertices[head_mask, 1].max() - 0.05
        left_eye_mask = face_mask & (vertices[:, 0] < -0.03) & (np.abs(vertices[:, 1] - eye_y) < 0.03)
        right_eye_mask = face_mask & (vertices[:, 0] > 0.03) & (np.abs(vertices[:, 1] - eye_y) < 0.03)
        
        return {
            'head': head_mask,
            'face': face_mask,
            'mouth': mouth_mask,
            'left_eye': left_eye_mask,
            'right_eye': right_eye_mask
        }
    
    def create_viseme_morphs(self, base_verts: np.ndarray, regions: Dict) -> Dict[str, np.ndarray]:
        """Create morph targets for lip-sync visemes"""
        morphs = {}
        mouth_mask = regions['mouth']
        mouth_indices = np.where(mouth_mask)[0]
        
        if len(mouth_indices) == 0:
            return morphs
        
        mouth_center = base_verts[mouth_mask].mean(axis=0)
        
        # Viseme A (open mouth vertically)
        delta_a = np.zeros_like(base_verts)
        for idx in mouth_indices:
            v = base_verts[idx]
            offset = v - mouth_center
            delta_a[idx] = [0, -offset[1] * 0.3, offset[2] * 0.2]
        morphs['viseme_aa'] = delta_a
        
        # Viseme O (round lips)
        delta_o = np.zeros_like(base_verts)
        for idx in mouth_indices:
            v = base_verts[idx]
            offset = v - mouth_center
            r = np.linalg.norm(offset[:2])
            if r > 0:
                delta_o[idx] = [offset[0] * 0.2, offset[1] * 0.2, offset[2] * 0.3]
        morphs['viseme_o'] = delta_o
        
        # Viseme E (wide smile)
        delta_e = np.zeros_like(base_verts)
        for idx in mouth_indices:
            v = base_verts[idx]
            offset = v - mouth_center
            delta_e[idx] = [offset[0] * 0.4, -abs(offset[1]) * 0.1, offset[2] * 0.1]
        morphs['viseme_e'] = delta_e
        
        # Viseme I (narrow smile)
        delta_i = np.zeros_like(base_verts)
        for idx in mouth_indices:
            v = base_verts[idx]
            offset = v - mouth_center
            delta_i[idx] = [offset[0] * 0.3, -abs(offset[1]) * 0.15, offset[2] * 0.05]
        morphs['viseme_i'] = delta_i
        
        # Viseme U (pucker)
        delta_u = np.zeros_like(base_verts)
        for idx in mouth_indices:
            v = base_verts[idx]
            offset = v - mouth_center
            delta_u[idx] = [offset[0] * 0.15, offset[1] * 0.15, offset[2] * 0.4]
        morphs['viseme_u'] = delta_u
        
        # Viseme M (lips closed)
        delta_m = np.zeros_like(base_verts)
        for idx in mouth_indices:
            v = base_verts[idx]
            offset = v - mouth_center
            delta_m[idx] = [0, offset[1] * 0.2, -offset[2] * 0.1]
        morphs['viseme_m'] = delta_m
        
        # Viseme F (bottom lip to teeth)
        delta_f = np.zeros_like(base_verts)
        for idx in mouth_indices:
            v = base_verts[idx]
            if v[1] < mouth_center[1]:  # lower lip
                delta_f[idx] = [0, 0.01, -0.01]
        morphs['viseme_f'] = delta_f
        
        return morphs
    
    def create_expression_morphs(self, base_verts: np.ndarray, regions: Dict) -> Dict[str, np.ndarray]:
        """Create facial expression morph targets"""
        morphs = {}
        face_mask = regions['face']
        mouth_mask = regions['mouth']
        
        # Smile
        delta_smile = np.zeros_like(base_verts)
        mouth_center = base_verts[mouth_mask].mean(axis=0) if mouth_mask.any() else np.array([0, 0.8, 0])
        for idx in np.where(mouth_mask)[0]:
            v = base_verts[idx]
            offset = v - mouth_center
            delta_smile[idx] = [offset[0] * 0.3, abs(offset[1]) * 0.2, 0]
        morphs['expr_smile'] = delta_smile
        
        # Thinking (slight frown + head tilt)
        delta_think = np.zeros_like(base_verts)
        for idx in np.where(mouth_mask)[0]:
            v = base_verts[idx]
            delta_think[idx] = [0, -0.005, 0]
        morphs['expr_thinking'] = delta_think
        
        # Surprise (raised eyebrows, open mouth)
        delta_surprise = np.zeros_like(base_verts)
        for idx in np.where(regions['left_eye'] | regions['right_eye'])[0]:
            delta_surprise[idx] = [0, 0.01, 0]
        for idx in np.where(mouth_mask)[0]:
            v = base_verts[idx]
            offset = v - mouth_center
            delta_surprise[idx] = [0, -abs(offset[1]) * 0.4, offset[2] * 0.2]
        morphs['expr_surprise'] = delta_surprise
        
        return morphs
    
    def create_hand_gesture_morphs(self, base_verts: np.ndarray) -> Dict[str, np.ndarray]:
        """Create hand gesture pose morphs"""
        morphs = {}
        
        # Find hand regions (lower arm extremities)
        left_hand_mask = (base_verts[:, 0] < -0.2) & (base_verts[:, 1] < 0.75) & (base_verts[:, 1] > 0.6)
        right_hand_mask = (base_verts[:, 0] > 0.2) & (base_verts[:, 1] < 0.75) & (base_verts[:, 1] > 0.6)
        
        # Stop gesture (right hand raised, palm forward)
        delta_stop = np.zeros_like(base_verts)
        for idx in np.where(right_hand_mask)[0]:
            delta_stop[idx] = [0.05, 0.4, 0.15]
        morphs['gesture_stop'] = delta_stop
        
        # Wave gesture (right hand up and tilted)
        delta_wave = np.zeros_like(base_verts)
        for idx in np.where(right_hand_mask)[0]:
            delta_wave[idx] = [0.1, 0.5, 0]
        morphs['gesture_wave'] = delta_wave
        
        # Thinking pose (hand to chin)
        delta_think_pose = np.zeros_like(base_verts)
        for idx in np.where(right_hand_mask)[0]:
            delta_think_pose[idx] = [-0.15, 0.15, 0.15]
        morphs['gesture_thinking'] = delta_think_pose
        
        # Point gesture (right hand forward, finger extended)
        delta_point = np.zeros_like(base_verts)
        for idx in np.where(right_hand_mask)[0]:
            delta_point[idx] = [0, 0.1, 0.3]
        morphs['gesture_point'] = delta_point
        
        return morphs
    
    def generate(self, output_path: Optional[Path] = None) -> str:
        """Generate complete AI Guardian GLB with all morph targets"""
        if trimesh is None:
            raise ImportError("trimesh required: pip install trimesh")
        
        if output_path is None:
            output_path = DEFAULT_OUTPUT
        
        print(f"[AIGuardian3D] Creating holographic humanoid mesh...")
        mesh = self.create_holographic_humanoid()
        base_verts = mesh.vertices.copy()
        
        print(f"[AIGuardian3D] Identifying facial regions...")
        regions = self.add_facial_region_markers(mesh)
        
        print(f"[AIGuardian3D] Creating viseme morphs...")
        viseme_morphs = self.create_viseme_morphs(base_verts, regions)
        
        print(f"[AIGuardian3D] Creating expression morphs...")
        expression_morphs = self.create_expression_morphs(base_verts, regions)
        
        print(f"[AIGuardian3D] Creating gesture morphs...")
        gesture_morphs = self.create_hand_gesture_morphs(base_verts)
        
        # Combine all morphs
        all_morphs = {**viseme_morphs, **expression_morphs, **gesture_morphs}
        
        print(f"[AIGuardian3D] Encoding {len(all_morphs)} morph targets to GLB...")
        glb_bytes = self._encode_glb_with_morphs(mesh, all_morphs)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(glb_bytes)
        
        print(f"[AIGuardian3D] ✓ Generated: {output_path}")
        print(f"[AIGuardian3D] Morph targets: {list(all_morphs.keys())}")
        
        return str(output_path)
    
    def _encode_glb_with_morphs(self, mesh: trimesh.Trimesh, morphs: Dict[str, np.ndarray]) -> bytes:
        """Encode mesh with morph targets to GLB format"""
        
        verts = mesh.vertices.astype(np.float32)
        faces = mesh.faces.astype(np.uint32)
        normals = mesh.vertex_normals.astype(np.float32)
        
        # Calculate bounds
        v_min = verts.min(axis=0).tolist()
        v_max = verts.max(axis=0).tolist()
        
        # Build binary buffer
        buffer_parts = []
        buffer_views = []
        accessors = []
        
        def add_data(data: bytes, target: Optional[int] = None) -> int:
            """Add data to buffer and return accessor index"""
            byte_offset = sum(len(p) for p in buffer_parts)
            buffer_parts.append(data)
            
            view_idx = len(buffer_views)
            buffer_views.append({
                "buffer": 0,
                "byteOffset": byte_offset,
                "byteLength": len(data),
                **({"target": target} if target is not None else {})
            })
            return view_idx
        
        # Vertices
        vert_bytes = verts.tobytes()
        vert_view = add_data(vert_bytes, target=34962)
        accessors.append({
            "bufferView": vert_view,
            "componentType": 5126,  # FLOAT
            "count": len(verts),
            "type": "VEC3",
            "min": v_min,
            "max": v_max
        })
        vert_accessor = len(accessors) - 1
        
        # Normals
        norm_bytes = normals.tobytes()
        norm_view = add_data(norm_bytes, target=34962)
        accessors.append({
            "bufferView": norm_view,
            "componentType": 5126,
            "count": len(normals),
            "type": "VEC3"
        })
        norm_accessor = len(accessors) - 1
        
        # Faces
        face_bytes = faces.tobytes()
        face_view = add_data(face_bytes, target=34963)
        accessors.append({
            "bufferView": face_view,
            "componentType": 5125,  # UNSIGNED_INT
            "count": len(faces) * 3,
            "type": "SCALAR"
        })
        face_accessor = len(accessors) - 1
        
        # Morph targets
        morph_targets = []
        morph_weights = []
        target_names = []
        
        for morph_name, delta in morphs.items():
            delta_f32 = delta.astype(np.float32)
            delta_bytes = delta_f32.tobytes()
            delta_view = add_data(delta_bytes, target=34962)
            
            delta_min = delta_f32.min(axis=0).tolist()
            delta_max = delta_f32.max(axis=0).tolist()
            
            accessors.append({
                "bufferView": delta_view,
                "componentType": 5126,
                "count": len(delta),
                "type": "VEC3",
                "min": delta_min,
                "max": delta_max
            })
            delta_accessor = len(accessors) - 1
            
            morph_targets.append({"POSITION": delta_accessor})
            morph_weights.append(0.0)
            target_names.append(morph_name)
        
        # Combine buffer
        full_buffer = b''.join(buffer_parts)
        
        # Pad to 4-byte alignment
        padding = (4 - (len(full_buffer) % 4)) % 4
        full_buffer += b'\x00' * padding
        
        # Build JSON structure
        gltf = {
            "asset": {"version": "2.0", "generator": "AIGuardian3D"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [{
                "primitives": [{
                    "attributes": {
                        "POSITION": vert_accessor,
                        "NORMAL": norm_accessor
                    },
                    "indices": face_accessor,
                    "mode": 4,  # TRIANGLES
                    "targets": morph_targets
                }],
                "weights": morph_weights,
                "extras": {"targetNames": target_names}
            }],
            "accessors": accessors,
            "bufferViews": buffer_views,
            "buffers": [{"byteLength": len(full_buffer)}]
        }
        
        json_str = json.dumps(gltf, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        json_padding = (4 - (len(json_bytes) % 4)) % 4
        json_bytes += b' ' * json_padding
        
        # GLB structure
        glb = io.BytesIO()
        glb.write(struct.pack('<I', 0x46546C67))  # magic: glTF
        glb.write(struct.pack('<I', 2))  # version
        
        total_length = 12 + 8 + len(json_bytes) + 8 + len(full_buffer)
        glb.write(struct.pack('<I', total_length))
        
        # JSON chunk
        glb.write(struct.pack('<I', len(json_bytes)))
        glb.write(struct.pack('<I', 0x4E4F534A))  # JSON
        glb.write(json_bytes)
        
        # BIN chunk
        glb.write(struct.pack('<I', len(full_buffer)))
        glb.write(struct.pack('<I', 0x004E4942))  # BIN
        glb.write(full_buffer)
        
        return glb.getvalue()


def main():
    """Generate AI Guardian 3D model"""
    generator = AIGuardian3DGenerator()
    output = generator.generate()
    print(f"\n✓ AI Guardian 3D model ready: {output}")


if __name__ == "__main__":
    main()
