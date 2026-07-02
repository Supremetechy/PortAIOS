/**
 * Integrated Voice and Desktop Control
 * Connects voice commands to desktop bridge and dynamic UI
 */

class IntegratedVoiceDesktop {
  constructor(voiceInput, dynamicUI, options = {}) {
    this.voiceInput = voiceInput;
    this.dynamicUI = dynamicUI;
    this.desktopBridge = dynamicUI.getDesktopBridge();
    
    this.options = {
      enableVoiceDesktopControl: true,
      enableMicrophoneToggle: true,
      ...options
    };
    
    this.initialize();
  }

  initialize() {
    console.log('[IntegratedVoice] Initializing integrated voice-desktop control...');
    
    // Connect voice input callbacks
    if (this.voiceInput) {
      this.setupVoiceCallbacks();
    }
    
    // Setup microphone controls if enabled
    if (this.options.enableMicrophoneToggle) {
      this.setupMicrophoneControls();
    }
    
    console.log('[IntegratedVoice] Initialization complete');
  }

  setupVoiceCallbacks() {
    // Extend onCommand callback to handle desktop commands
    const originalOnCommand = this.voiceInput.onCommand;
    this.voiceInput.onCommand = (command) => {
      console.log('[IntegratedVoice] Processing command:', command);
      
      // Try desktop/UI commands first
      if (this.handleDesktopCommand(command)) {
        console.log('[IntegratedVoice] Desktop command handled');
        return;
      }
      
      // Fall back to original command handler
      if (originalOnCommand) {
        originalOnCommand(command);
      }
    };

    // Setup microphone state callbacks
    this.voiceInput.onMicrophoneStart = () => {
      console.log('[IntegratedVoice] Microphone started');
      this.updateMicrophoneUI(true);
    };

    this.voiceInput.onMicrophoneStop = () => {
      console.log('[IntegratedVoice] Microphone stopped');
      this.updateMicrophoneUI(false);
    };

    this.voiceInput.onSilenceDetected = () => {
      console.log('[IntegratedVoice] Silence detected - microphone auto-stopped');
    };
  }

  setupMicrophoneControls() {
    // Add keyboard shortcut for microphone toggle (Ctrl+M or Cmd+M)
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
        e.preventDefault();
        this.toggleMicrophone();
      }
    });

    // Add visual microphone button if not present
    this.createMicrophoneButton();
  }

  createMicrophoneButton() {
    // Check if button already exists
    if (document.getElementById('voice-mic-toggle')) {
      return;
    }

    const button = document.createElement('button');
    button.id = 'voice-mic-toggle';
    button.className = 'voice-mic-toggle';
    button.setAttribute('aria-label', 'Toggle microphone');
    button.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
        <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
      </svg>
      <span class="mic-status">Off</span>
    `;
    
    button.addEventListener('click', () => this.toggleMicrophone());
    
    // Add to page
    document.body.appendChild(button);
    
    // Add styles
    this.addMicrophoneButtonStyles();
  }

  addMicrophoneButtonStyles() {
    const style = document.createElement('style');
    style.textContent = `
      .voice-mic-toggle {
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: rgba(0, 150, 255, 0.1);
        border: 2px solid rgba(0, 150, 255, 0.3);
        color: #0096ff;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        z-index: 1000;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
      }
      
      .voice-mic-toggle:hover {
        background: rgba(0, 150, 255, 0.2);
        border-color: rgba(0, 150, 255, 0.5);
        transform: scale(1.05);
      }
      
      .voice-mic-toggle.active {
        background: rgba(0, 255, 100, 0.2);
        border-color: rgba(0, 255, 100, 0.5);
        color: #00ff64;
        animation: pulse-mic 1.5s infinite;
      }
      
      .voice-mic-toggle svg {
        width: 28px;
        height: 28px;
      }
      
      .voice-mic-toggle .mic-status {
        font-size: 9px;
        font-weight: 600;
        margin-top: 2px;
        text-transform: uppercase;
      }
      
      @keyframes pulse-mic {
        0%, 100% { box-shadow: 0 0 0 0 rgba(0, 255, 100, 0.4); }
        50% { box-shadow: 0 0 0 10px rgba(0, 255, 100, 0); }
      }
    `;
    document.head.appendChild(style);
  }

  toggleMicrophone() {
    if (!this.voiceInput) {
      console.warn('[IntegratedVoice] Voice input not available');
      return;
    }

    const isActive = this.voiceInput.toggle();
    console.log('[IntegratedVoice] Microphone toggled:', isActive ? 'ON' : 'OFF');
  }

  updateMicrophoneUI(isActive) {
    const button = document.getElementById('voice-mic-toggle');
    if (button) {
      if (isActive) {
        button.classList.add('active');
        const status = button.querySelector('.mic-status');
        if (status) status.textContent = 'On';
      } else {
        button.classList.remove('active');
        const status = button.querySelector('.mic-status');
        if (status) status.textContent = 'Off';
      }
    }
  }

  async handleDesktopCommand(command) {
    const raw = typeof command === 'object' ? (command.command ?? '') : (command ?? '');
    const cmd = raw.toLowerCase().trim();

    // Try advanced desktop features first (clipboard, screenshots, etc)
    if (window.AIOS?.advancedDesktop) {
      const handled = await window.AIOS.advancedDesktop.handleVoiceCommand(cmd);
      if (handled) return true;
    }
    
    // Desktop navigation commands
    if (cmd.includes('show desktop') || cmd.includes('open desktop')) {
      if (this.desktopBridge) {
        this.desktopBridge.showDesktop();
      } else {
        this.dynamicUI.showDesktop([], '/home');
      }
      return true;
    }

    if (cmd.includes('show files') || cmd.includes('open files')) {
      if (this.desktopBridge) {
        this.desktopBridge.showDesktop();
      } else {
        this.dynamicUI.showDesktop([], '/home');
      }
      return true;
    }

    // Browser commands
    if (cmd.includes('open browser')) {
      const urlMatch = cmd.match(/open browser (.+)/);
      const url = urlMatch ? urlMatch[1] : 'about:blank';
      
      if (this.desktopBridge) {
        this.desktopBridge.showBrowser(url);
      } else {
        this.dynamicUI.showBrowser(url);
      }
      return true;
    }

    // App launching
    if (cmd.includes('launch') || cmd.includes('open app')) {
      const appMatch = cmd.match(/(?:launch|open app) (.+)/);
      if (appMatch) {
        const appName = appMatch[1];
        if (this.desktopBridge) {
          this.desktopBridge.launchApp(appName);
        }
        return true;
      }
    }

    // Navigation
    if (cmd === 'go back' || cmd === 'back') {
      if (this.desktopBridge) {
        this.desktopBridge.goBack();
      } else {
        this.dynamicUI.backToAvatar();
      }
      return true;
    }

    if (cmd === 'return to avatar' || cmd === 'show avatar') {
      if (this.desktopBridge) {
        this.desktopBridge.returnToAvatar();
      } else {
        this.dynamicUI.backToAvatar();
      }
      return true;
    }

    // Microphone control commands
    if (cmd.includes('turn on microphone') || cmd.includes('enable microphone')) {
      this.voiceInput.enableMicrophone();
      return true;
    }

    if (cmd.includes('turn off microphone') || cmd.includes('disable microphone') || cmd.includes('stop listening')) {
      this.voiceInput.disableMicrophone();
      return true;
    }

    // Terminal
    if (cmd.includes('open terminal') || cmd.includes('show terminal')) {
      this.dynamicUI.showTerminal('Terminal ready. Type your commands.');
      return true;
    }

    return false;
  }

  // Public API
  getMicrophoneState() {
    return this.voiceInput ? this.voiceInput.isMicrophoneActive() : false;
  }

  enableMicrophone() {
    return this.voiceInput ? this.voiceInput.enableMicrophone() : false;
  }

  disableMicrophone() {
    return this.voiceInput ? this.voiceInput.disableMicrophone() : false;
  }

  setSilenceDetection(enabled) {
    if (this.voiceInput) {
      this.voiceInput.setSilenceDetection(enabled);
    }
  }

  setAutoStopOnSilence(enabled) {
    if (this.voiceInput) {
      this.voiceInput.setAutoStopOnSilence(enabled);
    }
  }
}

// ES6 Export for module imports
export { IntegratedVoiceDesktop };

// Global API for non-module scripts
if (typeof window !== 'undefined') {
  window.AIOS = window.AIOS || {};
  window.AIOS.IntegratedVoiceDesktop = IntegratedVoiceDesktop;
}
