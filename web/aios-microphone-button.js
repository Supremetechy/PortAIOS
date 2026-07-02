/**
 * AIOS-styled Microphone Button Component
 * Matches the cyberpunk/neural interface theme
 */

class AIOSMicrophoneButton {
  constructor(container, voiceController, options = {}) {
    this.container = container || document.body;
    this.voiceController = voiceController;
    this.options = {
      position: options.position || 'bottom-right', // bottom-right, bottom-left, top-right, top-left
      theme: options.theme || 'cyan', // cyan, green, red, purple
      showLabel: options.showLabel !== false,
      showWaveform: options.showWaveform !== false,
      ...options
    };

    this.button = null;
    this.isActive = false;
    this.init();
  }

  init() {
    this.createButton();
    this.attachStyles();
    this.setupEventListeners();
  }

  createButton() {
    // Main button container
    this.button = document.createElement('div');
    this.button.id = 'aios-mic-button';
    this.button.className = `aios-mic-button ${this.options.position} theme-${this.options.theme}`;
    this.button.setAttribute('role', 'button');
    this.button.setAttribute('aria-label', 'Toggle microphone');
    this.button.setAttribute('tabindex', '0');

    // Inner structure
    this.button.innerHTML = `
      <div class="mic-glow"></div>
      <div class="mic-ring"></div>
      <div class="mic-content">
        <svg class="mic-icon" viewBox="0 0 24 24" width="28" height="28">
          <path fill="currentColor" d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
          <path fill="currentColor" d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
        </svg>
        ${this.options.showLabel ? '<div class="mic-label">MIC</div>' : ''}
      </div>
      ${this.options.showWaveform ? `
        <div class="mic-waveform">
          <span></span><span></span><span></span><span></span><span></span>
        </div>
      ` : ''}
      <div class="mic-status-text">OFF</div>
      <div class="corner-accent tl"></div>
      <div class="corner-accent tr"></div>
      <div class="corner-accent bl"></div>
      <div class="corner-accent br"></div>
    `;

    this.container.appendChild(this.button);
  }

  attachStyles() {
    const styleId = 'aios-mic-button-styles';
    if (document.getElementById(styleId)) return;

    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
      .aios-mic-button {
        position: fixed;
        width: 70px;
        height: 70px;
        cursor: pointer;
        user-select: none;
        z-index: 9999;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      }

      /* Positioning */
      .aios-mic-button.bottom-right {
        bottom: 2rem;
        right: 2rem;
      }

      .aios-mic-button.bottom-left {
        bottom: 2rem;
        left: 2rem;
      }

      .aios-mic-button.top-right {
        top: 2rem;
        right: 2rem;
      }

      .aios-mic-button.top-left {
        top: 2rem;
        left: 2rem;
      }

      /* Theme colors */
      .aios-mic-button.theme-cyan {
        --mic-color: #00d9ff;
        --mic-glow: rgba(0, 217, 255, 0.4);
      }

      .aios-mic-button.theme-green {
        --mic-color: #00ff64;
        --mic-glow: rgba(0, 255, 100, 0.4);
      }

      .aios-mic-button.theme-red {
        --mic-color: #ff3366;
        --mic-glow: rgba(255, 51, 102, 0.4);
      }

      .aios-mic-button.theme-purple {
        --mic-color: #b466ff;
        --mic-glow: rgba(180, 102, 255, 0.4);
      }

      /* Glow effect */
      .mic-glow {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 100%;
        height: 100%;
        background: radial-gradient(circle, var(--mic-glow) 0%, transparent 70%);
        opacity: 0;
        transition: opacity 0.3s ease;
      }

      .aios-mic-button:hover .mic-glow,
      .aios-mic-button.active .mic-glow {
        opacity: 1;
      }

      /* Ring */
      .mic-ring {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 100%;
        height: 100%;
        border: 2px solid var(--mic-color);
        border-radius: 50%;
        opacity: 0.3;
        transition: all 0.3s ease;
      }

      .aios-mic-button:hover .mic-ring {
        opacity: 0.6;
        transform: translate(-50%, -50%) scale(1.1);
      }

      .aios-mic-button.active .mic-ring {
        opacity: 1;
        animation: mic-ring-pulse 2s infinite;
      }

      @keyframes mic-ring-pulse {
        0%, 100% {
          transform: translate(-50%, -50%) scale(1);
          opacity: 1;
        }
        50% {
          transform: translate(-50%, -50%) scale(1.15);
          opacity: 0.6;
        }
      }

      /* Content */
      .mic-content {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: var(--mic-color);
        transition: all 0.3s ease;
      }

      .mic-icon {
        filter: drop-shadow(0 0 4px var(--mic-glow));
        transition: all 0.3s ease;
      }

      .aios-mic-button:hover .mic-icon {
        transform: scale(1.1);
      }

      .aios-mic-button.active .mic-icon {
        animation: mic-icon-pulse 1.5s infinite;
      }

      @keyframes mic-icon-pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.15); }
      }

      .mic-label {
        font-family: 'Share Tech Mono', 'Orbitron', monospace;
        font-size: 8px;
        font-weight: 700;
        letter-spacing: 1px;
        margin-top: 2px;
        text-shadow: 0 0 4px var(--mic-glow);
      }

      /* Waveform */
      .mic-waveform {
        position: absolute;
        bottom: -20px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        gap: 3px;
        opacity: 0;
        transition: opacity 0.3s ease;
      }

      .aios-mic-button.active .mic-waveform {
        opacity: 1;
      }

      .mic-waveform span {
        width: 3px;
        height: 8px;
        background: var(--mic-color);
        border-radius: 2px;
        animation: mic-wave 0.8s ease-in-out infinite;
      }

      .mic-waveform span:nth-child(1) { animation-delay: 0s; }
      .mic-waveform span:nth-child(2) { animation-delay: 0.1s; }
      .mic-waveform span:nth-child(3) { animation-delay: 0.2s; }
      .mic-waveform span:nth-child(4) { animation-delay: 0.3s; }
      .mic-waveform span:nth-child(5) { animation-delay: 0.4s; }

      @keyframes mic-wave {
        0%, 100% { height: 8px; }
        50% { height: 16px; }
      }

      /* Status text */
      .mic-status-text {
        position: absolute;
        top: -22px;
        left: 50%;
        transform: translateX(-50%);
        font-family: 'Share Tech Mono', monospace;
        font-size: 9px;
        font-weight: 700;
        color: var(--mic-color);
        text-shadow: 0 0 4px var(--mic-glow);
        opacity: 0;
        transition: opacity 0.3s ease;
        white-space: nowrap;
      }

      .aios-mic-button:hover .mic-status-text,
      .aios-mic-button.active .mic-status-text {
        opacity: 1;
      }

      /* Corner accents */
      .corner-accent {
        position: absolute;
        width: 12px;
        height: 12px;
        border: 1px solid var(--mic-color);
        opacity: 0;
        transition: opacity 0.3s ease;
      }

      .aios-mic-button:hover .corner-accent,
      .aios-mic-button.active .corner-accent {
        opacity: 0.5;
      }

      .corner-accent.tl {
        top: 0;
        left: 0;
        border-right: none;
        border-bottom: none;
      }

      .corner-accent.tr {
        top: 0;
        right: 0;
        border-left: none;
        border-bottom: none;
      }

      .corner-accent.bl {
        bottom: 0;
        left: 0;
        border-right: none;
        border-top: none;
      }

      .corner-accent.br {
        bottom: 0;
        right: 0;
        border-left: none;
        border-top: none;
      }

      /* Hover effects */
      .aios-mic-button:hover {
        transform: scale(1.05);
      }

      .aios-mic-button:active {
        transform: scale(0.95);
      }

      /* Focus styles */
      .aios-mic-button:focus {
        outline: none;
      }

      .aios-mic-button:focus-visible .mic-ring {
        opacity: 1;
        box-shadow: 0 0 0 3px var(--mic-glow);
      }

      /* Mobile adjustments */
      @media (max-width: 768px) {
        .aios-mic-button {
          width: 60px;
          height: 60px;
        }

        .aios-mic-button.bottom-right,
        .aios-mic-button.bottom-left {
          bottom: 1rem;
        }

        .aios-mic-button.bottom-right {
          right: 1rem;
        }

        .aios-mic-button.bottom-left {
          left: 1rem;
        }
      }
    `;

    document.head.appendChild(style);
  }

  setupEventListeners() {
    // Click/tap to toggle
    this.button.addEventListener('click', () => this.toggle());

    // Keyboard support
    this.button.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        this.toggle();
      }
    });

    // Connect to voice controller if provided
    if (this.voiceController) {
      this.voiceController.onMicrophoneStart = () => this.setActive(true);
      this.voiceController.onMicrophoneStop = () => this.setActive(false);
    }
  }

  toggle() {
    if (this.voiceController) {
      this.voiceController.toggle();
    } else {
      this.setActive(!this.isActive);
    }
  }

  setActive(active) {
    this.isActive = active;
    
    if (active) {
      this.button.classList.add('active');
      const statusText = this.button.querySelector('.mic-status-text');
      if (statusText) statusText.textContent = 'ON';
    } else {
      this.button.classList.remove('active');
      const statusText = this.button.querySelector('.mic-status-text');
      if (statusText) statusText.textContent = 'OFF';
    }
  }

  setTheme(theme) {
    this.button.classList.remove('theme-cyan', 'theme-green', 'theme-red', 'theme-purple');
    this.button.classList.add(`theme-${theme}`);
  }

  setPosition(position) {
    this.button.classList.remove('bottom-right', 'bottom-left', 'top-right', 'top-left');
    this.button.classList.add(position);
  }

  destroy() {
    if (this.button && this.button.parentNode) {
      this.button.parentNode.removeChild(this.button);
    }
  }
}

// ES6 Export for module imports
export { AIOSMicrophoneButton };

// Global API for non-module scripts
if (typeof window !== 'undefined') {
  window.AIOS = window.AIOS || {};
  window.AIOS.MicrophoneButton = AIOSMicrophoneButton;
}
