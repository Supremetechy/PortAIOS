/**
 * 3D Avatar Preview System
 * Real-time Three.js preview for avatar customization
 */

import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.157.0/build/three.module.js';
import { GLTFLoader } from 'https://cdn.jsdelivr.net/npm/three@0.157.0/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.157.0/examples/jsm/controls/OrbitControls.js';

export class AvatarPreview3D {
    constructor(containerElement) {
        this.container = containerElement;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.avatar = null;
        this.mixer = null;
        this.clock = new THREE.Clock();
        this.animationId = null;
        this.morphMeshes = [];
        this.currentAnimation = null;
        
        this.init();
    }
    
    init() {
        console.log('[AvatarPreview3D] Initializing...');
        
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0e27);
        
        // Camera
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
        this.camera.position.set(0, 0.15, 0.5);
        this.camera.lookAt(0, 0.1, 0);
        
        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.2;
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.container.appendChild(this.renderer.domElement);
        
        // Controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.minDistance = 0.3;
        this.controls.maxDistance = 2;
        this.controls.target.set(0, 0.1, 0);
        this.controls.enablePan = false;
        
        // Lighting
        this.setupLighting();
        
        // Handle resize
        window.addEventListener('resize', () => this.handleResize());
        
        // Start animation loop
        this.animate();
        
        console.log('[AvatarPreview3D] Ready');
    }
    
    setupLighting() {
        // Ambient light
        const ambient = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambient);
        
        // Key light (cyan-ish)
        const keyLight = new THREE.DirectionalLight(0x00ffff, 1.0);
        keyLight.position.set(2, 2, 2);
        this.scene.add(keyLight);
        
        // Fill light (magenta-ish)
        const fillLight = new THREE.DirectionalLight(0xff00ff, 0.5);
        fillLight.position.set(-2, 1, -1);
        this.scene.add(fillLight);
        
        // Rim light
        const rimLight = new THREE.DirectionalLight(0xffffff, 0.3);
        rimLight.position.set(0, 2, -2);
        this.scene.add(rimLight);
        
        // Hemisphere light for natural feel
        const hemiLight = new THREE.HemisphereLight(0x00ffff, 0x0a0e27, 0.3);
        this.scene.add(hemiLight);
    }
    
    async loadAvatar(modelPath) {
        console.log(`[AvatarPreview3D] Loading avatar: ${modelPath}`);
        
        // Remove existing avatar
        if (this.avatar) {
            this.scene.remove(this.avatar);
            this.avatar = null;
            this.morphMeshes = [];
        }
        
        const loader = new GLTFLoader();
        
        return new Promise((resolve, reject) => {
            loader.load(
                modelPath,
                (gltf) => {
                    this.avatar = gltf.scene;
                    this.scene.add(this.avatar);
                    
                    // Find meshes with morph targets
                    this.avatar.traverse((child) => {
                        if (child.isMesh && child.morphTargetInfluences) {
                            this.morphMeshes.push(child);
                            console.log(`[AvatarPreview3D] Found morph mesh: ${child.name}`);
                            console.log(`  Morph targets: ${Object.keys(child.morphTargetDictionary || {}).length}`);
                        }
                    });
                    
                    // Setup animation mixer if animations exist
                    if (gltf.animations && gltf.animations.length > 0) {
                        this.mixer = new THREE.AnimationMixer(this.avatar);
                        console.log(`[AvatarPreview3D] Found ${gltf.animations.length} animations`);
                    }
                    
                    // Center and scale avatar
                    const box = new THREE.Box3().setFromObject(this.avatar);
                    const center = box.getCenter(new THREE.Vector3());
                    const size = box.getSize(new THREE.Vector3());
                    
                    this.avatar.position.x = -center.x;
                    this.avatar.position.y = -box.min.y;
                    
                    const maxDim = Math.max(size.x, size.y, size.z);
                    const scale = 0.4 / maxDim;
                    this.avatar.scale.multiplyScalar(scale);
                    
                    console.log('[AvatarPreview3D] Avatar loaded successfully');
                    resolve(this.avatar);
                },
                (progress) => {
                    const percent = (progress.loaded / progress.total * 100).toFixed(0);
                    console.log(`[AvatarPreview3D] Loading: ${percent}%`);
                },
                (error) => {
                    console.error('[AvatarPreview3D] Load failed:', error);
                    reject(error);
                }
            );
        });
    }
    
    setMorphTarget(targetName, value) {
        if (!this.morphMeshes.length) {
            console.warn('[AvatarPreview3D] No morph meshes loaded');
            return false;
        }
        
        let applied = false;
        
        this.morphMeshes.forEach(mesh => {
            const dict = mesh.morphTargetDictionary;
            if (dict && dict[targetName] !== undefined) {
                const index = dict[targetName];
                mesh.morphTargetInfluences[index] = value;
                applied = true;
            }
        });
        
        return applied;
    }
    
    animateMorphTarget(targetName, duration = 1000, fromValue = 0, toValue = 1) {
        const startTime = Date.now();
        
        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Ease in-out
            const eased = progress < 0.5
                ? 2 * progress * progress
                : 1 - Math.pow(-2 * progress + 2, 2) / 2;
            
            const value = fromValue + (toValue - fromValue) * eased;
            this.setMorphTarget(targetName, value);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        animate();
    }
    
    playExpressionSequence(sequence) {
        console.log('[AvatarPreview3D] Playing expression sequence:', sequence.name);
        
        let delay = 0;
        sequence.keyframes.forEach(keyframe => {
            setTimeout(() => {
                Object.entries(keyframe.morphs).forEach(([target, value]) => {
                    this.animateMorphTarget(target, keyframe.duration || 500, undefined, value);
                });
            }, delay);
            delay += (keyframe.duration || 500) + (keyframe.hold || 0);
        });
        
        // Reset after sequence
        setTimeout(() => {
            this.resetAllMorphs();
        }, delay);
    }
    
    resetAllMorphs() {
        this.morphMeshes.forEach(mesh => {
            if (mesh.morphTargetInfluences) {
                mesh.morphTargetInfluences.fill(0);
            }
        });
    }
    
    updateFromParams(params) {
        console.log('[AvatarPreview3D] Updating preview from params:', params);
        
        // Reset first
        this.resetAllMorphs();
        
        // Apply expression morphs
        if (params.smile_strength > 0) {
            this.setMorphTarget('Smile', params.smile_strength);
            this.setMorphTarget('mouthSmileLeft', params.smile_strength);
            this.setMorphTarget('mouthSmileRight', params.smile_strength);
        }
        
        if (params.frown_strength > 0) {
            this.setMorphTarget('Frown', params.frown_strength);
        }
        
        if (params.surprise_strength > 0) {
            this.setMorphTarget('Surprise', params.surprise_strength);
            this.setMorphTarget('browInnerUp', params.surprise_strength);
        }
        
        if (params.wink_strength > 0) {
            this.setMorphTarget('Wink_Left', params.wink_strength);
            this.setMorphTarget('eyeBlinkLeft', params.wink_strength);
        }
        
        // Note: head_color would require regenerating the avatar
        // We can show a preview sphere with the color instead
        this.updateColorPreview(params.head_color);
    }
    
    updateColorPreview(color) {
        // Update material color if possible
        this.morphMeshes.forEach(mesh => {
            if (mesh.material) {
                if (Array.isArray(color)) {
                    mesh.material.color.setRGB(color[0], color[1], color[2]);
                } else {
                    mesh.material.color.set(color);
                }
            }
        });
    }
    
    handleResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        
        this.renderer.setSize(width, height);
    }
    
    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());
        
        const delta = this.clock.getDelta();
        
        // Update controls
        this.controls.update();
        
        // Update animations
        if (this.mixer) {
            this.mixer.update(delta);
        }
        
        // Render
        this.renderer.render(this.scene, this.camera);
    }
    
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        if (this.renderer) {
            this.renderer.dispose();
            this.container.removeChild(this.renderer.domElement);
        }
        
        window.removeEventListener('resize', () => this.handleResize());
        
        console.log('[AvatarPreview3D] Destroyed');
    }
}
