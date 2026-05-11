/**
 * Dynamic UI Manager for AIOS Binary Avatar
 * Transforms the binary avatar into various visual UI modes:
 * - Avatar Mode (default): 3D binary avatar
 * - Desktop Mode: File browser/folder view
 * - Document Mode: Text/PDF viewer
 * - Media Mode: Image/video player
 * - Terminal Mode: Command line interface
 * - Browser Mode: Web content viewer
 */

const UI_MODES = {
  AVATAR: 'avatar',
  DESKTOP: 'desktop',
  DOCUMENT: 'document',
  MEDIA: 'media',
  TERMINAL: 'terminal',
  BROWSER: 'browser',
  TRANSITION: 'transition'
};

const TRANSITION_DURATION = 800; // ms

class DynamicUIManager {
  constructor(container, avatarRenderer, options = {}) {
    this.container = container;
    this.avatarRenderer = avatarRenderer;
    this.currentMode = UI_MODES.AVATAR;
    this.previousMode = null;
    this.transitionProgress = 0;
    this.isTransitioning = false;
    
    // UI containers for different modes
    this.uiContainers = {};
    this.options = {
      transitionDuration: options.transitionDuration || TRANSITION_DURATION,
      enableParticleEffects: options.enableParticleEffects !== false,
      ...options
    };
    
    this._init();
  }

  _init() {
    // Create overlay container for UI modes
    this.overlayContainer = document.createElement('div');
    this.overlayContainer.id = 'dynamic-ui-overlay';
    this.overlayContainer.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 10;
    `;
    this.container.appendChild(this.overlayContainer);

    // Create individual UI mode containers
    this._createDesktopUI();
    this._createDocumentUI();
    this._createMediaUI();
    this._createTerminalUI();
    this._createBrowserUI();

    console.log('[DynamicUI] Initialized with modes:', Object.keys(UI_MODES));
  }

  _createDesktopUI() {
    const desktop = document.createElement('div');
    desktop.className = 'ui-mode-container desktop-mode';
    desktop.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      opacity: 0;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      background: rgba(0, 10, 20, 0.95);
      backdrop-filter: blur(10px);
      transition: opacity ${this.options.transitionDuration}ms ease;
    `;

    desktop.innerHTML = `
      <div class="desktop-header" style="padding: 20px; border-bottom: 1px solid rgba(0, 255, 255, 0.2);">
        <h2 style="margin: 0; color: #00ffff; font-family: 'Courier New', monospace; font-size: 1.5em;">
          <span class="glitch-text">AIOS FILE SYSTEM</span>
        </h2>
        <div class="breadcrumb" style="margin-top: 10px; color: #00ffff; opacity: 0.7; font-size: 0.9em;">
          / <span id="current-path">home</span>
        </div>
      </div>
      <div class="desktop-content" style="flex: 1; overflow-y: auto; padding: 20px;">
        <div id="file-grid" class="file-grid" style="
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
          gap: 20px;
          padding: 10px;
        "></div>
      </div>
      <div class="desktop-footer" style="padding: 15px; border-top: 1px solid rgba(0, 255, 255, 0.2); color: #00ffff; font-size: 0.85em;">
        <span id="file-count">0 items</span> | <span id="storage-info">0 KB used</span>
      </div>
    `;

    this.overlayContainer.appendChild(desktop);
    this.uiContainers[UI_MODES.DESKTOP] = desktop;
  }

  _createDocumentUI() {
    const docContainer = document.createElement('div');
    docContainer.className = 'ui-mode-container document-mode';
    docContainer.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      opacity: 0;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      background: rgba(0, 10, 20, 0.95);
      backdrop-filter: blur(10px);
      transition: opacity ${this.options.transitionDuration}ms ease;
    `;

    docContainer.innerHTML = `
      <div class="document-header" style="padding: 20px; border-bottom: 1px solid rgba(0, 255, 255, 0.2);">
        <h2 id="doc-title" style="margin: 0; color: #00ffff; font-family: 'Courier New', monospace; font-size: 1.3em;">
          Document Viewer
        </h2>
        <div class="document-controls" style="margin-top: 10px; display: flex; gap: 10px;">
          <button class="doc-btn" onclick="window.dynamicUI?.closeDocument()" style="
            background: rgba(0, 255, 255, 0.1);
            border: 1px solid #00ffff;
            color: #00ffff;
            padding: 5px 15px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
          ">← Back</button>
          <button class="doc-btn" onclick="window.dynamicUI?.zoomIn()" style="
            background: rgba(0, 255, 255, 0.1);
            border: 1px solid #00ffff;
            color: #00ffff;
            padding: 5px 15px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
          ">Zoom +</button>
          <button class="doc-btn" onclick="window.dynamicUI?.zoomOut()" style="
            background: rgba(0, 255, 255, 0.1);
            border: 1px solid #00ffff;
            color: #00ffff;
            padding: 5px 15px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
          ">Zoom -</button>
        </div>
      </div>
      <div class="document-content" style="
        flex: 1;
        overflow-y: auto;
        padding: 30px;
        color: #00ffff;
        font-family: 'Courier New', monospace;
        line-height: 1.6;
        font-size: 14px;
      " id="document-viewer"></div>
    `;

    this.overlayContainer.appendChild(docContainer);
    this.uiContainers[UI_MODES.DOCUMENT] = docContainer;
  }

  _createMediaUI() {
    const media = document.createElement('div');
    media.className = 'ui-mode-container media-mode';
    media.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      opacity: 0;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      background: rgba(0, 0, 0, 0.98);
      backdrop-filter: blur(10px);
      transition: opacity ${this.options.transitionDuration}ms ease;
    `;

    media.innerHTML = `
      <div class="media-header" style="padding: 20px; border-bottom: 1px solid rgba(0, 255, 255, 0.2);">
        <h2 id="media-title" style="margin: 0; color: #00ffff; font-family: 'Courier New', monospace; font-size: 1.3em;">
          Media Viewer
        </h2>
        <button class="media-close" onclick="window.dynamicUI?.closeMedia()" style="
          position: absolute;
          top: 20px;
          right: 20px;
          background: rgba(0, 255, 255, 0.1);
          border: 1px solid #00ffff;
          color: #00ffff;
          padding: 5px 15px;
          cursor: pointer;
          font-family: 'Courier New', monospace;
        ">✕ Close</button>
      </div>
      <div class="media-content" style="
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
      " id="media-viewer"></div>
      <div class="media-controls" style="
        padding: 20px;
        border-top: 1px solid rgba(0, 255, 255, 0.2);
        display: flex;
        justify-content: center;
        gap: 15px;
      " id="media-controls"></div>
    `;

    this.overlayContainer.appendChild(media);
    this.uiContainers[UI_MODES.MEDIA] = media;
  }

  _createTerminalUI() {
    const terminal = document.createElement('div');
    terminal.className = 'ui-mode-container terminal-mode';
    terminal.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      opacity: 0;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      background: rgba(0, 0, 0, 0.95);
      backdrop-filter: blur(5px);
      transition: opacity ${this.options.transitionDuration}ms ease;
      font-family: 'Courier New', monospace;
    `;

    terminal.innerHTML = `
      <div class="terminal-header" style="
        padding: 10px 20px;
        background: rgba(0, 255, 255, 0.1);
        border-bottom: 1px solid #00ffff;
        color: #00ffff;
        font-size: 0.9em;
      ">
        AIOS Terminal v2.0 — Neural Command Interface
      </div>
      <div class="terminal-output" id="terminal-output" style="
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        color: #00ff00;
        font-size: 14px;
        line-height: 1.5;
      "></div>
      <div class="terminal-input-container" style="
        padding: 10px 20px;
        background: rgba(0, 255, 255, 0.05);
        border-top: 1px solid rgba(0, 255, 255, 0.3);
        display: flex;
        align-items: center;
        gap: 10px;
      ">
        <span style="color: #00ffff;">$</span>
        <input type="text" id="terminal-input" style="
          flex: 1;
          background: transparent;
          border: none;
          outline: none;
          color: #00ff00;
          font-family: 'Courier New', monospace;
          font-size: 14px;
        " placeholder="Enter command...">
      </div>
    `;

    this.overlayContainer.appendChild(terminal);
    this.uiContainers[UI_MODES.TERMINAL] = terminal;
  }

  _createBrowserUI() {
    const browser = document.createElement('div');
    browser.className = 'ui-mode-container browser-mode';
    browser.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      opacity: 0;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      background: rgba(0, 10, 20, 0.95);
      backdrop-filter: blur(10px);
      transition: opacity ${this.options.transitionDuration}ms ease;
    `;

    browser.innerHTML = `
      <div class="browser-header" style="padding: 15px 20px; border-bottom: 1px solid rgba(0, 255, 255, 0.2);">
        <div style="display: flex; align-items: center; gap: 10px;">
          <button onclick="window.dynamicUI?.browserBack()" style="
            background: rgba(0, 255, 255, 0.1);
            border: 1px solid #00ffff;
            color: #00ffff;
            padding: 5px 10px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
          ">←</button>
          <button onclick="window.dynamicUI?.browserForward()" style="
            background: rgba(0, 255, 255, 0.1);
            border: 1px solid #00ffff;
            color: #00ffff;
            padding: 5px 10px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
          ">→</button>
          <input type="text" id="browser-url" style="
            flex: 1;
            background: rgba(0, 255, 255, 0.05);
            border: 1px solid #00ffff;
            color: #00ffff;
            padding: 8px 15px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
          " placeholder="Enter URL or search...">
          <button onclick="window.dynamicUI?.closeBrowser()" style="
            background: rgba(0, 255, 255, 0.1);
            border: 1px solid #00ffff;
            color: #00ffff;
            padding: 5px 15px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
          ">✕</button>
        </div>
      </div>
      <div class="browser-content" id="browser-viewer" style="
        flex: 1;
        overflow: auto;
        background: rgba(255, 255, 255, 0.98);
      "></div>
    `;

    this.overlayContainer.appendChild(browser);
    this.uiContainers[UI_MODES.BROWSER] = browser;
  }

  /**
   * Switch to a different UI mode with smooth transition
   */
  async switchMode(newMode, data = {}) {
    if (newMode === this.currentMode || this.isTransitioning) {
      console.log('[DynamicUI] Already in mode:', newMode);
      return;
    }

    console.log(`[DynamicUI] Switching from ${this.currentMode} to ${newMode}`);
    this.isTransitioning = true;
    this.previousMode = this.currentMode;

    // Start transition effect on avatar
    if (this.options.enableParticleEffects) {
      this._triggerTransitionEffect();
    }

    // Fade out current mode
    if (this.currentMode !== UI_MODES.AVATAR) {
      const currentContainer = this.uiContainers[this.currentMode];
      if (currentContainer) {
        currentContainer.style.opacity = '0';
        currentContainer.style.pointerEvents = 'none';
      }
    } else {
      // Fade out avatar
      this._fadeAvatar(0);
    }

    await this._sleep(this.options.transitionDuration / 2);

    // Update mode
    this.currentMode = newMode;

    // Populate new mode with data
    if (newMode !== UI_MODES.AVATAR) {
      this._populateModeData(newMode, data);
      const newContainer = this.uiContainers[newMode];
      if (newContainer) {
        newContainer.style.opacity = '1';
        newContainer.style.pointerEvents = 'auto';
      }
    } else {
      this._fadeAvatar(1);
    }

    await this._sleep(this.options.transitionDuration / 2);

    this.isTransitioning = false;
    console.log('[DynamicUI] Transition complete. Current mode:', this.currentMode);

    // Emit event
    this._emitEvent('modeChanged', { from: this.previousMode, to: this.currentMode });
  }

  _fadeAvatar(opacity) {
    if (this.avatarRenderer && this.avatarRenderer.renderer) {
      this.avatarRenderer.renderer.domElement.style.opacity = opacity.toString();
    }
  }

  _triggerTransitionEffect() {
    // Create particle burst effect during transition
    if (this.avatarRenderer && this.avatarRenderer.setState) {
      this.avatarRenderer.setState('transforming');
      setTimeout(() => {
        if (this.currentMode === UI_MODES.AVATAR) {
          this.avatarRenderer.setState('idle');
        }
      }, this.options.transitionDuration);
    }
  }

  _populateModeData(mode, data) {
    switch (mode) {
      case UI_MODES.DESKTOP:
        this._populateDesktop(data);
        break;
      case UI_MODES.DOCUMENT:
        this._populateDocument(data);
        break;
      case UI_MODES.MEDIA:
        this._populateMedia(data);
        break;
      case UI_MODES.TERMINAL:
        this._populateTerminal(data);
        break;
      case UI_MODES.BROWSER:
        this._populateBrowser(data);
        break;
    }
  }

  _populateDesktop(data) {
    const fileGrid = this.uiContainers[UI_MODES.DESKTOP].querySelector('#file-grid');
    const pathEl = this.uiContainers[UI_MODES.DESKTOP].querySelector('#current-path');
    const fileCount = this.uiContainers[UI_MODES.DESKTOP].querySelector('#file-count');
    
    if (!fileGrid) return;

    fileGrid.innerHTML = '';
    const files = data.files || [];
    
    if (pathEl) pathEl.textContent = data.path || 'home';
    if (fileCount) fileCount.textContent = `${files.length} items`;

    files.forEach(file => {
      const fileEl = document.createElement('div');
      fileEl.className = 'file-item';
      fileEl.style.cssText = `
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 15px;
        border: 1px solid rgba(0, 255, 255, 0.3);
        background: rgba(0, 255, 255, 0.05);
        cursor: pointer;
        transition: all 0.3s ease;
        border-radius: 8px;
      `;
      
      const icon = file.type === 'folder' ? '📁' : this._getFileIcon(file.name);
      
      fileEl.innerHTML = `
        <div style="font-size: 3em; margin-bottom: 10px;">${icon}</div>
        <div style="color: #00ffff; font-size: 0.85em; text-align: center; word-break: break-word;">
          ${file.name}
        </div>
        <div style="color: #00ffff; opacity: 0.5; font-size: 0.7em; margin-top: 5px;">
          ${file.size || ''}
        </div>
      `;

      fileEl.addEventListener('mouseenter', () => {
        fileEl.style.background = 'rgba(0, 255, 255, 0.15)';
        fileEl.style.transform = 'translateY(-5px)';
        fileEl.style.boxShadow = '0 5px 20px rgba(0, 255, 255, 0.3)';
      });

      fileEl.addEventListener('mouseleave', () => {
        fileEl.style.background = 'rgba(0, 255, 255, 0.05)';
        fileEl.style.transform = 'translateY(0)';
        fileEl.style.boxShadow = 'none';
      });

      fileEl.addEventListener('click', () => {
        this._handleFileClick(file);
      });

      fileGrid.appendChild(fileEl);
    });
  }

  _populateDocument(data) {
    const viewer = this.uiContainers[UI_MODES.DOCUMENT].querySelector('#document-viewer');
    const title = this.uiContainers[UI_MODES.DOCUMENT].querySelector('#doc-title');
    
    if (title) title.textContent = data.title || 'Document';
    if (viewer) viewer.innerHTML = data.content || '<p>No content available</p>';
  }

  _populateMedia(data) {
    const viewer = this.uiContainers[UI_MODES.MEDIA].querySelector('#media-viewer');
    const title = this.uiContainers[UI_MODES.MEDIA].querySelector('#media-title');
    const controls = this.uiContainers[UI_MODES.MEDIA].querySelector('#media-controls');
    
    if (title) title.textContent = data.title || 'Media';
    if (!viewer) return;

    viewer.innerHTML = '';

    if (data.type === 'image') {
      const img = document.createElement('img');
      img.src = data.url;
      img.style.cssText = 'max-width: 90%; max-height: 90%; object-fit: contain; border: 2px solid #00ffff;';
      viewer.appendChild(img);
    } else if (data.type === 'video') {
      const video = document.createElement('video');
      video.src = data.url;
      video.controls = true;
      video.style.cssText = 'max-width: 90%; max-height: 90%; border: 2px solid #00ffff;';
      viewer.appendChild(video);
    }
  }

  _populateTerminal(data) {
    const output = this.uiContainers[UI_MODES.TERMINAL].querySelector('#terminal-output');
    if (!output) return;

    if (data.clear) {
      output.innerHTML = '';
    }

    if (data.message) {
      const line = document.createElement('div');
      line.textContent = data.message;
      line.style.marginBottom = '5px';
      output.appendChild(line);
      output.scrollTop = output.scrollHeight;
    }
  }

  _populateBrowser(data) {
    const urlInput = this.uiContainers[UI_MODES.BROWSER].querySelector('#browser-url');
    const viewer = this.uiContainers[UI_MODES.BROWSER].querySelector('#browser-viewer');
    
    if (urlInput && data.url) urlInput.value = data.url;
    if (viewer && data.content) viewer.innerHTML = data.content;
  }

  _handleFileClick(file) {
    console.log('[DynamicUI] File clicked:', file);
    this._emitEvent('fileClicked', file);

    if (file.type === 'folder') {
      // Navigate into folder
      this._emitEvent('navigateFolder', file);
    } else if (file.type === 'document' || file.name.match(/\.(txt|md|pdf|doc)$/i)) {
      // Open document
      this.switchMode(UI_MODES.DOCUMENT, {
        title: file.name,
        content: file.content || '<p>Loading...</p>'
      });
    } else if (file.name.match(/\.(jpg|jpeg|png|gif|webp)$/i)) {
      // Open image
      this.switchMode(UI_MODES.MEDIA, {
        type: 'image',
        url: file.url || file.path,
        title: file.name
      });
    } else if (file.name.match(/\.(mp4|webm|mov)$/i)) {
      // Open video
      this.switchMode(UI_MODES.MEDIA, {
        type: 'video',
        url: file.url || file.path,
        title: file.name
      });
    }
  }

  _getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const iconMap = {
      txt: '📄', md: '📝', pdf: '📕', doc: '📘', docx: '📘',
      jpg: '🖼️', jpeg: '🖼️', png: '🖼️', gif: '🖼️', webp: '🖼️',
      mp4: '🎬', webm: '🎬', mov: '🎬', avi: '🎬',
      mp3: '🎵', wav: '🎵', ogg: '🎵',
      zip: '📦', tar: '📦', gz: '📦',
      js: '⚙️', py: '🐍', rs: '🦀', cpp: '⚡', java: '☕',
    };
    return iconMap[ext] || '📄';
  }

  // Public API methods
  showDesktop(files, path = '/home') {
    return this.switchMode(UI_MODES.DESKTOP, { files, path });
  }

  showDocument(title, content) {
    return this.switchMode(UI_MODES.DOCUMENT, { title, content });
  }

  showMedia(type, url, title) {
    return this.switchMode(UI_MODES.MEDIA, { type, url, title });
  }

  showTerminal(message = null, clear = false) {
    return this.switchMode(UI_MODES.TERMINAL, { message, clear });
  }

  showBrowser(url, content = '') {
    return this.switchMode(UI_MODES.BROWSER, { url, content });
  }

  closeDocument() {
    return this.switchMode(UI_MODES.AVATAR);
  }

  closeMedia() {
    return this.switchMode(UI_MODES.AVATAR);
  }

  closeBrowser() {
    return this.switchMode(UI_MODES.AVATAR);
  }

  backToAvatar() {
    return this.switchMode(UI_MODES.AVATAR);
  }

  getCurrentMode() {
    return this.currentMode;
  }

  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  _emitEvent(name, data) {
    const event = new CustomEvent(`dynamicui:${name}`, { detail: data });
    window.dispatchEvent(event);
  }

  destroy() {
    this.overlayContainer?.remove();
    this.uiContainers = {};
  }
}

// Make available globally
if (typeof window !== 'undefined') {
  window.DynamicUIManager = DynamicUIManager;
  window.UI_MODES = UI_MODES;
}

export { DynamicUIManager, UI_MODES };
