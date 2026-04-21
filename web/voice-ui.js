/**
 * Voice Input UI Components
 * Visual feedback for voice recognition states
 */

class VoiceUI {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      position: options.position || 'bottom-center', // 'bottom-center', 'top-right', etc.
      showTranscript: options.showTranscript !== false,
      showWaveform: options.showWaveform !== false,
      ...options
    };

    this.elements = {};
    this.state = 'idle';
    
    this.init();
  }

  init() {
    this.createUI();
    this.attachStyles();
  }

  createUI() {
    // Main voice UI container
    this.elements.main = document.createElement('div');
    this.elements.main.id = 'voice-ui';
    this.elements.main.className = `voice-ui ${this.options.position}`;

    // Microphone button
    this.elements.micButton = document.createElement('button');
    this.elements.micButton.className = 'voice-mic-button';
    this.elements.micButton.innerHTML = `
      <svg class="mic-icon" viewBox="0 0 24 24" width="24" height="24">
        <path fill="currentColor" d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
        <path fill="currentColor" d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
      </svg>
      <span class="mic-label">Push to Talk</span>
    `;

    // State indicator
    this.elements.stateIndicator = document.createElement('div');
    this.elements.stateIndicator.className = 'voice-state-indicator';
    this.elements.stateIndicator.innerHTML = `
      <div class="state-dot"></div>
      <span class="state-text">Ready</span>
    `;

    // Waveform visualization
    if (this.options.showWaveform) {
      this.elements.waveform = document.createElement('div');
      this.elements.waveform.className = 'voice-waveform';
      this.elements.waveform.innerHTML = `
        <div class="wave-bar"></div>
        <div class="wave-bar"></div>
        <div class="wave-bar"></div>
        <div class="wave-bar"></div>
        <div class="wave-bar"></div>
      `;
    }

    // Transcript display
    if (this.options.showTranscript) {
      this.elements.transcript = document.createElement('div');
      this.elements.transcript.className = 'voice-transcript';
      this.elements.transcript.innerHTML = `
        <div class="transcript-interim"></div>
        <div class="transcript-final"></div>
      `;
    }

    // Command hints
    this.elements.hints = document.createElement('div');
    this.elements.hints.className = 'voice-hints';
    this.elements.hints.style.display = 'none';

    // Assemble UI
    this.elements.main.appendChild(this.elements.stateIndicator);
    
    if (this.options.showWaveform) {
      this.elements.main.appendChild(this.elements.waveform);
    }
    
    if (this.options.showTranscript) {
      this.elements.main.appendChild(this.elements.transcript);
    }
    
    this.elements.main.appendChild(this.elements.hints);
    this.elements.main.appendChild(this.elements.micButton);

    // Add to container
    this.container.appendChild(this.elements.main);
  }

  attachStyles() {
    const styleId = 'voice-ui-styles';
    if (document.getElementById(styleId)) return;

    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
      .voice-ui {
        position: fixed;
        z-index: 9999;
        background: rgba(0, 0, 0, 0.9);
        border: 2px solid #0f0;
        border-radius: 12px;
        padding: 15px 20px;
        box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
        font-family: 'Courier New', monospace;
        min-width: 300px;
        transition: all 0.3s ease;
      }

      .voice-ui.bottom-center {
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
      }

      .voice-ui.top-right {
        top: 80px;
        right: 20px;
      }

      .voice-ui.state-listening {
        border-color: #0ff;
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.5);
      }

      .voice-ui.state-processing {
        border-color: #ff0;
        box-shadow: 0 0 30px rgba(255, 255, 0, 0.5);
      }

      .voice-ui.state-error {
        border-color: #f00;
        box-shadow: 0 0 30px rgba(255, 0, 0, 0.5);
      }

      /* State Indicator */
      .voice-state-indicator {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
        color: #0f0;
        font-size: 12px;
      }

      .state-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #0f0;
        animation: pulse 2s ease-in-out infinite;
      }

      .voice-ui.state-listening .state-dot {
        background: #0ff;
        animation: pulse-fast 0.5s ease-in-out infinite;
      }

      .voice-ui.state-processing .state-dot {
        background: #ff0;
        animation: spin 1s linear infinite;
      }

      .voice-ui.state-error .state-dot {
        background: #f00;
        animation: blink 0.5s ease-in-out infinite;
      }

      @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.6; transform: scale(1.2); }
      }

      @keyframes pulse-fast {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.3); }
      }

      @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }

      @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
      }

      /* Waveform */
      .voice-waveform {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 3px;
        height: 30px;
        margin: 10px 0;
        opacity: 0;
        transition: opacity 0.3s;
      }

      .voice-ui.state-listening .voice-waveform,
      .voice-ui.state-processing .voice-waveform {
        opacity: 1;
      }

      .wave-bar {
        width: 4px;
        background: #0f0;
        border-radius: 2px;
        transition: height 0.1s ease;
      }

      .voice-ui.state-listening .wave-bar {
        background: #0ff;
        animation: wave 0.8s ease-in-out infinite;
      }

      .voice-ui.state-processing .wave-bar {
        background: #ff0;
      }

      .wave-bar:nth-child(1) { animation-delay: 0s; height: 10px; }
      .wave-bar:nth-child(2) { animation-delay: 0.1s; height: 15px; }
      .wave-bar:nth-child(3) { animation-delay: 0.2s; height: 20px; }
      .wave-bar:nth-child(4) { animation-delay: 0.3s; height: 15px; }
      .wave-bar:nth-child(5) { animation-delay: 0.4s; height: 10px; }

      @keyframes wave {
        0%, 100% { height: 10px; }
        50% { height: 25px; }
      }

      /* Transcript */
      .voice-transcript {
        margin: 10px 0;
        padding: 10px;
        background: rgba(0, 255, 0, 0.1);
        border: 1px solid rgba(0, 255, 0, 0.3);
        border-radius: 4px;
        min-height: 50px;
        max-height: 100px;
        overflow-y: auto;
      }

      .transcript-interim {
        color: #0ff;
        font-style: italic;
        opacity: 0.7;
        margin-bottom: 5px;
      }

      .transcript-final {
        color: #0f0;
        font-weight: bold;
      }

      /* Hints */
      .voice-hints {
        margin: 10px 0;
        padding: 8px;
        background: rgba(0, 255, 255, 0.1);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 4px;
        font-size: 11px;
        color: #0ff;
      }

      .voice-hints .hint-title {
        font-weight: bold;
        margin-bottom: 5px;
      }

      .voice-hints .hint-item {
        margin: 3px 0;
        padding-left: 10px;
      }

      /* Microphone Button */
      .voice-mic-button {
        width: 100%;
        padding: 12px;
        background: rgba(0, 255, 0, 0.1);
        border: 2px solid #0f0;
        border-radius: 8px;
        color: #0f0;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        transition: all 0.2s;
      }

      .voice-mic-button:hover {
        background: rgba(0, 255, 0, 0.2);
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
      }

      .voice-mic-button:active {
        transform: scale(0.95);
      }

      .voice-ui.state-listening .voice-mic-button {
        background: rgba(0, 255, 255, 0.2);
        border-color: #0ff;
        color: #0ff;
      }

      .mic-icon {
        width: 24px;
        height: 24px;
      }

      /* Hidden state */
      .voice-ui.hidden {
        opacity: 0;
        pointer-events: none;
      }

      /* Mobile responsiveness */
      @media (max-width: 768px) {
        .voice-ui {
          min-width: 280px;
          padding: 12px 15px;
        }

        .voice-mic-button {
          padding: 10px;
          font-size: 13px;
        }
      }
    `;

    document.head.appendChild(style);
  }

  setState(state) {
    this.state = state;
    
    // Update main container class
    this.elements.main.classList.remove('state-listening', 'state-processing', 'state-error', 'state-idle');
    this.elements.main.classList.add(`state-${state}`);

    // Update state text
    const stateTexts = {
      'idle': 'Ready',
      'listening': 'Listening...',
      'processing': 'Processing...',
      'thinking': 'Thinking...',
      'error': 'Error',
      'awake': 'Active'
    };

    const stateText = this.elements.stateIndicator.querySelector('.state-text');
    if (stateText) {
      stateText.textContent = stateTexts[state] || 'Ready';
    }

    // Update mic button label
    const micLabel = this.elements.micButton.querySelector('.mic-label');
    if (micLabel) {
      if (state === 'listening') {
        micLabel.textContent = 'Listening...';
      } else {
        micLabel.textContent = 'Push to Talk';
      }
    }
  }

  updateTranscript(interim, final) {
    if (!this.options.showTranscript || !this.elements.transcript) return;

    const interimEl = this.elements.transcript.querySelector('.transcript-interim');
    const finalEl = this.elements.transcript.querySelector('.transcript-final');

    if (interimEl) {
      interimEl.textContent = interim || '';
    }

    if (finalEl && final) {
      finalEl.textContent = final;
      
      // Auto-scroll to bottom
      this.elements.transcript.scrollTop = this.elements.transcript.scrollHeight;
    }
  }

  showHints(hints) {
    if (!this.elements.hints) return;

    if (!hints || hints.length === 0) {
      this.elements.hints.style.display = 'none';
      return;
    }

    const hintsHTML = `
      <div class="hint-title">Try saying:</div>
      ${hints.map(hint => `<div class="hint-item">"${hint}"</div>`).join('')}
    `;

    this.elements.hints.innerHTML = hintsHTML;
    this.elements.hints.style.display = 'block';
  }

  hideHints() {
    if (this.elements.hints) {
      this.elements.hints.style.display = 'none';
    }
  }

  show() {
    this.elements.main.classList.remove('hidden');
  }

  hide() {
    this.elements.main.classList.add('hidden');
  }

  onMicClick(callback) {
    this.elements.micButton.addEventListener('click', callback);
  }

  destroy() {
    if (this.elements.main && this.elements.main.parentNode) {
      this.elements.main.parentNode.removeChild(this.elements.main);
    }
  }
}

export { VoiceUI };

// Global API
if (typeof window !== 'undefined') {
  window.AIOS = window.AIOS || {};
  window.AIOS.VoiceUI = VoiceUI;
}
