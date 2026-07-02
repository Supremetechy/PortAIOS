/**
 * ScreenManager - Unified screen/modal management for PortAIOS
 * Manages internal screen transitions within the main AIOS interface
 * Supports: modals, full-screen modes, and overlay screens
 */

export class ScreenManager {
  constructor() {
    this.screens = new Map();
    this.activeScreen = null;
    this.history = [];
    this.modals = new Map();
    this.init();
  }

  init() {
    // Create modal container if it doesn't exist
    if (!document.getElementById('aios-modal-container')) {
      const container = document.createElement('div');
      container.id = 'aios-modal-container';
      container.className = 'aios-modal-container';
      document.body.appendChild(container);
    }

    // Create screen container for full-screen transitions
    if (!document.getElementById('aios-screen-container')) {
      const container = document.createElement('div');
      container.id = 'aios-screen-container';
      container.className = 'aios-screen-container';
      document.body.appendChild(container);
    }

    // Listen for Escape key to close modals
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeTopModal();
      }
    });
  }

  /**
   * Register a screen with the manager
   * @param {string} id - Unique screen identifier
   * @param {Object} config - Screen configuration
   *   - type: 'modal' | 'fullscreen' | 'overlay'
   *   - title: Screen title
   *   - content: HTML content or DOM element
   *   - onOpen: Callback when screen opens
   *   - onClose: Callback when screen closes
   *   - size: 'small' | 'medium' | 'large' | 'fullscreen' (for modals)
   */
  registerScreen(id, config) {
    this.screens.set(id, {
      id,
      type: config.type || 'modal',
      title: config.title || '',
      content: config.content || '',
      onOpen: config.onOpen || null,
      onClose: config.onClose || null,
      size: config.size || 'medium',
      closeButton: config.closeButton !== false,
      overlay: config.overlay !== false
    });
    console.log(`[ScreenManager] Registered screen: ${id} (${config.type})`);
  }

  /**
   * Open a screen by ID
   * @param {string} id - Screen ID
   * @param {Object} options - Additional options to pass to the screen
   */
  async openScreen(id, options = {}) {
    const screen = this.screens.get(id);
    if (!screen) {
      console.error(`[ScreenManager] Screen not found: ${id}`);
      return false;
    }

    // Close existing modal if type is modal
    if (screen.type === 'modal') {
      this.closeTopModal();
    }

    // Add to history
    if (this.activeScreen !== id) {
      this.history.push(id);
    }
    this.activeScreen = id;

    // Render based on type
    switch (screen.type) {
      case 'modal':
        this.renderModal(screen, options);
        break;
      case 'fullscreen':
        this.renderFullscreen(screen, options);
        break;
      case 'overlay':
        this.renderOverlay(screen, options);
        break;
    }

    // Call onOpen callback
    if (screen.onOpen) {
      await screen.onOpen(options);
    }

    // Dispatch event
    window.dispatchEvent(new CustomEvent('aios:screenOpen', { detail: { id, screen, options } }));
    return true;
  }

  /**
   * Render a modal screen
   */
  renderModal(screen, options) {
    const container = document.getElementById('aios-modal-container');
    
    const modal = document.createElement('div');
    modal.className = `aios-modal ${screen.size}-modal active`;
    modal.dataset.screenId = screen.id;
    
    const overlay = document.createElement('div');
    overlay.className = 'aios-modal-overlay';
    if (screen.overlay) {
      overlay.addEventListener('click', () => this.closeScreen(screen.id));
    }

    const content = document.createElement('div');
    content.className = 'aios-modal-content';
    
    // Header
    const header = document.createElement('div');
    header.className = 'aios-modal-header';
    
    const title = document.createElement('h2');
    title.className = 'aios-modal-title';
    title.textContent = screen.title;
    header.appendChild(title);
    
    if (screen.closeButton) {
      const closeBtn = document.createElement('button');
      closeBtn.className = 'aios-modal-close';
      closeBtn.innerHTML = '✕';
      closeBtn.setAttribute('aria-label', 'Close');
      closeBtn.addEventListener('click', () => this.closeScreen(screen.id));
      header.appendChild(closeBtn);
    }
    
    // Body
    const body = document.createElement('div');
    body.className = 'aios-modal-body';
    
    if (typeof screen.content === 'string') {
      body.innerHTML = screen.content;
    } else if (screen.content instanceof HTMLElement) {
      body.appendChild(screen.content);
    } else if (typeof screen.content === 'function') {
      const result = screen.content(options);
      if (result instanceof HTMLElement) {
        body.appendChild(result);
      } else if (typeof result === 'string') {
        body.innerHTML = result;
      }
    }
    
    content.appendChild(header);
    content.appendChild(body);
    modal.appendChild(overlay);
    modal.appendChild(content);
    container.appendChild(modal);
    
    this.modals.set(screen.id, modal);
    
    // Animate in
    requestAnimationFrame(() => {
      modal.classList.add('visible');
    });
  }

  /**
   * Render a fullscreen screen
   */
  renderFullscreen(screen, options) {
    const container = document.getElementById('aios-screen-container');
    container.innerHTML = '';
    
    const fullscreen = document.createElement('div');
    fullscreen.className = 'aios-fullscreen-screen';
    fullscreen.dataset.screenId = screen.id;
    
    // Header
    const header = document.createElement('div');
    header.className = 'aios-screen-header';
    
    const backBtn = document.createElement('button');
    backBtn.className = 'aios-screen-back';
    backBtn.innerHTML = '← Back';
    backBtn.addEventListener('click', () => this.closeScreen(screen.id));
    header.appendChild(backBtn);
    
    const title = document.createElement('h1');
    title.className = 'aios-screen-title';
    title.textContent = screen.title;
    header.appendChild(title);
    
    // Body
    const body = document.createElement('div');
    body.className = 'aios-screen-body';
    
    if (typeof screen.content === 'string') {
      body.innerHTML = screen.content;
    } else if (screen.content instanceof HTMLElement) {
      body.appendChild(screen.content);
    } else if (typeof screen.content === 'function') {
      const result = screen.content(options);
      if (result instanceof HTMLElement) {
        body.appendChild(result);
      } else if (typeof result === 'string') {
        body.innerHTML = result;
      }
    }
    
    fullscreen.appendChild(header);
    fullscreen.appendChild(body);
    container.appendChild(fullscreen);
    container.classList.add('active');
  }

  /**
   * Render an overlay screen
   */
  renderOverlay(screen, options) {
    // Similar to modal but different styling
    this.renderModal(screen, options);
  }

  /**
   * Close a specific screen
   */
  async closeScreen(id) {
    const screen = this.screens.get(id);
    if (!screen) return;

    // Call onClose callback
    if (screen.onClose) {
      await screen.onClose();
    }

    if (screen.type === 'modal' || screen.type === 'overlay') {
      const modal = this.modals.get(id);
      if (modal) {
        modal.classList.remove('visible');
        setTimeout(() => {
          modal.remove();
          this.modals.delete(id);
        }, 300); // Match transition duration
      }
    } else if (screen.type === 'fullscreen') {
      const container = document.getElementById('aios-screen-container');
      container.classList.remove('active');
      setTimeout(() => {
        container.innerHTML = '';
      }, 300);
    }

    // Update history
    const idx = this.history.indexOf(id);
    if (idx > -1) {
      this.history.splice(idx, 1);
    }
    
    this.activeScreen = this.history[this.history.length - 1] || null;

    // Dispatch event
    window.dispatchEvent(new CustomEvent('aios:screenClose', { detail: { id, screen } }));
  }

  /**
   * Close the topmost modal
   */
  closeTopModal() {
    const modalIds = Array.from(this.modals.keys());
    if (modalIds.length > 0) {
      this.closeScreen(modalIds[modalIds.length - 1]);
    }
  }

  /**
   * Close all screens
   */
  closeAllScreens() {
    for (const id of this.modals.keys()) {
      this.closeScreen(id);
    }
    const container = document.getElementById('aios-screen-container');
    container.classList.remove('active');
    container.innerHTML = '';
    this.history = [];
    this.activeScreen = null;
  }

  /**
   * Check if a screen is currently open
   */
  isScreenOpen(id) {
    return this.modals.has(id) || this.activeScreen === id;
  }

  /**
   * Get current active screen
   */
  getActiveScreen() {
    return this.activeScreen;
  }
}

// Global instance
export const screenManager = new ScreenManager();
window.screenManager = screenManager;
