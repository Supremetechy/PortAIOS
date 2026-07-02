/**
 * AIOS Terminal Panel
 *
 * Embeds a full PTY terminal powered by xterm.js into the AIOS HUD.
 * Multiple named sessions appear as tabs. The Python TerminalManager
 * streams output via eel.terminal_output(); keystrokes go back via
 * eel.terminal_input().
 *
 * Public API: window.aiosTerminal.{show, hide, toggle, createSession,
 *             activateSession, killSession, runCommand}
 */

(function () {
'use strict';

/* ─────────────────────────────────────────────────────────────────
   State
──────────────────────────────────────────────────────────────────── */
const _sessions = {};       // id → { term, fitAddon, name, wrapper }
let   _activeId  = null;
let   _panel     = null;
let   _tabBar    = null;
let   _termBody  = null;
let   _isVisible = false;
let   _xtermReady = false;
const _pendingInit = [];    // sessions queued while xterm.js loads

/* ─────────────────────────────────────────────────────────────────
   xterm.js loader — pulls from CDN once
──────────────────────────────────────────────────────────────────── */
function _loadXterm(cb) {
    if (window.Terminal && window.FitAddon) { cb(); return; }

    const css = document.createElement('link');
    css.rel   = 'stylesheet';
    css.href  = 'https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css';
    document.head.appendChild(css);

    function _loadFitAddon() {
        const s2 = document.createElement('script');
        s2.src   = 'https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js';
        s2.onload = () => { _xtermReady = true; cb(); };
        s2.onerror = () => console.error('[Terminal] Failed to load xterm-addon-fit');
        document.head.appendChild(s2);
    }

    const s1 = document.createElement('script');
    s1.src   = 'https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js';
    s1.onload = _loadFitAddon;
    s1.onerror = () => console.error('[Terminal] Failed to load xterm.js');
    document.head.appendChild(s1);
}

/* ─────────────────────────────────────────────────────────────────
   CSS injection
──────────────────────────────────────────────────────────────────── */
function _injectStyles() {
    if (document.getElementById('aios-term-css')) return;
    const style = document.createElement('style');
    style.id = 'aios-term-css';
    style.textContent = `
/* ── Terminal panel shell ────────────────────────────────────── */
#aios-terminal-panel {
    position: fixed;
    bottom: 0; left: 0; right: 0;
    height: 42vh;
    min-height: 180px;
    background: rgba(0,6,2,0.97);
    border-top: 1px solid rgba(0,255,157,0.28);
    z-index: 200;
    display: flex;
    flex-direction: column;
    font-family: 'Share Tech Mono','Courier New',monospace;
    box-shadow: 0 -6px 40px rgba(0,255,157,0.10), 0 -1px 0 rgba(0,255,157,0.05);
    transform: translateY(100%);
    transition: transform 0.28s cubic-bezier(0.4,0,0.2,1);
    user-select: none;
}
#aios-terminal-panel.aios-term-visible {
    transform: translateY(0);
}

/* ── Header ─────────────────────────────────────────────────── */
.aios-term-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 10px;
    background: rgba(0,255,157,0.04);
    border-bottom: 1px solid rgba(0,255,157,0.14);
    flex-shrink: 0;
    height: 30px;
}
.aios-term-title {
    color: #00ff9d;
    font-size: 9px;
    letter-spacing: 2px;
    white-space: nowrap;
    text-shadow: 0 0 8px #00ff9d66;
}

/* ── Session tabs ────────────────────────────────────────────── */
.aios-term-tabs {
    display: flex;
    gap: 2px;
    flex: 1;
    overflow-x: auto;
    scrollbar-width: none;
    align-items: center;
}
.aios-term-tabs::-webkit-scrollbar { display: none; }
.aios-term-tab {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 2px 10px;
    font-size: 10px;
    color: rgba(0,255,157,0.5);
    border: 1px solid rgba(0,255,157,0.18);
    cursor: pointer;
    white-space: nowrap;
    background: transparent;
    transition: all 0.15s ease;
    border-radius: 2px;
    height: 22px;
}
.aios-term-tab:hover  { color:#00ff9d; border-color:rgba(0,255,157,0.4); }
.aios-term-tab.active { color:#00ff9d; border-color:#00ff9d; background:rgba(0,255,157,0.08);
                        text-shadow:0 0 8px #00ff9d55; }
.aios-term-tab-close {
    opacity: 0.45;
    font-size: 9px;
    line-height: 1;
    padding: 1px 2px;
    border-radius: 2px;
}
.aios-term-tab-close:hover { opacity: 1; background: rgba(255,0,0,0.2); color:#ff1744; }

/* ── Header action buttons ────────────────────────────────────── */
.aios-term-actions { display:flex; gap:4px; align-items:center; }
.aios-term-hbtn {
    background: transparent;
    border: 1px solid rgba(0,255,157,0.3);
    color: #00ff9d;
    padding: 2px 8px;
    font-size: 11px;
    font-family: inherit;
    cursor: pointer;
    border-radius: 2px;
    height: 22px;
    line-height: 1;
    transition: all 0.15s;
}
.aios-term-hbtn:hover { background:rgba(0,255,157,0.1); border-color:#00ff9d; }

/* ── Terminal body ───────────────────────────────────────────── */
.aios-term-body {
    flex: 1;
    position: relative;
    min-height: 0;
    overflow: hidden;
}
.aios-term-instance {
    position: absolute;
    inset: 6px 8px;
    display: none;
}
.aios-term-instance.active { display: block; }

/* ── Status bar ──────────────────────────────────────────────── */
.aios-term-statusbar {
    display: flex;
    justify-content: space-between;
    padding: 2px 10px;
    font-size: 9px;
    color: rgba(0,255,157,0.35);
    border-top: 1px solid rgba(0,255,157,0.08);
    flex-shrink: 0;
    height: 18px;
    align-items: center;
}
#aios-term-status  { color:rgba(0,255,157,0.6); }
#aios-term-dims    { letter-spacing:1px; }

/* ── Resize grip at top of panel ────────────────────────────── */
.aios-term-grip {
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    cursor: ns-resize;
    background: transparent;
}
.aios-term-grip:hover { background: rgba(0,255,157,0.12); }

/* ── Top-bar toggle button ───────────────────────────────────── */
#aios-term-toggle-btn {
    background: transparent;
    border: 1px solid rgba(0,255,157,0.4);
    color: #00ff9d;
    padding: 2px 10px;
    font-family: 'Share Tech Mono',monospace;
    font-size: 9px;
    letter-spacing: 1px;
    cursor: pointer;
    border-radius: 2px;
    transition: all 0.15s;
    height: 22px;
    white-space: nowrap;
}
#aios-term-toggle-btn:hover  { border-color:#00ff9d; background:rgba(0,255,157,0.08); }
#aios-term-toggle-btn.active { background:rgba(0,255,157,0.15); border-color:#00ff9d;
                                box-shadow:0 0 8px rgba(0,255,157,0.2); }

/* xterm.js overrides for AIOS palette */
.aios-term-instance .xterm            { height:100%; }
.aios-term-instance .xterm-viewport   { background:transparent !important; }
.aios-term-instance .xterm-screen     { }
    `;
    document.head.appendChild(style);
}

/* ─────────────────────────────────────────────────────────────────
   Build panel DOM
──────────────────────────────────────────────────────────────────── */
function _buildPanel() {
    if (_panel) return;
    _injectStyles();

    _panel = document.createElement('div');
    _panel.id = 'aios-terminal-panel';
    _panel.innerHTML = `
        <div class="aios-term-grip" id="aios-term-grip"></div>
        <div class="aios-term-header">
            <span class="aios-term-title">[ AIOS TERMINAL ]</span>
            <div class="aios-term-tabs" id="aios-term-tabs"></div>
            <div class="aios-term-actions">
                <button class="aios-term-hbtn" id="aios-term-new-btn" title="New session [Ctrl+Shift+T]">＋</button>
                <button class="aios-term-hbtn" id="aios-term-close-btn" title="Collapse panel">▼</button>
            </div>
        </div>
        <div class="aios-term-body" id="aios-term-body"></div>
        <div class="aios-term-statusbar">
            <span id="aios-term-status">● READY</span>
            <span id="aios-term-dims"></span>
        </div>
    `;
    document.body.appendChild(_panel);

    _tabBar    = document.getElementById('aios-term-tabs');
    _termBody  = document.getElementById('aios-term-body');

    document.getElementById('aios-term-new-btn').onclick   = () => createSession();
    document.getElementById('aios-term-close-btn').onclick = hideTerminal;

    _setupResizeGrip();
}

/* ─────────────────────────────────────────────────────────────────
   Drag-to-resize the panel from its top edge
──────────────────────────────────────────────────────────────────── */
function _setupResizeGrip() {
    const grip = document.getElementById('aios-term-grip');
    if (!grip) return;
    let startY = 0, startH = 0;

    grip.addEventListener('mousedown', e => {
        startY = e.clientY;
        startH = _panel.getBoundingClientRect().height;
        e.preventDefault();

        function onMove(ev) {
            const newH = Math.max(120, startH + (startY - ev.clientY));
            _panel.style.height = newH + 'px';
        }
        function onUp() {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            _refitActive();
        }
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    });
}

/* ─────────────────────────────────────────────────────────────────
   Create a new terminal session
──────────────────────────────────────────────────────────────────── */
async function createSession(name) {
    name = name || `shell-${Object.keys(_sessions).length + 1}`;

    if (!_panel) _buildPanel();
    if (!_isVisible) showTerminal();

    if (!_xtermReady) {
        // Load xterm.js then re-run
        _loadXterm(() => _createSessionNow(name));
        return;
    }
    _createSessionNow(name);
}

async function _createSessionNow(name) {
    let sessionId;
    try {
        sessionId = await eel.terminal_create(name)();
    } catch (err) {
        console.warn('[Terminal] Backend unavailable; demo session');
        sessionId = 'demo_' + Date.now();
    }
    _spawnXterm(sessionId, name);
    return sessionId;
}

/* ─────────────────────────────────────────────────────────────────
   Instantiate xterm.js inside a session wrapper div
──────────────────────────────────────────────────────────────────── */
function _spawnXterm(sessionId, name) {
    const wrapper = document.createElement('div');
    wrapper.className = 'aios-term-instance';
    wrapper.id = 'aios-term-' + sessionId;
    _termBody.appendChild(wrapper);

    const term = new Terminal({
        theme: {
            background:    '#000602',
            foreground:    '#00ff9d',
            cursor:        '#00ff9d',
            cursorAccent:  '#000602',
            selectionBackground: 'rgba(0,255,157,0.25)',
            black:         '#001a0d', brightBlack:   '#003318',
            red:           '#ff1744', brightRed:     '#ff4569',
            green:         '#00ff9d', brightGreen:   '#69ffb5',
            yellow:        '#ffc400', brightYellow:  '#ffd740',
            blue:          '#00f5ff', brightBlue:    '#40c4ff',
            magenta:       '#ff0080', brightMagenta: '#ff4dd9',
            cyan:          '#00e5ff', brightCyan:    '#18ffff',
            white:         '#e8fff4', brightWhite:   '#ffffff',
        },
        fontFamily: "'Share Tech Mono','Courier New',monospace",
        fontSize:   12,
        lineHeight: 1.3,
        cursorBlink: true,
        cursorStyle: 'block',
        scrollback:  5000,
        allowProposedApi: true,
        convertEol: false,
    });

    const fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(wrapper);

    _sessions[sessionId] = { term, fitAddon, name, wrapper, sessionId };

    requestAnimationFrame(() => {
        fitAddon.fit();
        _sendResize(sessionId, term.cols, term.rows);
    });

    term.onData(data => {
        try { eel.terminal_input(sessionId, data)(); } catch (_) {}
    });

    term.onResize(({ cols, rows }) => _sendResize(sessionId, cols, rows));

    _addTab(sessionId, name);
    activateSession(sessionId);

    // Replay scrollback from backend
    try {
        eel.terminal_scrollback(sessionId)().then(b64 => {
            if (b64) {
                const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
                if (bytes.length) term.write(bytes);
            }
        });
    } catch (_) {}
}

/* ─────────────────────────────────────────────────────────────────
   Tab management
──────────────────────────────────────────────────────────────────── */
function _addTab(sessionId, name) {
    const tab = document.createElement('div');
    tab.className = 'aios-term-tab';
    tab.id = 'aios-tab-' + sessionId;

    const label = document.createElement('span');
    label.textContent = name;

    const closeBtn = document.createElement('span');
    closeBtn.className = 'aios-term-tab-close';
    closeBtn.textContent = '✕';
    closeBtn.title = 'Close session';
    closeBtn.onclick = e => { e.stopPropagation(); killSession(sessionId); };

    tab.appendChild(label);
    tab.appendChild(closeBtn);
    tab.onclick = () => activateSession(sessionId);
    _tabBar.appendChild(tab);
}

function activateSession(sessionId) {
    if (!_sessions[sessionId]) return;
    _activeId = sessionId;

    document.querySelectorAll('.aios-term-tab').forEach(t => t.classList.remove('active'));
    const tab = document.getElementById('aios-tab-' + sessionId);
    if (tab) tab.classList.add('active');

    document.querySelectorAll('.aios-term-instance').forEach(el => el.classList.remove('active'));
    const wrapper = document.getElementById('aios-term-' + sessionId);
    if (wrapper) wrapper.classList.add('active');

    const s = _sessions[sessionId];
    if (s) {
        requestAnimationFrame(() => {
            s.fitAddon.fit();
            _sendResize(sessionId, s.term.cols, s.term.rows);
            s.term.focus();
            _updateDims(sessionId);
        });
    }
}

function killSession(sessionId) {
    try { eel.terminal_kill(sessionId)(); } catch (_) {}

    const s = _sessions[sessionId];
    if (s) {
        s.term.dispose();
        s.wrapper.remove();
        delete _sessions[sessionId];
    }
    const tab = document.getElementById('aios-tab-' + sessionId);
    if (tab) tab.remove();

    const remaining = Object.keys(_sessions);
    if (remaining.length > 0) {
        activateSession(remaining[remaining.length - 1]);
    } else {
        _activeId = null;
        const el = document.getElementById('aios-term-status');
        if (el) el.textContent = '● NO SESSIONS';
    }
}

function _sendResize(sessionId, cols, rows) {
    try { eel.terminal_resize(sessionId, cols, rows)(); } catch (_) {}
}

function _updateDims(sessionId) {
    const s = _sessions[sessionId];
    const el = document.getElementById('aios-term-dims');
    if (s && el) el.textContent = `${s.term.cols}×${s.term.rows}`;
}

function _refitActive() {
    if (!_activeId || !_sessions[_activeId]) return;
    const s = _sessions[_activeId];
    s.fitAddon.fit();
    _sendResize(_activeId, s.term.cols, s.term.rows);
    _updateDims(_activeId);
}

/* ─────────────────────────────────────────────────────────────────
   Eel callback — Python pushes output bytes here (base64-encoded)
──────────────────────────────────────────────────────────────────── */
eel.expose(function terminal_output(sessionId, b64Data) {
    const s = _sessions[sessionId];
    if (!s) return;

    if (b64Data === null || b64Data === undefined) {
        // Session exited
        s.term.writeln('\r\n\x1b[2m[session closed]\x1b[0m');
        const tab = document.getElementById('aios-tab-' + sessionId);
        if (tab) tab.style.opacity = '0.45';
        const statusEl = document.getElementById('aios-term-status');
        if (statusEl) { statusEl.textContent = '● CLOSED'; statusEl.style.color = 'rgba(255,23,68,0.6)'; }
        return;
    }

    try {
        const bytes = Uint8Array.from(atob(b64Data), c => c.charCodeAt(0));
        s.term.write(bytes);
    } catch (err) {
        console.warn('[Terminal] output decode error:', err);
    }
}, 'terminal_output');

/* ─────────────────────────────────────────────────────────────────
   Panel show / hide / toggle
──────────────────────────────────────────────────────────────────── */
function showTerminal(sessionId) {
    if (!_panel) _buildPanel();
    _panel.classList.add('aios-term-visible');
    _isVisible = true;

    const btn = document.getElementById('aios-term-toggle-btn');
    if (btn) btn.classList.add('active');

    if (Object.keys(_sessions).length === 0) {
        // First open — create initial session
        _loadXterm(() => _createSessionNow('main'));
    } else if (sessionId && _sessions[sessionId]) {
        activateSession(sessionId);
    } else if (_activeId && _sessions[_activeId]) {
        activateSession(_activeId);
    }

    setTimeout(_refitActive, 300);
}

function hideTerminal() {
    if (_panel) _panel.classList.remove('aios-term-visible');
    _isVisible = false;
    const btn = document.getElementById('aios-term-toggle-btn');
    if (btn) btn.classList.remove('active');
}

function toggleTerminal() {
    if (_isVisible) hideTerminal(); else showTerminal();
}

/* ─────────────────────────────────────────────────────────────────
   Keyboard shortcuts
──────────────────────────────────────────────────────────────────── */
document.addEventListener('keydown', e => {
    // Ctrl+` or Ctrl+~ to toggle
    if (e.ctrlKey && e.key === '`') {
        e.preventDefault();
        toggleTerminal();
    }
    // Ctrl+Shift+T — new tab when panel is visible
    if (e.ctrlKey && e.shiftKey && e.key === 'T' && _isVisible) {
        e.preventDefault();
        createSession();
    }
});

/* ─────────────────────────────────────────────────────────────────
   ResizeObserver — refit terminal when window or panel size changes
──────────────────────────────────────────────────────────────────── */
const _resizeObs = new ResizeObserver(() => {
    if (!_isVisible) return;
    requestAnimationFrame(_refitActive);
});

/* ─────────────────────────────────────────────────────────────────
   Inject top-bar toggle button + wire resize observer
──────────────────────────────────────────────────────────────────── */
function _initToggleButton() {
    if (document.getElementById('aios-term-toggle-btn')) return;
    const btn = document.createElement('button');
    btn.id        = 'aios-term-toggle-btn';
    btn.textContent = '⌨ TERMINAL';
    btn.title     = 'Toggle embedded terminal  (Ctrl+`)';
    btn.onclick   = toggleTerminal;

    // Insert before the clock in the top-bar, or append
    const topBar = document.getElementById('top-bar');
    const clock  = document.getElementById('clock');
    if (topBar && clock) {
        topBar.insertBefore(btn, clock);
    } else if (topBar) {
        topBar.appendChild(btn);
    }

    _resizeObs.observe(document.body);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _initToggleButton);
} else {
    _initToggleButton();
}

/* ─────────────────────────────────────────────────────────────────
   Public API
──────────────────────────────────────────────────────────────────── */
window.aiosTerminal = {
    show:            showTerminal,
    hide:            hideTerminal,
    toggle:          toggleTerminal,
    createSession,
    activateSession,
    killSession,

    /**
     * Run a shell command inside a named session, creating it if needed.
     * Called by the AIOS agent when it needs to execute a long-running task.
     *
     * @param {string} command      - Shell command string
     * @param {string} [sessionName] - Human-readable session name
     * @returns {Promise<string>}   - Resolves to the session ID
     */
    async runCommand(command, sessionName) {
        sessionName = sessionName || 'agent';

        // Reuse an existing session with the same name if alive
        const existing = Object.values(_sessions).find(s => s.name === sessionName);
        const sessionId = existing ? existing.sessionId : null;

        if (!_isVisible) showTerminal(sessionId || undefined);

        if (sessionId) {
            activateSession(sessionId);
            try { await eel.terminal_send_command(sessionId, command)(); } catch (_) {}
            return sessionId;
        }

        // Create a new named session then run the command
        return new Promise(resolve => {
            _loadXterm(async () => {
                let sid;
                try {
                    sid = await eel.terminal_create(sessionName)();
                } catch (_) {
                    sid = 'demo_' + Date.now();
                }
                _spawnXterm(sid, sessionName);
                // Give the shell 300 ms to print its prompt before sending the command
                setTimeout(async () => {
                    try { await eel.terminal_send_command(sid, command)(); } catch (_) {}
                    resolve(sid);
                }, 350);
            });
        });
    },

    get sessions() { return { ..._sessions }; },
    get activeId()  { return _activeId; },
    get isVisible() { return _isVisible; },
};

})();
