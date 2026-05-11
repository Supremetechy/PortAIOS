/**
 * avatar-mode-switcher.js
 * Manages switching between different avatar rendering modes:
 * - Binary Avatar (existing Three.js shader-based avatar)
 * - React 3D Avatar (realistic lip-sync avatar from Avatar.jsx)
 * - Dynamic UI Avatar (binary substrate + DynamicUIManager overlays
 *   that morph into desktop / terminal / browser views in response to
 *   voice commands — see web/index-dynamic-avatar.html)
 */

export const AVATAR_MODES = {
  BINARY: 'binary',
  REACT_3D: 'react3d',
  DYNAMIC: 'dynamic'
};

// Iteration order used by toggle() to cycle through modes.
const MODE_CYCLE = [AVATAR_MODES.BINARY, AVATAR_MODES.REACT_3D, AVATAR_MODES.DYNAMIC];

export class AvatarModeSwitcher {
  constructor() {
    this.currentMode = AVATAR_MODES.BINARY;
    this.binaryAvatar = null;
    this.reactAvatar = null;
    this.dynamicUI = null;
    this.binaryContainer = null;
    this.reactContainer = null;
    this.onModeChange = null;
    // Default landing view when entering DYNAMIC mode (desktop is the most
    // visually obvious "the avatar transformed into UI" cue).
    this.dynamicEntryView = 'desktop';
  }

  /**
   * Initialize the mode switcher with avatar instances and (optionally) the
   * DynamicUIManager that powers DYNAMIC mode.
   */
  init(binaryAvatar, reactAvatar, dynamicUI = null) {
    this.binaryAvatar = binaryAvatar;
    this.reactAvatar = reactAvatar;
    this.dynamicUI = dynamicUI;

    // Create containers if they don't exist
    this.setupContainers();

    // Set initial mode
    this.setMode(this.currentMode);
  }

  setupContainers() {
    // Binary avatar uses existing avatar-layer
    this.binaryContainer = document.getElementById('avatar-layer');
    
    // Reuse the page-level React avatar container when it exists.
    const existingContainer = document.getElementById('react-avatar-container');
    if (existingContainer) {
      this.reactContainer = existingContainer;
      return;
    }

    // Create dedicated container for React avatar if it doesn't exist
    if (!document.getElementById('react-avatar-layer')) {
      const reactLayer = document.createElement('div');
      reactLayer.id = 'react-avatar-layer';
      reactLayer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 1;
        pointer-events: none;
        display: none;
      `;
      document.body.insertBefore(reactLayer, document.body.firstChild);
      this.reactContainer = reactLayer;
    } else {
      this.reactContainer = document.getElementById('react-avatar-layer');
    }
  }

  /**
   * Switch to a specific avatar mode
   */
  async setMode(mode) {
    if (mode === this.currentMode) return;
    
    console.log(`[AvatarModeSwitcher] Switching from ${this.currentMode} to ${mode}`);
    
    const previousMode = this.currentMode;
    this.currentMode = mode;

    // Hide/show appropriate containers
    if (mode === AVATAR_MODES.BINARY) {
      this.showBinaryAvatar();
      this.hideReactAvatar();
      this.exitDynamicMode();
    } else if (mode === AVATAR_MODES.REACT_3D) {
      this.hideBinaryAvatar();
      this.exitDynamicMode();
      await this.showReactAvatar();
    } else if (mode === AVATAR_MODES.DYNAMIC) {
      // Dynamic mode: binary avatar stays as the substrate, the
      // DynamicUIManager overlays drive the visible transformation.
      this.showBinaryAvatar();
      this.hideReactAvatar();
      this.enterDynamicMode();
    }

    // Notify listeners
    if (this.onModeChange) {
      this.onModeChange(mode, previousMode);
    }

    // Update UI indicator
    this.updateModeIndicator(mode);
  }

  enterDynamicMode() {
    if (!this.dynamicUI) {
      console.warn('[AvatarModeSwitcher] DYNAMIC mode requested but no DynamicUIManager was supplied to init()');
      return;
    }
    // Show the configured landing view so the user sees an immediate change.
    const entry = this.dynamicEntryView;
    if (entry === 'terminal' && typeof this.dynamicUI.showTerminal === 'function') {
      this.dynamicUI.showTerminal('AIOS dynamic mode online. Speak a command...');
    } else if (entry === 'browser' && typeof this.dynamicUI.showBrowser === 'function') {
      this.dynamicUI.showBrowser('about:blank', '<h1>AIOS Dynamic UI</h1>');
    } else if (typeof this.dynamicUI.showDesktop === 'function') {
      this.dynamicUI.showDesktop([], '/home');
    }
  }

  exitDynamicMode() {
    if (this.dynamicUI && typeof this.dynamicUI.backToAvatar === 'function') {
      this.dynamicUI.backToAvatar();
    }
  }

  showBinaryAvatar() {
    if (this.binaryContainer) {
      this.binaryContainer.style.display = 'block';
    }
    // Resume binary avatar if it has a resume method
    if (this.binaryAvatar && typeof this.binaryAvatar.resume === 'function') {
      this.binaryAvatar.resume();
    }
  }

  hideBinaryAvatar() {
    if (this.binaryContainer) {
      this.binaryContainer.style.display = 'none';
    }
    // Pause binary avatar to save resources
    if (this.binaryAvatar && typeof this.binaryAvatar.pause === 'function') {
      this.binaryAvatar.pause();
    }
  }

  async showReactAvatar() {
    if (this.reactContainer) {
      this.reactContainer.style.display = 'block';
    }
    // Initialize React avatar if not already done
    if (this.reactAvatar && !this.reactAvatar.isInitialized) {
      await this.reactAvatar.init();
    }
  }

  hideReactAvatar() {
    if (this.reactContainer) {
      this.reactContainer.style.display = 'none';
    }
    // Stop any ongoing speech
    if (this.reactAvatar) {
      this.reactAvatar.stopSpeaking();
    }
  }

  updateModeIndicator(mode) {
    const badge = document.getElementById('mode-badge');
    if (badge) {
      const modeNames = {
        [AVATAR_MODES.BINARY]: 'BINARY AVATAR',
        [AVATAR_MODES.REACT_3D]: '3D AVATAR (LIP-SYNC)',
        [AVATAR_MODES.DYNAMIC]: 'DYNAMIC UI'
      };
      badge.textContent = modeNames[mode] || 'AVATAR MODE';
    }
  }

  /**
   * Route speak command to the active avatar
   */
  async speak(text, options = {}) {
    if (this.currentMode === AVATAR_MODES.BINARY && this.binaryAvatar) {
      return await this.binaryAvatar.speak(text, options);
    } else if (this.currentMode === AVATAR_MODES.REACT_3D && this.reactAvatar) {
      // React avatar needs phoneme data from backend
      // This should be provided in options.speechData
      if (options.speechData) {
        return await this.reactAvatar.speak(text, options.speechData);
      } else {
        console.warn('[AvatarModeSwitcher] React 3D mode requires speechData with phonemes');
        // Fallback to binary avatar
        if (this.binaryAvatar) {
          return await this.binaryAvatar.speak(text, options);
        }
      }
    }
  }

  /**
   * Set emotion on active avatar
   */
  setEmotion(emotion) {
    if (this.currentMode === AVATAR_MODES.BINARY && this.binaryAvatar) {
      this.binaryAvatar.setEmotion?.(emotion);
    } else if (this.currentMode === AVATAR_MODES.REACT_3D && this.reactAvatar) {
      this.reactAvatar.setEmotion(emotion);
    }
  }

  /**
   * Set activity state on active avatar
   */
  setActivity(activity) {
    if (this.currentMode === AVATAR_MODES.BINARY && this.binaryAvatar) {
      this.binaryAvatar.setActivity?.(activity);
    } else if (this.currentMode === AVATAR_MODES.REACT_3D && this.reactAvatar) {
      this.reactAvatar.setActivity(activity);
    }
  }

  /**
   * Get current mode
   */
  getMode() {
    return this.currentMode;
  }

  /**
   * Cycle through the available modes (Binary → 3D → Dynamic → Binary).
   * If DynamicUIManager wasn't supplied to init(), DYNAMIC is skipped so
   * the toggle behaves exactly like the original two-mode flip.
   */
  async toggle() {
    const cycle = this.dynamicUI ? MODE_CYCLE : [AVATAR_MODES.BINARY, AVATAR_MODES.REACT_3D];
    const idx = cycle.indexOf(this.currentMode);
    const newMode = cycle[(idx + 1) % cycle.length];
    await this.setMode(newMode);
  }

  /**
   * Cleanup
   */
  destroy() {
    if (this.binaryAvatar) {
      this.binaryAvatar.destroy?.();
    }
    if (this.reactAvatar) {
      this.reactAvatar.destroy();
    }
  }
}
