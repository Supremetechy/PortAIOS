/**
 * Dynamic UI Manager for AIOS Binary Avatar
 * Transforms the avatar display into live OS-native views:
 *   Dashboard · Desktop (file browser) · Document · Media · Terminal · Browser · Browserbase
 */

const UI_MODES = {
  AVATAR:       'avatar',
  DASHBOARD:    'dashboard',
  DESKTOP:      'desktop',
  DOCUMENT:     'document',
  MEDIA:        'media',
  TERMINAL:     'terminal',
  BROWSER:      'browser',
  BROWSERBASE:  'browserbase',
  TRANSITION:   'transition'
};

const TRANSITION_DURATION = 700;

class DynamicUIManager {
  constructor(container, avatarRenderer, options = {}) {
    this.container      = container;
    this.avatarRenderer = avatarRenderer;
    this.currentMode    = UI_MODES.AVATAR;
    this.previousMode   = null;
    this.isTransitioning = false;
    this.commandHistory  = [];

    this.uiContainers = {};
    this.options = {
      transitionDuration:   options.transitionDuration  || TRANSITION_DURATION,
      enableParticleEffects: options.enableParticleEffects !== false,
      enableNativeDesktop:   options.enableNativeDesktop  !== false,
      ...options
    };

    this.desktopBridge = null;
    this._dashClockTimer = null;
    this._init();
  }

  // ─────────────────────────────────────────────
  // Init
  // ─────────────────────────────────────────────
  _init() {
    this.overlayContainer = document.createElement('div');
    this.overlayContainer.id = 'dynamic-ui-overlay';
    this.overlayContainer.style.cssText = `
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      pointer-events: none; z-index: 10;
    `;
    this.container.appendChild(this.overlayContainer);

    this._createDashboardUI();
    this._createDesktopUI();
    this._createDocumentUI();
    this._createMediaUI();
    this._createTerminalUI();
    this._createBrowserUI();
    this._createBrowserbaseUI();

    if (this.options.enableNativeDesktop) {
      this._initializeDesktopBridge();
    }

    console.log('[DynamicUI] Initialized – modes:', Object.values(UI_MODES).filter(m => m !== 'transition').join(', '));
  }

  async _initializeDesktopBridge() {
    try {
      if (typeof NativeDesktopBridge !== 'undefined') {
        this.desktopBridge = new NativeDesktopBridge({
          onViewChange: (v) => this._handleDesktopViewChange(v),
          onError: (e) => console.error('[DynamicUI] Desktop bridge error:', e)
        });
        const ok = await this.desktopBridge.initialize();
        if (ok) console.log('[DynamicUI] Desktop bridge ready');
      }
    } catch (e) {
      console.error('[DynamicUI] Desktop bridge init failed:', e);
    }
  }

  _handleDesktopViewChange(viewData) {
    switch (viewData.view) {
      case 'desktop': this.showDesktop(viewData.data.files, viewData.data.path); break;
      case 'browser': this.showBrowser(viewData.data.url); break;
      case 'avatar':  this.backToAvatar(); break;
    }
  }

  // ─────────────────────────────────────────────
  // UI builders
  // ─────────────────────────────────────────────
  _createDashboardUI() {
    const dash = document.createElement('div');
    dash.className = 'ui-mode-container dashboard-mode';
    dash.style.cssText = `
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      opacity: 0; pointer-events: none;
      display: grid; grid-template-columns: 1fr 260px;
      background: rgba(0,10,20,0.96); backdrop-filter: blur(12px);
      transition: opacity ${this.options.transitionDuration}ms ease;
      font-family: 'Courier New', monospace;
    `;

    dash.innerHTML = `
      <div style="padding:28px 32px; display:flex; flex-direction:column; gap:20px; overflow-y:auto;">
        <div style="display:flex; justify-content:space-between; align-items:baseline;">
          <h2 style="color:#00ffff; font-size:1.1em; letter-spacing:3px; margin:0;">SYSTEM DASHBOARD</h2>
          <span id="dash-clock" style="color:#00ffff; font-size:1.3em; opacity:.9;">--:--:--</span>
        </div>

        <div id="dash-stats" style="display:grid; grid-template-columns:repeat(3,1fr); gap:14px;"></div>

        <div>
          <div style="color:rgba(0,255,255,.5); font-size:.75em; letter-spacing:3px; margin-bottom:10px;">RECENT COMMANDS</div>
          <div id="dash-history" style="display:flex; flex-direction:column; gap:6px;"></div>
        </div>
      </div>

      <div style="border-left:1px solid rgba(0,255,255,.15); padding:28px 20px; display:flex; flex-direction:column; gap:10px;">
        <div style="color:rgba(0,255,255,.5); font-size:.75em; letter-spacing:3px; margin-bottom:4px;">QUICK LAUNCH</div>
        <button class="ql" onclick="window.switchToMode?.('desktop')">📁  File Browser</button>
        <button class="ql" onclick="window.switchToMode?.('browser')">🌐  Web Browser</button>
        <button class="ql" onclick="window.switchToMode?.('browserbase')">☁  Cloud Browser</button>
        <button class="ql" onclick="window.switchToMode?.('terminal')">💻  Terminal</button>
        <button class="ql" onclick="window.switchToMode?.('document')">📄  Documents</button>
        <button class="ql" onclick="window.switchToMode?.('media')">🖼️  Media</button>
        <div style="flex:1;"></div>
        <button class="ql" style="border-color:rgba(0,255,255,.5);" onclick="window.switchToMode?.('avatar')">⚡  Back to Avatar</button>
      </div>
    `;

    // Quick-launch button styles
    dash.querySelectorAll('.ql').forEach(b => {
      b.style.cssText = `
        background: rgba(0,255,255,.05); border: 1px solid rgba(0,255,255,.25);
        color: #00ffff; padding: 11px 14px; cursor: pointer;
        font-family: 'Courier New', monospace; font-size: .88em;
        text-align: left; border-radius: 6px; transition: all .18s;
      `;
      b.addEventListener('mouseenter', () => { b.style.background = 'rgba(0,255,255,.15)'; b.style.borderColor = '#00ffff'; });
      b.addEventListener('mouseleave', () => { b.style.background = 'rgba(0,255,255,.05)'; b.style.borderColor = 'rgba(0,255,255,.25)'; });
    });

    this.overlayContainer.appendChild(dash);
    this.uiContainers[UI_MODES.DASHBOARD] = dash;
  }

  _createDesktopUI() {
    const desktop = document.createElement('div');
    desktop.className = 'ui-mode-container desktop-mode';
    desktop.style.cssText = `
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      opacity: 0; pointer-events: none;
      background: rgba(0,10,20,.96); backdrop-filter: blur(12px);
      transition: opacity ${this.options.transitionDuration}ms ease;
    `;
    desktop.id = 'os-file-browser-container';

    this.overlayContainer.appendChild(desktop);
    this.uiContainers[UI_MODES.DESKTOP] = desktop;
    
    // Initialize file browser when mode becomes active
    this._desktopBrowserInstance = null;
  }

  _createDocumentUI() {
    const doc = document.createElement('div');
    doc.className = 'ui-mode-container document-mode';
    doc.style.cssText = `
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      opacity: 0; pointer-events: none;
      display: flex; flex-direction: column;
      background: rgba(0,10,20,.96); backdrop-filter: blur(12px);
      transition: opacity ${this.options.transitionDuration}ms ease;
      font-family: 'Courier New', monospace;
    `;

    doc.innerHTML = `
      <div style="padding:16px 24px; border-bottom:1px solid rgba(0,255,255,.15);
                  display:flex; align-items:center; gap:12px;">
        <button onclick="window.dynamicUI?.closeDocument()" style="
          background:rgba(0,255,255,.08); border:1px solid rgba(0,255,255,.3);
          color:#00ffff; padding:5px 12px; cursor:pointer;
          font-family:'Courier New',monospace; border-radius:4px;">← Back</button>
        <h2 id="doc-title" style="margin:0; color:#00ffff; font-size:1em; letter-spacing:2px;">Document Viewer</h2>
        <div style="flex:1;"></div>
        <button onclick="window.dynamicUI?.zoomIn()" style="
          background:rgba(0,255,255,.08); border:1px solid rgba(0,255,255,.3);
          color:#00ffff; padding:5px 10px; cursor:pointer;
          font-family:'Courier New',monospace; border-radius:4px;">A+</button>
        <button onclick="window.dynamicUI?.zoomOut()" style="
          background:rgba(0,255,255,.08); border:1px solid rgba(0,255,255,.3);
          color:#00ffff; padding:5px 10px; cursor:pointer;
          font-family:'Courier New',monospace; border-radius:4px;">A-</button>
      </div>
      <div id="document-viewer" style="
        flex:1; overflow-y:auto; padding:32px;
        color:#00ffff; line-height:1.7; font-size:14px;
      "></div>
    `;

    this.overlayContainer.appendChild(doc);
    this.uiContainers[UI_MODES.DOCUMENT] = doc;
  }

  _createMediaUI() {
    const media = document.createElement('div');
    media.className = 'ui-mode-container media-mode';
    media.style.cssText = `
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      opacity: 0; pointer-events: none;
      display: flex; flex-direction: column;
      background: rgba(0,0,0,.98); backdrop-filter: blur(10px);
      transition: opacity ${this.options.transitionDuration}ms ease;
    `;

    media.innerHTML = `
      <div style="padding:16px 24px; border-bottom:1px solid rgba(0,255,255,.15);
                  display:flex; align-items:center; gap:12px; font-family:'Courier New',monospace;">
        <h2 id="media-title" style="margin:0; color:#00ffff; font-size:1em; letter-spacing:2px; flex:1;">Media Viewer</h2>
        <button onclick="window.dynamicUI?.closeMedia()" style="
          background:rgba(0,255,255,.08); border:1px solid rgba(0,255,255,.3);
          color:#00ffff; padding:5px 12px; cursor:pointer;
          font-family:'Courier New',monospace; border-radius:4px;">✕ Close</button>
      </div>
      <div id="media-viewer" style="
        flex:1; display:flex; align-items:center; justify-content:center; padding:20px;
      "></div>
      <div id="media-controls" style="
        padding:16px; border-top:1px solid rgba(0,255,255,.15);
        display:flex; justify-content:center; gap:12px;
      "></div>
    `;

    this.overlayContainer.appendChild(media);
    this.uiContainers[UI_MODES.MEDIA] = media;
  }

  _createTerminalUI() {
    const terminal = document.createElement('div');
    terminal.className = 'ui-mode-container terminal-mode';
    terminal.style.cssText = `
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      opacity: 0; pointer-events: none;
      display: flex; flex-direction: column;
      background: rgba(0,0,0,.97); backdrop-filter: blur(5px);
      transition: opacity ${this.options.transitionDuration}ms ease;
      font-family: 'Courier New', monospace;
    `;

    terminal.innerHTML = `
      <div style="padding:10px 20px; background:rgba(0,255,255,.08);
                  border-bottom:1px solid #00ffff; color:#00ffff; font-size:.88em;
                  display:flex; align-items:center; gap:12px;">
        <span>AIOS Terminal</span>
        <div style="flex:1;"></div>
        <button onclick="window.dynamicUI?.clearTerminal()" style="
          background:transparent; border:1px solid rgba(0,255,255,.4);
          color:rgba(0,255,255,.7); padding:3px 10px; cursor:pointer;
          font-family:'Courier New',monospace; font-size:.85em; border-radius:3px;">Clear</button>
        <button onclick="window.dynamicUI?.backToAvatar()" style="
          background:transparent; border:1px solid rgba(0,255,255,.4);
          color:rgba(0,255,255,.7); padding:3px 10px; cursor:pointer;
          font-family:'Courier New',monospace; font-size:.85em; border-radius:3px;">✕</button>
      </div>
      <div id="terminal-output" style="
        flex:1; overflow-y:auto; padding:20px; color:#00ff00;
        font-size:14px; line-height:1.5;
      "></div>
      <div style="padding:10px 20px; background:rgba(0,255,255,.04);
                  border-top:1px solid rgba(0,255,255,.2);
                  display:flex; align-items:center; gap:10px;">
        <span style="color:#00ffff;">$</span>
        <input type="text" id="terminal-input" autocomplete="off" style="
          flex:1; background:transparent; border:none; outline:none;
          color:#00ff00; font-family:'Courier New',monospace; font-size:14px;
        " placeholder="Type a command…">
      </div>
    `;

    // Wire up Enter key
    const input = terminal.querySelector('#terminal-input');
    const output = terminal.querySelector('#terminal-output');
    let history = [];
    let historyIndex = -1;

    if (input) {
      input.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
          const cmd = input.value.trim();
          if (!cmd) return;
          history.unshift(cmd);
          historyIndex = -1;
          input.value = '';
          this._terminalPrint(`$ ${cmd}`, '#00ffff', output);
          await this._executeTerminalCommand(cmd, output);
        } else if (e.key === 'ArrowUp') {
          historyIndex = Math.min(historyIndex + 1, history.length - 1);
          if (history[historyIndex]) input.value = history[historyIndex];
          e.preventDefault();
        } else if (e.key === 'ArrowDown') {
          historyIndex = Math.max(historyIndex - 1, -1);
          input.value = historyIndex >= 0 ? history[historyIndex] : '';
          e.preventDefault();
        }
      });
    }

    this.overlayContainer.appendChild(terminal);
    this.uiContainers[UI_MODES.TERMINAL] = terminal;
  }

  _createBrowserUI() {
    const browser = document.createElement('div');
    browser.className = 'ui-mode-container browser-mode';
    browser.style.cssText = `
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      opacity: 0; pointer-events: none;
      display: flex; flex-direction: column;
      background: rgba(0,10,20,.96); backdrop-filter: blur(10px);
      transition: opacity ${this.options.transitionDuration}ms ease;
      font-family: 'Courier New', monospace;
    `;

    browser.innerHTML = `
      <div style="padding:10px 16px; border-bottom:1px solid rgba(0,255,255,.2);
                  display:flex; align-items:center; gap:8px;">
        <button onclick="window.dynamicUI?.browserBack()" title="Back" style="
          background:rgba(0,255,255,.08); border:1px solid rgba(0,255,255,.3);
          color:#00ffff; padding:5px 10px; cursor:pointer;
          font-family:'Courier New',monospace; border-radius:4px;">←</button>
        <button onclick="window.dynamicUI?.browserForward()" title="Forward" style="
          background:rgba(0,255,255,.08); border:1px solid rgba(0,255,255,.3);
          color:#00ffff; padding:5px 10px; cursor:pointer;
          font-family:'Courier New',monospace; border-radius:4px;">→</button>
        <button onclick="window.dynamicUI?.browserRefresh()" title="Refresh" style="
          background:rgba(0,255,255,.08); border:1px solid rgba(0,255,255,.3);
          color:#00ffff; padding:5px 10px; cursor:pointer;
          font-family:'Courier New',monospace; border-radius:4px;">↺</button>
        <input type="text" id="browser-url" placeholder="Enter URL or search…" style="
          flex:1; background:rgba(0,255,255,.05); border:1px solid rgba(0,255,255,.3);
          color:#00ffff; padding:7px 14px; font-family:'Courier New',monospace;
          font-size:13px; border-radius:4px; outline:none;
        ">
        <button id="browser-go" style="
          background:rgba(0,255,255,.12); border:1px solid rgba(0,255,255,.4);
          color:#00ffff; padding:7px 14px; cursor:pointer;
          font-family:'Courier New',monospace; border-radius:4px;">Go</button>
        <button onclick="window.open(document.getElementById('browser-url').value,'_blank')" style="
          background:rgba(0,255,255,.08); border:1px solid rgba(0,255,255,.25);
          color:rgba(0,255,255,.7); padding:7px 10px; cursor:pointer;
          font-family:'Courier New',monospace; font-size:.8em; border-radius:4px;" title="Open in new tab">↗</button>
        <button onclick="window.dynamicUI?.closeBrowser()" style="
          background:rgba(255,0,0,.08); border:1px solid rgba(255,80,80,.4);
          color:rgba(255,100,100,.9); padding:7px 10px; cursor:pointer;
          font-family:'Courier New',monospace; border-radius:4px;">✕</button>
      </div>
      <iframe id="browser-frame"
        sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
        style="flex:1; border:none; background:#fff;"
        src="about:blank"></iframe>
      <div id="browser-blocked" style="
        display:none; flex:1; flex-direction:column; align-items:center;
        justify-content:center; gap:16px; color:#00ffff; padding:40px;
      ">
        <div style="font-size:2em;">🔒</div>
        <div style="font-size:1.1em; letter-spacing:2px;">SITE BLOCKED EMBEDDING</div>
        <div style="color:rgba(0,255,255,.6); font-size:.9em; text-align:center;">
          This site sets <code style="color:#0ff;">X-Frame-Options</code> on their server,
          preventing iframe display. Use the ↗ button to open it in a new tab.
        </div>
        <button id="browser-open-tab" style="
          background:rgba(0,255,255,.1); border:1px solid #00ffff;
          color:#00ffff; padding:10px 24px; cursor:pointer;
          font-family:'Courier New',monospace; border-radius:6px; font-size:.95em;
        ">Open in New Tab</button>
      </div>
    `;

    // Wire up Go button and Enter key on URL bar
    const urlInput = browser.querySelector('#browser-url');
    const goBtn    = browser.querySelector('#browser-go');
    const frame    = browser.querySelector('#browser-frame');
    const blocked  = browser.querySelector('#browser-blocked');
    const openTab  = browser.querySelector('#browser-open-tab');

    const navigate = () => {
      const raw = urlInput?.value?.trim();
      if (!raw) return;
      this.navigateBrowser(raw);
    };

    goBtn?.addEventListener('click', navigate);
    urlInput?.addEventListener('keydown', (e) => { if (e.key === 'Enter') navigate(); });

    // Detect when a frame load fails (X-Frame-Options)
    frame?.addEventListener('load', () => {
      try {
        // If we can access contentDocument and it's not empty, it loaded ok
        const doc = frame.contentDocument;
        if (doc && (doc.body?.innerHTML || doc.title)) {
          if (frame) frame.style.display = 'block';
          if (blocked) blocked.style.display = 'none';
        }
      } catch {
        // CORS block → site loaded but we can't read it (actually that's fine, it rendered)
      }
    });

    openTab?.addEventListener('click', () => {
      const url = urlInput?.value;
      if (url && url !== 'about:blank') window.open(url, '_blank');
    });

    this.overlayContainer.appendChild(browser);
    this.uiContainers[UI_MODES.BROWSER] = browser;
  }

  _createBrowserbaseUI() {
    const bb = document.createElement('div');
    bb.className = 'ui-mode-container browserbase-mode';
    bb.style.cssText = `
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      opacity: 0; pointer-events: none;
      transition: opacity ${this.options.transitionDuration}ms ease;
    `;
    this.overlayContainer.appendChild(bb);
    this.uiContainers[UI_MODES.BROWSERBASE] = bb;
    this._browserbasePanel = null;
  }

  // ─────────────────────────────────────────────
  // Transition engine
  // ─────────────────────────────────────────────
  async switchMode(newMode, data = {}) {
    if (newMode === this.currentMode || this.isTransitioning) return;

    console.log(`[DynamicUI] ${this.currentMode} → ${newMode}`);
    this.isTransitioning = true;
    this.previousMode = this.currentMode;

    if (this.options.enableParticleEffects) this._triggerTransitionEffect();

    // Fade out current
    if (this.currentMode !== UI_MODES.AVATAR) {
      const cur = this.uiContainers[this.currentMode];
      if (cur) { cur.style.opacity = '0'; cur.style.pointerEvents = 'none'; }
    } else {
      this._fadeAvatar(0);
    }

    await this._sleep(this.options.transitionDuration / 2);

    // Stop dashboard clock if leaving dashboard
    if (this.currentMode === UI_MODES.DASHBOARD) this._stopDashClock();

    this.currentMode = newMode;

    if (newMode !== UI_MODES.AVATAR) {
      this._populateModeData(newMode, data);
      const next = this.uiContainers[newMode];
      if (next) { next.style.opacity = '1'; next.style.pointerEvents = 'auto'; }
      
      // Initialize advanced OS components on first use
      if (newMode === UI_MODES.DESKTOP && !this._desktopBrowserInstance && window.OSFileBrowser) {
        this._desktopBrowserInstance = new window.OSFileBrowser(next);
      }
      if (newMode === UI_MODES.BROWSER && !this._browserInstance && window.OSBrowser) {
        this._browserInstance = new window.OSBrowser(next);
      }
      if (newMode === UI_MODES.BROWSERBASE && !this._browserbasePanel && window.BrowserbasePanel) {
        this._browserbasePanel = new window.BrowserbasePanel(next, {
          onClose: () => this.backToAvatar()
        });
      }
    } else {
      this._fadeAvatar(1);
    }

    await this._sleep(this.options.transitionDuration / 2);
    this.isTransitioning = false;

    // Start dashboard live clock
    if (newMode === UI_MODES.DASHBOARD) this._startDashClock();

    this._emitEvent('modeChanged', { from: this.previousMode, to: newMode });
    console.log('[DynamicUI] Transition complete:', newMode);
  }

  _fadeAvatar(opacity) {
    if (this.avatarRenderer?.renderer) {
      this.avatarRenderer.renderer.domElement.style.opacity = opacity.toString();
    }
  }

  _triggerTransitionEffect() {
    if (this.avatarRenderer?.setState) {
      this.avatarRenderer.setState('transforming');
      setTimeout(() => {
        if (this.currentMode === UI_MODES.AVATAR) this.avatarRenderer.setState('idle');
      }, this.options.transitionDuration);
    }
  }

  // ─────────────────────────────────────────────
  // Populate mode data
  // ─────────────────────────────────────────────
  _populateModeData(mode, data) {
    switch (mode) {
      case UI_MODES.DASHBOARD: this._populateDashboard(data); break;
      case UI_MODES.DESKTOP:   this._populateDesktop(data);   break;
      case UI_MODES.DOCUMENT:  this._populateDocument(data);  break;
      case UI_MODES.MEDIA:     this._populateMedia(data);     break;
      case UI_MODES.TERMINAL:  this._populateTerminal(data);  break;
      case UI_MODES.BROWSER:      this._populateBrowser(data);      break;
      case UI_MODES.BROWSERBASE:  this._populateBrowserbase(data);  break;
    }
  }

  _populateDashboard(data) {
    const statsEl   = this.uiContainers[UI_MODES.DASHBOARD]?.querySelector('#dash-stats');
    const historyEl = this.uiContainers[UI_MODES.DASHBOARD]?.querySelector('#dash-history');
    if (!statsEl) return;

    const stats = [
      { label: 'UPTIME',  id: 'dash-uptime',   val: data.uptime  || '00:00:00' },
      { label: 'STATUS',  id: 'dash-status',   val: data.status  || 'ONLINE',  color: '#00ff88' },
      { label: 'VOICE',   id: 'dash-voice',    val: data.voice   || 'READY' },
    ];

    statsEl.innerHTML = stats.map(s => `
      <div style="
        background:rgba(0,255,255,.05); border:1px solid rgba(0,255,255,.18);
        padding:16px; border-radius:6px;
      ">
        <div style="color:rgba(0,255,255,.45); font-size:.72em; letter-spacing:3px; margin-bottom:8px;">${s.label}</div>
        <div id="${s.id}" style="color:${s.color || '#00ffff'}; font-size:1.35em; font-weight:bold;">${s.val}</div>
      </div>
    `).join('');

    if (historyEl) {
      const cmds = (data.history || this.commandHistory).slice(0, 8);
      historyEl.innerHTML = cmds.length
        ? cmds.map(c => `
            <div style="
              padding:6px 12px; background:rgba(0,255,255,.04);
              border-left:2px solid rgba(0,255,255,.3);
              color:rgba(0,255,255,.75); font-size:.85em;
            ">&gt; ${c}</div>
          `).join('')
        : `<div style="color:rgba(0,255,255,.3); font-size:.85em;">No commands yet — try the voice bar below</div>`;
    }

    // Async stats from backend
    if (typeof eel !== 'undefined') {
      eel.get_system_stats()().then(s => {
        if (!s) return;
        const u = document.getElementById('dash-uptime');
        const st = document.getElementById('dash-status');
        if (u && s.uptime)  u.textContent = s.uptime;
        if (st && s.status) st.textContent = s.status.toUpperCase();
      }).catch(() => {});
    }
  }

  _startDashClock() {
    const update = () => {
      const el = document.getElementById('dash-clock');
      if (el) el.textContent = new Date().toLocaleTimeString();
    };
    update();
    this._dashClockTimer = setInterval(update, 1000);
  }

  _stopDashClock() {
    clearInterval(this._dashClockTimer);
    this._dashClockTimer = null;
  }

  _populateDesktop(data) {
    const grid     = this.uiContainers[UI_MODES.DESKTOP]?.querySelector('#file-grid');
    const pathEl   = this.uiContainers[UI_MODES.DESKTOP]?.querySelector('#current-path');
    const countEl  = this.uiContainers[UI_MODES.DESKTOP]?.querySelector('#file-count');
    if (!grid) return;

    grid.innerHTML = '';
    const files = data.files || [];
    if (pathEl)  pathEl.textContent  = data.path || '~';
    if (countEl) countEl.textContent = `${files.length} items`;

    // Store current path for "up" navigation
    this._currentDesktopPath = data.path || '~';

    files.forEach(file => {
      const el = document.createElement('div');
      el.style.cssText = `
        display:flex; flex-direction:column; align-items:center;
        padding:14px 8px; border:1px solid rgba(0,255,255,.25);
        background:rgba(0,255,255,.04); cursor:pointer;
        transition:all .22s; border-radius:8px; text-align:center;
      `;
      const icon = file.type === 'folder' ? '📁' : this._getFileIcon(file.name);
      el.innerHTML = `
        <div style="font-size:2.4em; margin-bottom:8px;">${icon}</div>
        <div style="color:#00ffff; font-size:.78em; word-break:break-word; line-height:1.3;">${file.name}</div>
        ${file.size ? `<div style="color:rgba(0,255,255,.4); font-size:.68em; margin-top:4px;">${file.size}</div>` : ''}
      `;
      el.addEventListener('mouseenter', () => {
        el.style.background = 'rgba(0,255,255,.13)';
        el.style.transform  = 'translateY(-4px)';
        el.style.boxShadow  = '0 6px 20px rgba(0,255,255,.25)';
      });
      el.addEventListener('mouseleave', () => {
        el.style.background = 'rgba(0,255,255,.04)';
        el.style.transform  = 'translateY(0)';
        el.style.boxShadow  = 'none';
      });
      el.addEventListener('click', () => this._handleFileClick(file));
      grid.appendChild(el);
    });
  }

  _populateDocument(data) {
    const viewer = this.uiContainers[UI_MODES.DOCUMENT]?.querySelector('#document-viewer');
    const title  = this.uiContainers[UI_MODES.DOCUMENT]?.querySelector('#doc-title');
    if (title)  title.textContent  = data.title   || 'Document';
    if (viewer) viewer.innerHTML   = data.content  || '<p style="color:rgba(0,255,255,.5)">No content available.</p>';
  }

  _populateMedia(data) {
    const viewer   = this.uiContainers[UI_MODES.MEDIA]?.querySelector('#media-viewer');
    const title    = this.uiContainers[UI_MODES.MEDIA]?.querySelector('#media-title');
    if (title)  title.textContent = data.title || 'Media';
    if (!viewer) return;
    viewer.innerHTML = '';
    if (data.type === 'image') {
      const img = document.createElement('img');
      img.src = data.url;
      img.style.cssText = 'max-width:90%; max-height:90%; object-fit:contain; border:2px solid #00ffff; border-radius:4px;';
      viewer.appendChild(img);
    } else if (data.type === 'video') {
      const v = document.createElement('video');
      v.src = data.url; v.controls = true;
      v.style.cssText = 'max-width:90%; max-height:90%; border:2px solid #00ffff;';
      viewer.appendChild(v);
    }
  }

  _populateTerminal(data) {
    const output = this.uiContainers[UI_MODES.TERMINAL]?.querySelector('#terminal-output');
    const input  = this.uiContainers[UI_MODES.TERMINAL]?.querySelector('#terminal-input');
    if (!output) return;
    if (data.clear) output.innerHTML = '';
    if (data.message) this._terminalPrint(data.message, '#00ff00', output);
    if (!data.message && !data.clear) {
      // Welcome banner on first open
      if (!output.children.length) {
        ['AIOS Terminal — Neural Command Interface', 'Type "help" for available commands.', ''].forEach((l, i) =>
          this._terminalPrint(l, i === 0 ? '#00ffff' : 'rgba(0,255,255,.5)', output));
      }
    }
    setTimeout(() => input?.focus(), 100);
  }

  _populateBrowser(data) {
    const urlInput = this.uiContainers[UI_MODES.BROWSER]?.querySelector('#browser-url');
    if (urlInput && data.url && data.url !== 'about:blank') {
      urlInput.value = data.url;
      this.navigateBrowser(data.url);
    }
  }

  _populateBrowserbase(data) {
    // If a URL was specified via voice command, queue a navigation once the panel is ready
    if (data.url && data.url !== 'about:blank' && this._browserbasePanel) {
      if (this._browserbasePanel.sessionId) {
        this._browserbasePanel.navigateTo(data.url);
      } else {
        // Auto-create session then navigate
        this._browserbasePanel.createSession().then(() => {
          if (data.url) this._browserbasePanel.navigateTo(data.url);
        });
      }
    }
    if (data.task && this._browserbasePanel) {
      if (this._browserbasePanel.sessionId) {
        this._browserbasePanel.runTask(data.task);
      } else {
        this._browserbasePanel.createSession().then(() => {
          if (data.task) this._browserbasePanel.runTask(data.task);
        });
      }
    }
  }

  // ─────────────────────────────────────────────
  // File handling
  // ─────────────────────────────────────────────
  _handleFileClick(file) {
    this._emitEvent('fileClicked', file);
    if (file.type === 'folder') {
      this._emitEvent('navigateFolder', file);
      return;
    }
    const ext = file.name.split('.').pop().toLowerCase();
    if (/^(txt|md|pdf|doc|docx|json|py|js|ts|html|css|sh)$/.test(ext)) {
      this.showDocument(file.name, file.content || `<pre style="color:#00ffff;white-space:pre-wrap;">${file.name}\n\nLoading content…</pre>`);
    } else if (/^(jpg|jpeg|png|gif|webp|svg)$/.test(ext)) {
      this.showMedia('image', file.url || file.path, file.name);
    } else if (/^(mp4|webm|mov|avi)$/.test(ext)) {
      this.showMedia('video', file.url || file.path, file.name);
    }
  }

  _getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const map = {
      txt:'📄', md:'📝', pdf:'📕', doc:'📘', docx:'📘',
      jpg:'🖼️', jpeg:'🖼️', png:'🖼️', gif:'🖼️', webp:'🖼️', svg:'🖼️',
      mp4:'🎬', webm:'🎬', mov:'🎬', avi:'🎬',
      mp3:'🎵', wav:'🎵', ogg:'🎵',
      zip:'📦', tar:'📦', gz:'📦', rar:'📦',
      js:'⚙️', ts:'⚙️', jsx:'⚙️', tsx:'⚙️',
      py:'🐍', rb:'💎', go:'🐹', rs:'🦀', cpp:'⚡', java:'☕',
      json:'🔧', yaml:'🔧', toml:'🔧', xml:'🔧',
      html:'🌐', css:'🎨',
      sh:'📟', bash:'📟', zsh:'📟',
    };
    return map[ext] || '📄';
  }

  // ─────────────────────────────────────────────
  // Terminal helpers
  // ─────────────────────────────────────────────
  _terminalPrint(text, color = '#00ff00', outputEl = null) {
    const output = outputEl || document.getElementById('terminal-output');
    if (!output) return;
    const line = document.createElement('div');
    line.style.cssText = `margin-bottom:3px; color:${color}; white-space:pre-wrap; word-break:break-all;`;
    line.textContent = text;
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
  }

  async _executeTerminalCommand(cmd, outputEl) {
    const lower = cmd.toLowerCase().trim();

    if (lower === 'clear') { if (outputEl) outputEl.innerHTML = ''; return; }

    if (lower === 'help') {
      ['Commands:', '  clear      Clear terminal output', '  help       Show this help',
       '  mode       Show current display mode', '  avatar     Return to avatar view',
       '  files      Open file browser', '  browser    Open web browser', '  browserbase  Open cloud browser (Browserbase)',
       '  Any other input is sent to the AIOS agent'].forEach(l =>
        this._terminalPrint(l, '#00ffff', outputEl));
      return;
    }

    if (lower === 'mode') {
      this._terminalPrint(`Mode: ${this.currentMode}`, '#00ffff', outputEl); return;
    }
    if (lower === 'avatar') { this.backToAvatar(); return; }
    if (lower === 'files')  { this.showDesktop([], '~'); this._emitEvent('desktopRequested', {}); return; }
    if (lower === 'browser')      { this.showBrowser('about:blank'); return; }
    if (lower === 'browserbase') { this.showBrowserbase(); return; }

    // Backend agent
    if (typeof eel !== 'undefined') {
      try {
        this._terminalPrint('…', 'rgba(0,255,255,.4)', outputEl);
        const result = await eel.agent_execute(cmd)();
        // Remove the ellipsis line
        const out = outputEl || document.getElementById('terminal-output');
        if (out?.lastChild) out.removeChild(out.lastChild);
        const text = typeof result === 'string' ? result : JSON.stringify(result, null, 2);
        text.split('\n').forEach(l => this._terminalPrint(l, '#00ff00', outputEl));
        return;
      } catch (err) {
        const out = outputEl || document.getElementById('terminal-output');
        if (out?.lastChild) out.removeChild(out.lastChild);
        this._terminalPrint(`Error: ${err.message}`, '#ff4444', outputEl);
        return;
      }
    }

    this._terminalPrint(`Command not found: ${cmd}`, '#ff4444', outputEl);
  }

  // ─────────────────────────────────────────────
  // Browser helpers
  // ─────────────────────────────────────────────
  _toEmbedUrl(url) {
    // YouTube: watch?v=ID or youtu.be/ID → /embed/ID
    let m = url.match(/(?:youtube\.com\/watch\?.*v=|youtu\.be\/)([A-Za-z0-9_-]{11})/);
    if (m) return `https://www.youtube.com/embed/${m[1]}?autoplay=0`;

    // Vimeo: vimeo.com/ID → player.vimeo.com/video/ID
    m = url.match(/^https?:\/\/(?:www\.)?vimeo\.com\/(\d+)/);
    if (m) return `https://player.vimeo.com/video/${m[1]}`;

    return url;
  }

  navigateBrowser(url) {
    if (!url) return;
    const raw = url.trim();
    let resolved = raw;

    if (!/^https?:\/\//i.test(raw)) {
      if (raw.includes('.') && !raw.includes(' ')) {
        resolved = 'https://' + raw;
      } else {
        resolved = `https://www.google.com/search?q=${encodeURIComponent(raw)}`;
      }
    }

    // Convert known watch URLs to embeddable equivalents
    resolved = this._toEmbedUrl(resolved);

    const frame    = document.getElementById('browser-frame');
    const urlInput = document.getElementById('browser-url');
    const blocked  = document.getElementById('browser-blocked');
    const openTab  = document.getElementById('browser-open-tab');

    if (urlInput) urlInput.value = resolved;
    if (blocked)  blocked.style.display = 'none';
    if (frame) {
      frame.style.display = 'block';
      frame.src = resolved;

      // Fallback: if the frame doesn't render within 4 s, assume blocked
      const timeout = setTimeout(() => {
        try {
          const doc = frame.contentDocument;
          if (!doc || !doc.body) {
            if (blocked) blocked.style.display = 'flex';
            if (frame)   frame.style.display   = 'none';
            if (openTab) openTab.onclick = () => window.open(resolved, '_blank');
          }
        } catch { /* cross-origin — frame rendered fine */ }
      }, 4000);

      frame.addEventListener('load', () => {
        clearTimeout(timeout);
        try {
          const doc = frame.contentDocument;
          // Chrome renders X-Frame-Options refusals as an error page with
          // class "neterror" or "interstitial-wrapper" on the body.
          const isErrorPage = doc?.body?.classList?.contains('neterror') ||
                              doc?.body?.classList?.contains('interstitial-wrapper');
          if (isErrorPage) {
            if (blocked) { blocked.style.display = 'flex'; if (openTab) openTab.onclick = () => window.open(resolved, '_blank'); }
            if (frame)   frame.style.display = 'none';
          } else if (doc?.title || doc?.body?.innerHTML) {
            if (blocked) blocked.style.display = 'none';
          }
        } catch { /* cross-origin: frame rendered fine */ }
      }, { once: true });
    }
  }

  browserBack()    { const f = document.getElementById('browser-frame'); if (f) { try { f.contentWindow.history.back(); } catch {} } }
  browserForward() { const f = document.getElementById('browser-frame'); if (f) { try { f.contentWindow.history.forward(); } catch {} } }
  browserRefresh() { const f = document.getElementById('browser-frame'); if (f) { f.src = f.src; } }

  // ─────────────────────────────────────────────
  // Desktop navigation
  // ─────────────────────────────────────────────
  desktopUp() {
    const path = this._currentDesktopPath || '';
    const parent = path.replace(/\/[^/]+\/?$/, '') || '/';
    this._emitEvent('navigateFolder', { name: '..', type: 'folder', path: parent });
  }

  clearTerminal() {
    const output = document.getElementById('terminal-output');
    if (output) output.innerHTML = '';
  }

  // ─────────────────────────────────────────────
  // Command history
  // ─────────────────────────────────────────────
  addCommandHistory(cmd) {
    this.commandHistory = [cmd, ...this.commandHistory.slice(0, 19)];
    // Live-update dashboard if active
    if (this.currentMode === UI_MODES.DASHBOARD) {
      const historyEl = this.uiContainers[UI_MODES.DASHBOARD]?.querySelector('#dash-history');
      if (historyEl) {
        const cmds = this.commandHistory.slice(0, 8);
        historyEl.innerHTML = cmds.map(c => `
          <div style="
            padding:6px 12px; background:rgba(0,255,255,.04);
            border-left:2px solid rgba(0,255,255,.3);
            color:rgba(0,255,255,.75); font-size:.85em;
          ">&gt; ${c}</div>
        `).join('');
      }
    }
  }

  // ─────────────────────────────────────────────
  // Public API
  // ─────────────────────────────────────────────
  showDashboard(data = {})           { return this.switchMode(UI_MODES.DASHBOARD, data); }
  showDesktop(files, path = '~')     { return this.switchMode(UI_MODES.DESKTOP,   { files, path }); }
  showDocument(title, content)       { return this.switchMode(UI_MODES.DOCUMENT,  { title, content }); }
  showMedia(type, url, title)        { return this.switchMode(UI_MODES.MEDIA,     { type, url, title }); }
  showTerminal(message = null, clear = false) { return this.switchMode(UI_MODES.TERMINAL, { message, clear }); }
  showBrowser(url, content = '')     { return this.switchMode(UI_MODES.BROWSER,      { url, content }); }
  showBrowserbase(url = '', task = '') { return this.switchMode(UI_MODES.BROWSERBASE, { url, task }); }
  closeDocument()    { return this.switchMode(UI_MODES.AVATAR); }
  closeMedia()       { return this.switchMode(UI_MODES.AVATAR); }
  closeBrowser()     { return this.switchMode(UI_MODES.AVATAR); }
  closeBrowserbase() { return this.switchMode(UI_MODES.AVATAR); }
  backToAvatar()     { return this.switchMode(UI_MODES.AVATAR); }
  getCurrentMode() { return this.currentMode; }

  zoomIn()  { const v = document.getElementById('document-viewer'); if (v) v.style.fontSize = (parseFloat(getComputedStyle(v).fontSize) * 1.1) + 'px'; }
  zoomOut() { const v = document.getElementById('document-viewer'); if (v) v.style.fontSize = (parseFloat(getComputedStyle(v).fontSize) * 0.9) + 'px'; }

  handleVoiceCommand(cmd) { return this.desktopBridge?.handleVoiceCommand(cmd) || false; }
  getDesktopBridge()      { return this.desktopBridge; }

  _sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
  _emitEvent(name, data) { window.dispatchEvent(new CustomEvent(`dynamicui:${name}`, { detail: data })); }

  destroy() { this._stopDashClock(); this.overlayContainer?.remove(); this.uiContainers = {}; }
}

if (typeof window !== 'undefined') {
  window.DynamicUIManager = DynamicUIManager;
  window.UI_MODES = UI_MODES;
}

export { DynamicUIManager, UI_MODES };
