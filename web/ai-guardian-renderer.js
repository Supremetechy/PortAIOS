/**
 * AIGuardianRenderer — Three.js particle-system avatar
 *
 * Samples AI-Guardian.jpg pixel-by-pixel and builds a cloud of ~20 000
 * glowing neon particles that form the guardian's shape.  Every particle
 * floats independently, reacts to voice volume, and the eye / mouth
 * regions animate with blinking and lipsync — identical in spirit to the
 * original binary-avatar.js digit-particle renderer.
 *
 * Drop-in replacement: same constructor signature + full public API as
 * HolographicFaceRenderer / BinaryAvatarRenderer.
 */

import * as THREE from 'three';

// ─── Palette table (0–1 float RGB) ───────────────────────────────────────────
const PALETTES = {
    'matrix':        { r: 0.000, g: 1.000, b: 0.616 },
    'cyan':          { r: 0.000, g: 0.961, b: 1.000 },
    'amber':         { r: 1.000, g: 0.769, b: 0.000 },
    'cyber-magenta': { r: 1.000, g: 0.000, b: 0.502 },
    'ice':           { r: 0.690, g: 0.878, b: 1.000 },
    'red':           { r: 1.000, g: 0.090, b: 0.267 },
};

// ─── Activity config ──────────────────────────────────────────────────────────
const ACTIVITY = {
    idle:         { glowMult: 1.00, oscSpeed: 1.0, turbulence: 0.00, scanSpeed: 0.07 },
    listening:    { glowMult: 1.50, oscSpeed: 1.3, turbulence: 0.00, scanSpeed: 0.11 },
    thinking:     { glowMult: 1.25, oscSpeed: 2.8, turbulence: 0.60, scanSpeed: 0.24 },
    speaking:     { glowMult: 1.40, oscSpeed: 1.5, turbulence: 0.00, scanSpeed: 0.09 },
    initializing: { glowMult: 1.00, oscSpeed: 2.0, turbulence: 0.25, scanSpeed: 0.18 },
    alert:        { glowMult: 2.00, oscSpeed: 4.0, turbulence: 1.00, scanSpeed: 0.28 },
    error:        { glowMult: 2.00, oscSpeed: 4.0, turbulence: 1.00, scanSpeed: 0.28 },
    background:   { glowMult: 0.55, oscSpeed: 0.5, turbulence: 0.00, scanSpeed: 0.04 },
};

// ─── Vertex shader ────────────────────────────────────────────────────────────
// Each particle = one sampled pixel.
// aOffset:  random phase [0, 2π] — keeps particles out of sync
// aRegion:  0 = body, 1 = eye area, 2 = mouth area
// aBase:    base position at rest (same as position attribute)
const VERT = /* glsl */`
attribute float aOffset;
attribute float aRegion;
attribute float aSize;

uniform float uTime;
uniform float uOscSpeed;   // activity-driven oscillation rate
uniform float uGlowMult;   // activity-driven brightness/size boost
uniform float uTurbulence; // 0–1 glitch amplitude (thinking/alert)
uniform float uVolume;     // 0–1 speaking volume
uniform float uJawOpen;    // 0–1 mouth open
uniform float uBlink;      // 0–1 both eyes
uniform float uWink;       // 0–1 right eye
uniform float uSurprise;   // 0–1 eyebrow / eye size

// 3D rest positions for face feature centres (Y = UV v - 0.5)
//   eye Y  :  0.862 UV → y =  0.362
//   mouth Y:  0.800 UV → y =  0.300
const float EYE_CY   =  0.362;
const float MOUTH_CY =  0.300;

varying float vAlpha;

void main() {
    vec3 pos = position;    // rest position baked in at build time

    // ── Global oscillation: every particle floats gently ─────────────────
    float t    = uTime * uOscSpeed;
    float sinP = sin(t * 0.9 + aOffset);
    float cosP = cos(t * 0.65 + aOffset * 1.37);
    float amp  = 0.007 * uGlowMult;
    pos.y += sinP * amp;
    pos.x += cosP * amp * 0.55;

    // ── Turbulence (thinking / alert): random lateral jitter ─────────────
    if (uTurbulence > 0.0) {
        float jitterX = sin(t * 6.3 + aOffset * 4.1) * 0.022 * uTurbulence;
        float jitterY = cos(t * 5.1 + aOffset * 3.7) * 0.018 * uTurbulence;
        pos.x += jitterX;
        pos.y += jitterY;
    }

    // ── Eye blink: compress eye particles toward eye-centre Y ─────────────
    if (aRegion == 1.0) {
        float closeLeft  = uBlink;
        float closeRight = max(uBlink, uWink);
        // Left/right split: left eye particles have x < 0 (image centre)
        float closeAmt = (pos.x < 0.0) ? closeLeft : closeRight;
        float surpExt  = uSurprise * 0.008;  // surprise pushes eye particles outward
        pos.y = mix(pos.y, EYE_CY, closeAmt * 0.80);
        pos.y += surpExt * sign(pos.y - EYE_CY);
    }

    // ── Mouth open: lower particles drop, upper lift ───────────────────────
    if (aRegion == 2.0 && uJawOpen > 0.01) {
        float below = step(pos.y, MOUTH_CY);  // 1 = below lip, 0 = above
        pos.y -= uJawOpen * 0.045 * below;
        pos.y += uJawOpen * 0.012 * (1.0 - below);
    }

    // ── Speaking pulse: expand all particles slightly with volume ──────────
    if (uVolume > 0.02) {
        vec2 fromCentre = pos.xy;
        pos.xy += fromCentre * uVolume * 0.018;
    }

    // ── Point size ────────────────────────────────────────────────────────
    float baseSize  = aSize * 2.8 * uGlowMult;
    float speakSize = baseSize * (1.0 + uVolume * 0.55);
    gl_PointSize = max(1.0, speakSize);

    vAlpha      = (aSize / 3.0) * min(1.0, uGlowMult * 0.95);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
}
`;

// ─── Fragment shader ──────────────────────────────────────────────────────────
// Draws each particle as a soft glowing disc.
const FRAG = /* glsl */`
precision highp float;

uniform vec3  uPalette;
uniform float uGlowMult;
uniform float uTime;        // drives scanline pass-through on particles
uniform float uScanY;       // 0–1 scan Y position

varying float vAlpha;

void main() {
    // Circular mask
    vec2  cxy = 2.0 * gl_PointCoord - 1.0;
    float r   = dot(cxy, cxy);
    if (r > 1.0) discard;

    // Soft glow: bright centre, fading edge
    float glow = exp(-r * 2.4) * vAlpha;

    // Scan-line brightening: particles near the sweep line glow extra
    // gl_FragCoord gives screen pixel position; we compare normalised Y.
    // Use a rough proxy: add a time-based global shimmer instead
    float shimmer = sin(uTime * 2.1 + r * 8.0) * 0.5 + 0.5;
    float finalA  = glow * (0.88 + shimmer * 0.18 * uGlowMult);

    gl_FragColor  = vec4(uPalette * (glow * 1.6 + 0.15), finalA);
}
`;

// ─────────────────────────────────────────────────────────────────────────────

export class AIGuardianRenderer {

    constructor(container, options = {}) {
        this.container = container;
        this.options   = {
            colorPalette:    options.colorPalette || options.palette || 'cyan',
            enableCRT:       options.enableCRT       !== false,
            enableChromatic: options.enableChromatic !== false,
            enableBloom:     options.enableBloom     !== false,
            enableHoloScan:  options.enableHoloScan  !== false,
        };

        // Public state — read externally by HUD intervals
        this.state = {
            emotion:   'neutral',
            activity:  'idle',
            volume:    0.0,
            cpuLoad:   0.0,
            frequency: new Float32Array(128),
            jawOpen:   0.0,
        };

        this._cust = {
            smile:        0.0,
            frown:        0.0,
            surprise:     0.0,
            wink:         0.0,
            viseme:       0.5,
            subdivisions: 4,
            skinColor:    [216, 184, 153],
        };

        this._destroyed    = false;
        this._animId       = null;
        this._T            = 0;
        this._prevTs       = null;
        this._speed        = 1.0;
        this._mouthT       = 0;
        this._scanY        = 0;
        this._oscSpeed     = 1.0;
        this._turbulence   = 0.0;
        this._imgAspect    = 0.5714;

        // Blink state
        this._blinkClock  = 0;
        this._nextBlink   = 3000 + Math.random() * 4500;
        this._blinking    = false;
        this._blinkPhase  = 0;
        this._blinkVal    = 0;

        this._initThree();
        this._loadAndBuild();
        this._startLoop();
    }

    // ── Three.js setup ────────────────────────────────────────────────────────

    _initThree() {
        const W = this.container.clientWidth  || window.innerWidth;
        const H = this.container.clientHeight || window.innerHeight;

        this.renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setSize(W, H);
        this.renderer.setClearColor(0x000000, 0);

        Object.assign(this.renderer.domElement.style, {
            display:  'block',
            position: 'absolute',
            inset:    '0',
            width:    '100%',
            height:   '100%',
        });
        this.container.appendChild(this.renderer.domElement);
        this.canvas = this.renderer.domElement;

        // Orthographic camera: frustum height = 1, width = screen aspect
        const screenAspect = W / H;
        this.camera = new THREE.OrthographicCamera(
            -screenAspect / 2,  screenAspect / 2,
             0.5,               -0.5,
             0.01,               10
        );
        this.camera.position.z = 1;

        this.scene = new THREE.Scene();

        // Uniforms shared across all geometry
        const pal = PALETTES[this.options.colorPalette] || PALETTES.cyan;
        this.uniforms = {
            uTime:       { value: 0 },
            uPalette:    { value: new THREE.Vector3(pal.r, pal.g, pal.b) },
            uOscSpeed:   { value: 1.0 },
            uGlowMult:   { value: 1.0 },
            uTurbulence: { value: 0.0 },
            uVolume:     { value: 0.0 },
            uJawOpen:    { value: 0.0 },
            uBlink:      { value: 0.0 },
            uWink:       { value: 0.0 },
            uSurprise:   { value: 0.0 },
            uScanY:      { value: 0.0 },
        };

        this._ro = new ResizeObserver(() => this._resize());
        this._ro.observe(this.container);
    }

    // ── Image sampling ────────────────────────────────────────────────────────
    // Draws the image to an offscreen canvas, reads pixels, and creates a
    // BufferGeometry where each bright pixel becomes one particle.

    _loadAndBuild() {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.src = '/assets/AI-Guardian.jpg';
        img.onload = () => {
            this._imgAspect = img.naturalWidth / img.naturalHeight;
            const data = this._samplePixels(img);
            if (data && data.count > 0) {
                this._buildParticles(data);
            } else {
                this._buildFallbackParticles();
            }
            this._resize();
        };
        img.onerror = () => {
            console.warn('[AIGuardian] Image failed to load; using fallback particles');
            this._buildFallbackParticles();
        };
    }

    _samplePixels(img) {
        const IW     = img.naturalWidth;
        const IH     = img.naturalHeight;
        const aspect = IW / IH;
        const stride = 3;  // sample every 3rd pixel → ~85 000 candidates

        // Offscreen canvas to read pixel data
        const cv  = document.createElement('canvas');
        cv.width  = IW;
        cv.height = IH;
        const ctx = cv.getContext('2d');
        ctx.drawImage(img, 0, 0);
        const px = ctx.getImageData(0, 0, IW, IH).data;

        // Pre-allocate (max possible particles)
        const maxP = Math.ceil(IW / stride) * Math.ceil(IH / stride);
        const pos  = new Float32Array(maxP * 3);
        const size = new Float32Array(maxP);
        const off  = new Float32Array(maxP);
        const reg  = new Float32Array(maxP);

        let count = 0;

        for (let py = 0; py < IH; py += stride) {
            for (let px_  = 0; px_ < IW; px_ += stride) {
                const i   = (py * IW + px_) * 4;
                const r   = px[i]   / 255;
                const g   = px[i+1] / 255;
                const b   = px[i+2] / 255;
                const lum = r * 0.299 + g * 0.587 + b * 0.114;

                if (lum < 0.09) continue;  // skip dark background

                // UV: u left→right, v bottom→top (Three.js convention)
                const u = px_  / IW;
                const v = 1 - py / IH;  // flip Y

                // World-space position (ortho, image fills height ±0.5)
                const wx = (u - 0.5) * aspect;
                const wy =  v - 0.5;
                const wz = (Math.random() - 0.5) * 0.015;  // thin depth band

                pos[count * 3]     = wx;
                pos[count * 3 + 1] = wy;
                pos[count * 3 + 2] = wz;

                // Size from luminance: brighter pixels → larger particle
                size[count] = lum * 2.2 + 0.4;

                // Random phase offset for oscillation desynchronisation
                off[count] = Math.random() * Math.PI * 2;

                // Region: 1 = eye zone, 2 = mouth zone, 0 = body
                const dEyeL = Math.hypot((u - 0.438) / 0.065,
                                         (v - 0.862) / (0.065 * aspect * 0.72));
                const dEyeR = Math.hypot((u - 0.562) / 0.065,
                                         (v - 0.862) / (0.065 * aspect * 0.72));
                let region  = 0;
                if (dEyeL < 1 || dEyeR < 1) region = 1;
                else if (Math.abs(u - 0.50) < 0.065 && Math.abs(v - 0.800) < 0.042) region = 2;
                reg[count] = region;

                count++;
            }
        }

        return { pos, size, off, reg, count };
    }

    _buildParticles({ pos, size, off, reg, count }) {
        if (this.points) {
            this.scene.remove(this.points);
            this.points.geometry.dispose();
            this.points.material.dispose();
        }

        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(pos.subarray(0, count * 3), 3));
        geo.setAttribute('aSize',    new THREE.BufferAttribute(size.subarray(0, count), 1));
        geo.setAttribute('aOffset',  new THREE.BufferAttribute(off.subarray(0, count), 1));
        geo.setAttribute('aRegion',  new THREE.BufferAttribute(reg.subarray(0, count), 1));

        const mat = new THREE.ShaderMaterial({
            uniforms:       this.uniforms,
            vertexShader:   VERT,
            fragmentShader: FRAG,
            transparent:    true,
            depthWrite:     false,
            blending:       THREE.AdditiveBlending,
        });

        this.points = new THREE.Points(geo, mat);
        this.scene.add(this.points);

        console.log(`[AIGuardian] ${count.toLocaleString()} particles built`);
    }

    // Simple animated sphere of particles as fallback when image is unavailable
    _buildFallbackParticles() {
        const N   = 6000;
        const pos = new Float32Array(N * 3);
        const sz  = new Float32Array(N);
        const off = new Float32Array(N);
        const reg = new Float32Array(N);

        for (let i = 0; i < N; i++) {
            const theta = Math.random() * Math.PI * 2;
            const phi   = Math.acos(2 * Math.random() - 1);
            const r     = 0.18 + Math.random() * 0.06;
            pos[i*3]     = r * Math.sin(phi) * Math.cos(theta) * this._imgAspect;
            pos[i*3+1]   = r * Math.cos(phi);
            pos[i*3+2]   = r * Math.sin(phi) * Math.sin(theta) * 0.2;
            sz[i]  = 0.8 + Math.random() * 1.4;
            off[i] = Math.random() * Math.PI * 2;
        }

        this._buildParticles({ pos, size: sz, off, reg, count: N });
    }

    _resize() {
        if (this._destroyed) return;
        const W = this.container.clientWidth  || window.innerWidth;
        const H = this.container.clientHeight || window.innerHeight;
        if (!W || !H) return;

        this.renderer.setSize(W, H);

        const screenAspect = W / H;
        this.camera.left   = -screenAspect / 2;
        this.camera.right  =  screenAspect / 2;
        this.camera.top    =  0.5;
        this.camera.bottom = -0.5;
        this.camera.updateProjectionMatrix();
    }

    // ── Render loop ───────────────────────────────────────────────────────────

    _startLoop() {
        const tick = (ts) => {
            if (this._destroyed) return;
            const dt = this._prevTs !== null
                ? Math.min((ts - this._prevTs) / 1000, 0.05) * this._speed
                : 0;
            this._prevTs = ts;
            this._T += dt;
            this._update(dt);
            this.renderer.render(this.scene, this.camera);
            this._animId = requestAnimationFrame(tick);
        };
        this._animId = requestAnimationFrame(tick);
    }

    _update(dt) {
        const act = this.state.activity;
        const cfg = ACTIVITY[act] || ACTIVITY.idle;

        // Scan line (passed as uniform for future use)
        this._scanY = (this._scanY + cfg.scanSpeed * dt) % 1.0;

        // Smooth activity-driven parameters
        this._oscSpeed   = this._oscSpeed   * 0.92 + cfg.oscSpeed   * 0.08;
        this._turbulence = this._turbulence * 0.90 + cfg.turbulence * 0.10;

        // Mouth oscillation
        if (act === 'speaking') {
            this._mouthT += dt * 0.19;
        } else {
            this._mouthT       *= 0.90;
            this.state.jawOpen *= 0.88;
        }

        // Blink
        this._blinkClock += dt * 1000;
        if (!this._blinking && this._blinkClock >= this._nextBlink) {
            this._blinking   = true;
            this._blinkPhase = 0;
            this._blinkClock = 0;
            this._nextBlink  = 3000 + Math.random() * 4500;
        }
        if (this._blinking) {
            this._blinkPhase += dt * 12;
            this._blinkVal    = Math.sin(Math.min(Math.PI, this._blinkPhase));
            if (this._blinkPhase >= Math.PI) { this._blinking = false; this._blinkVal = 0; }
        }

        // Viseme-driven jaw
        const visGain = this._cust.viseme || 0.5;
        let jaw = this.state.jawOpen;
        if (act === 'speaking') {
            jaw = Math.max(jaw,
                Math.abs(Math.sin(this._mouthT * 0.88))
                * this.state.volume * (visGain * 2) * 0.70);
        }

        // Push to uniforms
        const pal = PALETTES[this.options.colorPalette] || PALETTES.cyan;
        this.uniforms.uTime.value       = this._T;
        this.uniforms.uPalette.value.set(pal.r, pal.g, pal.b);
        this.uniforms.uOscSpeed.value   = this._oscSpeed;
        this.uniforms.uGlowMult.value   = cfg.glowMult;
        this.uniforms.uTurbulence.value = this._turbulence;
        this.uniforms.uVolume.value     = this.state.volume;
        this.uniforms.uJawOpen.value    = Math.min(1, jaw);
        this.uniforms.uBlink.value      = this._blinkVal;
        this.uniforms.uWink.value       = this._cust.wink    || 0;
        this.uniforms.uSurprise.value   = this._cust.surprise || 0;
        this.uniforms.uScanY.value      = this._scanY;
    }

    // ── Public API ────────────────────────────────────────────────────────────

    setState(s) {
        if (typeof s === 'string') this.state.activity = s;
        else Object.assign(this.state, s);
        return this;
    }

    setActivity(a)      { this.state.activity = a;                              return this; }
    setEmotion(e)       { this.state.emotion  = e;                              return this; }
    setColorPalette(n)  { if (PALETTES[n]) this.options.colorPalette = n;       return this; }
    setFrequencyData(a) { this.state.frequency = a;                             return this; }
    setSpeed(n)         { this._speed = n;                                      return this; }
    onResize()          { this._resize();                                       return this; }

    setVolume(v) {
        this.state.volume = Math.max(0, Math.min(1, v));
        if (this.state.activity === 'speaking') this.state.jawOpen = this.state.volume;
        return this;
    }

    setCustomization(obj) { Object.assign(this._cust, obj); return this; }
    getCustomization()    { return { ...this._cust }; }

    destroy() {
        this._destroyed = true;
        if (this._animId) cancelAnimationFrame(this._animId);
        this._ro?.disconnect();
        this.points?.geometry.dispose();
        this.points?.material.dispose();
        this.renderer?.dispose();
    }
}

// Drop-in alias — all existing imports of BinaryAvatarRenderer still work
export { AIGuardianRenderer as BinaryAvatarRenderer };
