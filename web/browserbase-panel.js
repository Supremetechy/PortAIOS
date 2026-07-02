/**
 * PortAIOS · Browserbase Panel
 * Cloud browser automation control panel.
 *
 * Embeds the Browserbase live session viewer inside PortAIOS and exposes
 * controls for creating sessions, running automation tasks, and navigating
 * via voice or text input.
 */

class BrowserbasePanel {
  constructor(container, options = {}) {
    this.container    = container;
    this.sessionId    = null;
    this.liveViewUrl  = null;
    this.taskHistory  = [];
    this.onClose      = options.onClose || null;
    this._statusTimer = null;
    this._render();
  }

  // ──────────────────────────────────────────────
  // Render
  // ──────────────────────────────────────────────
  _render() {
    this.container.innerHTML = `
      <div class="bb-panel" id="bb-root">

        <!-- Header bar -->
        <div class="bb-header">
          <div class="bb-logo">
            <span class="bb-dot"></span>
            <span>BROWSERBASE</span>
            <span class="bb-badge" id="bb-status-badge">OFFLINE</span>
          </div>
          <div class="bb-header-actions">
            <button class="bb-btn bb-btn-sm" id="bb-config-btn" title="Configure API key">⚙ Config</button>
            <button class="bb-btn bb-btn-sm bb-btn-danger" id="bb-close-btn">✕ Close</button>
          </div>
        </div>

        <!-- Config panel (hidden by default) -->
        <div class="bb-config-panel" id="bb-config-panel" style="display:none;">
          <div class="bb-config-row">
            <label class="bb-label">API Key</label>
            <input class="bb-input" id="bb-api-key" type="password" placeholder="bb_live_..." autocomplete="off">
          </div>
          <div class="bb-config-row">
            <label class="bb-label">Project ID</label>
            <input class="bb-input" id="bb-project-id" type="text" placeholder="your-project-id">
          </div>
          <div class="bb-config-row bb-config-actions">
            <button class="bb-btn bb-btn-primary" id="bb-save-config-btn">Save</button>
            <span class="bb-config-hint">
              Get your keys at <code>browserbase.com</code>
            </span>
          </div>
        </div>

        <!-- Session controls -->
        <div class="bb-session-bar">
          <button class="bb-btn bb-btn-primary" id="bb-new-session-btn">▶ New Session</button>
          <span class="bb-session-id" id="bb-session-id">No active session</span>
          <button class="bb-btn bb-btn-danger bb-btn-sm" id="bb-stop-session-btn" style="display:none;">■ Stop</button>
        </div>

        <!-- URL navigation bar -->
        <div class="bb-nav-bar" id="bb-nav-bar" style="display:none;">
          <input class="bb-url-input" id="bb-url-input" type="text"
                 placeholder="Enter URL or describe a task…">
          <button class="bb-btn bb-btn-primary bb-btn-sm" id="bb-go-btn">Go</button>
          <button class="bb-btn bb-btn-sm" id="bb-automate-btn" title="Run as automation task">⚡ Automate</button>
        </div>

        <!-- Main area: live viewer or setup prompt -->
        <div class="bb-main" id="bb-main">
          <div class="bb-empty" id="bb-empty">
            <div class="bb-empty-icon">☁</div>
            <div class="bb-empty-title">Cloud Browser Ready</div>
            <div class="bb-empty-hint">
              Click <strong>New Session</strong> to launch a remote Browserbase browser.<br>
              Control it by voice: <em>"open browserbase"</em>, <em>"automate google search for AI news"</em>
            </div>
          </div>
          <iframe class="bb-frame" id="bb-frame"
                  sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
                  src="about:blank" style="display:none;"></iframe>
        </div>

        <!-- Task history / log -->
        <div class="bb-log" id="bb-log"></div>
      </div>
    `;

    this._injectStyles();
    this._bindEvents();
    this._checkConfig();
  }

  _bindEvents() {
    const q = (id) => this.container.querySelector(`#${id}`);

    q('bb-close-btn').addEventListener('click', () => {
      if (this.sessionId) this.stopSession().then(() => this.onClose?.());
      else this.onClose?.();
    });

    q('bb-config-btn').addEventListener('click', () => {
      const panel = q('bb-config-panel');
      panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    });

    q('bb-save-config-btn').addEventListener('click', () => this._saveConfig());

    q('bb-new-session-btn').addEventListener('click', () => this.createSession());
    q('bb-stop-session-btn').addEventListener('click', () => this.stopSession());
    q('bb-go-btn').addEventListener('click', () => this._handleGo());
    q('bb-automate-btn').addEventListener('click', () => this._handleAutomate());

    q('bb-url-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this._handleGo();
    });
  }

  // ──────────────────────────────────────────────
  // Config
  // ──────────────────────────────────────────────
  async _checkConfig() {
    if (typeof eel === 'undefined') return;
    try {
      const cfg = await eel.browserbase_get_config()();
      if (!cfg.configured) this._showConfigPanel();
    } catch (_) {}
  }

  _showConfigPanel() {
    const panel = this.container.querySelector('#bb-config-panel');
    if (panel) panel.style.display = 'block';
  }

  async _saveConfig() {
    const apiKey    = this.container.querySelector('#bb-api-key')?.value?.trim();
    const projectId = this.container.querySelector('#bb-project-id')?.value?.trim();
    if (!apiKey || !projectId) {
      this._log('Both API Key and Project ID are required', 'error');
      return;
    }
    this._log('Saving Browserbase configuration…');
    const result = await eel.browserbase_set_config(apiKey, projectId)();
    if (result.success) {
      this._log('Configuration saved', 'success');
      this.container.querySelector('#bb-config-panel').style.display = 'none';
    } else {
      this._log(result.message, 'error');
    }
  }

  // ──────────────────────────────────────────────
  // Session lifecycle
  // ──────────────────────────────────────────────
  async createSession() {
    this._log('Creating Browserbase session…');
    this._setBadge('CONNECTING', '#f0a500');
    this.container.querySelector('#bb-new-session-btn').disabled = true;

    try {
      const result = await eel.browserbase_create_session()();
      if (!result.success) {
        this._log(result.message, 'error');
        this._setBadge('ERROR', '#ff4444');
        this.container.querySelector('#bb-new-session-btn').disabled = false;
        return;
      }

      const { session } = result;
      this.sessionId   = session.session_id;
      this.liveViewUrl = session.live_view_url;

      this._log(`Session started: ${this.sessionId.slice(0, 12)}…`, 'success');
      this._setBadge('LIVE', '#00ff88');
      this._showSessionActive();
      this._loadLiveView(this.liveViewUrl);
    } catch (err) {
      this._log(`Error: ${err.message || err}`, 'error');
      this._setBadge('ERROR', '#ff4444');
      this.container.querySelector('#bb-new-session-btn').disabled = false;
    }
  }

  async stopSession() {
    if (!this.sessionId) return;
    this._log(`Stopping session ${this.sessionId.slice(0, 12)}…`);
    try {
      await eel.browserbase_stop_session(this.sessionId)();
    } catch (_) {}
    this.sessionId   = null;
    this.liveViewUrl = null;
    this._showSessionInactive();
    this._setBadge('OFFLINE', '#888');
    this._clearFrame();
    this._log('Session stopped', 'info');
  }

  // ──────────────────────────────────────────────
  // Navigation / automation
  // ──────────────────────────────────────────────
  async navigateTo(url) {
    if (!this.sessionId) { this._log('No active session — create one first', 'error'); return; }
    if (!url.startsWith('http')) url = 'https://' + url;
    this._log(`Navigating to ${url}…`);
    const result = await eel.browserbase_navigate(this.sessionId, url)();
    if (result.success) this._log(`Navigated → ${url}`, 'success');
    else this._log(result.message, 'error');
  }

  async runTask(task) {
    if (!this.sessionId) { this._log('No active session — create one first', 'error'); return; }
    this._log(`⚡ Automating: ${task}`);
    const result = await eel.browserbase_run_task(this.sessionId, task)();
    if (result.success) this._log(`Done: ${result.message}`, 'success');
    else this._log(result.message, 'error');
  }

  // ──────────────────────────────────────────────
  // UI helpers
  // ──────────────────────────────────────────────
  _handleGo() {
    const val = this.container.querySelector('#bb-url-input')?.value?.trim();
    if (!val) return;
    // If it looks like a URL, navigate; otherwise treat as task
    if (val.includes('.') && !val.includes(' ')) {
      this.navigateTo(val);
    } else {
      this.runTask(`go to ${val}`);
    }
  }

  _handleAutomate() {
    const val = this.container.querySelector('#bb-url-input')?.value?.trim();
    if (!val) return;
    this.runTask(val);
  }

  _showSessionActive() {
    const q = (id) => this.container.querySelector(`#${id}`);
    q('bb-new-session-btn').disabled = false;
    q('bb-new-session-btn').style.display = 'none';
    q('bb-stop-session-btn').style.display = 'inline-flex';
    q('bb-session-id').textContent = `Session: ${this.sessionId?.slice(0, 16)}…`;
    q('bb-nav-bar').style.display = 'flex';
    q('bb-empty').style.display = 'none';
    q('bb-frame').style.display = 'block';
  }

  _showSessionInactive() {
    const q = (id) => this.container.querySelector(`#${id}`);
    q('bb-new-session-btn').disabled = false;
    q('bb-new-session-btn').style.display = 'inline-flex';
    q('bb-stop-session-btn').style.display = 'none';
    q('bb-session-id').textContent = 'No active session';
    q('bb-nav-bar').style.display = 'none';
    q('bb-empty').style.display = 'flex';
    q('bb-frame').style.display = 'none';
  }

  _loadLiveView(url) {
    const frame = this.container.querySelector('#bb-frame');
    if (frame) frame.src = url;
  }

  _clearFrame() {
    const frame = this.container.querySelector('#bb-frame');
    if (frame) frame.src = 'about:blank';
  }

  _setBadge(text, color) {
    const badge = this.container.querySelector('#bb-status-badge');
    if (badge) {
      badge.textContent = text;
      badge.style.background = color;
    }
  }

  _log(message, type = 'info') {
    const log = this.container.querySelector('#bb-log');
    if (!log) return;
    const colors = { info: 'rgba(0,255,255,.65)', success: '#00ff88', error: '#ff5555' };
    const entry = document.createElement('div');
    entry.style.cssText = `
      padding:4px 10px; font-size:.78em; color:${colors[type] || colors.info};
      border-left:2px solid ${colors[type] || colors.info};
      margin-bottom:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    `;
    const time = new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});
    entry.textContent = `[${time}] ${message}`;
    log.insertBefore(entry, log.firstChild);
    // Keep last 20 entries
    while (log.children.length > 20) log.removeChild(log.lastChild);
    this.taskHistory.unshift({ time, message, type });
  }

  // ──────────────────────────────────────────────
  // Styles
  // ──────────────────────────────────────────────
  _injectStyles() {
    if (document.getElementById('bb-panel-styles')) return;
    const s = document.createElement('style');
    s.id = 'bb-panel-styles';
    s.textContent = `
      .bb-panel {
        height: 100%; display: flex; flex-direction: column;
        background: rgba(0,8,18,.97); color: #00ffff;
        font-family: 'Courier New', monospace; overflow: hidden;
      }
      .bb-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 8px 14px; border-bottom: 1px solid rgba(0,255,255,.2);
        background: rgba(0,255,255,.04); flex-shrink: 0;
      }
      .bb-logo { display: flex; align-items: center; gap: 10px; font-size: .85em; letter-spacing: 2px; }
      .bb-dot {
        width: 8px; height: 8px; background: #00ff88; border-radius: 50%;
        box-shadow: 0 0 6px #00ff88;
      }
      .bb-badge {
        font-size: .7em; padding: 2px 8px; border-radius: 3px;
        background: #888; color: #000; font-weight: bold; letter-spacing: 1px;
        transition: background .3s;
      }
      .bb-header-actions { display: flex; gap: 6px; }
      .bb-btn {
        display: inline-flex; align-items: center; gap: 5px;
        background: rgba(0,255,255,.08); border: 1px solid rgba(0,255,255,.3);
        color: #00ffff; padding: 6px 13px; cursor: pointer; border-radius: 4px;
        font-family: 'Courier New', monospace; font-size: .82em;
        transition: all .15s;
      }
      .bb-btn:hover { background: rgba(0,255,255,.18); border-color: #00ffff; }
      .bb-btn:disabled { opacity: .4; cursor: not-allowed; }
      .bb-btn-sm { padding: 4px 9px; font-size: .75em; }
      .bb-btn-primary { background: rgba(0,255,136,.12); border-color: #00ff88; color: #00ff88; }
      .bb-btn-primary:hover { background: rgba(0,255,136,.25); }
      .bb-btn-danger { background: rgba(255,60,60,.08); border-color: rgba(255,80,80,.5); color: #ff5555; }
      .bb-btn-danger:hover { background: rgba(255,60,60,.2); }
      .bb-config-panel {
        background: rgba(0,255,255,.03); border-bottom: 1px solid rgba(0,255,255,.15);
        padding: 12px 14px; flex-shrink: 0;
      }
      .bb-config-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
      .bb-config-actions { justify-content: flex-start; }
      .bb-config-hint { font-size: .75em; color: rgba(0,255,255,.5); }
      .bb-label { font-size: .78em; min-width: 80px; color: rgba(0,255,255,.7); }
      .bb-input {
        flex: 1; background: rgba(0,255,255,.06); border: 1px solid rgba(0,255,255,.25);
        color: #00ffff; padding: 6px 10px; border-radius: 4px;
        font-family: 'Courier New', monospace; font-size: .83em; outline: none;
      }
      .bb-input:focus { border-color: #00ffff; }
      .bb-session-bar {
        display: flex; align-items: center; gap: 10px;
        padding: 7px 14px; border-bottom: 1px solid rgba(0,255,255,.15);
        background: rgba(0,255,255,.02); flex-shrink: 0;
      }
      .bb-session-id { flex: 1; font-size: .78em; color: rgba(0,255,255,.6); }
      .bb-nav-bar {
        display: flex; gap: 6px; align-items: center;
        padding: 6px 14px; border-bottom: 1px solid rgba(0,255,255,.12);
        flex-shrink: 0;
      }
      .bb-url-input {
        flex: 1; background: rgba(0,255,255,.06); border: 1px solid rgba(0,255,255,.25);
        color: #00ffff; padding: 7px 12px; border-radius: 4px;
        font-family: 'Courier New', monospace; font-size: .84em; outline: none;
      }
      .bb-url-input:focus { border-color: #00ffff; }
      .bb-main { flex: 1; position: relative; overflow: hidden; }
      .bb-frame { width: 100%; height: 100%; border: none; display: block; }
      .bb-empty {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        height: 100%; gap: 16px; padding: 40px; text-align: center;
      }
      .bb-empty-icon { font-size: 3.5em; opacity: .5; }
      .bb-empty-title { font-size: 1.1em; letter-spacing: 3px; color: rgba(0,255,255,.8); }
      .bb-empty-hint { font-size: .82em; color: rgba(0,255,255,.45); line-height: 1.7; max-width: 480px; }
      .bb-empty-hint em { color: rgba(0,255,255,.75); font-style: normal; }
      .bb-log {
        max-height: 110px; overflow-y: auto; border-top: 1px solid rgba(0,255,255,.12);
        padding: 6px 10px; flex-shrink: 0; background: rgba(0,0,0,.3);
      }
      .bb-log::-webkit-scrollbar { width: 4px; }
      .bb-log::-webkit-scrollbar-thumb { background: rgba(0,255,255,.2); }
    `;
    document.head.appendChild(s);
  }
}

window.BrowserbasePanel = BrowserbasePanel;
