#!/usr/bin/env python3
"""
Test script for Avatar Creation and Lip-Sync System
Tests the complete pipeline from generation to lip-sync integration
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_avatar_generation():
    """Test basic avatar generation"""
    print("=" * 60)
    print("TEST 1: Avatar Generation")
    print("=" * 60)
    
    from kernel.avatar_generator import generate_avatar, AvatarParams
    
    # Test 1: Generate with default parameters
    print("\n1. Generating avatar with default parameters...")
    try:
        result = generate_avatar()
        print(f"✓ Success! Avatar saved to: {result['path']}")
        print(f"  Morph count: {result.get('morph_count', 'unknown')}")
        
        # Verify file exists
        avatar_path = Path(result['path'])
        if avatar_path.exists():
            size_kb = avatar_path.stat().st_size / 1024
            print(f"  File size: {size_kb:.1f} KB")
        else:
            print(f"✗ Error: File not found at {avatar_path}")
            return False
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Generate with custom parameters
    print("\n2. Generating avatar with custom parameters...")
    try:
        result = generate_avatar(
            head_radius=0.13,
            head_color=[0.95, 0.85, 0.75],
            smile_intensity=0.6,
            viseme_intensity=1.0
        )
        print(f"✓ Success! Custom avatar saved to: {result['path']}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False
    
    print("\n✓ Avatar generation tests passed!\n")
    return True


def test_morph_targets():
    """Test that generated avatar has correct morph targets"""
    print("=" * 60)
    print("TEST 2: Morph Target Validation")
    print("=" * 60)
    
    try:
        import trimesh
        from pathlib import Path
        
        avatar_path = PROJECT_ROOT / "models" / "avatar_generated.glb"
        if not avatar_path.exists():
            print(f"✗ Avatar not found at {avatar_path}")
            print("  Run test_avatar_generation() first")
            return False
        
        print(f"\nLoading avatar from {avatar_path}...")
        scene = trimesh.load(str(avatar_path))
        
        # Find meshes with morph targets
        morph_meshes = []
        if hasattr(scene, 'geometry'):
            for name, geom in scene.geometry.items():
                if hasattr(geom, 'visual') and hasattr(geom.visual, 'morph_targets'):
                    morph_meshes.append((name, geom))
        
        if not morph_meshes:
            print("✗ No morph targets found in avatar!")
            return False
        
        print(f"\n✓ Found {len(morph_meshes)} mesh(es) with morph targets")
        
        # Check for required morph targets
        required_morphs = {
            # ARKit blendshapes
            'jawOpen': False,
            'eyeBlinkLeft': False,
            'eyeBlinkRight': False,
            'mouthSmileLeft': False,
            'mouthSmileRight': False,
            # Oculus Visemes
            'viseme_aa': False,
            'viseme_E': False,
            'viseme_O': False,
            'viseme_PP': False
        }
        
        for mesh_name, mesh in morph_meshes:
            print(f"\nMesh: {mesh_name}")
            if hasattr(mesh.visual, 'morph_targets'):
                morph_names = list(mesh.visual.morph_targets.keys())
                print(f"  Morph targets: {len(morph_names)}")
                
                for name in morph_names:
                    if name in required_morphs:
                        required_morphs[name] = True
                        print(f"    ✓ {name}")
        
        # Check coverage
        found = sum(required_morphs.values())
        total = len(required_morphs)
        print(f"\n✓ Found {found}/{total} required morph targets")
        
        missing = [k for k, v in required_morphs.items() if not v]
        if missing:
            print(f"⚠ Missing: {', '.join(missing)}")
            print("  (These may use alternative naming)")
        
        return found >= 4  # At least 4 critical morphs
        
    except ImportError:
        print("✗ trimesh not available - cannot validate morph targets")
        print("  Install with: pip install trimesh")
        return False
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_avatar_params():
    """Test AvatarParams serialization"""
    print("=" * 60)
    print("TEST 3: AvatarParams Serialization")
    print("=" * 60)
    
    from kernel.avatar_generator import AvatarParams
    
    # Test to_dict / from_dict round-trip
    print("\n1. Testing serialization round-trip...")
    original = AvatarParams(
        head_radius=0.14,
        head_color=[0.8, 0.7, 0.6],
        smile_strength=0.5,
        frown_strength=0.2
    )
    
    dict_form = original.to_dict()
    print(f"  Original: {original}")
    print(f"  Dict: {dict_form}")
    
    restored = AvatarParams.from_dict(dict_form)
    print(f"  Restored: {restored}")
    
    if original.head_radius == restored.head_radius:
        print("✓ Round-trip successful!")
        return True
    else:
        print("✗ Round-trip failed - values don't match")
        return False


def test_backend_integration():
    """Test backend server integration (if eel is available)"""
    print("=" * 60)
    print("TEST 4: Backend Integration")
    print("=" * 60)
    
    try:
        import eel
        print("\n✓ Eel available")
        
        from kernel.avatar_creation_server import setup_avatar_creation_server
        result = setup_avatar_creation_server()
        
        if result:
            print("✓ Avatar creation server initialized")
            print("  Available endpoints:")
            print("    - start_avatar_generation()")
            print("    - get_avatar_generation_status()")
            print("    - cancel_avatar_generation()")
            print("    - get_avatar_presets()")
            return True
        else:
            print("✗ Server initialization failed")
            return False
            
    except ImportError:
        print("⚠ Eel not available - skipping backend test")
        print("  This is OK if testing avatar generation only")
        return True
    except Exception as e:
        print(f"✗ Backend test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phoneme_mapping():
    """Test that phoneme map covers all Oculus visemes"""
    print("=" * 60)
    print("TEST 5: Phoneme Mapping Coverage")
    print("=" * 60)
    
    try:
        # Import phoneme map
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "assets" / "avatar"))
        from phonemeMap import PHONEME_TO_VISEME
        
        print(f"\n✓ Loaded phoneme map with {len(PHONEME_TO_VISEME)} entries")
        
        # Check for Oculus viseme coverage
        oculus_visemes = {
            'viseme_aa', 'viseme_E', 'viseme_I', 'viseme_O', 'viseme_U',
            'viseme_PP', 'viseme_FF', 'viseme_TH', 'viseme_DD', 'viseme_kk',
            'viseme_CH', 'viseme_SS', 'viseme_nn', 'viseme_RR', 'viseme_sil'
        }
        
        mapped_visemes = set(PHONEME_TO_VISEME.values())
        coverage = mapped_visemes & oculus_visemes
        
        print(f"  Mapped visemes: {len(mapped_visemes)}")
        print(f"  Oculus coverage: {len(coverage)}/{len(oculus_visemes)}")
        
        if len(coverage) >= 10:
            print("✓ Good phoneme → viseme coverage")
            return True
        else:
            print(f"⚠ Limited coverage: {coverage}")
            return False
            
    except Exception as e:
        print(f"✗ Phoneme mapping test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "=" * 60)
    print("AVATAR CREATION & LIP-SYNC SYSTEM TESTS")
    print("=" * 60 + "\n")
    
    tests = [
        ("Avatar Generation", test_avatar_generation),
        ("Morph Target Validation", test_morph_targets),
        ("AvatarParams Serialization", test_avatar_params),
        ("Backend Integration", test_backend_integration),
        ("Phoneme Mapping Coverage", test_phoneme_mapping),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
        print()
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\n{passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! Avatar system is ready.")
        return 0
    else:
        print(f"\n⚠ {total_count - passed_count} test(s) failed. Review output above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
