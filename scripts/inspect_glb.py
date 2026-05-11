"""Extract morph target names + mesh structure from a binary glTF (.glb)
and report whether it has the morphs the React 3D lip-sync avatar needs.

Usage:
    python3 scripts/inspect_glb.py [path/to/avatar.glb]

If no path is given, inspects models/avatar.glb (the file the React 3D
avatar loads in REACT_3D mode).
"""
import json
import re
import struct
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GLB = REPO_ROOT / "models" / "avatar.glb"
PHONEME_MAP_JS = REPO_ROOT / "assets" / "avatar" / "phonemeMap.js"

# Reference set of ARKit blendshapes the renderer probes (Avatar.jsx
# uses these for emotion presets, jaw drive, blink). Not exhaustive.
ARKIT_REFERENCE = {
    "jawOpen", "eyeBlinkLeft", "eyeBlinkRight",
    "mouthSmileLeft", "mouthSmileRight",
    "mouthFrownLeft", "mouthFrownRight",
    "browInnerUp", "browDownLeft", "browDownRight",
    "cheekSquintLeft", "cheekSquintRight",
    "eyeSquintLeft", "eyeSquintRight",
    "mouthPucker",
}


def load_phoneme_visemes() -> set:
    """Parse phonemeMap.js and return the set of viseme names it writes to."""
    if not PHONEME_MAP_JS.exists():
        return set()
    text = PHONEME_MAP_JS.read_text()
    return set(re.findall(r"'(viseme_[A-Za-z0-9]+)'", text))


def inspect(glb_path: Path) -> None:
    with glb_path.open("rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        assert magic == b"glTF", f"Not a glTF binary: magic={magic!r}"
        chunk_len, chunk_type = struct.unpack("<I4s", f.read(8))
        assert chunk_type == b"JSON", f"First chunk should be JSON, got {chunk_type!r}"
        json_bytes = f.read(chunk_len)

    gltf = json.loads(json_bytes)

    print(f"File:          {glb_path}")
    print(f"glTF version:  {version}")
    print(f"File length:   {length:,} bytes")
    print(f"Generator:     {gltf.get('asset', {}).get('generator', '<unknown>')}")
    print(f"Meshes:        {len(gltf.get('meshes', []))}")
    print()

    all_morph_names: set = set()
    for mi, mesh in enumerate(gltf.get("meshes", [])):
        name = mesh.get("name", f"<unnamed mesh {mi}>")
        target_names = (mesh.get("extras") or {}).get("targetNames") or []
        primitive_target_count = max(
            (len(p.get("targets") or []) for p in mesh.get("primitives", [])),
            default=0,
        )
        print(f"--- Mesh #{mi}: {name!r}")
        print(f"    primitives:        {len(mesh.get('primitives', []))}")
        print(f"    morph slots:       {primitive_target_count}")
        print(f"    targetNames count: {len(target_names)}")
        if target_names:
            for n in target_names:
                all_morph_names.add(n)
        print()

    print("=" * 60)
    print(f"Total unique morph target names: {len(all_morph_names)}")
    print("=" * 60)

    expected_visemes = load_phoneme_visemes()
    if expected_visemes:
        present = expected_visemes & all_morph_names
        missing = expected_visemes - all_morph_names
        print(f"\nphonemeMap.js viseme coverage: "
              f"{len(present)}/{len(expected_visemes)}")
        if present:
            print(f"  + present: {sorted(present)}")
        if missing:
            print(f"  - missing: {sorted(missing)}")
            print(f"\n  -> Lip sync will be silent for these phonemes.")
        else:
            print(f"\n  -> All phoneme-map visemes present. Lip sync will work.")

    arkit_present = ARKIT_REFERENCE & all_morph_names
    arkit_missing = ARKIT_REFERENCE - all_morph_names
    print(f"\nARKit blendshape coverage (probe set): "
          f"{len(arkit_present)}/{len(ARKIT_REFERENCE)}")
    if arkit_present:
        print(f"  + present: {sorted(arkit_present)}")
    if arkit_missing:
        print(f"  - missing: {sorted(arkit_missing)}")
    if not arkit_present:
        print(f"\n  -> No ARKit morphs found. Emotions, blink, and jaw drive")
        print(f"     will be no-ops in Avatar.jsx.")

    print()
    if all_morph_names:
        print("All morph names:")
        for n in sorted(all_morph_names):
            print(f"  {n}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GLB
    if not target.exists():
        print(f"ERROR: {target} not found", file=sys.stderr)
        sys.exit(1)
    inspect(target)
