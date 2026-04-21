/**
 * Johnny Mnemonic Binary Avatar System — Enhanced
 * Lo-Tek cyberspace aesthetic with procedural binary geometry
 *
 * Features:
 * - SDF head/neck/shoulders silhouette with jaw articulation
 * - Falling "data rain" background particle layer
 * - Holographic horizontal scan sweep
 * - Chromatic aberration + CRT scanline post-processing
 * - Audio-reactive mouth zone displacement
 * - Depth-coded brightness (foreground bright, background dim)
 * - Glitch pass tied to AI state transitions
 */

// esm.sh resolves bare specifiers server-side — no import map needed,
// immune to browser extensions (MetaMask SES) that block bare specifiers.
import * as THREE from 'https://esm.sh/three@0.160.0';
import { EffectComposer } from 'https://esm.sh/three@0.160.0/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'https://esm.sh/three@0.160.0/examples/jsm/postprocessing/RenderPass.js';
import { ShaderPass } from 'https://esm.sh/three@0.160.0/examples/jsm/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'https://esm.sh/three@0.160.0/examples/jsm/postprocessing/UnrealBloomPass.js';

class BinaryAvatarRenderer {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      digitCount: options.digitCount || 8000,
      rainCount: options.rainCount || 1200,
      colorPalette: options.colorPalette || 'matrix',
      avatarType: options.avatarType || 'head',
      enableCRT: options.enableCRT !== false,
      enableChromatic: options.enableChromatic !== false,
      enableBloom: options.enableBloom !== false,
      //enableDataRain: options.enableDataRain !== false,
      enableHoloScan: options.enableHoloScan !== false,
      ...options
    };

    this.state = {
      emotion: 'neutral',
      activity: 'idle',
      volume: 0.0,
      cpuLoad: 0.0,
      frequency: new Float32Array(128),
      jawOpen: 0.0
    };

    this.time = 0;
    this.animationId = null;

    this.init();
  }

  init() {
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x000000, 0.06);

    const aspect = this.container.clientWidth / this.container.clientHeight;
    this.camera = new THREE.PerspectiveCamera(55, aspect, 0.1, 120);
    this.camera.position.set(0, 0.15, 4.8);
    this.camera.lookAt(0, 0.15, 0);

    this.renderer = new THREE.WebGLRenderer({
      antialias: false,
      alpha: true,
      powerPreference: 'high-performance'
    });
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setClearColor(0x000000, 0);
    this.container.appendChild(this.renderer.domElement);

    this.createBinaryDigitSystem();

    //if (this.options.enableDataRain) {
    //  this.createDataRain();
    //}

    this.setupPostProcessing();
    this.addAmbientEffects();

    this._onResize = () => this.onResize();
    window.addEventListener('resize', this._onResize);

    this.animate();
  }

  // ── Digit texture atlas ──────────────────────────────────────────────
  createDigitTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 48px "Courier New", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // 4 glyphs: 0  1  {  }
    ctx.fillText('0', 32, 32);
    ctx.fillText('1', 96, 32);
    ctx.fillText('{', 160, 32);
    ctx.fillText('}', 224, 32);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    return texture;
  }

  // ── SDF: head + neck + shoulders ─────────────────────────────────────
  headSDF(x, y, z) {
    // Cranium — slightly tall ellipsoid
    const hx = x, hy = y - 0.55, hz = z;
    const cranium = Math.sqrt(
      (hx * hx) / (0.72 * 0.72) +
      (hy * hy) / (0.92 * 0.92) +
      (hz * hz) / (0.70 * 0.70)
    ) - 1.0;

    // Jaw — smaller sphere, offset downward
    const jx = x, jy = y - 0.08, jz = z;
    const jaw = Math.sqrt(
      (jx * jx) / (0.52 * 0.52) +
      (jy * jy) / (0.38 * 0.38) +
      (jz * jz) / (0.48 * 0.48)
    ) - 1.0;

    // Neck — vertical capsule
    const nx = x, ny = y + 0.30, nz = z;
    const neck = Math.sqrt(
      (nx * nx) / (0.22 * 0.22) +
      (nz * nz) / (0.20 * 0.20)
    ) - 1.0;
    const neckClamp = Math.max(neck, Math.abs(ny) / 0.45 - 1.0);

    // Shoulders — wide flat ellipsoid
    const sx = x, sy = y + 0.85, sz = z;
    const shoulders = Math.sqrt(
      (sx * sx) / (1.25 * 1.25) +
      (sy * sy) / (0.22 * 0.22) +
      (sz * sz) / (0.50 * 0.50)
    ) - 1.0;

    // Smooth union
    return Math.min(cranium, jaw, neckClamp, shoulders);
  }

  sampleSDFPosition(index) {
    // Stratified sampling: generate candidate positions inside the SDF
    for (let attempt = 0; attempt < 20; attempt++) {
      const x = (Math.random() - 0.5) * 3.2;
      const y = (Math.random() - 0.5) * 3.2 + 0.2;
      const z = (Math.random() - 0.5) * 2.0;

      const d = this.headSDF(x, y, z);

      if (d < 0.05) {
        // Bias surface points (shells)
        const jitter = 0.04;
        return new THREE.Vector3(
          x + (Math.random() - 0.5) * jitter,
          y + (Math.random() - 0.5) * jitter,
          z + (Math.random() - 0.5) * jitter
        );
      }
    }
    // Fallback: put it on the head sphere surface
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    return new THREE.Vector3(
      Math.sin(phi) * Math.cos(theta) * 0.7,
      Math.sin(phi) * Math.sin(theta) * 0.7 + 0.55,
      Math.cos(phi) * 0.65
    );
  }

  // ── Main digit point cloud ───────────────────────────────────────────
  createBinaryDigitSystem() {
    this.digitTexture = this.createDigitTexture();

    const digitGeometry = new THREE.PlaneGeometry(0.075, 0.11);

    const digitMaterial = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uDigitTexture: { value: this.digitTexture },
        uVolume: { value: 0 },
        uJawOpen: { value: 0 },
        uActivity: { value: 0 },
        uColorPalette: { value: this.getColorPalette() },
        uFlickerSpeed: { value: 10.0 },
        uGlitchIntensity: { value: 0.0 },
        uScanY: { value: -99.0 }
      },
      vertexShader: this.getVertexShader(),
      fragmentShader: this.getFragmentShader(),
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    this.digitMesh = new THREE.InstancedMesh(
      digitGeometry,
      digitMaterial,
      this.options.digitCount
    );

    this.initializeDigitPositions();
    this.scene.add(this.digitMesh);
  }

  initializeDigitPositions() {
    const dummy = new THREE.Object3D();
    const color = new THREE.Color();

    // Store base positions for jaw animation
    this._basePositions = new Float32Array(this.options.digitCount * 3);

    for (let i = 0; i < this.options.digitCount; i++) {
      const pos = this.sampleSDFPosition(i);

      this._basePositions[i * 3] = pos.x;
      this._basePositions[i * 3 + 1] = pos.y;
      this._basePositions[i * 3 + 2] = pos.z;

      dummy.position.copy(pos);
      dummy.rotation.z = (Math.random() - 0.5) * 0.3;
      const s = 0.65 + Math.random() * 0.55;
      dummy.scale.setScalar(s);
      dummy.updateMatrix();

      this.digitMesh.setMatrixAt(i, dummy.matrix);

      // Depth-coded brightness: farther from camera → dimmer
      const depth = (pos.z + 1) / 2; // 0‥1
      const brightness = 0.35 + depth * 0.65;
      color.setRGB(brightness, brightness, brightness);
      this.digitMesh.setColorAt(i, color);
    }

    this.digitMesh.instanceMatrix.needsUpdate = true;
    if (this.digitMesh.instanceColor) this.digitMesh.instanceColor.needsUpdate = true;
  }

  // ── Data rain (falling background digits) ────────────────────────────
  createDataRain() {
    const count = this.options.rainCount;
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const randoms = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      positions[i * 3]     = (Math.random() - 0.5) * 12;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 10;
      positions[i * 3 + 2] = -2 - Math.random() * 6;
      randoms[i] = Math.random();
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('aRandom', new THREE.BufferAttribute(randoms, 1));

    const rainMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uColor: { value: this.getColorPalette() }
      },
      vertexShader: `
        attribute float aRandom;
        varying float vAlpha;
        varying float vRandom;
        uniform float uTime;
        void main() {
          vRandom = aRandom;
          vec3 p = position;
          // Fall downward, wrap around
          p.y = mod(p.y - uTime * (0.8 + aRandom * 1.5) + 5.0, 10.0) - 5.0;
          vAlpha = smoothstep(-5.0, -2.0, p.y) * smoothstep(5.0, 2.0, p.y);
          vAlpha *= 0.15 + aRandom * 0.20;
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          gl_Position = projectionMatrix * mv;
          gl_PointSize = (2.5 + aRandom * 2.5) * (50.0 / -mv.z);
        }
      `,
      fragmentShader: `
        uniform vec3 uColor;
        varying float vAlpha;
        varying float vRandom;
        void main() {
          float d = length(gl_PointCoord - 0.5);
          if (d > 0.5) discard;
          gl_FragColor = vec4(uColor, vAlpha * (1.0 - d * 2.0));
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    this.rainPoints = new THREE.Points(geo, rainMat);
    this.scene.add(this.rainPoints);
  }

  // ── Shaders ──────────────────────────────────────────────────────────
  getVertexShader() {
    return `
      uniform float uTime;
      uniform float uVolume;
      uniform float uJawOpen;
      uniform float uActivity;
      uniform float uScanY;

      // instanceColor is auto-injected by Three.js InstancedMesh

      varying vec2 vUv;
      varying float vDigitType;
      varying float vBrightness;
      varying vec3 vColor;
      varying float vScanHighlight;

      float hash(vec3 p) {
        return fract(sin(dot(p, vec3(12.9898, 78.233, 45.164))) * 43758.5453);
      }

      void main() {
        vUv = uv;
        vColor = instanceColor;

        vec4 instancePos = instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
        vec3 pos = position;

        // ── Digit flicker (0 ↔ 1 ↔ { ↔ }) ──
        float flickerRate = uActivity == 1.0 ? 25.0 : 8.0;
        float fid = float(gl_InstanceID);
        float rnd = hash(vec3(fid, floor(uTime * flickerRate), 0.0));
        vDigitType = floor(rnd * 4.0); // 0..3

        // ── Brightness pulse ──
        float pulseSpeed = uActivity == 2.0 ? 6.0 : 1.5;
        vBrightness = 0.6 + 0.4 * sin(uTime * pulseSpeed + fid * 0.07);

        // ── Mouth region displacement (speaking) ──
        float mouthMask = smoothstep(0.35, 0.0, abs(instancePos.y - 0.05))
                        * smoothstep(0.4, 0.0, abs(instancePos.x));
        if (uActivity == 2.0) {
          pos.y -= uVolume * mouthMask * 0.18;
          pos.z += uVolume * mouthMask * 0.08;
          vBrightness += uVolume * mouthMask * 0.5;
        }
        // Jaw open articulation
        if (instancePos.y < 0.15) {
          float jawMask = smoothstep(0.15, -0.15, instancePos.y);
          pos.y -= uJawOpen * jawMask * 0.12;
        }

        // ── Thinking: gentle orbit ──
        if (uActivity == 1.0) {
          float orbit = sin(uTime * 2.0 + fid * 0.3) * 0.03;
          pos.x += orbit;
          pos.z += cos(uTime * 2.0 + fid * 0.3) * 0.02;
        }

        // ── Idle breathing ──
        if (uActivity == 0.0) {
          float breath = sin(uTime * 0.8) * 0.008;
          pos.y += breath;
        }

        // ── Holographic scan highlight ──
        float scanDist = abs(instancePos.y - uScanY);
        vScanHighlight = smoothstep(0.15, 0.0, scanDist) * 0.6;

        // ── Depth-based parallax scale ──
        float depth = length(instancePos.xyz);
        float depthScale = mix(0.85, 1.15, depth / 2.5);
        pos *= depthScale;

        vec4 mvPosition = modelViewMatrix * instanceMatrix * vec4(pos, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        gl_PointSize = 90.0 / -mvPosition.z;
      }
    `;
  }

  getFragmentShader() {
    return `
      uniform sampler2D uDigitTexture;
      uniform vec3 uColorPalette;
      uniform float uActivity;
      uniform float uGlitchIntensity;

      varying vec2 vUv;
      varying float vDigitType;
      varying float vBrightness;
      varying vec3 vColor;
      varying float vScanHighlight;

      void main() {
        // Sample from 4-glyph texture atlas
        vec2 atlasUV = vUv;
        float col = floor(vDigitType);         // 0..3
        atlasUV.x = atlasUV.x * 0.25 + col * 0.25;

        vec4 digit = texture2D(uDigitTexture, atlasUV);

        vec3 color = uColorPalette * digit.rgb * vBrightness * vColor;

        // Holographic scan brightening
        color += uColorPalette * vScanHighlight;

        // Error state: red shift
        if (uActivity == 3.0) {
          color = mix(color, vec3(1.0, 0.05, 0.0), 0.75);
        }

        // Glitch noise
        if (uGlitchIntensity > 0.0) {
          color *= 1.0 + uGlitchIntensity * (fract(sin(vUv.y * 120.0 + vUv.x * 80.0) * 43758.5453) - 0.5);
        }

        gl_FragColor = vec4(color, digit.a * 0.92);
      }
    `;
  }

  // ── Post-processing ──────────────────────────────────────────────────
  setupPostProcessing() {
    this.composer = new EffectComposer(this.renderer);

    const renderPass = new RenderPass(this.scene, this.camera);
    this.composer.addPass(renderPass);

    if (this.options.enableBloom) {
      this.bloomPass = new UnrealBloomPass(
        new THREE.Vector2(this.container.clientWidth, this.container.clientHeight),
        1.4, 0.45, 0.82
      );
      this.composer.addPass(this.bloomPass);
    }

    if (this.options.enableChromatic) {
      this.chromaticPass = new ShaderPass(this.getChromaticAberrationShader());
      this.composer.addPass(this.chromaticPass);
    }

    if (this.options.enableCRT) {
      this.crtPass = new ShaderPass(this.getCRTShader());
      this.crtPass.renderToScreen = true;
      this.composer.addPass(this.crtPass);
    }
  }

  getChromaticAberrationShader() {
    return {
      uniforms: {
        tDiffuse: { value: null },
        uAberration: { value: 0.003 },
        uActivity: { value: 0 }
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform float uAberration;
        uniform float uActivity;
        varying vec2 vUv;
        void main() {
          float shift = uAberration * (uActivity == 3.0 ? 4.0 : 1.0);
          vec2 dir = vUv - 0.5;
          float r = texture2D(tDiffuse, vUv + dir * shift).r;
          float g = texture2D(tDiffuse, vUv).g;
          float b = texture2D(tDiffuse, vUv - dir * shift).b;
          gl_FragColor = vec4(r, g, b, 1.0);
        }
      `
    };
  }

  getCRTShader() {
    return {
      uniforms: {
        tDiffuse: { value: null },
        uTime: { value: 0 },
        uScanlineIntensity: { value: 0.12 },
        uNoiseIntensity: { value: 0.04 },
        uFlickerIntensity: { value: 0.015 }
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform float uTime;
        uniform float uScanlineIntensity;
        uniform float uNoiseIntensity;
        uniform float uFlickerIntensity;
        varying vec2 vUv;

        float random(vec2 st) {
          return fract(sin(dot(st, vec2(12.9898, 78.233))) * 43758.5453);
        }

        void main() {
          vec4 color = texture2D(tDiffuse, vUv);

          // Scanlines
          float scanline = sin(vUv.y * 900.0) * uScanlineIntensity;
          color.rgb -= scanline;

          // Film grain
          float noise = random(vUv + fract(uTime)) * uNoiseIntensity;
          color.rgb += noise - uNoiseIntensity * 0.5;

          // Screen flicker
          float flicker = 1.0 - uFlickerIntensity * sin(uTime * 8.7);
          color.rgb *= flicker;

          // Barrel-distortion vignette
          vec2 c = vUv - 0.5;
          float vignette = 1.0 - dot(c, c) * 0.35;
          color.rgb *= vignette;

          gl_FragColor = color;
        }
      `
    };
  }

  // ── Ambient background ───────────────────────────────────────────────
  addAmbientEffects() {
    // Wireframe grid
    const gridGeo = new THREE.PlaneGeometry(24, 24, 32, 32);
    const gridMat = new THREE.MeshBasicMaterial({
      color: this.getColorPalette(),
      wireframe: true,
      transparent: true,
      opacity: 0.025
    });
    this.backgroundGrid = new THREE.Mesh(gridGeo, gridMat);
    this.backgroundGrid.position.z = -6;
    this.scene.add(this.backgroundGrid);

    // Horizon line glow
    const horizonGeo = new THREE.PlaneGeometry(20, 0.005);
    const horizonMat = new THREE.MeshBasicMaterial({
      color: this.getColorPalette(),
      transparent: true,
      opacity: 0.15,
      blending: THREE.AdditiveBlending
    });
    this.horizonLine = new THREE.Mesh(horizonGeo, horizonMat);
    this.horizonLine.position.set(0, -1.2, -4);
    this.scene.add(this.horizonLine);
  }

  // ── Color palettes ──────────────────────────────────────────────────
  getColorPalette() {
    const palettes = {
      'matrix':        new THREE.Vector3(0.0, 1.0, 0.0),
      'cyber-magenta': new THREE.Vector3(1.0, 0.0, 1.0),
      'cyan':          new THREE.Vector3(0.0, 1.0, 1.0),
      'amber':         new THREE.Vector3(1.0, 0.75, 0.0),
      'red':           new THREE.Vector3(1.0, 0.0, 0.0),
      'ice':           new THREE.Vector3(0.6, 0.85, 1.0),
      'gold':          new THREE.Vector3(1.0, 0.84, 0.0)
    };
    return palettes[this.options.colorPalette] || palettes['matrix'];
  }

  // ── Animation loop ──────────────────────────────────────────────────
  animate() {
    this.animationId = requestAnimationFrame(() => this.animate());

    const dt = 0.016;
    this.time += dt;

    // Update digit uniforms
    if (this.digitMesh && this.digitMesh.material) {
      const u = this.digitMesh.material.uniforms;
      u.uTime.value = this.time;
      u.uVolume.value = this.state.volume;
      u.uJawOpen.value = this.state.jawOpen;
      u.uActivity.value = this.getActivityValue();

      // Glitch bursts on error or state transitions
      const targetGlitch = this.state.activity === 'error' ? 0.55 : 0.0;
      u.uGlitchIntensity.value += (targetGlitch - u.uGlitchIntensity.value) * 0.1;

      // Holographic scan line: sweeps up every ~4s
      if (this.options.enableHoloScan) {
        const scanCycle = (this.time % 4.0) / 4.0;
        u.uScanY.value = -1.5 + scanCycle * 3.5;
      }
    }

    // Update chromatic pass
    if (this.chromaticPass) {
      this.chromaticPass.uniforms.uActivity.value = this.getActivityValue();
      // Increase aberration during speech
      const baseAberration = 0.003;
      const speechBoost = this.state.activity === 'speaking' ? this.state.volume * 0.004 : 0;
      this.chromaticPass.uniforms.uAberration.value = baseAberration + speechBoost;
    }

    // Update CRT
    if (this.crtPass) {
      this.crtPass.uniforms.uTime.value = this.time;
    }

    // Update data rain
    if (this.rainPoints && this.rainPoints.material) {
      this.rainPoints.material.uniforms.uTime.value = this.time;
    }

    // Rotate background
    if (this.backgroundGrid) {
      this.backgroundGrid.rotation.z = this.time * 0.03;
    }

    // Smooth jaw toward volume
    this.state.jawOpen += (this.state.volume - this.state.jawOpen) * 0.25;

    this.composer.render();
  }

  getActivityValue() {
    const map = { 'idle': 0, 'thinking': 1, 'speaking': 2, 'error': 3 };
    return map[this.state.activity] || 0;
  }

  // ── Public API ──────────────────────────────────────────────────────
  setState(newState) {
    Object.assign(this.state, newState);
  }

  setEmotion(emotion) {
    this.state.emotion = emotion;
  }

  setActivity(activity) {
    // Trigger brief glitch on state change
    if (activity !== this.state.activity && this.digitMesh) {
      this.digitMesh.material.uniforms.uGlitchIntensity.value = 0.35;
    }
    this.state.activity = activity;
  }

  setVolume(volume) {
    this.state.volume = Math.max(0, Math.min(1, volume));
  }

  setFrequencyData(frequencyArray) {
    this.state.frequency = frequencyArray;
  }

  onResize() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.composer.setSize(w, h);
  }

  destroy() {
    if (this.animationId) cancelAnimationFrame(this.animationId);

    this.scene.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        (Array.isArray(obj.material) ? obj.material : [obj.material]).forEach(m => m.dispose());
      }
    });

    if (this.renderer) this.renderer.dispose();
    window.removeEventListener('resize', this._onResize);
  }
}

export { BinaryAvatarRenderer };
