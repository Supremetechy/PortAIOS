/**
 * AI Guardian 3D Interactive Avatar
 * Combines holographic shader effects with 3D lip-sync, gestures, and expressions
 * 
 * Features:
 * - Holographic wireframe visual style matching AI-Guardian.jpg
 * - Real-time lip-sync with viseme morphing
 * - Hand gesture animations (stop, wave, point, thinking)
 * - Facial expressions (smile, thinking, surprise)
 * - Audio-reactive glow and particles
 */

import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.158.0/build/three.module.js';
import { GLTFLoader } from 'https://cdn.jsdelivr.net/npm/three@0.158.0/examples/jsm/loaders/GLTFLoader.js';

// Holographic shader for the AI Guardian aesthetic
const HOLOGRAPHIC_VERTEX_SHADER = /* glsl */`
    varying vec3 vPosition;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    
    void main() {
        vPosition = position;
        vNormal = normalize(normalMatrix * normal);
        
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        vViewPosition = -mvPosition.xyz;
        
        gl_Position = projectionMatrix * mvPosition;
    }
`;

const HOLOGRAPHIC_FRAGMENT_SHADER = /* glsl */`
    uniform vec3 uColorPrimary;
    uniform vec3 uColorSecondary;
    uniform float uTime;
    uniform float uActivity;
    uniform float uVolume;
    uniform float uGlowIntensity;
    
    varying vec3 vPosition;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    
    void main() {
        // Fresnel effect for holographic rim lighting
        vec3 viewDir = normalize(vViewPosition);
        float fresnel = pow(1.0 - abs(dot(viewDir, vNormal)), 2.5);
        
        // Scanlines
        float scanline = sin(vPosition.y * 40.0 + uTime * 2.0) * 0.5 + 0.5;
        scanline = pow(scanline, 3.0) * 0.3;
        
        // Grid pattern
        float gridX = step(0.98, fract(vPosition.x * 10.0));
        float gridY = step(0.98, fract(vPosition.y * 10.0));
        float gridZ = step(0.98, fract(vPosition.z * 10.0));
        float grid = max(max(gridX, gridY), gridZ) * 0.4;
        
        // Pulse based on activity and volume
        float pulse = sin(uTime * 3.0) * 0.5 + 0.5;
        pulse = mix(pulse, uVolume, 0.7);
        pulse *= uActivity;
        
        // Color mixing
        vec3 color = mix(uColorPrimary, uColorSecondary, fresnel);
        color += vec3(scanline);
        color += vec3(grid);
        color *= (1.0 + pulse * 0.5);
        
        // Glow intensity
        color *= uGlowIntensity;
        
        // Edge enhancement
        color += fresnel * uColorPrimary * 0.8;
        
        // Transparency based on fresnel for holographic effect
        float alpha = fresnel * 0.7 + 0.3 + grid * 0.3;
        alpha = clamp(alpha, 0.4, 1.0);
        
        gl_FragColor = vec4(color, alpha);
    }
`;

export class AIGuardian3D {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            modelUrl: options.modelUrl || '/models/ai_guardian.glb',
            colorPrimary: options.colorPrimary || new THREE.Color(0x00ffff),
            colorSecondary: options.colorSecondary || new THREE.Color(0x0088ff),
            autoRotate: options.autoRotate !== false,
            enableParticles: options.enableParticles !== false,
            ...options
        };
        
        // State
        this.state = {
            activity: 'idle',      // idle, thinking, speaking, listening
            emotion: 'neutral',     // neutral, happy, thinking, surprised
            gesture: 'none',        // none, stop, wave, point, thinking
            volume: 0.0,
            speaking: false
        };
        
        // Animation
        this.clock = new THREE.Clock();
        this.morphTargets = {};
        this.currentViseme = null;
        this.visemeWeight = 0;
        this.targetVisemeWeight = 0;
        
        // Audio
        this.audioContext = null;
        this.analyser = null;
        this.frequencyData = null;
        
        // Three.js objects
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.avatar = null;
        this.material = null;
        this.particles = null;
        this.platform = null;
        
        this.animationId = null;
        this.initialized = false;
    }
    
    async init() {
        console.log('[AIGuardian3D] Initializing...');
        
        this._setupScene();
        this._setupLighting();
        this._setupPlatform();
        
        if (this.options.enableParticles) {
            this._setupParticles();
        }
        
        try {
            await this._loadAvatar();
            this.initialized = true;
            this._startAnimation();
            console.log('[AIGuardian3D] ✓ Initialized successfully');
        } catch (error) {
            console.error('[AIGuardian3D] Failed to load avatar:', error);
            this._showFallback();
        }
        
        // Setup window resize handler
        window.addEventListener('resize', () => this._onResize());
        this._onResize();
        
        return this;
    }
    
    _setupScene() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x000000);
        this.scene.fog = new THREE.Fog(0x000a0f, 3, 10);
        
        // Camera
        const aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 100);
        this.camera.position.set(0, 1.5, 3.5);
        this.camera.lookAt(0, 1.0, 0);
        
        // Renderer
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true, 
            alpha: true,
            powerPreference: 'high-performance'
        });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.outputEncoding = THREE.sRGBEncoding;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.2;
        
        this.container.appendChild(this.renderer.domElement);
    }
    
    _setupLighting() {
        // Ambient light
        const ambient = new THREE.AmbientLight(0x0044aa, 0.3);
        this.scene.add(ambient);
        
        // Key light (cyan, from front-right)
        const keyLight = new THREE.DirectionalLight(0x00ffff, 0.8);
        keyLight.position.set(2, 3, 3);
        this.scene.add(keyLight);
        
        // Fill light (blue, from left)
        const fillLight = new THREE.DirectionalLight(0x0088ff, 0.5);
        fillLight.position.set(-2, 1, 2);
        this.scene.add(fillLight);
        
        // Rim light (bright cyan, from behind)
        const rimLight = new THREE.DirectionalLight(0x00ffff, 1.0);
        rimLight.position.set(0, 2, -3);
        this.scene.add(rimLight);
    }
    
    _setupPlatform() {
        // Circular platform with glowing rings
        const platformGeometry = new THREE.RingGeometry(0.4, 1.2, 64);
        const platformMaterial = new THREE.ShaderMaterial({
            uniforms: {
                uTime: { value: 0 },
                uColor: { value: new THREE.Color(0x00ffff) }
            },
            vertexShader: /* glsl */`
                varying vec2 vUv;
                void main() {
                    vUv = uv;
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: /* glsl */`
                uniform float uTime;
                uniform vec3 uColor;
                varying vec2 vUv;
                
                void main() {
                    float dist = length(vUv - 0.5) * 2.0;
                    float ring = sin(dist * 20.0 - uTime * 2.0) * 0.5 + 0.5;
                    ring = pow(ring, 3.0);
                    
                    float alpha = ring * (1.0 - dist * 0.5);
                    gl_FragColor = vec4(uColor, alpha * 0.6);
                }
            `,
            transparent: true,
            side: THREE.DoubleSide
        });
        
        this.platform = new THREE.Mesh(platformGeometry, platformMaterial);
        this.platform.rotation.x = -Math.PI / 2;
        this.platform.position.y = 0.01;
        this.scene.add(this.platform);
    }
    
    _setupParticles() {
        const particleCount = 500;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const velocities = new Float32Array(particleCount * 3);
        
        for (let i = 0; i < particleCount; i++) {
            const i3 = i * 3;
            const theta = Math.random() * Math.PI * 2;
            const radius = 1.5 + Math.random() * 2.0;
            const y = Math.random() * 4.0;
            
            positions[i3] = Math.cos(theta) * radius;
            positions[i3 + 1] = y;
            positions[i3 + 2] = Math.sin(theta) * radius;
            
            velocities[i3] = (Math.random() - 0.5) * 0.02;
            velocities[i3 + 1] = 0.01 + Math.random() * 0.02;
            velocities[i3 + 2] = (Math.random() - 0.5) * 0.02;
        }
        
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('velocity', new THREE.BufferAttribute(velocities, 3));
        
        const material = new THREE.PointsMaterial({
            color: 0x00ffff,
            size: 0.05,
            transparent: true,
            opacity: 0.6,
            blending: THREE.AdditiveBlending
        });
        
        this.particles = new THREE.Points(geometry, material);
        this.scene.add(this.particles);
    }
    
    async _loadAvatar() {
        const loader = new GLTFLoader();
        
        return new Promise((resolve, reject) => {
            loader.load(
                this.options.modelUrl,
                (gltf) => {
                    this.avatar = gltf.scene;
                    
                    // Apply holographic material to all meshes
                    this.avatar.traverse((child) => {
                        if (child.isMesh) {
                            this._setupAvatarMesh(child);
                        }
                    });
                    
                    this.scene.add(this.avatar);
                    console.log('[AIGuardian3D] Avatar loaded:', this.options.modelUrl);
                    resolve(gltf);
                },
                (progress) => {
                    const percent = (progress.loaded / progress.total * 100).toFixed(0);
                    console.log(`[AIGuardian3D] Loading... ${percent}%`);
                },
                (error) => {
                    reject(error);
                }
            );
        });
    }
    
    _setupAvatarMesh(mesh) {
        // Create holographic material
        this.material = new THREE.ShaderMaterial({
            uniforms: {
                uColorPrimary: { value: this.options.colorPrimary },
                uColorSecondary: { value: this.options.colorSecondary },
                uTime: { value: 0 },
                uActivity: { value: 0.3 },
                uVolume: { value: 0 },
                uGlowIntensity: { value: 1.0 }
            },
            vertexShader: HOLOGRAPHIC_VERTEX_SHADER,
            fragmentShader: HOLOGRAPHIC_FRAGMENT_SHADER,
            transparent: true,
            side: THREE.DoubleSide,
            blending: THREE.AdditiveBlending
        });
        
        mesh.material = this.material;
        
        // Store morph target references
        if (mesh.morphTargetDictionary && mesh.morphTargetInfluences) {
            this.morphTargets = mesh.morphTargetDictionary;
            this.morphInfluences = mesh.morphTargetInfluences;
            console.log('[AIGuardian3D] Morph targets available:', Object.keys(this.morphTargets));
        }
    }
    
    _showFallback() {
        // Create a simple holographic cube as fallback
        const geometry = new THREE.BoxGeometry(0.5, 0.5, 0.5);
        const material = new THREE.MeshBasicMaterial({ 
            color: 0x00ffff, 
            wireframe: true 
        });
        this.avatar = new THREE.Mesh(geometry, material);
        this.avatar.position.y = 1.5;
        this.scene.add(this.avatar);
        
        this.initialized = true;
        this._startAnimation();
    }
    
    _startAnimation() {
        const animate = () => {
            this.animationId = requestAnimationFrame(animate);
            
            const deltaTime = this.clock.getDelta();
            const elapsedTime = this.clock.getElapsedTime();
            
            this._update(deltaTime, elapsedTime);
            this.renderer.render(this.scene, this.camera);
        };
        
        animate();
    }
    
    _update(deltaTime, elapsedTime) {
        // Update shader uniforms
        if (this.material) {
            this.material.uniforms.uTime.value = elapsedTime;
            this.material.uniforms.uActivity.value = this._getActivityLevel();
            this.material.uniforms.uVolume.value = this.state.volume;
        }
        
        // Update platform
        if (this.platform) {
            this.platform.material.uniforms.uTime.value = elapsedTime;
            this.platform.rotation.z = elapsedTime * 0.1;
        }
        
        // Update particles
        if (this.particles) {
            this._updateParticles(deltaTime);
        }
        
        // Auto-rotate avatar
        if (this.avatar && this.options.autoRotate && this.state.activity === 'idle') {
            this.avatar.rotation.y = Math.sin(elapsedTime * 0.3) * 0.2;
        }
        
        // Update morph targets
        this._updateMorphTargets(deltaTime);
        
        // Update gesture poses
        this._updateGesture(deltaTime);
    }
    
    _updateParticles(deltaTime) {
        const positions = this.particles.geometry.attributes.position.array;
        const velocities = this.particles.geometry.attributes.velocity.array;
        
        for (let i = 0; i < positions.length; i += 3) {
            positions[i] += velocities[i];
            positions[i + 1] += velocities[i + 1];
            positions[i + 2] += velocities[i + 2];
            
            // Reset particles that go too high
            if (positions[i + 1] > 4.0) {
                positions[i + 1] = 0;
            }
        }
        
        this.particles.geometry.attributes.position.needsUpdate = true;
    }
    
    _updateMorphTargets(deltaTime) {
        if (!this.morphInfluences) return;
        
        // Smooth viseme transitions
        const lerpSpeed = 10.0;
        this.visemeWeight += (this.targetVisemeWeight - this.visemeWeight) * lerpSpeed * deltaTime;
        
        // Apply current viseme
        if (this.currentViseme && this.morphTargets[this.currentViseme] !== undefined) {
            const index = this.morphTargets[this.currentViseme];
            this.morphInfluences[index] = this.visemeWeight;
        }
        
        // Apply expression morphs
        const expressionMorph = `expr_${this.state.emotion}`;
        if (this.morphTargets[expressionMorph] !== undefined) {
            const index = this.morphTargets[expressionMorph];
            this.morphInfluences[index] = 0.7; // Blend expression at 70%
        }
    }
    
    _updateGesture(deltaTime) {
        if (!this.morphInfluences || this.state.gesture === 'none') return;
        
        const gestureMorph = `gesture_${this.state.gesture}`;
        if (this.morphTargets[gestureMorph] !== undefined) {
            const index = this.morphTargets[gestureMorph];
            // Smooth transition to gesture pose
            const target = 1.0;
            const current = this.morphInfluences[index] || 0;
            this.morphInfluences[index] = current + (target - current) * 3.0 * deltaTime;
        }
    }
    
    _getActivityLevel() {
        const levels = {
            idle: 0.3,
            listening: 0.5,
            thinking: 0.7,
            speaking: 1.0
        };
        return levels[this.state.activity] || 0.3;
    }
    
    _onResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }
    
    // Public API
    
    setActivity(activity) {
        this.state.activity = activity;
        console.log('[AIGuardian3D] Activity:', activity);
        return this;
    }
    
    setEmotion(emotion) {
        // Reset previous expression
        if (this.morphInfluences && this.state.emotion) {
            const prevMorph = `expr_${this.state.emotion}`;
            if (this.morphTargets[prevMorph] !== undefined) {
                this.morphInfluences[this.morphTargets[prevMorph]] = 0;
            }
        }
        
        this.state.emotion = emotion;
        console.log('[AIGuardian3D] Emotion:', emotion);
        return this;
    }
    
    setGesture(gesture) {
        // Reset previous gesture
        if (this.morphInfluences && this.state.gesture !== 'none') {
            const prevGesture = `gesture_${this.state.gesture}`;
            if (this.morphTargets[prevGesture] !== undefined) {
                this.morphInfluences[this.morphTargets[prevGesture]] = 0;
            }
        }
        
        this.state.gesture = gesture;
        console.log('[AIGuardian3D] Gesture:', gesture);
        return this;
    }
    
    setViseme(viseme, weight = 1.0) {
        // Reset previous viseme
        if (this.currentViseme && this.morphInfluences) {
            const prevIndex = this.morphTargets[this.currentViseme];
            if (prevIndex !== undefined) {
                this.morphInfluences[prevIndex] = 0;
            }
        }
        
        this.currentViseme = viseme;
        this.targetVisemeWeight = weight;
        return this;
    }
    
    setVolume(volume) {
        this.state.volume = Math.max(0, Math.min(1, volume));
        return this;
    }
    
    async speak(text, options = {}) {
        this.state.speaking = true;
        this.setActivity('speaking');
        
        if (options.emotion) {
            this.setEmotion(options.emotion);
        }
        
        if (options.gesture) {
            this.setGesture(options.gesture);
        }
        
        // This will be called by the viseme integration system
        console.log('[AIGuardian3D] Speaking:', text);
        
        return this;
    }
    
    stopSpeaking() {
        this.state.speaking = false;
        this.setActivity('idle');
        this.setViseme(null, 0);
        this.setGesture('none');
        return this;
    }
    
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        if (this.renderer) {
            this.renderer.dispose();
            this.container.removeChild(this.renderer.domElement);
        }
        
        // Cleanup Three.js resources
        this.scene?.traverse((object) => {
            if (object.geometry) object.geometry.dispose();
            if (object.material) {
                if (Array.isArray(object.material)) {
                    object.material.forEach(m => m.dispose());
                } else {
                    object.material.dispose();
                }
            }
        });
        
        console.log('[AIGuardian3D] Destroyed');
    }
}

export default AIGuardian3D;
