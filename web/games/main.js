import { MemoryGame }          from './MemoryGame.js';
import { ShooterGame }         from './ShooterGame.js';
import { PokerGame }           from './PokerGame.js';
import { GameVoiceController } from './voice-controller.js';
import { GameGestureController } from './gesture-controller.js';

class AIOS {
    constructor() {
        this.apps = {
            memory:  { title: 'Memory Match',  class: MemoryGame,  instance: null },
            shooter: { title: 'Arena Shooter', class: ShooterGame, instance: null },
            poker:   { title: 'Poker Hands',   class: PokerGame,   instance: null }
        };
        this.activeApp  = null;
        this.isMuted    = false;
        this.audioCtx   = null;
        this.sounds     = {};
        this.ambientLoop = null;
        this.shooterLoop = null;

        this.voice   = new GameVoiceController();
        this.gesture = new GameGestureController();
    }

    async init() {
        this.setupIcons();
        this.setupClock();
        this.setupAudio();
        this.setupWindowFunctions();
        this.setupVoice();
        await this.setupGesture();
        this.setupHelpOverlay();
    }

    // ── App icons ──────────────────────────────────────────────────────────────
    setupIcons() {
        document.getElementById('app-memory').onclick  = () => this.openApp('memory');
        document.getElementById('app-shooter').onclick = () => this.openApp('shooter');
        document.getElementById('app-poker').onclick   = () => this.openApp('poker');
    }

    setupClock() {
        const tick = () => {
            document.getElementById('os-clock').textContent =
                new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        };
        tick();
        setInterval(tick, 1000);
    }

    // ── Window helpers exposed to inline onclick ───────────────────────────────
    setupWindowFunctions() {
        window.closeApp = (id) => {
            const win = document.getElementById(`window-${id}`);
            if (win) win.style.display = 'none';
            if (id === 'shooter') { this.stopShooterMusic(); this.startAmbientMusic(); }
            this.activeApp = null;
            this.voice.activeGame   = null;
            this.gesture.activeGame = null;
        };

        window.playSound = (name) => {
            if (this.isMuted || !this.audioCtx || !this.sounds[name]) return;
            const src = this.audioCtx.createBufferSource();
            src.buffer = this.sounds[name];
            src.connect(this.audioCtx.destination);
            src.start(0);
        };
    }

    // ── Audio ──────────────────────────────────────────────────────────────────
    async setupAudio() {
        document.getElementById('mute-toggle').onclick = () => {
            this.isMuted = !this.isMuted;
            document.getElementById('mute-toggle').textContent = this.isMuted ? '🔇' : '🔊';
            if (this.audioCtx) this.isMuted ? this.audioCtx.suspend() : this.audioCtx.resume();
        };

        const unlock = async () => {
            if (!this.audioCtx) {
                this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                await this.loadSounds();
                this.startAmbientMusic();
            } else if (this.audioCtx.state === 'suspended' && !this.isMuted) {
                await this.audioCtx.resume();
            }
            if (this.activeApp === 'shooter') this.startShooterMusic();
        };
        document.body.addEventListener('click',      unlock, { once: true });
        document.body.addEventListener('touchstart', unlock, { once: true });
    }

    async loadSounds() {
        const urls = {
            os_ambient:       'assets/audio/os_ambient_loop.mp3',
            shooter_music:    'assets/audio/shooter_music_loop.mp3',
            laser_shot:       'assets/audio/laser_shot.mp3',
            explosion_digital:'assets/audio/explosion_digital.mp3',
            ui_success_chime: 'assets/audio/ui_success_chime.mp3'
        };
        await Promise.all(Object.entries(urls).map(async ([name, url]) => {
            try {
                const buf = await (await fetch(url)).arrayBuffer();
                this.sounds[name] = await this.audioCtx.decodeAudioData(buf);
            } catch (e) { console.warn('[Audio] Could not load', name, e); }
        }));
    }

    startAmbientMusic() {
        if (this.ambientLoop || !this.sounds.os_ambient) return;
        this.ambientLoop = this.audioCtx.createBufferSource();
        this.ambientLoop.buffer = this.sounds.os_ambient;
        this.ambientLoop.loop = true;
        this.ambientLoop.connect(this.audioCtx.destination);
        this.ambientLoop.start(0);
    }

    stopAmbientMusic() {
        if (this.ambientLoop) { this.ambientLoop.stop(); this.ambientLoop = null; }
    }

    startShooterMusic() {
        this.stopAmbientMusic();
        if (this.shooterLoop || !this.sounds.shooter_music) return;
        this.shooterLoop = this.audioCtx.createBufferSource();
        this.shooterLoop.buffer = this.sounds.shooter_music;
        this.shooterLoop.loop = true;
        this.shooterLoop.connect(this.audioCtx.destination);
        this.shooterLoop.start(0);
    }

    stopShooterMusic() {
        if (this.shooterLoop) { this.shooterLoop.stop(); this.shooterLoop = null; }
    }

    // ── Open app ───────────────────────────────────────────────────────────────
    openApp(id) {
        // Close any existing window
        if (this.activeApp && this.activeApp !== id) window.closeApp(this.activeApp);

        const win  = document.getElementById(`window-${id}`);
        const root = document.getElementById(`${id}-root`);
        win.style.display = 'flex';

        this.apps[id].instance = new this.apps[id].class(root);
        this.apps[id].instance.init();

        this.activeApp = id;
        this.voice.activeGame   = id;
        this.gesture.activeGame = id;

        if (id === 'shooter') this.startShooterMusic();
    }

    // ── Voice controller ───────────────────────────────────────────────────────
    setupVoice() {
        const statusEl = document.getElementById('voice-status');
        const toggleEl = document.getElementById('voice-toggle');
        const ok = this.voice.init(statusEl);

        if (toggleEl) {
            toggleEl.onclick = () => {
                this.voice.toggle();
                toggleEl.classList.toggle('active', this.voice.isActive);
            };
        }

        // ── Global OS events ───────────────────────────────────────────────
        this.voice.on('openApp',  id  => this.openApp(id));
        this.voice.on('closeApp', id  => { if (id) window.closeApp(id); });
        this.voice.on('mute',     ()  => {
            if (!this.isMuted) document.getElementById('mute-toggle').click();
        });
        this.voice.on('unmute',   ()  => {
            if (this.isMuted) document.getElementById('mute-toggle').click();
        });
        this.voice.on('showHelp', ()  => this.toggleHelp(true));

        // ── Memory events ──────────────────────────────────────────────────
        this.voice.on('memory:restart', () => this._game('memory')?.restart());
        this.voice.on('memory:hint',    () => this._game('memory')?.revealHint());
        this.voice.on('memory:flip',    i  => this._game('memory')?.flipCardByIndex(i));

        // ── Shooter events ─────────────────────────────────────────────────
        this.voice.on('shooter:restart', () => this._game('shooter')?.restart());
        this.voice.on('shooter:fire',    () => this._game('shooter')?.setAutoFire(true));
        this.voice.on('shooter:stopfire',() => this._game('shooter')?.setAutoFire(false));
        this.voice.on('shooter:move',    ({ dx, dy }) => this._game('shooter')?.setVoiceMove(dx, dy));

        // ── Poker events ───────────────────────────────────────────────────
        this.voice.on('poker:restart', () => this._game('poker')?.restart());
        this.voice.on('poker:analyze', () => this._game('poker')?.submitHand());
        this.voice.on('poker:clear',   () => this._game('poker')?.clearSelection());
        this.voice.on('poker:select',  i  => this._game('poker')?.toggleCardAt(i));

        if (ok) console.log('[AIOS] Voice controller ready');
    }

    // ── Gesture controller ─────────────────────────────────────────────────────
    async setupGesture() {
        const pipEl     = document.getElementById('gesture-pip');
        const statusEl  = document.getElementById('gesture-status');
        const cursorEl  = document.getElementById('gesture-cursor');
        const toggleEl  = document.getElementById('gesture-toggle');

        await this.gesture.init(pipEl, statusEl, cursorEl);

        if (toggleEl) {
            toggleEl.onclick = async () => {
                await this.gesture.toggle();
                toggleEl.classList.toggle('active', this.gesture.isActive);
                if (pipEl) pipEl.style.display = this.gesture.isActive ? 'block' : 'none';
            };
        }

        // ── Desktop hit-test ───────────────────────────────────────────────
        this.gesture.on('gesture:click', ({ x, y }) => {
            const el = document.elementFromPoint(x * window.innerWidth, y * window.innerHeight);
            const icon = el?.closest('.app-icon');
            if (icon) icon.click();
        });

        // ── Memory events ──────────────────────────────────────────────────
        this.gesture.on('memory:gesture:flip', ({ x, y }) =>
            this._game('memory')?.flipCardByPosition(x, y));
        this.gesture.on('memory:hint',    () => this._game('memory')?.revealHint());
        this.gesture.on('memory:restart', () => this._game('memory')?.restart());

        // ── Shooter events ─────────────────────────────────────────────────
        this.gesture.on('shooter:fire',    () => this._game('shooter')?.setAutoFire(true));
        this.gesture.on('shooter:stopfire',() => this._game('shooter')?.setAutoFire(false));
        this.gesture.on('shooter:restart', () => this._game('shooter')?.restart());
        this.gesture.on('shooter:move',    ({ dx, dy }) => this._game('shooter')?.setVoiceMove(dx, dy));
        this.gesture.on('shooter:handpos', ({ x, y }) => this._game('shooter')?.setHandPosition(x, y));

        // ── Poker events ───────────────────────────────────────────────────
        this.gesture.on('poker:gesture:select', ({ x, y }) =>
            this._game('poker')?.toggleCardByPosition(x, y));
        this.gesture.on('poker:analyze', () => this._game('poker')?.submitHand());
        this.gesture.on('poker:clear',   () => this._game('poker')?.clearSelection());

        console.log('[AIOS] Gesture controller ready');
    }

    // ── Help overlay ───────────────────────────────────────────────────────────
    setupHelpOverlay() {
        document.getElementById('help-toggle')?.addEventListener('click', () => this.toggleHelp());
        document.getElementById('help-close')?.addEventListener('click', () => this.toggleHelp(false));
    }

    toggleHelp(force) {
        const el = document.getElementById('help-overlay');
        if (!el) return;
        const show = force !== undefined ? force : el.style.display === 'none';
        el.style.display = show ? 'flex' : 'none';
    }

    // ── Utility ────────────────────────────────────────────────────────────────
    _game(id) { return this.apps[id]?.instance; }
}

const os = new AIOS();
os.init();
