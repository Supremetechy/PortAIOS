/**
 * SpatialEnvironmentRenderer
 * Cyberpunk corridor background environment — designed to composite
 * behind BinaryAvatarRenderer via layered <canvas> elements.
 *
 * Layers (near → far):
 *  - Floor / ceiling perspective-scrolling grids
 *  - Side wall grids
 *  - Vertical data-stream columns
 *  - Horizon glow planes
 *  - Vanishing-point light shaft
 *
 * Mirrors the BinaryAvatarRenderer public API:
 *   setState(obj)   setActivity(str)   setVolume(num)
 *   setEmotion(str) setFrequencyData(arr)
 *   onResize()      destroy()
 *
 * Activity values: 'idle' | 'thinking' | 'speaking' | 'error'
 *
 * Usage
 * ─────
 *   // mount env FIRST so avatar sits on top
 *   const envEl   = document.getElementById('env');
 *   const avatarEl = document.getElementById('avatar');
 *
 *   // both containers must be position:absolute inside a position:relative wrapper
 *   const env    = new SpatialEnvironmentRenderer(envEl, { colorPalette: 'matrix' });
 *   const avatar = new BinaryAvatarRenderer(avatarEl, { colorPalette: 'matrix' });
 *
 *   // drive both from one call
 *   env.setActivity('speaking');
 *   avatar.setActivity('speaking');
 */

import * as THREE from 'https://esm.sh/three@0.160.0';
import { EffectComposer } from 'https://esm.sh/three@0.160.0/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass }     from 'https://esm.sh/three@0.160.0/examples/jsm/postprocessing/RenderPass.js';
import { ShaderPass }     from 'https://esm.sh/three@0.160.0/examples/jsm/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'https://esm.sh/three@0.160.0/examples/jsm/postprocessing/UnrealBloomPass.js';

// ── Palette registry ────────────────────────────────────────────────────────
const PALETTES = {
  'matrix':        { primary: [0.0, 1.0, 0.0],   accent: [0.0, 0.6, 0.0],   fog: 0x001a00, sky: 0x000800 },
  'cyan':          { primary: [0.0, 1.0, 1.0],   accent: [0.0, 0.5, 0.8],   fog: 0x00121a, sky: 0x000510 },
  'amber':         { primary: [1.0, 0.75, 0.0],  accent: [0.8, 0.4, 0.0],   fog: 0x1a0d00, sky: 0x080400 },
  'cyber-magenta': { primary: [1.0, 0.0, 1.0],   accent: [0.6, 0.0, 0.8],   fog: 0x12001a, sky: 0x070010 },
  'ice':           { primary: [0.6, 0.85, 1.0],  accent: [0.3, 0.6, 0.9],   fog: 0x060c14, sky: 0x020508 },
  'gold':          { primary: [1.0, 0.84, 0.0],  accent: [0.7, 0.5, 0.0],   fog: 0x140e00, sky: 0x070500 },
  'red':           { primary: [1.0, 0.0, 0.0],   accent: [0.6, 0.0, 0.0],   fog: 0x1a0000, sky: 0x080000 },
};

class SpatialEnvironmentRenderer {
  constructor(container, options = {}) {
    this.container = container;

    this.options = {
      colorPalette:    options.colorPalette    || 'matrix',
      streamCount:     options.streamCount     || 28,
      enableBloom:     options.enableBloom     !== false,
      enableCRT:       options.enableCRT       !== false,
      enableHoloScan:  options.enableHoloScan  !== false,
      bloomStrength:   options.bloomStrength   || 1.1,
      ...options,
    };

    this.state = {
      emotion:   'neutral',
      activity:  'idle',
      volume:    0.0,
      cpuLoad:   0.0,
      frequency: new Float32Array(128),
    };

    this._palette    = PALETTES[this.options.colorPalette] || PALETTES['matrix'];
    this._time       = 0;
    this._speed      = 1.0;
    this._animId     = null;
    this._allMats    = [];   // every material that owns uColor / uAccent
    this._streamMats = [];

    this._init();
  }

  // ── Internal helpers ──────────────────────────────────────────────────────

  _v3(r, g, b)  { return new THREE.Vector3(r, g, b); }
  _pv3()        { return this._v3(...this._palette.primary); }
  _av3()        { return this._v3(...this._palette.accent);  }
  _actVal()     {
    return { idle: 0, thinking: 1, speaking: 2, error: 3 }[this.state.activity] || 0;
  }

  _track(mat) { this._allMats.push(mat); return mat; }

  // ── Bootstrap ─────────────────────────────────────────────────────────────

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

    // Scene & camera
    this._scene = new THREE.Scene();
    this._scene.fog = new THREE.FogExp2(this._palette.fog, 0.045);

    this._camera = new THREE.PerspectiveCamera(62, W / H, 0.1, 200);
    this._camera.position.set(0, 0.2, 5);
    this._camera.lookAt(0, 0, 0);

    // Renderer
    this._renderer = new THREE.WebGLRenderer({
      antialias: false,
      alpha: true,
      powerPreference: 'high-performance',
    });
    this._renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this._renderer.setSize(W, H);
    this._renderer.setClearColor(this._palette.sky || 0x000000, 1);
    this.container.appendChild(this._renderer.domElement);

    // Geometry layers
    this._floorMat  = this._makeFloorGrid(false);
    this._ceilMat   = this._makeFloorGrid(true);
    this._wallMatL  = this._makeWallGrid(-1);
    this._wallMatR  = this._makeWallGrid(1);
    this._streamMats = this._makeDataStreams();
    this._horizMat  = this._makeHorizonGlow();
    this._shaftMat  = this._makeLightShaft();

    // Post-processing
    this._setupPostFX(W, H);

    // Resize listener
    this._onResize = () => this.onResize();
    window.addEventListener('resize', this._onResize);

    this._animate();
  }

  // ── Floor / ceiling grid ──────────────────────────────────────────────────

  _makeFloorGrid(isCeiling) {
    const mat = this._track(new THREE.ShaderMaterial({
      uniforms: {
        uTime:   { value: 0 },
        uColor:  { value: this._pv3() },
        uAccent: { value: this._av3() },
        uSpeed:  { value: 1.0 },
      },
      vertexShader: /* glsl */`
        varying vec2 vUv;
        varying float vDepth;
        void main(){
          vUv = uv;
          vec4 mvp = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          vDepth = mvp.z / mvp.w;
          gl_Position = mvp;
        }`,
      fragmentShader: /* glsl */`
        uniform float uTime;
        uniform vec3  uColor;
        uniform vec3  uAccent;
        uniform float uSpeed;
        varying vec2  vUv;
        varying float vDepth;

        float grid(vec2 uv, float scale, float width){
          vec2 g = abs(fract(uv * scale - 0.5) - 0.5) / fwidth(uv * scale);
          return 1.0 - min(min(g.x, g.y), 1.0);
        }
        void main(){
          vec2 scrollUv = vec2(vUv.x, vUv.y + uTime * uSpeed * 0.04);
          float g1 = grid(scrollUv, 8.0,  0.5) * 0.9;
          float g2 = grid(scrollUv, 40.0, 0.3) * 0.4;
          float fade = pow(1.0 - vUv.y, 2.5) * smoothstep(0.0, 0.15, vUv.y);
          vec3  col  = (uColor * g1 + uAccent * g2) * fade;
          float alpha = (g1 + g2) * fade;
          gl_FragColor = vec4(col, alpha);
        }`,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    }));

    const geo  = new THREE.PlaneGeometry(60, 80, 1, 1);
    const mesh = new THREE.Mesh(geo, mat);
    mesh.rotation.x = isCeiling ? Math.PI / 2 : -Math.PI / 2;
    mesh.position.set(0, isCeiling ? 2.4 : -1.55, -35);
    this._scene.add(mesh);
    return mat;
  }

  // ── Side wall grids ───────────────────────────────────────────────────────

  _makeWallGrid(side /* -1 = left, +1 = right */) {
    const mat = this._track(new THREE.ShaderMaterial({
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
          vec2  suv  = vec2(vUv.x, vUv.y + uTime * uSpeed * 0.04);
          float g    = grid(suv, 6.0);
          float hFade = smoothstep(0.0, 0.12, 1.0 - vUv.x) * smoothstep(0.0, 0.08, vUv.x);
          float vFade = smoothstep(0.0, 0.10, vUv.y) * smoothstep(0.0, 0.10, 1.0 - vUv.y);
          vec3  col  = uColor * g * hFade * vFade * 0.55;
          gl_FragColor = vec4(col, g * hFade * vFade * 0.55);
        }`,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    }));

    const geo  = new THREE.PlaneGeometry(80, 5, 1, 1);
    const mesh = new THREE.Mesh(geo, mat);
    mesh.rotation.y = side === 1 ? -Math.PI / 2 : Math.PI / 2;
    mesh.position.set(side * 6.5, 0.42, -35);
    this._scene.add(mesh);
    return mat;
  }

  // ── Data-stream columns ───────────────────────────────────────────────────

  _makeDataStreams() {
    const mats = [];
    const count = this.options.streamCount;

    for (let i = 0; i < count; i++) {
      const x     = (Math.random() - 0.5) * 18;
      const z     = -5 - Math.random() * 70;
      const speed = 0.4 + Math.random() * 1.6;
      const phase = Math.random() * Math.PI * 2;

      const mat = this._track(new THREE.ShaderMaterial({
        uniforms: {
          uTime:  { value: 0 },
          uColor: { value: this._pv3() },
          uSpeed: { value: speed },
          uPhase: { value: phase },
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
            float t   = uTime * uSpeed + uPhase;
            float row = floor((vUv.y + t) * 18.0);
            float col = floor(vUv.x * 3.0);
            float ch  = hash(row + col * 100.0);

            float bright = step(0.3, ch)
              * smoothstep(0.0, 0.06, fract(vUv.x * 3.0) - 0.03)
              * smoothstep(0.0, 0.06, 1.0 - fract(vUv.x * 3.0) - 0.03);

            // head glow
            float fy = fract(vUv.y + t);
            bright  *= 0.2 + 0.8 * smoothstep(0.0, 0.35, fy) * smoothstep(1.0, 0.55, fy);

            gl_FragColor = vec4(uColor * bright, bright * 0.55);
          }`,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }));

      const h    = 3.5 + Math.random() * 4;
      const geo  = new THREE.PlaneGeometry(0.18, h);
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(x, (Math.random() - 0.5) * 2, z);
      mesh.rotation.y = (Math.random() - 0.5) * 0.6;
      this._scene.add(mesh);
      mats.push(mat);
    }

    return mats;
  }

  // ── Horizon glow ──────────────────────────────────────────────────────────

  _makeHorizonGlow() {
    const mat = this._track(new THREE.ShaderMaterial({
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

    // near horizon line
    const m1 = new THREE.Mesh(geo, mat);
    m1.position.set(0, -1.55, -3);
    this._scene.add(m1);

    // deep horizon line
    const m2 = new THREE.Mesh(geo.clone(), mat);
    m2.position.set(0, -1.55, -20);
    this._scene.add(m2);

    return mat;
  }

  // ── Vanishing-point light shaft ───────────────────────────────────────────

  _makeLightShaft() {
    const mat = this._track(new THREE.ShaderMaterial({
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

  // ── Post-processing ───────────────────────────────────────────────────────

  _setupPostFX(W, H) {
    this._composer = new EffectComposer(this._renderer);
    this._composer.addPass(new RenderPass(this._scene, this._camera));

    if (this.options.enableBloom) {
      this._bloomPass = new UnrealBloomPass(
        new THREE.Vector2(W, H),
        this.options.bloomStrength, 0.5, 0.75
      );
      this._composer.addPass(this._bloomPass);
    }

    if (this.options.enableCRT) {
      this._crtPass = new ShaderPass({
        uniforms: {
          tDiffuse:  { value: null },
          uTime:     { value: 0 },
          uActivity: { value: 0 },
        },
        vertexShader: /* glsl */`
          varying vec2 vUv;
          void main(){
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }`,
        fragmentShader: /* glsl */`
          uniform sampler2D tDiffuse;
          uniform float uTime;
          uniform float uActivity;
          varying vec2 vUv;

          float rand(vec2 st){ return fract(sin(dot(st, vec2(12.9898, 78.233))) * 43758.5453); }

          void main(){
            float ab  = uActivity == 3.0 ? 0.006 : 0.0018;
            vec2  dir = vUv - 0.5;
            float r = texture2D(tDiffuse, vUv + dir * ab).r;
            float g = texture2D(tDiffuse, vUv).g;
            float b = texture2D(tDiffuse, vUv - dir * ab).b;
            vec3  col = vec3(r, g, b);

            // scanlines
            col -= sin(vUv.y * 900.0) * 0.04;
            // film grain
            col += rand(vUv + fract(uTime)) * 0.025 - 0.012;
            // vignette
            vec2 c = vUv - 0.5;
            col  *= 1.0 - dot(c, c) * 0.45;

            // error glitch band
            if (uActivity == 3.0){
              float band = step(0.99, rand(vec2(floor(vUv.y * 60.0 + uTime * 30.0), 0.0)));
              col = mix(col, vec3(1.0, 0.0, 0.0) * col.g * 2.0, band * 0.6);
            }
            gl_FragColor = vec4(col, 1.0);
          }`,
      });
      this._crtPass.renderToScreen = true;
      this._composer.addPass(this._crtPass);
    }
  }

  // ── Animation loop ────────────────────────────────────────────────────────

  _animate() {
    this._animId = requestAnimationFrame(() => this._animate());

    this._time += 0.016;
    const t   = this._time;
    const act = this._actVal();

    // ── Camera motion ──
    this._camera.rotation.z = Math.sin(t * 0.18) * 0.04;
    this._camera.position.y = 0.2 + Math.sin(t * 0.22) * 0.05;

    if (act === 2 /* speaking */) {
      this._camera.position.y += Math.sin(t * 6) * 0.012;
    }
    if (act === 3 /* error */) {
      this._camera.position.x = Math.sin(t * 30) * 0.04;
    } else {
      this._camera.position.x += (0 - this._camera.position.x) * 0.1;
    }
    if (act === 1 /* thinking */) {
      this._camera.position.x = Math.sin(t * 0.4) * 0.3;
    }

    // ── Bloom response ──
    if (this._bloomPass) {
      const targets = [1.1, 1.3, 1.6, 2.0];
      this._bloomPass.strength += (targets[act] - this._bloomPass.strength) * 0.08;
    }

    // ── Uniform updates ──
    const speed = this._speed;

    this._floorMat.uniforms.uTime.value  = t;
    this._floorMat.uniforms.uSpeed.value = speed;
    this._ceilMat.uniforms.uTime.value   = t;
    this._ceilMat.uniforms.uSpeed.value  = speed;
    this._wallMatL.uniforms.uTime.value  = t;
    this._wallMatL.uniforms.uSpeed.value = speed;
    this._wallMatR.uniforms.uTime.value  = t;
    this._wallMatR.uniforms.uSpeed.value = speed;

    this._horizMat.uniforms.uTime.value     = t;
    this._shaftMat.uniforms.uTime.value     = t;
    this._shaftMat.uniforms.uActivity.value = act;

    this._streamMats.forEach(m => { m.uniforms.uTime.value = t; });

    if (this._crtPass) {
      this._crtPass.uniforms.uTime.value     = t;
      this._crtPass.uniforms.uActivity.value = act;
    }

    this._composer.render();
  }

  // ── Palette hot-swap ──────────────────────────────────────────────────────

  _applyPalette() {
    const p = this._palette;
    this._scene.fog.color.setHex(p.fog);
    this._renderer.setClearColor(p.sky || 0x000000, 1);

    this._allMats.forEach(m => {
      if (m.uniforms.uColor)  m.uniforms.uColor.value  = this._pv3();
      if (m.uniforms.uAccent) m.uniforms.uAccent.value = this._av3();
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Public API — mirrors BinaryAvatarRenderer
  // ═══════════════════════════════════════════════════════════════════════════

  /**
   * Batch-update state. Accepts any subset of:
   *   { emotion, activity, volume, cpuLoad, frequency }
   */
  setState(newState) {
    Object.assign(this.state, newState);
  }

  /** 'neutral' | 'happy' | 'focused' | … (reserved for future visual hooks) */
  setEmotion(emotion) {
    this.state.emotion = emotion;
  }

  /** 'idle' | 'thinking' | 'speaking' | 'error' */
  setActivity(activity) {
    this.state.activity = activity;
  }

  /** 0.0 – 1.0. Drives light-shaft pulse when speaking. */
  setVolume(volume) {
    this.state.volume = Math.max(0, Math.min(1, volume));
  }

  /** Float32Array of frequency bins (matches Web Audio AnalyserNode output). */
  setFrequencyData(frequencyArray) {
    this.state.frequency = frequencyArray;
  }

  /**
   * Switch colour palette at runtime.
   * @param {string} name — one of 'matrix' | 'cyan' | 'amber' | 'cyber-magenta' | 'ice' | 'gold' | 'red'
   */
  setColorPalette(name) {
    const p = PALETTES[name];
    if (!p) { console.warn(`SpatialEnvironmentRenderer: unknown palette "${name}"`); return; }
    this._palette = p;
    this._applyPalette();
  }

  /**
   * Scroll speed multiplier (default 1.0).
   * Useful to match avatar speech cadence.
   */
  setSpeed(speed) {
    this._speed = Math.max(0, speed);
  }

  /** Call on container resize (or let the built-in window listener handle it). */
  onResize() {
    const W = this.container.clientWidth;
    const H = this.container.clientHeight;
    if (!W || !H || !this._camera || !this._renderer || !this._composer) return;
    this._camera.aspect = W / H;
    this._camera.updateProjectionMatrix();
    this._renderer.setSize(W, H);
    this._composer.setSize(W, H);
  }

  /** Tear down renderer, geometries, and event listeners. */
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

    if (this._renderer) {
      this._renderer.dispose();
      if (this._renderer.domElement.parentNode) {
        this._renderer.domElement.parentNode.removeChild(this._renderer.domElement);
      }
    }

    window.removeEventListener('resize', this._onResize);
  }
}

export { SpatialEnvironmentRenderer };
