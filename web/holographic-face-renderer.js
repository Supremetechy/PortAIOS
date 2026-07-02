/**
 * HolographicFaceRenderer
 * ─────────────────────────────────────────────────────────────────────────────
 * Canvas-2D holographic human face renderer.
 * Exported as `BinaryAvatarRenderer` for zero-change drop-in compatibility
 * with avatar-integration.html.
 *
 * Public API (mirrors BinaryAvatarRenderer):
 *   setState(strOrObj)    setActivity(str)    setEmotion(str)
 *   setVolume(num)        setColorPalette(name)   setFrequencyData(arr)
 *   setSpeed(num)         setCustomization(obj)    onResize()          destroy()
 *   state.emotion  state.volume  state.activity
 *   options.enableCRT  options.enableChromatic  options.enableBloom
 */

export class BinaryAvatarRenderer {

  // ── Constructor ─────────────────────────────────────────────────────────────
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      enableCRT:       options.enableCRT       !== false,
      enableChromatic: options.enableChromatic !== false,
      enableBloom:     options.enableBloom     !== false,
      colorPalette:    options.colorPalette    || options.palette || 'cyan',
    };

    // Public state (read externally by HUD update intervals)
    this.state = {
      emotion:   'neutral',
      activity:  'idle',
      volume:    0.0,
      cpuLoad:   0.0,
      frequency: new Float32Array(128),
      jawOpen:   0.0,
    };

    // Internal
    this._destroyed  = false;
    this._animId     = null;
    this._T          = 0;
    this._prevT      = 0;
    this._speed      = 1.0;
    this._avState    = 'idle';
    this._col        = { r: 0, g: 255, b: 255 };
    this._targetCol  = { r: 0, g: 255, b: 255 };
    this._isSpeaking = false;
    this._mouthT     = 0;
    this._blinkPhase = 0;
    this._blinking   = false;
    this._nextBlink  = 3500 + Math.random() * 3500;
    this._blinkClock = 0;
    this._orbitAngle = 0;
    this._customization = {
      smile: 0.5,
      frown: 0.0,
      surprise: 0.0,
      wink: 0.0,
      viseme: 0.5,
      subdivisions: 4,
      skinColor: [216, 184, 153],
    };

    this._parts = Array.from({ length: 120 }, () => ({
      x:   Math.random(),
      y:   Math.random(),
      spd: 0.25 + Math.random() * 0.8,
      ch:  Math.random() > 0.5 ? '1' : '0',
      a:   0.04 + Math.random() * 0.1,
    }));

    const pal = this._palette(this.options.colorPalette);
    this._col       = { ...pal };
    this._targetCol = { ...pal };

    this._initCanvas();
    this._startLoop();
  }

  // ── Canvas bootstrap ────────────────────────────────────────────────────────
  _initCanvas() {
    this.canvas = document.createElement('canvas');
    Object.assign(this.canvas.style, {
      display:  'block',
      position: 'absolute',
      inset:    '0',
      width:    '100%',
      height:   '100%',
    });
    this.ctx = this.canvas.getContext('2d');
    this.container.appendChild(this.canvas);

    this._ro = new ResizeObserver(() => this._resize());
    this._ro.observe(this.container);
    this._resize();
  }

  _resize() {
    if (this._destroyed) return;
    const W = this.container.clientWidth  || window.innerWidth;
    const H = this.container.clientHeight || window.innerHeight;
    if (W && H) { this.canvas.width = W; this.canvas.height = H; }
  }

  // ── Public API ──────────────────────────────────────────────────────────────
  setActivity(a) {
    this.state.activity = a;
    const MAP = {
      idle:'idle', thinking:'thinking', speaking:'speaking', error:'alert',
      background:'idle', initializing:'idle', listening:'listening',
      surprised:'alert', happy:'idle', focused:'thinking',
    };
    this._avState    = MAP[a] || 'idle';
    this._isSpeaking = (this._avState === 'speaking');
    this._targetCol  = { ...this._statePalette(this._avState) };
  }

  setEmotion(e) { this.state.emotion = e; }

  setVolume(v) {
    this.state.volume = v;
    if (this._avState === 'speaking') this.state.jawOpen = v;
  }

  setState(obj) {
    if (typeof obj === 'string') { this.setActivity(obj); return; }
    if (obj.emotion)              this.setEmotion(obj.emotion);
    if (obj.activity)             this.setActivity(obj.activity);
    if (obj.volume   != null)     this.setVolume(obj.volume);
  }

  setColorPalette(name) { this._targetCol = { ...this._palette(name) }; }
  setFrequencyData(arr) { this.state.frequency = arr; }
  setSpeed(s)           { this._speed = s; }
  onResize()            { this._resize(); }
  setCustomization(next = {}) {
    const clamp = (v, min = 0, max = 1) => Math.max(min, Math.min(max, Number(v) || 0));
    const skin = Array.isArray(next.skinColor)
      ? next.skinColor
      : Array.isArray(next.skin_color)
        ? next.skin_color.map((v) => v <= 1 ? v * 255 : v)
        : this._customization.skinColor;

    this._customization = {
      ...this._customization,
      smile: next.smile != null ? clamp(next.smile) : this._customization.smile,
      frown: next.frown != null ? clamp(next.frown) : this._customization.frown,
      surprise: next.surprise != null ? clamp(next.surprise) : this._customization.surprise,
      wink: next.wink != null ? clamp(next.wink) : this._customization.wink,
      viseme: next.viseme != null ? clamp(next.viseme) : this._customization.viseme,
      subdivisions: next.subdivisions != null
        ? Math.max(2, Math.min(6, Math.round(Number(next.subdivisions) || 4)))
        : this._customization.subdivisions,
      skinColor: skin.slice(0, 3).map((v) => Math.max(0, Math.min(255, Number(v) || 0))),
    };
  }
  getCustomization() { return { ...this._customization, skinColor: [...this._customization.skinColor] }; }

  destroy() {
    this._destroyed = true;
    if (this._animId) cancelAnimationFrame(this._animId);
    if (this._ro)     this._ro.disconnect();
    this.canvas?.remove();
  }

  // ── Palette maps ────────────────────────────────────────────────────────────
  _palette(name) {
    return ({
      'matrix':        { r:0,   g:255, b:80  },
      'cyan':          { r:0,   g:255, b:255 },
      'cyber-magenta': { r:255, g:0,   b:255 },
      'amber':         { r:255, g:180, b:0   },
      'ice':           { r:150, g:220, b:255 },
      'red':           { r:255, g:40,  b:0   },
    })[name] || { r:0, g:255, b:255 };
  }

  _statePalette(s) {
    return ({
      idle:      { r:0,   g:255, b:255 },
      listening: { r:0,   g:180, b:255 },
      thinking:  { r:140, g:30,  b:255 },
      speaking:  { r:0,   g:255, b:165 },
      alert:     { r:255, g:40,  b:0   },
    })[s] || { r:0, g:255, b:255 };
  }

  // ── Render loop ─────────────────────────────────────────────────────────────
  _startLoop() {
    const tick = (ts) => {
      if (this._destroyed) return;
      this._animId = requestAnimationFrame(tick);
      this._frame(ts);
    };
    this._animId = requestAnimationFrame(tick);
  }

  _frame(ts) {
    const dt = Math.min(ts - this._prevT, 50);
    this._prevT = ts;
    this._T     = ts;

    // Lerp color
    const { r, g, b } = this._targetCol;
    this._col.r = this._lerp(this._col.r, r, 0.04);
    this._col.g = this._lerp(this._col.g, g, 0.04);
    this._col.b = this._lerp(this._col.b, b, 0.04);

    // Mouth
    if (this._isSpeaking) this._mouthT += 0.19;
    else                  this._mouthT  = 0;

    // Blink
    this._blinkClock += dt;
    if (!this._blinking && this._blinkClock >= this._nextBlink) {
      this._blinking = true; this._blinkPhase = 0;
    }
    if (this._blinking) {
      this._blinkPhase += dt * 0.012;
      if (this._blinkPhase >= Math.PI) {
        this._blinking = false; this._blinkClock = 0;
        this._nextBlink = 3200 + Math.random() * 3800;
      }
    }
    const blink = this._blinking ? Math.max(0, Math.cos(this._blinkPhase)) : 1;

    const W   = this.canvas.width;
    const H   = this.canvas.height;
    if (!W || !H) return;

    const S   = Math.min(W, H) * 0.68;
    const fcx = W / 2;
    const fcy = H / 2;

    const CFG = {
      idle:      { pSpeed:0.7,  glow:1,   flicker:0,    eyeMult:1   },
      listening: { pSpeed:1.2,  glow:2.4, flicker:0,    eyeMult:1.8 },
      thinking:  { pSpeed:4.5,  glow:1.5, flicker:0.22, eyeMult:1.2 },
      speaking:  { pSpeed:1.8,  glow:1.8, flicker:0,    eyeMult:1.4 },
      alert:     { pSpeed:3,    glow:3,   flicker:0.32, eyeMult:2.4 },
    };
    const cfg = CFG[this._avState] || CFG.idle;

    let fa = 1;
    if (cfg.flicker > 0)
      fa = 0.52 + 0.48 * Math.abs(Math.sin(ts * 0.045 / cfg.flicker));

    const visemeGain = 0.35 + this._customization.viseme * 1.3;
    const mouthOpen = this._isSpeaking
      ? Math.abs(Math.sin(this._mouthT * 0.88)) * S * 0.068 * visemeGain
      : 0;

    const ctx = this.ctx;
    // Transparent — env-layer shows through
    ctx.clearRect(0, 0, W, H);

    this._drawRain(ctx, W, H, cfg);
    this._drawListenRings(ctx, W, H, fcx, fcy, S);
    this._drawOrbit(ctx, W, H, fcx, fcy, S, cfg);

    ctx.globalAlpha = fa;
    this._drawFace(ctx, W, H, S, fcx, fcy, cfg, blink, mouthOpen);
    ctx.globalAlpha = 1;

    this._drawGlitch(ctx, W, H, cfg);
    this._drawSpeakBars(ctx, W, H, fcx, cfg);
    this._drawScan(ctx, W, H);
    this._drawAlertBorder(ctx, W, H);
    this._drawListenBorder(ctx, W, H);
  }

  // ── Background rain ─────────────────────────────────────────────────────────
  _drawRain(ctx, W, H, cfg) {
    ctx.font = '9px monospace';
    const { r, g, b } = this._col;
    for (const p of this._parts) {
      ctx.fillStyle = this._rgba(r * .32, g * .42, b * .42, p.a);
      ctx.fillText(p.ch, p.x * W, p.y * H);
      p.y += p.spd * cfg.pSpeed * 0.0012;
      if (p.y > 1) {
        p.y = -0.02; p.x = Math.random();
        p.ch = Math.random() > 0.5 ? '1' : '0';
      }
    }
  }

  // ── Listening concentric rings ───────────────────────────────────────────────
  _drawListenRings(ctx, W, H, fcx, fcy, S) {
    if (this._avState !== 'listening') return;
    const { r, g, b } = this._col;
    for (let i = 1; i <= 3; i++) {
      const ph  = this._T * 0.0028 - i * 0.55;
      const alp = Math.max(0, Math.sin(ph)) * 0.25;
      const rad = S * (0.28 + i * 0.12) * (0.5 + 0.5 * Math.abs(Math.sin(ph * 0.45)));
      ctx.strokeStyle = this._rgba(r, g, b, alp);
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(fcx, fcy, rad, 0, Math.PI * 2); ctx.stroke();
    }
  }

  // ── Thinking orbit nodes ────────────────────────────────────────────────────
  _drawOrbit(ctx, W, H, fcx, fcy, S, cfg) {
    if (this._avState !== 'thinking') return;
    this._orbitAngle += 0.02;
    const { r, g, b } = this._col;
    const or = S * 0.5;
    ctx.save();
    for (let i = 0; i < 6; i++) {
      const a  = this._orbitAngle + (i / 6) * Math.PI * 2;
      const x  = fcx + Math.cos(a) * or;
      const y  = fcy + Math.sin(a) * or;
      const sz = 2.5 + 1.5 * Math.sin(this._orbitAngle * 2.5 + i);
      ctx.fillStyle   = this._rgba(r, g, b, 0.7);
      ctx.shadowColor = this._rgba(r, g, b, 1);
      ctx.shadowBlur  = 10;
      ctx.fillRect(x - sz / 2, y - sz / 2, sz, sz);
      const na = a + Math.PI / 3;
      ctx.strokeStyle = this._rgba(r, g, b, 0.12);
      ctx.shadowBlur  = 0;
      ctx.lineWidth   = 0.8;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(fcx + Math.cos(na) * or, fcy + Math.sin(na) * or);
      ctx.stroke();
    }
    ctx.shadowBlur = 0;
    ctx.restore();
  }

  // ── Holographic human face ──────────────────────────────────────────────────
  _drawFace(ctx, W, H, S, fcx, fcy, cfg, blink, mouthOpen) {
    const { r, g, b } = this._col;
    const T = this._T;
    const custom = this._customization;
    const [sr, sg, sb] = custom.skinColor;

    // ── proportions ──
    const hcx = fcx;
    const hcy = fcy - S * 0.015;
    const surpriseShape = custom.surprise * 0.035;
    const hrx = S * (0.262 - surpriseShape * 0.4);
    const hry = S * (0.33 + surpriseShape);

    const eyeY  = hcy - S * (0.085 + custom.surprise * 0.018);
    const eyeSp = S * 0.125;
    const eyeW  = S * 0.165;
    const eyeH  = S * (0.052 + custom.surprise * 0.025);

    const browY = eyeY - S * (0.068 + custom.surprise * 0.028);

    const nTop  = eyeY  + S * 0.015;
    const nTip  = hcy   + S * 0.1;
    const nW    = S * 0.065;

    const mY    = hcy + S * 0.2;
    const mW    = S * 0.2;
    const smileCurve = (custom.smile - custom.frown) * S * 0.055;
    const surpriseOpen = custom.surprise * S * 0.085;
    const expressionMouthOpen = mouthOpen + surpriseOpen;

    // Thinking: eyes look slightly up
    const lookY = this._avState === 'thinking' ? -eyeH * 0.25 : 0;

    // ── 1. Ambient face glow ──
    const fg = ctx.createRadialGradient(hcx, hcy, 0, hcx, hcy, hrx * 1.1);
    fg.addColorStop(0,   this._rgba(r, g, b, 0.06));
    fg.addColorStop(0.28, this._rgba(sr, sg, sb, 0.035));
    fg.addColorStop(0.7, this._rgba(r, g, b, 0.025));
    fg.addColorStop(1,   this._rgba(r, g, b, 0));
    ctx.fillStyle = fg;
    ctx.beginPath();
    ctx.ellipse(hcx, hcy, hrx * 1.1, hry * 1.1, 0, 0, Math.PI * 2);
    ctx.fill();

    // ── 2. Head outline ──
    ctx.save();
    ctx.shadowColor = this._rgba(r, g, b, 1);
    ctx.shadowBlur  = 18 * cfg.glow;
    ctx.strokeStyle = this._rgba(r, g, b, 0.48);
    ctx.lineWidth   = 1.4;
    ctx.beginPath();
    ctx.moveTo(hcx, hcy - hry);
    ctx.bezierCurveTo(hcx + hrx * 0.55, hcy - hry,        hcx + hrx,        hcy - hry * 0.32, hcx + hrx * 0.88, hcy);
    ctx.bezierCurveTo(hcx + hrx * 0.72, hcy + hry * 0.42, hcx + hrx * 0.42, hcy + hry * 0.88, hcx,              hcy + hry);
    ctx.bezierCurveTo(hcx - hrx * 0.42, hcy + hry * 0.88, hcx - hrx * 0.72, hcy + hry * 0.42, hcx - hrx * 0.88, hcy);
    ctx.bezierCurveTo(hcx - hrx,        hcy - hry * 0.32, hcx - hrx * 0.55, hcy - hry,         hcx,              hcy - hry);
    ctx.closePath();
    ctx.fillStyle = this._rgba(sr, sg, sb, 0.045);
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    // ── 3. Wireframe structure lines ──
    ctx.save();
    ctx.strokeStyle = this._rgba(r, g, b, 0.09);
    ctx.lineWidth   = 0.7;
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(hcx, hcy, hrx, hry, 0, 0, Math.PI * 2);
    ctx.clip();
    const lineCount = custom.subdivisions;
    for (let i = 0; i < lineCount; i++) {
      const t = lineCount === 1 ? 0.5 : i / (lineCount - 1);
      const ly = hcy - hry * 0.62 + t * hry * 1.24;
      const local = Math.abs((ly - hcy) / hry);
      const xf = Math.max(0.32, Math.sqrt(Math.max(0, 1 - local * local)) * 0.96);
      ctx.beginPath(); ctx.moveTo(hcx - hrx*xf, ly); ctx.lineTo(hcx + hrx*xf, ly); ctx.stroke();
    }
    ctx.beginPath(); ctx.moveTo(hcx, hcy - hry*0.92); ctx.lineTo(hcx, hcy + hry*0.88); ctx.stroke();
    ctx.restore();
    ctx.restore();

    // ── 4. Eyebrows ──
    ctx.save();
    ctx.shadowColor = this._rgba(r, g, b, 1);
    ctx.shadowBlur  = 8 * cfg.glow;
    ctx.strokeStyle = this._rgba(r, g, b, this._avState === 'alert' ? 0.9 : 0.65);
    ctx.lineWidth   = S * 0.013;
    ctx.lineCap     = 'round';
    const browLift  = (this._avState === 'alert' ? -S * 0.014 : 0) - custom.surprise * S * 0.026 + custom.frown * S * 0.014;
    ctx.beginPath();
    ctx.moveTo(hcx - eyeSp - eyeW*0.52, browY + browLift + S*0.012);
    ctx.quadraticCurveTo(hcx - eyeSp - eyeW*0.08, browY + browLift - S*0.018, hcx - eyeSp + eyeW*0.44, browY + browLift + S*0.006);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(hcx + eyeSp - eyeW*0.44, browY + browLift + S*0.006);
    ctx.quadraticCurveTo(hcx + eyeSp + eyeW*0.08, browY + browLift - S*0.018, hcx + eyeSp + eyeW*0.52, browY + browLift + S*0.012);
    ctx.stroke();
    ctx.restore();

    // ── 5. Eyes ──
    const self = this;
    function eye(ex, ey, w, h, blinkF) {
      const hb = h * Math.max(0.04, blinkF);
      const iy = ey + lookY;

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(ex - w/2, ey);
      ctx.quadraticCurveTo(ex - w*0.12, ey - hb,       ex,        ey - hb*0.72);
      ctx.quadraticCurveTo(ex + w*0.12, ey - hb,       ex + w/2,  ey);
      ctx.quadraticCurveTo(ex + w*0.12, ey + hb*0.6,   ex,        ey + hb*0.48);
      ctx.quadraticCurveTo(ex - w*0.12, ey + hb*0.6,   ex - w/2,  ey);
      ctx.closePath();
      ctx.clip();

      // Iris gradient
      const ig = ctx.createRadialGradient(ex, iy, 0, ex, iy, hb * 1.1);
      ig.addColorStop(0,    self._rgba(r*0.6, g, b, 0.95));
      ig.addColorStop(0.55, self._rgba(r*0.3, g*0.75, b, 0.6));
      ig.addColorStop(1,    self._rgba(r*0.1, g*0.25, b*0.5, 0.2));
      ctx.fillStyle = ig;
      ctx.fillRect(ex - w, ey - hb*1.2, w*2, hb*2.4);

      // Pupil
      ctx.beginPath(); ctx.arc(ex, iy, hb*0.28, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(0,0,0,.78)'; ctx.fill();
      ctx.strokeStyle = self._rgba(r, g, b, 0.7);
      ctx.lineWidth = 0.8; ctx.stroke();

      // Specular
      ctx.beginPath(); ctx.arc(ex - hb*0.14, iy - hb*0.22, hb*0.1, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(255,255,255,.75)'; ctx.fill();
      ctx.restore();

      // Outline (over clip)
      ctx.save();
      ctx.shadowColor = self._rgba(r, g, b, 1);
      ctx.shadowBlur  = 16 * cfg.glow * cfg.eyeMult;
      ctx.strokeStyle = self._rgba(r, g, b, 0.82);
      ctx.lineWidth   = 1.5;
      ctx.beginPath();
      ctx.moveTo(ex - w/2, ey);
      ctx.quadraticCurveTo(ex - w*0.12, ey - hb, ex, ey - hb*0.72);
      ctx.quadraticCurveTo(ex + w*0.12, ey - hb, ex + w/2, ey);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(ex - w/2, ey);
      ctx.quadraticCurveTo(ex - w*0.12, ey + hb*0.6, ex, ey + hb*0.48);
      ctx.quadraticCurveTo(ex + w*0.12, ey + hb*0.6, ex + w/2, ey);
      ctx.stroke();
      ctx.strokeStyle = self._rgba(r, g, b, 0.3);
      ctx.lineWidth = 0.7;
      ctx.beginPath(); ctx.arc(ex - w/2, ey, hb*0.18, 0, Math.PI*2); ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.restore();
    }

    const winkBlink = Math.max(0.04, blink * (1 - custom.wink * 0.96));
    eye(hcx - eyeSp, eyeY, eyeW, eyeH, winkBlink);
    eye(hcx + eyeSp, eyeY, eyeW, eyeH, blink);

    // ── 6. Nose ──
    ctx.save();
    ctx.strokeStyle = this._rgba(r, g, b, 0.38);
    ctx.lineWidth = 1.1; ctx.lineCap = 'round';
    ctx.shadowColor = this._rgba(r, g, b, .5); ctx.shadowBlur = 4;
    ctx.beginPath();
    ctx.moveTo(hcx - S*0.024, nTop);
    ctx.bezierCurveTo(hcx - S*0.036, nTip - S*0.04, hcx - nW*0.78, nTip, hcx - nW, nTip + S*0.012);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(hcx + S*0.024, nTop);
    ctx.bezierCurveTo(hcx + S*0.036, nTip - S*0.04, hcx + nW*0.78, nTip, hcx + nW, nTip + S*0.012);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(hcx - nW, nTip + S*0.012);
    ctx.quadraticCurveTo(hcx, nTip + S*0.032, hcx + nW, nTip + S*0.012);
    ctx.stroke();
    ctx.restore();

    // ── 7. Philtrum ──
    ctx.save();
    ctx.strokeStyle = this._rgba(r, g, b, 0.2);
    ctx.lineWidth = 0.7;
    ctx.beginPath(); ctx.moveTo(hcx, nTip + S*0.032); ctx.lineTo(hcx, mY - S*0.012); ctx.stroke();
    ctx.restore();

    // ── 8. Mouth ──
    ctx.save();
    ctx.shadowColor = this._rgba(r, g, b, 1);
    ctx.shadowBlur  = 12 * cfg.glow;
    ctx.strokeStyle = this._rgba(r, g, b, 0.72);
    ctx.lineWidth   = 1.8; ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(hcx - mW, mY);
    ctx.bezierCurveTo(hcx - mW*0.6, mY - S*0.022 - smileCurve * 0.35, hcx - mW*0.15, mY - S*0.034 - smileCurve * 0.55, hcx,       mY - S*0.01 - smileCurve * 0.35);
    ctx.bezierCurveTo(hcx + mW*0.15, mY - S*0.034 - smileCurve * 0.55, hcx + mW*0.6,  mY - S*0.022 - smileCurve * 0.35, hcx + mW, mY);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(hcx - mW, mY);
    ctx.quadraticCurveTo(hcx, mY + S*0.036 + expressionMouthOpen + smileCurve, hcx + mW, mY);
    ctx.stroke();
    if (expressionMouthOpen > S * 0.004) {
      ctx.beginPath();
      ctx.moveTo(hcx - mW*0.85, mY);
      ctx.bezierCurveTo(hcx - mW*0.45, mY - S*0.015, hcx - mW*0.08, mY - S*0.018, hcx,          mY - S*0.007);
      ctx.bezierCurveTo(hcx + mW*0.08, mY - S*0.018, hcx + mW*0.45, mY - S*0.015, hcx + mW*0.85, mY);
      ctx.quadraticCurveTo(hcx, mY + S*0.024 + expressionMouthOpen * 0.82, hcx - mW*0.85, mY);
      ctx.closePath();
      ctx.fillStyle = this._rgba(0, r*0.08, b*0.12, 0.5);
      ctx.fill();
    }
    ctx.strokeStyle = this._rgba(r, g, b, 0.32); ctx.lineWidth = 0.7;
    [hcx - mW, hcx + mW].forEach(lx => {
      ctx.beginPath(); ctx.arc(lx, mY, S*0.007, 0, Math.PI*2); ctx.stroke();
    });
    ctx.shadowBlur = 0;
    ctx.restore();

    // ── 9. Scan sweep inside face ──
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(hcx, hcy, hrx*1.01, hry*1.01, 0, 0, Math.PI*2);
    ctx.clip();
    const sweep = (T * 0.07) % (hry * 2.2);
    const scanGradient = ctx.createLinearGradient(0, hcy - hry + sweep - 28, 0, hcy - hry + sweep + 28);
    scanGradient.addColorStop(0,   this._rgba(r, g, b, 0));
    scanGradient.addColorStop(0.5, this._rgba(r, g, b, 0.1));
    scanGradient.addColorStop(1,   this._rgba(r, g, b, 0));
    ctx.fillStyle = scanGradient;
    ctx.fillRect(hcx - hrx, hcy - hry + sweep - 28, hrx*2, 56);
    for (let ly = hcy - hry; ly < hcy + hry; ly += 4) {
      ctx.fillStyle = 'rgba(0,0,0,.08)';
      ctx.fillRect(hcx - hrx, ly, hrx*2, 1);
    }
    ctx.restore();

    // ── 10. Eye halos ──
    ctx.save();
    [[hcx - eyeSp, eyeY], [hcx + eyeSp, eyeY]].forEach(([ex, ey]) => {
      const gh = ctx.createRadialGradient(ex, ey, 0, ex, ey, eyeW*0.9);
      gh.addColorStop(0, this._rgba(r, g, b, 0.12 * cfg.eyeMult * blink));
      gh.addColorStop(1, this._rgba(r, g, b, 0));
      ctx.fillStyle = gh;
      ctx.fillRect(ex - eyeW, ey - eyeW, eyeW*2, eyeW*2);
    });
    ctx.restore();
  }

  // ── Glitch strip displacement ───────────────────────────────────────────────
  _drawGlitch(ctx, W, H, cfg) {
    if (cfg.flicker === 0 || Math.random() > cfg.flicker * 0.18) return;
    for (let i = 0; i < 2; i++) {
      const sh = 2 + Math.random() * 10;
      const sy = Math.random() * H;
      if (sy + sh > H) continue;
      const data = ctx.getImageData(0, sy, W, sh);
      ctx.putImageData(data, (Math.random() - 0.5) * 22, sy);
    }
  }

  // ── Speech waveform bars ────────────────────────────────────────────────────
  _drawSpeakBars(ctx, W, H, fcx, cfg) {
    if (this._avState !== 'speaking' || !this._isSpeaking) return;
    const { r, g, b } = this._col;
    const by = H - 18, n = 18, bw = 4, gap = 3;
    const tw = n * (bw + gap);
    ctx.shadowColor = this._rgba(r, g, b, 1); ctx.shadowBlur = 7;
    for (let i = 0; i < n; i++) {
      const barH = 5 + 16 * Math.abs(Math.sin(this._T * 0.016 + i * 0.55));
      ctx.fillStyle = this._rgba(r, g, b, 0.5);
      ctx.fillRect(fcx - tw/2 + i*(bw+gap), by - barH, bw, barH);
    }
    ctx.shadowBlur = 0;
  }

  // ── Full-canvas scan sweep ──────────────────────────────────────────────────
  _drawScan(ctx, W, H) {
    const { r, g, b } = this._col;
    const y = (this._T * 0.09) % H;
    const g2 = ctx.createLinearGradient(0, y-36, 0, y+36);
    g2.addColorStop(0,   this._rgba(r, g, b, 0));
    g2.addColorStop(0.5, this._rgba(r, g, b, 0.05));
    g2.addColorStop(1,   this._rgba(r, g, b, 0));
    ctx.fillStyle = g2;
    ctx.fillRect(0, y-36, W, 72);
  }

  // ── Alert border strobe ─────────────────────────────────────────────────────
  _drawAlertBorder(ctx, W, H) {
    if (this._avState !== 'alert') return;
    const { r, g, b } = this._col;
    const strobe = Math.sin(this._T * 0.024) > 0 ? 0.85 : 0.08;
    ctx.strokeStyle = this._rgba(r, g, b, strobe);
    ctx.shadowColor = this._rgba(r, g, b, 1);
    ctx.shadowBlur  = 26; ctx.lineWidth = 2.5;
    ctx.strokeRect(5, 5, W-10, H-10);
    ctx.shadowBlur  = 0;
  }

  // ── Listening border pulse ──────────────────────────────────────────────────
  _drawListenBorder(ctx, W, H) {
    if (this._avState !== 'listening') return;
    const { r, g, b } = this._col;
    const p = 0.28 + 0.72 * Math.abs(Math.sin(this._T * 0.005));
    ctx.strokeStyle = this._rgba(r, g, b, p);
    ctx.shadowColor = this._rgba(r, g, b, 1);
    ctx.shadowBlur  = 18; ctx.lineWidth = 1.2;
    ctx.strokeRect(5, 5, W-10, H-10);
    ctx.shadowBlur  = 0;
  }

  // ── Utility ─────────────────────────────────────────────────────────────────
  _lerp(a, b, t)    { return a + (b - a) * t; }
  _rgba(r, g, b, a) { return `rgba(${r|0},${g|0},${b|0},${a.toFixed(3)})`; }
}
