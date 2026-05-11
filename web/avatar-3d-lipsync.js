/**
 * 3D Avatar with Real-time Lip-Sync
 * Syncs mouth movements with phoneme data from Piper TTS
 */

import * as THREE from 'https://esm.sh/three@0.160.0';
import { GLTFLoader } from 'https://esm.sh/three@0.160.0/examples/jsm/loaders/GLTFLoader.js';

class LipSyncAvatar {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      modelUrl: options.modelUrl || null,
      useBinaryFallback: options.useBinaryFallback !== false,
      ...options
    };

    // Scene components
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.avatar = null;
    this.mixer = null;
    
    // Viseme/morph targets
    this.morphTargets = {};
    this.currentViseme = 'REST';
    this.targetViseme = 'REST';
    this.visemeTransition = 0;
    
    // Audio
    this.audioContext = null;
    this.audioSource = null;
    this.startTime = 0;
    
    // Phoneme timeline
    this.currentTimeline = [];
    this.currentIndex = 0;
    
    // Animation
    this.animationId = null;
    this.clock = new THREE.Clock();
    
    // Binary avatar fallback
    this.binaryAvatar = null;
    
    this.init();
  }

  async init() {
    console.log('[LipSync] Initializing 3D avatar with lip-sync...');
    
    // Setup Three.js scene
    this.setupScene();
    
    // Try to load 3D model
    if (this.options.modelUrl) {
      try {
        await this.loadAvatar(this.options.modelUrl);
      } catch (error) {
        console.warn('[LipSync] Failed to load 3D model, using binary fallback:', error);
        this.useBinaryFallback();
      }
    } else if (this.options.useBinaryFallback) {
      this.useBinaryFallback();
    }
    
    // Setup audio context
    this.setupAudio();
    
    // Register for viseme data
    this.registerVisemeListener();
    
    // Start animation loop
    this.animate();
  }

  setupScene() {
    // Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x000000);
    
    // Camera
    const aspect = this.container.clientWidth / this.container.clientHeight;
    this.camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 1000);
    this.camera.position.set(0, 1.6, 2);
    this.camera.lookAt(0, 1.6, 0);
    
    // Renderer
    this.renderer = new THREE.WebGLRenderer({ 
      antialias: true,
      alpha: true 
    });
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.container.appendChild(this.renderer.domElement);
    
    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    this.scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(0, 2, 1);
    this.scene.add(directionalLight);
    
    // Handle resize
    window.addEventListener('resize', () => this.onResize());
  }

  async loadAvatar(url) {
    const loader = new GLTFLoader();
    
    return new Promise((resolve, reject) => {
      loader.load(
        url,
        (gltf) => {
          this.avatar = gltf.scene;
          this.scene.add(this.avatar);
          
          // Setup morph targets for visemes
          this.setupMorphTargets(gltf);
          
          // Setup animations if present
          if (gltf.animations && gltf.animations.length > 0) {
            this.mixer = new THREE.AnimationMixer(this.avatar);
          }
          
          console.log('[LipSync] 3D avatar loaded successfully');
          resolve();
        },
        (progress) => {
          console.log(`[LipSync] Loading: ${(progress.loaded / progress.total * 100).toFixed(0)}%`);
        },
        (error) => {
          console.error('[LipSync] Error loading avatar:', error);
          reject(error);
        }
      );
    });
  }

  setupMorphTargets(gltf) {
    // Find mesh with morph targets for mouth
    gltf.scene.traverse((object) => {
      if (object.isMesh && object.morphTargetDictionary) {
        console.log('[LipSync] Found morph targets:', Object.keys(object.morphTargetDictionary));
        
        // Map visemes to morph target indices
        const dict = object.morphTargetDictionary;
        
        // Standard viseme names (adjust based on your model)
        const visemeNames = {
          'REST': 'viseme_sil',  // silence
          'P': 'viseme_PP',      // bilabial
          'F': 'viseme_FF',      // labiodental
          'TH': 'viseme_TH',     // dental
          'T': 'viseme_DD',      // alveolar
          'S': 'viseme_SS',      // alveolar fricative
          'CH': 'viseme_CH',     // postalveolar
          'K': 'viseme_kk',      // velar
          'AA': 'viseme_aa',     // open vowel
          'E': 'viseme_E',       // mid vowel
          'I': 'viseme_I',       // close front vowel
          'O': 'viseme_O',       // mid back vowel
          'U': 'viseme_U',       // close back vowel
        };
        
        // Map our viseme codes to morph target indices
        for (const [viseme, morphName] of Object.entries(visemeNames)) {
          if (dict.hasOwnProperty(morphName)) {
            this.morphTargets[viseme] = {
              mesh: object,
              index: dict[morphName]
            };
          }
        }
        
        console.log('[LipSync] Mapped visemes:', Object.keys(this.morphTargets));
      }
    });
  }

  useBinaryFallback() {
    console.log('[LipSync] Using binary avatar fallback');
    
    // Import and use existing binary avatar
    import('./binary-avatar.js').then(({ BinaryAvatarRenderer }) => {
      this.binaryAvatar = new BinaryAvatarRenderer(this.container, {
        colorPalette: 'matrix',
        digitCount: 6000,
        enableCRT: true,
        enableChromatic: true,
        enableBloom: true
      });
      
      console.log('[LipSync] Binary avatar fallback active');
    }).catch(error => {
      console.error('[LipSync] Failed to load binary avatar fallback:', error);
    });
  }

  setupAudio() {
    document.addEventListener('click', () => {
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        console.log('[LipSync] Audio context initialized');
      }
    }, { once: true });
  }

  registerVisemeListener() {
    // Register with backend to receive viseme data
    if (typeof eel !== 'undefined') {
      eel.register_viseme_listener()().then(() => {
        console.log('[LipSync] Registered for viseme streaming');
      }).catch(error => {
        console.warn('[LipSync] Could not register for visemes:', error);
      });
    }
    
    // Setup receiver function
    window.receive_viseme_data = (payload) => {
      this.handleVisemeData(payload);
    };
    
    // Expose to Eel
    if (typeof eel !== 'undefined') {
      eel.expose(window.receive_viseme_data, 'receive_viseme_data');
    }
  }

  handleVisemeData(payload) {
    console.log(`[LipSync] Received viseme data: ${payload.phonemes.length} phonemes`);
    
    // Store timeline
    this.currentTimeline = payload.phonemes;
    this.currentIndex = 0;
    
    // Decode and play audio
    this.playAudio(payload.audio);
    
    // Start tracking phonemes
    this.startTime = this.audioContext ? this.audioContext.currentTime : performance.now() / 1000;
  }

  async playAudio(audioBase64) {
    if (!this.audioContext) {
      console.warn('[LipSync] Audio context not initialized');
      return;
    }
    
    try {
      // Decode base64
      const binaryString = window.atob(audioBase64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      // Decode audio data
      const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);
      
      // Stop current audio if playing
      if (this.audioSource) {
        this.audioSource.stop();
      }
      
      // Create and play source
      this.audioSource = this.audioContext.createBufferSource();
      this.audioSource.buffer = audioBuffer;
      this.audioSource.connect(this.audioContext.destination);
      this.audioSource.start(0);
      
      this.startTime = this.audioContext.currentTime;
      
      console.log('[LipSync] Playing audio with lip-sync');
      
    } catch (error) {
      console.error('[LipSync] Failed to play audio:', error);
    }
  }

  updateLipSync() {
    if (!this.currentTimeline || this.currentTimeline.length === 0) {
      return;
    }
    
    // Get current playback time
    const currentTime = this.audioContext 
      ? (this.audioContext.currentTime - this.startTime)
      : ((performance.now() / 1000) - this.startTime);
    
    // Find current phoneme
    while (this.currentIndex < this.currentTimeline.length) {
      const phoneme = this.currentTimeline[this.currentIndex];
      const phonemeEnd = phoneme.t + phoneme.d;
      
      if (currentTime < phonemeEnd) {
        // This is the current phoneme
        const viseme = phoneme.v || this.phonemeToViseme(phoneme.p);
        
        if (viseme !== this.targetViseme) {
          this.targetViseme = viseme;
          this.visemeTransition = 0;
          console.log(`[LipSync] Viseme: ${viseme} (phoneme: ${phoneme.p})`);
        }
        
        break;
      }
      
      this.currentIndex++;
    }
    
    // Transition to target viseme
    if (this.visemeTransition < 1) {
      this.visemeTransition = Math.min(1, this.visemeTransition + 0.2);
    }
    
    // Apply morph targets
    this.applyViseme(this.targetViseme, this.visemeTransition);
    
    // Update binary avatar if used
    if (this.binaryAvatar) {
      // Map viseme to activity
      const volume = this.targetViseme !== 'REST' ? 0.5 : 0;
      this.binaryAvatar.setVolume(volume);
    }
  }

  phonemeToViseme(phoneme) {
    // Fallback mapping if viseme not provided
    const mapping = {
      'p': 'P', 'b': 'P', 'm': 'P',
      'f': 'F', 'v': 'F',
      't': 'T', 'd': 'T', 's': 'S',
      'k': 'K', 'g': 'K',
      'a': 'AA', 'e': 'E', 'i': 'I', 'o': 'O', 'u': 'U'
    };
    
    return mapping[phoneme] || 'REST';
  }

  applyViseme(viseme, weight) {
    if (!this.morphTargets[viseme]) {
      return;
    }
    
    const { mesh, index } = this.morphTargets[viseme];
    
    // Reset all mouth morphs
    for (const vis of Object.keys(this.morphTargets)) {
      const target = this.morphTargets[vis];
      if (target.mesh === mesh) {
        target.mesh.morphTargetInfluences[target.index] = 0;
      }
    }
    
    // Apply target viseme
    mesh.morphTargetInfluences[index] = weight;
  }

  animate() {
    this.animationId = requestAnimationFrame(() => this.animate());
    
    const delta = this.clock.getDelta();
    
    // Update lip-sync
    this.updateLipSync();
    
    // Update animation mixer
    if (this.mixer) {
      this.mixer.update(delta);
    }
    
    // Render
    this.renderer.render(this.scene, this.camera);
  }

  onResize() {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    
    this.renderer.setSize(width, height);
  }

  destroy() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
    }
    
    if (this.audioSource) {
      this.audioSource.stop();
    }
    
    if (this.binaryAvatar) {
      this.binaryAvatar.destroy();
    }
    
    // Clean up Three.js
    this.scene.traverse((object) => {
      if (object.geometry) object.geometry.dispose();
      if (object.material) {
        if (Array.isArray(object.material)) {
          object.material.forEach(mat => mat.dispose());
        } else {
          object.material.dispose();
        }
      }
    });
    
    if (this.renderer) {
      this.renderer.dispose();
    }
  }
}

export { LipSyncAvatar };

// Global API
if (typeof window !== 'undefined') {
  window.AIOS = window.AIOS || {};
  window.AIOS.LipSyncAvatar = LipSyncAvatar;
}
