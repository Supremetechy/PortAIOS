/**
 * AIOS Games - Voice Command Controller
 * Routes Web Speech API transcripts to game-specific actions.
 * Uses wake words: "hey aios", "aios", "computer"
 */

export class GameVoiceController {
  constructor() {
    this.recognition = null;
    this.isActive = false;
    this.isAwake = false;
    this.activeGame = null; // 'memory' | 'shooter' | 'poker' | null
    this._handlers = {};
    this.statusEl = null;
    this.wakeWords = ['hey aios', 'aios', 'computer', 'activate'];
    this._sleepTimer = null;
    this.supported = false;
  }

  // ── Event bus ──────────────────────────────────────────────────────────────
  on(event, handler) { this._handlers[event] = handler; }
  emit(event, data)  { if (this._handlers[event]) this._handlers[event](data); }

  // ── Init ───────────────────────────────────────────────────────────────────
  init(statusEl) {
    this.statusEl = statusEl;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      this.setStatus('🎤 Unsupported', 'error');
      return false;
    }
    this.supported = true;
    this.recognition = new SR();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = 'en-US';

    this.recognition.onresult = (e) => {
      const result = e.results[e.results.length - 1];
      const text = result[0].transcript.toLowerCase().trim();
      if (result.isFinal) {
        this._route(text);
      } else {
        this.setStatus(`🎤 "${text}"`, 'interim');
      }
    };

    this.recognition.onend = () => {
      if (this.isActive) setTimeout(() => this._safeStart(), 200);
    };

    this.recognition.onerror = (e) => {
      if (e.error !== 'no-speech' && e.error !== 'aborted') {
        console.warn('[Voice]', e.error);
      }
    };

    return true;
  }

  _safeStart() {
    try { this.recognition.start(); } catch (_) { /* already running */ }
  }

  // ── Public controls ────────────────────────────────────────────────────────
  enable() {
    if (!this.supported) return;
    this.isActive = true;
    this._safeStart();
    this.setStatus('🎤 Say "Hey AIOS"', 'standby');
  }

  disable() {
    if (!this.supported) return;
    this.isActive = false;
    try { this.recognition.stop(); } catch (_) {}
    this.setStatus('🎤 Off', 'idle');
  }

  toggle() { this.isActive ? this.disable() : this.enable(); }

  setStatus(text, state = 'idle') {
    if (!this.statusEl) return;
    this.statusEl.textContent = text;
    this.statusEl.dataset.state = state;
  }

  // ── Routing ────────────────────────────────────────────────────────────────
  _route(transcript) {
    if (!this.isAwake) {
      const hit = this.wakeWords.find(w => transcript.includes(w));
      if (!hit) return;
      this.isAwake = true;
      this.setStatus('🎤 Awake!', 'awake');
      setTimeout(() => this.setStatus('🎤 Listening...', 'active'), 1200);
      this._resetSleep();
      const rest = transcript.slice(transcript.indexOf(hit) + hit.length).trim();
      if (rest) this._routeCommand(rest);
      return;
    }
    this._routeCommand(transcript);
  }

  _routeCommand(cmd) {
    this.setStatus(`🎤 "${cmd}"`, 'command');
    setTimeout(() => this.setStatus('🎤 Listening...', 'active'), 2000);
    this._resetSleep();

    // ── Global OS ──────────────────────────────────────────────────────────
    if (/open memory|memory match|play memory/.test(cmd))  return this.emit('openApp', 'memory');
    if (/open shooter|arena shooter|play shooter/.test(cmd)) return this.emit('openApp', 'shooter');
    if (/open poker|poker hands|play poker/.test(cmd))     return this.emit('openApp', 'poker');
    if (/\b(close|exit|quit|desktop)\b/.test(cmd))         return this.emit('closeApp', this.activeGame);
    if (/\bmute\b/.test(cmd))                               return this.emit('mute');
    if (/unmute|sound on/.test(cmd))                        return this.emit('unmute');
    if (/help|commands|cheat sheet/.test(cmd))              return this.emit('showHelp');
    if (/sleep|goodbye/.test(cmd)) {
      this.isAwake = false;
      this.setStatus('🎤 Say "Hey AIOS"', 'standby');
      return;
    }

    // ── Game-specific ──────────────────────────────────────────────────────
    switch (this.activeGame) {
      case 'memory':  return this._routeMemory(cmd);
      case 'shooter': return this._routeShooter(cmd);
      case 'poker':   return this._routePoker(cmd);
    }
  }

  _routeMemory(cmd) {
    if (/restart|new game|reset/.test(cmd)) return this.emit('memory:restart');
    if (/\bhint\b/.test(cmd))               return this.emit('memory:hint');
    const m = cmd.match(/flip\s+(?:card\s+)?(\w+)/);
    if (m) {
      const n = this._word2num(m[1]);
      if (n >= 1 && n <= 16) this.emit('memory:flip', n - 1);
    }
  }

  _routeShooter(cmd) {
    if (/restart|reboot|new game/.test(cmd))        return this.emit('shooter:restart');
    if (/\b(fire|shoot|attack|open fire)\b/.test(cmd)) return this.emit('shooter:fire');
    if (/cease fire|stop (fire|shooting)/.test(cmd))   return this.emit('shooter:stopfire');
    if (/move up|go up|north/.test(cmd))    return this.emit('shooter:move', { dx: 0, dy: -1 });
    if (/move down|go down|south/.test(cmd)) return this.emit('shooter:move', { dx: 0, dy: 1 });
    if (/move left|go left|west/.test(cmd)) return this.emit('shooter:move', { dx: -1, dy: 0 });
    if (/move right|go right|east/.test(cmd)) return this.emit('shooter:move', { dx: 1, dy: 0 });
  }

  _routePoker(cmd) {
    if (/restart|new game|reset/.test(cmd))              return this.emit('poker:restart');
    if (/analyze|submit|confirm|scan|check/.test(cmd))   return this.emit('poker:analyze');
    if (/clear|deselect all|reset selection/.test(cmd))  return this.emit('poker:clear');
    const m = cmd.match(/select\s+(?:card\s+)?(\w+)/);
    if (m) {
      const n = this._word2num(m[1]);
      if (n >= 1 && n <= 8) this.emit('poker:select', n - 1);
    }
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  _word2num(word) {
    const map = { one:1, two:2, three:3, four:4, five:5, six:6, seven:7, eight:8,
                  nine:9, ten:10, eleven:11, twelve:12, thirteen:13, fourteen:14,
                  fifteen:15, sixteen:16 };
    return map[word.toLowerCase()] ?? parseInt(word, 10);
  }

  _resetSleep() {
    clearTimeout(this._sleepTimer);
    this._sleepTimer = setTimeout(() => {
      this.isAwake = false;
      this.setStatus('🎤 Say "Hey AIOS"', 'standby');
    }, 60000);
  }
}
