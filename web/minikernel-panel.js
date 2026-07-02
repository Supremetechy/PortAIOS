/**
 * MiniKernelPanel
 *
 * Wires the MiniKernel AI pipeline (intent → validate → execute) into the
 * AIOS web UI via the eel Python bridge.
 *
 * Responsibilities:
 *   - Boots minikernel via eel.minikernel_boot()
 *   - Polls service status every 3 s via eel.minikernel_status()
 *   - Routes commands through eel.minikernel_command()
 *   - Renders results in #mk-output
 *   - Drives the #dot-mk top-bar stat chip
 */

export class MiniKernelPanel {
    /**
     * @param {object} opts
     * @param {function} opts.logActivity  - AIOS activity log function
     * @param {function} opts.speak        - AIOS speak(text, emotion) function
     * @param {function} opts.setActivity  - AIOS setActivity(state) function
     */
    constructor({ logActivity, speak, setActivity } = {}) {
        this._log         = logActivity || ((m) => console.log('[MK]', m));
        this._speak       = speak       || (() => {});
        this._setActivity = setActivity || (() => {});

        this._status    = 'offline';   // offline | booting | running | error
        this._pollTimer = null;
        this._history   = [];

        this._el = {};
        this._bindElements();
        this._wireButtons();
    }

    // ── DOM wiring ────────────────────────────────────────────────────────

    _bindElements() {
        this._el = {
            dot:      document.getElementById('dot-mk'),
            stateVal: document.getElementById('mk-state-val'),
            svcVal:   document.getElementById('mk-svc-val'),
            capVal:   document.getElementById('mk-cap-val'),
            memVal:   document.getElementById('mk-mem-val'),
            output:   document.getElementById('mk-output'),
            bootBtn:  document.getElementById('mk-boot-btn'),
            shutBtn:  document.getElementById('mk-shut-btn'),
            clearBtn: document.getElementById('mk-clear-btn'),
        };
    }

    _wireButtons() {
        this._el.bootBtn?.addEventListener('click', () => this.boot());
        this._el.shutBtn?.addEventListener('click', () => this.shutdown());
        this._el.clearBtn?.addEventListener('click', () => this._clearOutput());
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────

    /** Boot minikernel and begin polling. */
    async boot() {
        if (!this._eelReady()) {
            this._appendOutput('system', 'eel bridge unavailable — no backend');
            return;
        }
        this._setStatus('booting');
        this._appendOutput('system', 'Booting MiniKernel…');

        try {
            const res = await eel.minikernel_boot()();
            if (res.status === 'running') {
                this._appendOutput('system', 'MiniKernel already running.');
            }
        } catch (e) {
            this._appendOutput('error', 'Boot error: ' + e.message);
        }

        this._startPolling();
    }

    /** Gracefully shut down the minikernel. */
    async shutdown() {
        if (!this._eelReady()) return;
        try {
            await eel.minikernel_shutdown_kernel()();
            this._setStatus('offline');
            this._appendOutput('system', 'MiniKernel shut down.');
        } catch (e) {
            this._appendOutput('error', 'Shutdown error: ' + e.message);
        }
        this._stopPolling();
    }

    // ── Command handling ──────────────────────────────────────────────────

    /**
     * Attempt to handle a command through the minikernel pipeline.
     *
     * @returns {boolean} true if the command was consumed, false to fall through
     *                    to other handlers.
     */
    async handleCommand(text) {
        if (this._status !== 'running') return false;
        if (!this._eelReady('minikernel_command')) return false;

        this._appendOutput('cmd', '› ' + text);
        this._setActivity('thinking');

        try {
            const res = await eel.minikernel_command(text)();
            this._history.push({ cmd: text, result: res, ts: new Date().toISOString() });

            if (res.success) {
                const firstLine = (res.output || 'Done').split('\n')[0];
                this._appendOutput('ok', res.output || 'Done');
                this._log('MiniKernel: ' + firstLine);
                this._speak(firstLine, 'neutral');
            } else {
                const err = res.error || 'Unknown error';
                this._appendOutput('error', err);
                this._log('MiniKernel error: ' + err);
            }

            if (res.intent) {
                const { type, action, confidence } = res.intent;
                const pct  = ((confidence || 0) * 100).toFixed(0);
                const risk = res.risk ? ` · risk: ${res.risk}` : '';
                this._appendOutput('meta', `${type}/${action} @ ${pct}%${risk}`);
            }
        } catch (e) {
            this._appendOutput('error', 'eel error: ' + e.message);
            this._setActivity('idle');
            return false;
        }

        this._setActivity('idle');
        return true;
    }

    // ── Status polling ────────────────────────────────────────────────────

    _startPolling() {
        if (this._pollTimer) return;
        this._pollTimer = setInterval(() => this._pollStatus(), 3000);
        this._pollStatus();
    }

    _stopPolling() {
        clearInterval(this._pollTimer);
        this._pollTimer = null;
    }

    async _pollStatus() {
        if (!this._eelReady('minikernel_status')) return;
        try {
            const s = await eel.minikernel_status()();
            this._applyStatus(s);
        } catch (_) {}
    }

    _applyStatus(s) {
        const prev = this._status;
        this._setStatus(s.state);

        if (s.state === 'running' && prev !== 'running') {
            this._appendOutput('system', `Online · ${s.services} service(s) · ${s.memory_mb} MB`);
            if (s.capabilities?.length) {
                this._appendOutput('meta', 'caps: ' + s.capabilities.join(', '));
            }
        }

        if (this._el.stateVal) this._el.stateVal.textContent = (s.state || '—').toUpperCase();
        if (this._el.svcVal)   this._el.svcVal.textContent   = s.services ?? '—';
        if (this._el.memVal)   this._el.memVal.textContent   = (s.memory_mb ?? 0) + ' MB';
        if (this._el.capVal)   this._el.capVal.textContent   = (s.capabilities?.length ?? 0) + ' active';
    }

    // ── Internal helpers ──────────────────────────────────────────────────

    _setStatus(state) {
        this._status = state || 'offline';
        const dot = this._el.dot;
        if (!dot) return;
        dot.className = 'stat-dot';
        if (state === 'booting') dot.classList.add('warn');
        else if (state !== 'running') dot.classList.add('off');
    }

    _appendOutput(type, text) {
        const out = this._el.output;
        if (!out) return;
        const el = document.createElement('div');
        el.className = 'mk-line mk-' + type;
        // Preserve newlines in multi-line results
        el.style.whiteSpace = 'pre-wrap';
        el.textContent = text;
        out.appendChild(el);
        out.scrollTop = out.scrollHeight;
        while (out.children.length > 300) out.removeChild(out.firstChild);
    }

    _clearOutput() {
        if (this._el.output) this._el.output.innerHTML = '';
    }

    _eelReady(fn) {
        return typeof eel !== 'undefined' && (!fn || typeof eel[fn] === 'function');
    }

    /** Expose current status for external checks. */
    get status() { return this._status; }
}
