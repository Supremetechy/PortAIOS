/**
 * AvatarSystemRenderer
 * ─────────────────────────────────────────────────────────────────────────────
 * Unified renderer merging SpatialEnvironmentRenderer + BinaryAvatarRenderer
 * into a single THREE scene, single WebGLRenderer, and single EffectComposer.
 *
 * Environment layers (back → front):
 *   1. Floor / ceiling perspective-scrolling grids
 *   2. Side wall grids
 *   3. Vertical data-stream columns
 *   4. Horizon glow planes
 *   5. Vanishing-point light shaft
 *   6. Binary digit head (SDF-sampled instanced mesh) ← avatar layer
 *
 * Post-processing stack (shared):
 *   UnrealBloom → ChromaticAberration → CRT scanline/grain/vignette
 *
 * Public API
 * ──────────
 *   setState(obj)          — batch-update { emotion, activity, volume, cpuLoad, frequency }
 *   setActivity(str)       — 'idle' | 'thinking' | 'speaking' | 'error'
 *   setEmotion(str)        — 'neutral' | 'happy' | 'focused' | …
 *   setVolume(num)         — 0.0–1.0
 *   setFrequencyData(arr)  — Float32Array (Web Audio AnalyserNode)
 *   setColorPalette(name)  — hot-swap palette at runtime
 *   setSpeed(num)          — environment scroll speed multiplier
 *   onResize()             — call on container resize (window listener built in)
 *   destroy()              — full teardown
 *
 * Usage
 * ──────
 *   import { AvatarSystemRenderer } from './AvatarSystemRenderer.js';
 *
 *   const el  = document.getElementById('stage');
 *   const sys = new AvatarSystemRenderer(el, { colorPalette: 'matrix' });
 *
 *   sys.setActivity('speaking');
 *   sys.setVolume(0.8);
 */

import * as THREE from 'https://esm.sh/three@0.160.0';
import { EffectComposer }  from 'https://esm.sh/three@0.160.0/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass }      from 'https://esm.sh/three@0.160.0/examples/jsm/postprocessing/RenderPass.js';
import { ShaderPass }      from 'https://esm.sh/three@0.160.0/examples/jsm/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'https://esm.sh/three@0.160.0/examples/jsm/postprocessing/UnrealBloomPass.js';

// ── Palette registry ──────────────────────────────────────────────────────────
const PALETTES = {
  'matrix':        { primary: [0.0, 1.0, 0.0],  accent: [0.0, 0.6, 0.0],  fog: 0x001200, sky: 0x000800 },
  'cyan':          { primary: [0.0, 1.0, 1.0],  accent: [0.0, 0.5, 0.8],  fog: 0x00121a, sky: 0x000510 },
  'amber':         { primary: [1.0, 0.75, 0.0], accent: [0.8, 0.4, 0.0],  fog: 0x1a0d00, sky: 0x080400 },
  'cyber-magenta': { primary: [1.0, 0.0, 1.0],  accent: [0.6, 0.0, 0.8],  fog: 0x12001a, sky: 0x070010 },
  'ice':           { primary: [0.6, 0.85, 1.0], accent: [0.3, 0.6, 0.9],  fog: 0x060c14, sky: 0x020508 },
  'gold':          { primary: [1.0, 0.84, 0.0], accent: [0.7, 0.5, 0.0],  fog: 0x140e00, sky: 0x070500 },
  'red':           { primary: [1.0, 0.0, 0.0],  accent: [0.6, 0.0, 0.0],  fog: 0x1a0000, sky: 0x080000 },
};

// ── Activity index map ────────────────────────────────────────────────────────
const ACTIVITY = { idle: 0, thinking: 1, speaking: 2, error: 3 };

class BinaryAvatarRenderer {

  // ───────────────────────────────────────────────────────────────────────────
  constructor(container, options = {}) {
    this.container = container;

    this.options = {
      // avatar
      digitCount:      options.digitCount      ?? 8000,
      colorPalette:    options.colorPalette     ?? 'matrix',
      avatarType:      options.avatarType       ?? 'head',
      enableHoloScan:  options.enableHoloScan   !== false,
      // environment
      streamCount:     options.streamCount      ?? 28,
      // shared post-fx
      enableBloom:     options.enableBloom      !== false,
      enableChromatic: options.enableChromatic  !== false,
      enableCRT:       options.enableCRT        !== false,
      bloomStrength:   options.bloomStrength    ?? 1.4,
      ...options,
    };

    this.state = {
      emotion:   'neutral',
      activity:  'idle',
      volume:    0.0,
      cpuLoad:   0.0,
      frequency: new Float32Array(128),
      jawOpen:   0.0,
    };

    this._palette   = PALETTES[this.options.colorPalette] || PALETTES['matrix'];
    this._time      = 0;
    this._speed     = 1.0;
    this._animId    = null;
    this._envMats   = [];   // environment materials (uColor / uAccent)

    this._init();
  }

  // ── Tiny helpers ────────────────────────────────────────────────────────────
  _v3(r, g, b) { return new THREE.Vector3(r, g, b); }
  _pv3()       { return this._v3(...this._palette.primary); }
  _av3()       { return this._v3(...this._palette.accent);  }
  _palColor()  { return new THREE.Color(...this._palette.primary); }
  _actVal()    { return ACTIVITY[this.state.activity] ?? 0; }
  _trackEnv(m) { this._envMats.push(m); return m; }

  // ── Bootstrap ───────────────────────────────────────────────────────────────
  _init() {
    if (this._destroyed) return;
    const W = this.container.clientWidth;
    const H = this.container.clientHeight;

    if (W === 0 || H === 0) {
      if (!this._initRetryId) {
        this._initRetryId = requestAnimationFrame(() => {
          this._initRetryId = null;
          this._init();
        });
      }
      return;
    }

    // ── Scene ──
    this._scene = new THREE.Scene();
    this._scene.fog = new THREE.FogExp2(this._palette.fog, 0.045);

    // ── Avatar camera (closer, slightly elevated) ──
    this._camera = new THREE.PerspectiveCamera(55, W / H, 0.1, 200);
    this._camera.position.set(0, 0.15, 4.8);
    this._camera.lookAt(0, 0.15, 0);

    // ── Renderer (single, opaque — env provides the bg) ──
    this._renderer = new THREE.WebGLRenderer({
      antialias: false,
      alpha: false,
      powerPreference: 'high-performance',
    });
    this._renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this._renderer.setSize(W, H);
    this._renderer.setClearColor(this._palette.sky || 0x000000, 1);
    this.container.appendChild(this._renderer.domElement);

    // ── Build layers (order = scene z-sort, env first) ──
    this._buildEnvironment();
    this._buildAvatarDigits();

    // ── Post-processing ──
    this._setupPostFX(W, H);

    // ── Resize ──
    this._onResize = () => this.onResize();
    window.addEventListener('resize', this._onResize);

    this._animate();
  }

  // ╔═══════════════════════════════════════════════════════════════════════════
  // ║  ENVIRONMENT LAYERS
  // ╚═══════════════════════════════════════════════════════════════════════════

  _buildEnvironment() {
    this._floorMat  = this._makeFloorGrid(false);
    this._ceilMat   = this._makeFloorGrid(true);
    this._wallMatL  = this._makeWallGrid(-1);
    this._wallMatR  = this._makeWallGrid(1);
    this._streamMats = this._makeDataStreams();
    this._horizMat  = this._makeHorizonGlow();
    this._shaftMat  = this._makeLightShaft();
  }

  // ── Floor / ceiling scrolling grid ────────────────────────────────────────
  _makeFloorGrid(isCeiling) {
    const mat = this._trackEnv(new THREE.ShaderMaterial({
      uniforms: {
        uTime:   { value: 0 },
        uColor:  { value: this._pv3() },
        uAccent: { value: this._av3() },
        uSpeed:  { value: 1.0 },
      },
      vertexShader: /* glsl */`
        varying vec2 vUv;
        void main(){
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }`,
      fragmentShader: /* glsl */`
        uniform float uTime;
        uniform vec3  uColor;
        uniform vec3  uAccent;
        uniform float uSpeed;
        varying vec2  vUv;

        float grid(vec2 uv, float scale){
          vec2 g = abs(fract(uv * scale - 0.5) - 0.5) / fwidth(uv * scale);
          return 1.0 - min(min(g.x, g.y), 1.0);
        }
        void main(){
          vec2  suv  = vec2(vUv.x, vUv.y + uTime * uSpeed * 0.04);
          float g1   = grid(suv, 8.0)  * 0.9;
          float g2   = grid(suv, 40.0) * 0.4;
          float fade = pow(1.0 - vUv.y, 2.5) * smoothstep(0.0, 0.15, vUv.y);
          vec3  col  = (uColor * g1 + uAccent * g2) * fade;
          gl_FragColor = vec4(col, (g1 + g2) * fade);
        }`,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    }));

    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(60, 80), mat);
    mesh.rotation.x = isCeiling ? Math.PI / 2 : -Math.PI / 2;
    mesh.position.set(0, isCeiling ? 2.4 : -1.55, -35);
    this._scene.add(mesh);
    return mat;
  }

  // ── Side wall grids ──────────────────────────────────────────────────────
  _makeWallGrid(side) {
    const mat = this._trackEnv(new THREE.ShaderMaterial({
      uniforms: {
        uTime:   { value: 0 },
        uColor:  { value: this._pv3() },
        uAccent: { value: this._av3() },
        uSpeed:  { value: 1.0 },
      },
      vertexShader: /* glsl */`
        varying vec2 vUv;
        void main(){
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }`,
      fragmentShader: /* glsl */`
        uniform float uTime;
        uniform vec3  uColor;
        uniform vec3  uAccent;
        uniform float uSpeed;
        varying vec2  vUv;

        float grid(vec2 uv, float s){
          vec2 g = abs(fract(uv * s - 0.5) - 0.5) / fwidth(uv * s);
          return 1.0 - min(min(g.x, g.y), 1.0);
        }
        void main(){
          vec2  suv   = vec2(vUv.x, vUv.y + uTime * uSpeed * 0.04);
          float g     = grid(suv, 6.0);
          float hFade = smoothstep(0.0, 0.12, 1.0 - vUv.x) * smoothstep(0.0, 0.08, vUv.x);
          float vFade = smoothstep(0.0, 0.10, vUv.y) * smoothstep(0.0, 0.10, 1.0 - vUv.y);
          vec3  col   = uColor * g * hFade * vFade * 0.55;
          gl_FragColor = vec4(col, g * hFade * vFade * 0.55);
        }`,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    }));

    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(80, 5), mat);
    mesh.rotation.y = side === 1 ? -Math.PI / 2 : Math.PI / 2;
    mesh.position.set(side * 6.5, 0.42, -35);
    this._scene.add(mesh);
    return mat;
  }

  // ── Vertical data-stream columns ─────────────────────────────────────────
  _makeDataStreams() {
    const mats  = [];
    const count = this.options.streamCount;

    for (let i = 0; i < count; i++) {
      const mat = this._trackEnv(new THREE.ShaderMaterial({
        uniforms: {
          uTime:  { value: 0 },
          uColor: { value: this._pv3() },
          uSpeed: { value: 0.4 + Math.random() * 1.6 },
          uPhase: { value: Math.random() * Math.PI * 2 },
        },
        vertexShader: /* glsl */`
          varying vec2 vUv;
          void main(){
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }`,
        fragmentShader: /* glsl */`
          uniform float uTime;
          uniform vec3  uColor;
          uniform float uSpeed;
          uniform float uPhase;
          varying vec2  vUv;

          float hash(float n){ return fract(sin(n) * 43758.5453); }

          void main(){
            float t      = uTime * uSpeed + uPhase;
            float row    = floor((vUv.y + t) * 18.0);
            float ch     = hash(row + floor(vUv.x * 3.0) * 100.0);
            float bright = step(0.3, ch)
              * smoothstep(0.0, 0.06, fract(vUv.x * 3.0) - 0.03)
              * smoothstep(0.0, 0.06, 1.0 - fract(vUv.x * 3.0) - 0.03);

            float fy = fract(vUv.y + t);
            bright  *= 0.2 + 0.8 * smoothstep(0.0, 0.35, fy) * smoothstep(1.0, 0.55, fy);

            gl_FragColor = vec4(uColor * bright, bright * 0.55);
          }`,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }));

      const h    = 3.5 + Math.random() * 4;
      const mesh = new THREE.Mesh(new THREE.PlaneGeometry(0.18, h), mat);
      mesh.position.set(
        (Math.random() - 0.5) * 18,
        (Math.random() - 0.5) * 2,
        -5 - Math.random() * 70,
      );
      mesh.rotation.y = (Math.random() - 0.5) * 0.6;
      this._scene.add(mesh);
      mats.push(mat);
    }

    return mats;
  }

  // ── Horizon glow ─────────────────────────────────────────────────────────
  _makeHorizonGlow() {
    const mat = this._trackEnv(new THREE.ShaderMaterial({
      uniforms: {
        uColor: { value: this._pv3() },
        uTime:  { value: 0 },
      },
      vertexShader: /* glsl */`
        varying vec2 vUv;
        void main(){
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }`,
      fragmentShader: /* glsl */`
        uniform vec3  uColor;
        uniform float uTime;
        varying vec2  vUv;
        void main(){
          float fade  = pow(1.0 - abs(vUv.y - 0.5) * 2.0, 3.0)
                      * pow(1.0 - abs(vUv.x - 0.5) * 1.8, 1.5);
          float pulse = 0.7 + 0.3 * sin(uTime * 0.5);
          gl_FragColor = vec4(uColor * fade * pulse * 0.5, fade * 0.35);
        }`,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    }));

    const geo = new THREE.PlaneGeometry(50, 0.04);
    [[-3], [-20]].forEach(([z]) => {
      const m = new THREE.Mesh(geo.clone(), mat);
      m.position.set(0, -1.55, z);
      this._scene.add(m);
    });
    return mat;
  }

  // ── Vanishing-point light shaft ──────────────────────────────────────────
  _makeLightShaft() {
    const mat = this._trackEnv(new THREE.ShaderMaterial({
      uniforms: {
        uTime:     { value: 0 },
        uColor:    { value: this._pv3() },
        uActivity: { value: 0 },
      },
      vertexShader: /* glsl */`
        varying vec2 vUv;
        void main(){
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }`,
      fragmentShader: /* glsl */`
        uniform float uTime;
        uniform vec3  uColor;
        uniform float uActivity;
        varying vec2  vUv;
        void main(){
          float cx    = abs(vUv.x - 0.5) * 2.0;
          float beam  = pow(1.0 - cx, 6.0) * (1.0 - vUv.y) * 0.25;
          float pulse = uActivity == 2.0
                      ? 0.7 + 0.3 * sin(uTime * 8.0)
                      : 0.7 + 0.15 * sin(uTime * 0.7);
          gl_FragColor = vec4(uColor * beam * pulse, beam * pulse * 0.8);
        }`,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    }));

    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(12, 80), mat);
    mesh.rotation.x = Math.PI / 2;
    mesh.position.set(0, -1.54, -35);
    this._scene.add(mesh);
    return mat;
  }

  // ╔═══════════════════════════════════════════════════════════════════════════
  // ║  AVATAR LAYER — binary digit head
  // ╚═══════════════════════════════════════════════════════════════════════════

  _buildAvatarDigits() {
    this._digitTexture = this._createDigitTexture();

    const mat = new THREE.ShaderMaterial({
      uniforms: {
        uTime:            { value: 0 },
        uDigitTexture:    { value: this._digitTexture },
        uVolume:          { value: 0 },
        uJawOpen:         { value: 0 },
        uActivity:        { value: 0 },
        uColorPalette:    { value: this._pv3() },
        uFlickerSpeed:    { value: 10.0 },
        uGlitchIntensity: { value: 0.0 },
        uScanY:           { value: -99.0 },
      },
      vertexShader:   this._avatarVertexShader(),
      fragmentShader: this._avatarFragmentShader(),
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    this._digitMesh = new THREE.InstancedMesh(
      new THREE.PlaneGeometry(0.075, 0.11),
      mat,
      this.options.digitCount,
    );

    this._initDigitPositions();
    this._scene.add(this._digitMesh);
    this._avatarMat = mat;
  }

  // ── Digit texture atlas (0  1  {  }) ─────────────────────────────────────
  _createDigitTexture() {
    const canvas = document.createElement('canvas');
    canvas.width  = 256;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 48px "Courier New", monospace';
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('0', 32,  32);
    ctx.fillText('1', 96,  32);
    ctx.fillText('{', 160, 32);
    ctx.fillText('}', 224, 32);
    const tex = new THREE.CanvasTexture(canvas);
    tex.needsUpdate = true;
    return tex;
  }

  // ── SDF: cranium + jaw + neck + shoulders ─────────────────────────────────
  _headSDF(x, y, z) {
    const cranium = Math.sqrt(
      ((x) * (x)) / (0.72 * 0.72) +
      ((y - 0.55) * (y - 0.55)) / (0.92 * 0.92) +
      ((z) * (z)) / (0.70 * 0.70)
    ) - 1.0;

    const jaw = Math.sqrt(
      ((x) * (x)) / (0.52 * 0.52) +
      ((y - 0.08) * (y - 0.08)) / (0.38 * 0.38) +
      ((z) * (z)) / (0.48 * 0.48)
    ) - 1.0;

    const ny   = y + 0.30;
    const neck = Math.sqrt(
      ((x) * (x)) / (0.22 * 0.22) +
      ((z) * (z)) / (0.20 * 0.20)
    ) - 1.0;
    const neckClamp = Math.max(neck, Math.abs(ny) / 0.45 - 1.0);

    const shoulders = Math.sqrt(
      ((x) * (x)) / (1.25 * 1.25) +
      ((y + 0.85) * (y + 0.85)) / (0.22 * 0.22) +
      ((z) * (z)) / (0.50 * 0.50)
    ) - 1.0;

    return Math.min(cranium, jaw, neckClamp, shoulders);
  }

  _sampleSDFPosition() {
    for (let attempt = 0; attempt < 20; attempt++) {
      const x = (Math.random() - 0.5) * 3.2;
      const y = (Math.random() - 0.5) * 3.2 + 0.2;
      const z = (Math.random() - 0.5) * 2.0;
      if (this._headSDF(x, y, z) < 0.05) {
        const j = 0.04;
        return new THREE.Vector3(
          x + (Math.random() - 0.5) * j,
          y + (Math.random() - 0.5) * j,
          z + (Math.random() - 0.5) * j,
        );
      }
    }
    const theta = Math.random() * Math.PI * 2;
    const phi   = Math.acos(2 * Math.random() - 1);
    return new THREE.Vector3(
      Math.sin(phi) * Math.cos(theta) * 0.7,
      Math.sin(phi) * Math.sin(theta) * 0.7 + 0.55,
      Math.cos(phi) * 0.65,
    );
  }

  _initDigitPositions() {
    const dummy = new THREE.Object3D();
    const color = new THREE.Color();
    const n     = this.options.digitCount;

    this._basePositions = new Float32Array(n * 3);

    for (let i = 0; i < n; i++) {
      const pos = this._sampleSDFPosition();

      this._basePositions[i * 3]     = pos.x;
      this._basePositions[i * 3 + 1] = pos.y;
      this._basePositions[i * 3 + 2] = pos.z;

      dummy.position.copy(pos);
      dummy.rotation.z = (Math.random() - 0.5) * 0.3;
      dummy.scale.setScalar(0.65 + Math.random() * 0.55);
      dummy.updateMatrix();
      this._digitMesh.setMatrixAt(i, dummy.matrix);

      const brightness = 0.35 + ((pos.z + 1) / 2) * 0.65;
      color.setRGB(brightness, brightness, brightness);
      this._digitMesh.setColorAt(i, color);
    }

    this._digitMesh.instanceMatrix.needsUpdate = true;
    if (this._digitMesh.instanceColor) this._digitMesh.instanceColor.needsUpdate = true;
  }

  // ── Avatar vertex shader ─────────────────────────────────────────────────
  _avatarVertexShader() {
    return /* glsl */`
      uniform float uTime;
      uniform float uVolume;
      uniform float uJawOpen;
      uniform float uActivity;
      uniform float uScanY;

      varying vec2  vUv;
      varying float vDigitType;
      varying float vBrightness;
      varying vec3  vColor;
      varying float vScanHighlight;

      float hash(vec3 p){
        return fract(sin(dot(p, vec3(12.9898, 78.233, 45.164))) * 43758.5453);
      }

      void main(){
        vUv   = uv;
        vColor = instanceColor;

        vec4  instancePos = instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
        vec3  pos         = position;

        // Digit flicker
        float flickerRate = uActivity == 1.0 ? 25.0 : 8.0;
        float fid = float(gl_InstanceID);
        float rnd = hash(vec3(fid, floor(uTime * flickerRate), 0.0));
        vDigitType = floor(rnd * 4.0);

        // Brightness pulse
        float pulseSpeed = uActivity == 2.0 ? 6.0 : 1.5;
        vBrightness = 0.6 + 0.4 * sin(uTime * pulseSpeed + fid * 0.07);

        // Mouth displacement (speaking)
        float mouthMask = smoothstep(0.35, 0.0, abs(instancePos.y - 0.05))
                        * smoothstep(0.40, 0.0, abs(instancePos.x));
        if(uActivity == 2.0){
          pos.y -= uVolume * mouthMask * 0.18;
          pos.z += uVolume * mouthMask * 0.08;
          vBrightness += uVolume * mouthMask * 0.5;
        }

        // Jaw articulation
        if(instancePos.y < 0.15){
          float jawMask = smoothstep(0.15, -0.15, instancePos.y);
          pos.y -= uJawOpen * jawMask * 0.12;
        }

        // Thinking: gentle orbit
        if(uActivity == 1.0){
          pos.x += sin(uTime * 2.0 + fid * 0.3) * 0.03;
          pos.z += cos(uTime * 2.0 + fid * 0.3) * 0.02;
        }

        // Idle breathing
        if(uActivity == 0.0){
          pos.y += sin(uTime * 0.8) * 0.008;
        }

        // Holographic scan highlight
        vScanHighlight = smoothstep(0.15, 0.0, abs(instancePos.y - uScanY)) * 0.6;

        // Depth-based parallax scale
        float depthScale = mix(0.85, 1.15, length(instancePos.xyz) / 2.5);
        pos *= depthScale;

        vec4 mvPosition = modelViewMatrix * instanceMatrix * vec4(pos, 1.0);
        gl_Position     = projectionMatrix * mvPosition;
        gl_PointSize    = 90.0 / -mvPosition.z;
      }
    `;
  }

  // ── Avatar fragment shader ───────────────────────────────────────────────
  _avatarFragmentShader() {
    return /* glsl */`
      uniform sampler2D uDigitTexture;
      uniform vec3      uColorPalette;
      uniform float     uActivity;
      uniform float     uGlitchIntensity;

      varying vec2  vUv;
      varying float vDigitType;
      varying float vBrightness;
      varying vec3  vColor;
      varying float vScanHighlight;

      void main(){
        vec2 atlasUV = vUv;
        atlasUV.x    = atlasUV.x * 0.25 + floor(vDigitType) * 0.25;

        vec4 digit = texture2D(uDigitTexture, atlasUV);
        vec3 col   = uColorPalette * digit.rgb * vBrightness * vColor;

        // Holographic scan
        col += uColorPalette * vScanHighlight;

        // Error: red shift
        if(uActivity == 3.0)
          col = mix(col, vec3(1.0, 0.05, 0.0), 0.75);

        // Glitch noise
        if(uGlitchIntensity > 0.0)
          col *= 1.0 + uGlitchIntensity
               * (fract(sin(vUv.y * 120.0 + vUv.x * 80.0) * 43758.5453) - 0.5);

        gl_FragColor = vec4(col, digit.a * 0.92);
      }
    `;
  }

  // ╔═══════════════════════════════════════════════════════════════════════════
  // ║  SHARED POST-PROCESSING
  // ╚═══════════════════════════════════════════════════════════════════════════

  _setupPostFX(W, H) {
    this._composer = new EffectComposer(this._renderer);
    this._composer.addPass(new RenderPass(this._scene, this._camera));

    // Bloom
    if (this.options.enableBloom) {
      this._bloomPass = new UnrealBloomPass(
        new THREE.Vector2(W, H),
        this.options.bloomStrength, 0.45, 0.82,
      );
      this._composer.addPass(this._bloomPass);
    }

    // Chromatic aberration
    if (this.options.enableChromatic) {
      this._chromaticPass = new ShaderPass({
        uniforms: {
          tDiffuse:     { value: null },
          uAberration:  { value: 0.003 },
          uActivity:    { value: 0 },
        },
        vertexShader: /* glsl */`
          varying vec2 vUv;
          void main(){
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }`,
        fragmentShader: /* glsl */`
          uniform sampler2D tDiffuse;
          uniform float     uAberration;
          uniform float     uActivity;
          varying vec2      vUv;
          void main(){
            float shift = uAberration * (uActivity == 3.0 ? 4.0 : 1.0);
            vec2  dir   = vUv - 0.5;
            float r = texture2D(tDiffuse, vUv + dir * shift).r;
            float g = texture2D(tDiffuse, vUv).g;
            float b = texture2D(tDiffuse, vUv - dir * shift).b;
            gl_FragColor = vec4(r, g, b, 1.0);
          }`,
      });
      this._composer.addPass(this._chromaticPass);
    }

    // CRT scanline / grain / vignette / error glitch
    if (this.options.enableCRT) {
      this._crtPass = new ShaderPass({
        uniforms: {
          tDiffuse:           { value: null },
          uTime:              { value: 0 },
          uScanlineIntensity: { value: 0.12 },
          uNoiseIntensity:    { value: 0.04 },
          uFlickerIntensity:  { value: 0.015 },
          uActivity:          { value: 0 },
        },
        vertexShader: /* glsl */`
          varying vec2 vUv;
          void main(){
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }`,
        fragmentShader: /* glsl */`
          uniform sampler2D tDiffuse;
          uniform float     uTime;
          uniform float     uScanlineIntensity;
          uniform float     uNoiseIntensity;
          uniform float     uFlickerIntensity;
          uniform float     uActivity;
          varying vec2      vUv;

          float rand(vec2 st){ return fract(sin(dot(st, vec2(12.9898, 78.233))) * 43758.5453); }

          void main(){
            vec4  color   = texture2D(tDiffuse, vUv);

            // Chromatic split on error (extra layer beyond the dedicated pass)
            if(uActivity == 3.0){
              float band = step(0.99, rand(vec2(floor(vUv.y * 60.0 + uTime * 30.0), 0.0)));
              color.rgb  = mix(color.rgb, vec3(1.0, 0.0, 0.0) * color.g * 2.0, band * 0.6);
            }

            // Scanlines
            color.rgb -= sin(vUv.y * 900.0) * uScanlineIntensity;

            // Film grain
            color.rgb += rand(vUv + fract(uTime)) * uNoiseIntensity - uNoiseIntensity * 0.5;

            // Screen flicker
            color.rgb *= 1.0 - uFlickerIntensity * sin(uTime * 8.7);

            // Barrel-distortion vignette
            vec2  c       = vUv - 0.5;
            color.rgb    *= 1.0 - dot(c, c) * 0.35;

            gl_FragColor  = color;
          }`,
      });
      this._crtPass.renderToScreen = true;
      this._composer.addPass(this._crtPass);
    }
  }

  // ╔═══════════════════════════════════════════════════════════════════════════
  // ║  ANIMATION LOOP
  // ╚═══════════════════════════════════════════════════════════════════════════

  _animate() {
    this._animId = requestAnimationFrame(() => this._animate());

    this._time += 0.016;
    const t     = this._time;
    const act   = this._actVal();
    const speed = this._speed;

    // ── Camera motion ──────────────────────────────────────────────────────
    this._camera.rotation.z = Math.sin(t * 0.18) * 0.025;
    this._camera.position.y = 0.15 + Math.sin(t * 0.22) * 0.03;

    if (act === 0) { /* idle breathing already in vertex shader */ }
    if (act === 1) { // thinking: slow camera orbit
      this._camera.position.x = Math.sin(t * 0.4) * 0.2;
    } else if (act === 3) { // error: shake
      this._camera.position.x = Math.sin(t * 30) * 0.035;
    } else {
      this._camera.position.x += (0 - this._camera.position.x) * 0.08;
    }
    if (act === 2) { // speaking: subtle bounce
      this._camera.position.y += Math.sin(t * 6) * 0.008;
    }

    // ── Bloom ramp per state ───────────────────────────────────────────────
    if (this._bloomPass) {
      const targets = [1.4, 1.6, 1.9, 2.2];
      this._bloomPass.strength += (targets[act] - this._bloomPass.strength) * 0.06;
    }

    // ── Environment uniforms ───────────────────────────────────────────────
    this._floorMat.uniforms.uTime.value   = t;
    this._floorMat.uniforms.uSpeed.value  = speed;
    this._ceilMat.uniforms.uTime.value    = t;
    this._ceilMat.uniforms.uSpeed.value   = speed;
    this._wallMatL.uniforms.uTime.value   = t;
    this._wallMatL.uniforms.uSpeed.value  = speed;
    this._wallMatR.uniforms.uTime.value   = t;
    this._wallMatR.uniforms.uSpeed.value  = speed;
    this._horizMat.uniforms.uTime.value   = t;
    this._shaftMat.uniforms.uTime.value   = t;
    this._shaftMat.uniforms.uActivity.value = act;
    this._streamMats.forEach(m => { m.uniforms.uTime.value = t; });

    // ── Avatar uniforms ────────────────────────────────────────────────────
    const u = this._avatarMat.uniforms;
    u.uTime.value     = t;
    u.uVolume.value   = this.state.volume;
    u.uJawOpen.value  = this.state.jawOpen;
    u.uActivity.value = act;

    // Glitch burst on error, decay otherwise
    const targetGlitch = act === 3 ? 0.55 : 0.0;
    u.uGlitchIntensity.value += (targetGlitch - u.uGlitchIntensity.value) * 0.1;

    // Holographic scan sweep (every ~4 s)
    if (this.options.enableHoloScan) {
      u.uScanY.value = -1.5 + ((t % 4.0) / 4.0) * 3.5;
    }

    // ── Shared post-fx uniforms ────────────────────────────────────────────
    if (this._chromaticPass) {
      this._chromaticPass.uniforms.uActivity.value  = act;
      this._chromaticPass.uniforms.uAberration.value =
        0.003 + (act === 2 ? this.state.volume * 0.004 : 0);
    }
    if (this._crtPass) {
      this._crtPass.uniforms.uTime.value     = t;
      this._crtPass.uniforms.uActivity.value = act;
    }

    // Smooth jaw toward volume
    this.state.jawOpen += (this.state.volume - this.state.jawOpen) * 0.25;

    this._composer.render();
  }

  // ╔═══════════════════════════════════════════════════════════════════════════
  // ║  PALETTE HOT-SWAP (env + avatar simultaneously)
  // ╚═══════════════════════════════════════════════════════════════════════════

  _applyPalette() {
    const p = this._palette;
    this._scene.fog.color.setHex(p.fog);
    this._renderer.setClearColor(p.sky || 0x000000, 1);

    // Environment mats
    this._envMats.forEach(m => {
      if (m.uniforms.uColor)  m.uniforms.uColor.value  = this._pv3();
      if (m.uniforms.uAccent) m.uniforms.uAccent.value = this._av3();
    });

    // Avatar mat
    if (this._avatarMat) {
      this._avatarMat.uniforms.uColorPalette.value = this._pv3();
    }
  }

  // ╔═══════════════════════════════════════════════════════════════════════════
  // ║  PUBLIC API
  // ╚═══════════════════════════════════════════════════════════════════════════

  /** Batch-update state: { emotion, activity, volume, cpuLoad, frequency } */
  setState(newState) {
    Object.assign(this.state, newState);
  }

  /** 'neutral' | 'happy' | 'focused' | … */
  setEmotion(emotion) {
    this.state.emotion = emotion;
  }

  /** 'idle' | 'thinking' | 'speaking' | 'error' */
  setActivity(activity) {
    // Trigger a brief glitch burst on any state transition
    if (activity !== this.state.activity && this._avatarMat) {
      this._avatarMat.uniforms.uGlitchIntensity.value = 0.35;
    }
    this.state.activity = activity;
  }

  /** 0.0 – 1.0 */
  setVolume(volume) {
    this.state.volume = Math.max(0, Math.min(1, volume));
  }

  /** Float32Array from Web Audio AnalyserNode */
  setFrequencyData(frequencyArray) {
    this.state.frequency = frequencyArray;
  }

  /**
   * Hot-swap colour palette for both environment and avatar.
   * @param {string} name  'matrix' | 'cyan' | 'amber' | 'cyber-magenta' | 'ice' | 'gold' | 'red'
   */
  setColorPalette(name) {
    const p = PALETTES[name];
    if (!p) {
      console.warn(`AvatarSystemRenderer: unknown palette "${name}"`);
      return;
    }
    this._palette = p;
    this._applyPalette();
  }

  /**
   * Environment scroll speed multiplier (default 1.0).
   * @param {number} speed
   */
  setSpeed(speed) {
    this._speed = Math.max(0, speed);
  }

  /** Call on container resize (window listener is built in). */
  onResize() {
    const W = this.container.clientWidth;
    const H = this.container.clientHeight;
    if (!W || !H || !this._camera || !this._renderer || !this._composer) return;
    this._camera.aspect = W / H;
    this._camera.updateProjectionMatrix();
    this._renderer.setSize(W, H);
    this._composer.setSize(W, H);
  }

  /** Full teardown — call when unmounting. */
  destroy() {
    this._destroyed = true;
    if (this._initRetryId) cancelAnimationFrame(this._initRetryId);
    if (this._animId) cancelAnimationFrame(this._animId);

    this._scene.traverse(obj => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        (Array.isArray(obj.material) ? obj.material : [obj.material])
          .forEach(m => m.dispose());
      }
    });

    if (this._digitTexture) this._digitTexture.dispose();

    if (this._renderer) {
      this._renderer.dispose();
      this._renderer.domElement?.parentNode?.removeChild(this._renderer.domElement);
    }

    window.removeEventListener('resize', this._onResize);
  }
}

export {BinaryAvatarRenderer};
