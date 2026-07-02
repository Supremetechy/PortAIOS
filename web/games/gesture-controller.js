/**
 * AIOS Games - Hand Gesture Controller
 * Uses MediaPipe Hands (CDN) for browser-side landmark detection.
 * Classifies poses → routes actions to the active game.
 *
 * Gesture map:
 *   open_palm  → hover / stop-fire (shooter) / analyze (poker)
 *   fist       → shoot (shooter)
 *   point      → cursor aim
 *   pinch      → click / flip card / select card
 *   peace ✌️  → restart game
 *   thumbs_up  → confirm / analyze (poker)
 *   swipe_*    → directional boost (shooter) / card navigation
 */

export class GameGestureController {
  constructor() {
    this.isActive      = false;
    this.hands         = null;
    this.stream        = null;
    this.videoEl       = null;
    this.canvasEl      = null;
    this.ctx           = null;
    this.activeGame    = null;
    this._handlers     = {};
    this.statusEl      = null;
    this.cursorEl      = null;

    // Gesture state
    this.lastGesture      = null;
    this.currentGesture   = null;
    this.gestureHoldStart = 0;
    this.HOLD_MS          = 280; // hold this many ms before firing

    // Motion tracking for swipes
    this.palmHistory   = [];
    this.SWIPE_DIST    = 0.14; // normalized units across SWIPE_FRAMES
    this.SWIPE_FRAMES  = 6;
    this.SWIPE_MAX_MS  = 600;

    // Pinch / action cooldowns
    this.pinchCooldown = 0;

    // Cursor position (normalized, mirrored)
    this.cursorNorm = { x: 0.5, y: 0.5 };
  }

  // ── Event bus ──────────────────────────────────────────────────────────────
  on(event, handler) { this._handlers[event] = handler; }
  emit(event, data)  { if (this._handlers[event]) this._handlers[event](data); }

  // ── Init ───────────────────────────────────────────────────────────────────
  async init(pipContainerEl, statusEl, cursorEl) {
    this.statusEl = statusEl;
    this.cursorEl = cursorEl;

    // Build video + skeleton canvas inside the PiP container
    this.videoEl = document.createElement('video');
    this.videoEl.autoplay = true;
    this.videoEl.playsInline = true;
    this.videoEl.muted = true;
    this.videoEl.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform:scaleX(-1);';

    this.canvasEl = document.createElement('canvas');
    this.canvasEl.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;transform:scaleX(-1);';

    pipContainerEl.appendChild(this.videoEl);
    pipContainerEl.appendChild(this.canvasEl);
    this.ctx = this.canvasEl.getContext('2d');

    return true;
  }

  // ── Enable / Disable ───────────────────────────────────────────────────────
  async enable() {
    if (this.isActive) return;
    this.setStatus('🤚 Starting…', 'loading');

    try {
      await this._loadMediaPipe();

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240, facingMode: 'user' }
      });
      this.stream = stream;
      this.videoEl.srcObject = stream;
      await new Promise(res => { this.videoEl.onloadedmetadata = res; });

      this.canvasEl.width  = this.videoEl.videoWidth  || 320;
      this.canvasEl.height = this.videoEl.videoHeight || 240;

      this.hands = new window.Hands({
        locateFile: f => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`
      });
      this.hands.setOptions({
        maxNumHands: 1,
        modelComplexity: 0,
        minDetectionConfidence: 0.7,
        minTrackingConfidence: 0.5
      });
      this.hands.onResults(r => this._onResults(r));

      this.isActive = true;
      this._processFrame();
      this.setStatus('🤚 Active', 'active');
      if (this.cursorEl) this.cursorEl.style.display = 'block';

    } catch (err) {
      console.error('[Gesture]', err);
      this.setStatus('🤚 ' + (err.name === 'NotAllowedError' ? 'Cam denied' : err.message), 'error');
    }
  }

  disable() {
    this.isActive = false;
    if (this.stream) { this.stream.getTracks().forEach(t => t.stop()); this.stream = null; }
    this.videoEl.srcObject = null;
    this.ctx?.clearRect(0, 0, this.canvasEl.width, this.canvasEl.height);
    if (this.cursorEl) this.cursorEl.style.display = 'none';
    this.setStatus('🤚 Off', 'idle');
  }

  toggle() { this.isActive ? this.disable() : this.enable(); }

  setStatus(text, state = 'idle') {
    if (!this.statusEl) return;
    this.statusEl.textContent = text;
    this.statusEl.dataset.state = state;
  }

  // ── MediaPipe loader ───────────────────────────────────────────────────────
  _loadMediaPipe() {
    if (window.Hands) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js';
      s.crossOrigin = 'anonymous';
      s.onload = resolve;
      s.onerror = () => reject(new Error('Failed to load MediaPipe Hands'));
      document.head.appendChild(s);
    });
  }

  // ── Frame loop ─────────────────────────────────────────────────────────────
  async _processFrame() {
    if (!this.isActive) return;
    if (this.videoEl.readyState >= 2) {
      try { await this.hands.send({ image: this.videoEl }); } catch (_) {}
    }
    requestAnimationFrame(() => this._processFrame());
  }

  // ── Results handler ────────────────────────────────────────────────────────
  _onResults(results) {
    this.ctx.clearRect(0, 0, this.canvasEl.width, this.canvasEl.height);
    if (this.pinchCooldown > 0) this.pinchCooldown -= 16;

    if (!results.multiHandLandmarks?.length) {
      this.lastGesture = null;
      this.currentGesture = null;
      if (this.cursorEl) this.cursorEl.style.display = 'none';
      return;
    }

    const lm = results.multiHandLandmarks[0];
    this._drawSkeleton(lm);

    // Update cursor (index finger tip, mirror x)
    this.cursorNorm = { x: 1 - lm[8].x, y: lm[8].y };
    this._updateCursor(this.cursorNorm);

    // Track palm centre for swipe detection
    const now = Date.now();
    this.palmHistory.push({ x: lm[0].x, y: lm[0].y, t: now });
    if (this.palmHistory.length > this.SWIPE_FRAMES) this.palmHistory.shift();

    // Swipe takes priority
    const swipe = this._detectSwipe();
    if (swipe) { this._dispatch(swipe); return; }

    // Classify static gesture with hold debounce
    const gesture = this._classify(lm);

    if (gesture !== this.lastGesture) {
      this.lastGesture      = gesture;
      this.gestureHoldStart = now;
    } else if (gesture && now - this.gestureHoldStart >= this.HOLD_MS) {
      if (this.currentGesture !== gesture) {
        this.currentGesture = gesture;
        this._dispatch(gesture);
      }
    }

    // Continuous hand-position feed (shooter movement)
    if (this.activeGame === 'shooter' && gesture === 'open_palm') {
      this.emit('shooter:handpos', { x: 1 - lm[9].x, y: lm[9].y });
    }
  }

  // ── Gesture classifier ─────────────────────────────────────────────────────
  _classify(lm) {
    // Finger extension helpers (tip.y < pip.y means extended upward)
    const indexExt  = lm[8].y  < lm[6].y;
    const middleExt = lm[12].y < lm[10].y;
    const ringExt   = lm[16].y < lm[14].y;
    const pinkyExt  = lm[20].y < lm[18].y;
    // Thumb: tip.x further from palm base for right-hand (we use general heuristic)
    const thumbTipDist = Math.hypot(lm[4].x - lm[2].x, lm[4].y - lm[2].y);
    const thumbExt  = thumbTipDist > 0.08;
    const thumbUp   = lm[4].y < lm[3].y && lm[4].y < lm[0].y;

    // Pinch: thumb tip ↔ index tip distance
    const pinchDist = Math.hypot(lm[4].x - lm[8].x, lm[4].y - lm[8].y);
    if (pinchDist < 0.07) return 'pinch';

    if (indexExt && middleExt && ringExt && pinkyExt) return 'open_palm';
    if (!indexExt && !middleExt && !ringExt && !pinkyExt) {
      return (thumbUp && thumbExt) ? 'thumbs_up' : 'fist';
    }
    if (indexExt && middleExt && !ringExt && !pinkyExt) return 'peace';
    if (indexExt && !middleExt && !ringExt && !pinkyExt) return 'point';

    return null;
  }

  // ── Swipe detector ─────────────────────────────────────────────────────────
  _detectSwipe() {
    if (this.palmHistory.length < this.SWIPE_FRAMES) return null;
    const first = this.palmHistory[0];
    const last  = this.palmHistory[this.palmHistory.length - 1];
    if (last.t - first.t > this.SWIPE_MAX_MS) return null;

    const dx = last.x - first.x;
    const dy = last.y - first.y;
    const adx = Math.abs(dx), ady = Math.abs(dy);

    if (adx > this.SWIPE_DIST && adx > ady) {
      this.palmHistory = [];
      return dx < 0 ? 'swipe_right' : 'swipe_left'; // mirrored
    }
    if (ady > this.SWIPE_DIST && ady > adx) {
      this.palmHistory = [];
      return dy < 0 ? 'swipe_up' : 'swipe_down';
    }
    return null;
  }

  // ── Dispatcher ─────────────────────────────────────────────────────────────
  _dispatch(gesture) {
    switch (this.activeGame) {
      case null:      return this._handleDesktop(gesture);
      case 'memory':  return this._handleMemory(gesture);
      case 'shooter': return this._handleShooter(gesture);
      case 'poker':   return this._handlePoker(gesture);
    }
  }

  _handleDesktop(gesture) {
    if (gesture === 'pinch')      this.emit('gesture:click',  this.cursorNorm);
    if (gesture === 'open_palm')  this.emit('gesture:hover',  this.cursorNorm);
    if (gesture === 'point')      this.emit('gesture:hover',  this.cursorNorm);
  }

  _handleMemory(gesture) {
    if (gesture === 'pinch' && this.pinchCooldown <= 0) {
      this.emit('memory:gesture:flip', this.cursorNorm);
      this.pinchCooldown = 900;
      this.currentGesture = null;
    }
    if (gesture === 'open_palm') this.emit('memory:hint');
    if (gesture === 'peace')     this.emit('memory:restart');
  }

  _handleShooter(gesture) {
    if (gesture === 'fist')        this.emit('shooter:fire');
    if (gesture === 'open_palm')   this.emit('shooter:stopfire');
    if (gesture === 'peace')       this.emit('shooter:restart');
    if (gesture === 'swipe_left')  this.emit('shooter:move', { dx: -1, dy: 0 });
    if (gesture === 'swipe_right') this.emit('shooter:move', { dx:  1, dy: 0 });
    if (gesture === 'swipe_up')    this.emit('shooter:move', { dx:  0, dy: -1 });
    if (gesture === 'swipe_down')  this.emit('shooter:move', { dx:  0, dy:  1 });
  }

  _handlePoker(gesture) {
    if (gesture === 'pinch' && this.pinchCooldown <= 0) {
      this.emit('poker:gesture:select', this.cursorNorm);
      this.pinchCooldown = 700;
      this.currentGesture = null;
    }
    if (gesture === 'open_palm' || gesture === 'thumbs_up') this.emit('poker:analyze');
    if (gesture === 'peace')  this.emit('poker:clear');
  }

  // ── Cursor ─────────────────────────────────────────────────────────────────
  _updateCursor(norm) {
    if (!this.cursorEl) return;
    this.cursorEl.style.display = 'block';
    this.cursorEl.style.left = (norm.x * window.innerWidth)  + 'px';
    this.cursorEl.style.top  = (norm.y * window.innerHeight) + 'px';
  }

  // ── Skeleton overlay ───────────────────────────────────────────────────────
  _drawSkeleton(lm) {
    const w = this.canvasEl.width, h = this.canvasEl.height;
    const CONNECTIONS = [
      [0,1],[1,2],[2,3],[3,4],
      [0,5],[5,6],[6,7],[7,8],
      [0,9],[9,10],[10,11],[11,12],
      [0,13],[13,14],[14,15],[15,16],
      [0,17],[17,18],[18,19],[19,20],
      [5,9],[9,13],[13,17]
    ];
    this.ctx.strokeStyle = '#00f2ff';
    this.ctx.lineWidth   = 1.5;
    CONNECTIONS.forEach(([a, b]) => {
      this.ctx.beginPath();
      this.ctx.moveTo(lm[a].x * w, lm[a].y * h);
      this.ctx.lineTo(lm[b].x * w, lm[b].y * h);
      this.ctx.stroke();
    });
    lm.forEach((pt, i) => {
      this.ctx.beginPath();
      this.ctx.arc(pt.x * w, pt.y * h, i === 8 ? 5 : 2.5, 0, Math.PI * 2);
      this.ctx.fillStyle = i === 8 ? '#ff00ff' : '#00f2ff';
      this.ctx.fill();
    });
  }
}
