"""Parameterized GLB avatar generator.

Builds a customizable AI avatar head with morph targets for facial expressions
and visemes. Uses trimesh + pygltflib so it runs in the standard Python runtime
(no Blender required), in contrast to gbl_creator.py which depends on bpy.

Output is written to ``models/avatar.glb`` by default — the path the React
avatar bridge in web/react-avatar-bridge.js already loads on startup.
"""

from __future__ import annotations

import io
import logging
import struct
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
try:
    import trimesh
    import trimesh.visual  # ColorVisuals lives in this submodule, not the top-level package
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    if exc.name == "trimesh":
        raise ModuleNotFoundError(
            "Missing dependency: trimesh. Install it with `pip install -r web/requirements-avatar.txt` "
            "or `pip install trimesh` before generating avatars."
        ) from exc
    raise

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
# NOTE: this generator emits a head with only 4 visemes (Viseme_A/E/M/O) and
# 5 emotion morphs (Smile/Frown/Surprise/Wink_Left/Wink_Right). The React 3D
# avatar lip-sync path expects the full Ready Player Me morph set (15 Oculus
# visemes + 52 ARKit blendshapes). Writing here would overwrite the RPM file
# at models/avatar.glb that react-avatar-bridge.js loads, so we deliberately
# emit to a sibling path. The customizer/onboarding flow can still preview
# the generated head from this URL — it just doesn't drive lip sync.
DEFAULT_OUTPUT = _REPO_ROOT / "models" / "avatar_generated.glb"


@dataclass
class AvatarParams:
    """User-tunable parameters for the generated avatar.

    All numeric fields are normalized 0.0-1.0 unless noted otherwise. Defaults
    produce the same baseline head shape as generator_glb.py.
    """

    subdivisions: int = 4          # icosphere detail (3-5 sane range)
    radius: float = 1.0            # head radius in scene units
    smile_strength: float = 0.5    # 0=neutral, 1=full grin
    frown_strength: float = 0.5
    surprise_strength: float = 0.5
    wink_strength: float = 0.5
    viseme_strength: float = 0.5   # scales mouth-shape morphs
    skin_color: Tuple[float, float, float] = (0.85, 0.72, 0.60)  # linear RGB

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> "AvatarParams":
        if not data:
            return cls()
        # JS-facing aliases → dataclass field names
        _aliases = {"head_radius": "radius", "head_color": "skin_color"}
        valid_keys = {f.name for f in fields(cls)}
        kwargs = {}
        for key, value in data.items():
            mapped = _aliases.get(key, key)
            if mapped == "skin_color" and isinstance(value, (list, tuple)):
                kwargs[mapped] = tuple(float(c) for c in value[:3])
            elif mapped in valid_keys:
                kwargs[mapped] = value
        return cls(**kwargs)

    def to_dict(self) -> Dict:
        return asdict(self)


# Morph target builders. Each takes the base vertex array and returns the
# *target* vertex positions; the GLB exporter stores the delta.
def _smile(base: np.ndarray, k: float) -> np.ndarray:
    out = base.copy()
    mask = (out[:, 2] < 0.2) & (np.abs(out[:, 0]) < 0.6)
    out[mask, 2] += 0.10 * k
    return out


def _frown(base: np.ndarray, k: float) -> np.ndarray:
    out = base.copy()
    mask = (out[:, 2] < 0.2) & (np.abs(out[:, 0]) < 0.6)
    out[mask, 2] -= 0.10 * k
    return out


def _surprise(base: np.ndarray, k: float) -> np.ndarray:
    out = base.copy()
    mask = out[:, 2] < -0.2
    out[mask, 2] -= 0.15 * k
    return out


def _wink_left(base: np.ndarray, k: float) -> np.ndarray:
    out = base.copy()
    mask = out[:, 0] < 0
    out[mask, 2] -= 0.20 * k
    return out


def _wink_right(base: np.ndarray, k: float) -> np.ndarray:
    out = base.copy()
    mask = out[:, 0] > 0
    out[mask, 2] -= 0.20 * k
    return out


def _viseme_a(base: np.ndarray, k: float) -> np.ndarray:
    out = base.copy()
    mask = out[:, 2] < 0
    out[mask, 2] -= 0.15 * k
    return out


def _viseme_o(base: np.ndarray, k: float) -> np.ndarray:
    out = base.copy()
    mask = out[:, 2] < 0
    out[mask, 0] *= 1.0 - 0.20 * k
    out[mask, 2] -= 0.10 * k
    return out


def _viseme_e(base: np.ndarray, k: float) -> np.ndarray:
    out = base.copy()
    mask = out[:, 2] < 0
    out[mask, 0] *= 1.0 + 0.10 * k
    return out


def _viseme_m(base: np.ndarray, k: float) -> np.ndarray:
    out = base.copy()
    mask = out[:, 2] < 0
    out[mask, 2] += 0.10 * k
    return out


# Order matters: GLB stores morph targets by index, names live in extras.
_MORPH_BUILDERS: List[Tuple[str, Callable[[np.ndarray, float], np.ndarray], str]] = [
    # Expressions (ARKit compatible)
    ("Smile", _smile, "smile_strength"),
    ("mouthSmileLeft", _smile, "smile_strength"),  # ARKit naming
    ("mouthSmileRight", _smile, "smile_strength"),
    ("Frown", _frown, "frown_strength"),
    ("Surprise", _surprise, "surprise_strength"),
    ("browInnerUp", _surprise, "surprise_strength"),  # ARKit naming
    ("Wink_Left", _wink_left, "wink_strength"),
    ("eyeBlinkLeft", _wink_left, "wink_strength"),  # ARKit naming
    ("Wink_Right", _wink_right, "wink_strength"),
    ("eyeBlinkRight", _wink_right, "wink_strength"),  # ARKit naming
    
    # Oculus Visemes (for lip-sync)
    ("viseme_aa", _viseme_a, "viseme_strength"),  # Oculus naming
    ("Viseme_A", _viseme_a, "viseme_strength"),
    ("viseme_O", _viseme_o, "viseme_strength"),  # Oculus naming
    ("Viseme_O", _viseme_o, "viseme_strength"),
    ("viseme_E", _viseme_e, "viseme_strength"),  # Oculus naming
    ("Viseme_E", _viseme_e, "viseme_strength"),
    ("viseme_PP", _viseme_m, "viseme_strength"),  # Oculus naming (lips closed)
    ("Viseme_M", _viseme_m, "viseme_strength"),
    
    # ARKit jaw (critical for lip-sync)
    ("jawOpen", _viseme_a, "viseme_strength"),  # Reuse viseme_a for jaw
]


def _build_mesh(params: AvatarParams) -> Tuple[trimesh.Trimesh, np.ndarray]:
    """Build the base mesh and return it alongside a per-vertex RGBA array.

    The colors are returned separately because trimesh widens ``mesh.visual``
    to a Union once assigned, which makes the type checker (rightly) refuse
    to access ``vertex_colors`` later — so we keep our own reference.
    """
    subs = max(2, min(6, int(params.subdivisions)))
    mesh = trimesh.creation.icosphere(subdivisions=subs, radius=float(params.radius))
    rgba = np.array(
        [
            int(np.clip(params.skin_color[0], 0.0, 1.0) * 255),
            int(np.clip(params.skin_color[1], 0.0, 1.0) * 255),
            int(np.clip(params.skin_color[2], 0.0, 1.0) * 255),
            255,
        ],
        dtype=np.uint8,
    )
    vertex_colors = np.tile(rgba, (len(mesh.vertices), 1))
    mesh.visual = trimesh.visual.ColorVisuals(mesh, vertex_colors=vertex_colors)
    return mesh, vertex_colors


def _morph_deltas(
    base_vertices: np.ndarray, params: AvatarParams
) -> List[Tuple[str, np.ndarray]]:
    deltas: List[Tuple[str, np.ndarray]] = []
    for name, builder, strength_attr in _MORPH_BUILDERS:
        k = float(getattr(params, strength_attr))
        target = builder(base_vertices, k)
        deltas.append((name, (target - base_vertices).astype(np.float32)))
    return deltas


def _write_glb_with_morphs(
    mesh: trimesh.Trimesh,
    vertex_colors: np.ndarray,
    morphs: List[Tuple[str, np.ndarray]],
    output_path: Path,
) -> None:
    """Write a GLB with POSITION + NORMAL + per-morph POSITION deltas.

    Built by hand because trimesh's GLB exporter does not currently emit
    `mesh.primitives[].targets`. Schema follows glTF 2.0 §3.7.2.3.
    """
    import json

    vertices = mesh.vertices.astype(np.float32)
    indices = mesh.faces.astype(np.uint32).flatten()
    normals = mesh.vertex_normals.astype(np.float32)
    colors = vertex_colors.astype(np.uint8)

    # Pack all binary buffers contiguously, 4-byte aligned.
    bin_chunks: List[bytes] = []
    buffer_views: List[Dict] = []
    accessors: List[Dict] = []
    offset = 0

    def _add_view(data: bytes, target: Optional[int] = None) -> int:
        nonlocal offset
        # 4-byte align
        pad = (-len(data)) % 4
        if pad:
            data = data + b"\x00" * pad
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(data)}
        if target is not None:
            view["target"] = target
        buffer_views.append(view)
        bin_chunks.append(data)
        offset += len(data)
        return len(buffer_views) - 1

    def _vec3_minmax(arr: np.ndarray) -> Tuple[List[float], List[float]]:
        return arr.min(axis=0).tolist(), arr.max(axis=0).tolist()

    # Indices accessor
    idx_view = _add_view(indices.tobytes(), target=34963)
    idx_accessor = len(accessors)
    accessors.append({
        "bufferView": idx_view,
        "componentType": 5125,  # UNSIGNED_INT
        "count": int(indices.size),
        "type": "SCALAR",
        "min": [int(indices.min())],
        "max": [int(indices.max())],
    })

    # Position accessor
    pos_view = _add_view(vertices.tobytes(), target=34962)
    pos_min, pos_max = _vec3_minmax(vertices)
    pos_accessor = len(accessors)
    accessors.append({
        "bufferView": pos_view,
        "componentType": 5126,  # FLOAT
        "count": int(len(vertices)),
        "type": "VEC3",
        "min": pos_min,
        "max": pos_max,
    })

    # Normal accessor
    nrm_view = _add_view(normals.tobytes(), target=34962)
    nrm_accessor = len(accessors)
    accessors.append({
        "bufferView": nrm_view,
        "componentType": 5126,
        "count": int(len(normals)),
        "type": "VEC3",
    })

    # Color accessor (vec4 unsigned byte normalized)
    col_view = _add_view(colors.tobytes(), target=34962)
    col_accessor = len(accessors)
    accessors.append({
        "bufferView": col_view,
        "componentType": 5121,  # UNSIGNED_BYTE
        "count": int(len(colors)),
        "type": "VEC4",
        "normalized": True,
    })

    # One POSITION accessor per morph target
    morph_targets_json: List[Dict] = []
    morph_names: List[str] = []
    for name, delta in morphs:
        mview = _add_view(delta.tobytes(), target=34962)
        mmin, mmax = _vec3_minmax(delta)
        macc = len(accessors)
        accessors.append({
            "bufferView": mview,
            "componentType": 5126,
            "count": int(len(delta)),
            "type": "VEC3",
            "min": mmin,
            "max": mmax,
        })
        morph_targets_json.append({"POSITION": macc})
        morph_names.append(name)

    primitive: Dict = {
        "attributes": {
            "POSITION": pos_accessor,
            "NORMAL": nrm_accessor,
            "COLOR_0": col_accessor,
        },
        "indices": idx_accessor,
        "mode": 4,  # TRIANGLES
    }
    if morph_targets_json:
        primitive["targets"] = morph_targets_json
        primitive["extras"] = {"targetNames": morph_names}

    gltf_json = {
        "asset": {"version": "2.0", "generator": "PortAIOS avatar_generator"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "AI_Avatar_Head"}],
        "meshes": [{
            "name": "AI_Avatar_Head",
            "primitives": [primitive],
            "weights": [0.0] * len(morph_targets_json),
            "extras": {"targetNames": morph_names} if morph_names else {},
        }],
        "buffers": [{"byteLength": offset}],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }

    bin_data = b"".join(bin_chunks)
    json_data = json.dumps(gltf_json, separators=(",", ":")).encode("utf-8")
    json_pad = (-len(json_data)) % 4
    json_data = json_data + b" " * json_pad
    bin_pad = (-len(bin_data)) % 4
    bin_data = bin_data + b"\x00" * bin_pad

    total_len = 12 + 8 + len(json_data) + 8 + len(bin_data)
    out = io.BytesIO()
    out.write(b"glTF")
    out.write(struct.pack("<II", 2, total_len))
    out.write(struct.pack("<II", len(json_data), 0x4E4F534A))  # 'JSON'
    out.write(json_data)
    out.write(struct.pack("<II", len(bin_data), 0x004E4942))   # 'BIN\0'
    out.write(bin_data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(out.getvalue())


def generate_avatar(
    params: Optional[AvatarParams] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """Generate a customized avatar GLB and return its path."""
    params = params or AvatarParams()
    output_path = Path(output_path) if output_path else DEFAULT_OUTPUT

    mesh, vertex_colors = _build_mesh(params)
    deltas = _morph_deltas(mesh.vertices.astype(np.float32), params)
    _write_glb_with_morphs(mesh, vertex_colors, deltas, output_path)
    logger.info(
        "Generated avatar GLB at %s (%d morph targets)", output_path, len(deltas)
    )
    return output_path


def generate_from_dict(
    params_dict: Optional[Dict] = None,
    output_path: Optional[str] = None,
) -> Dict:
    """JSON-friendly entry point used by the Eel bridge / HTTP endpoint."""
    try:
        params = AvatarParams.from_dict(params_dict)
        path = generate_avatar(params, Path(output_path) if output_path else None)
        return {
            "success": True,
            "path": str(path),
            "morph_targets": [name for name, _, _ in _MORPH_BUILDERS],
            "params": params.to_dict(),
        }
    except Exception as exc:  # noqa: BLE001 — surface to UI
        logger.exception("Avatar generation failed")
        return {"success": False, "error": str(exc)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = generate_from_dict({})
    print(result)
