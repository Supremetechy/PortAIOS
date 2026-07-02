/**
 * DeepGram Status Indicator Component
 * 
 * Adds visual indicators to the UI showing DeepGram agent status
 * Updates existing voice status elements to reflect DeepGram state
 */

class DeepGramStatusIndicator {
  constructor(options = {}) {
    this.options = {
      updateInterval: options.updateInterval || 1000,
      showDetailedStatus: options.showDetailedStatus ?? true,
      ...options
    };

    this.elements = {
      voiceStatus: document.getElementById('voice-status'),
      micStatus: document.getElementById('mic-status'),
      speechStatus: document.getElementById('speech-status'),
      voiceBars: document.getElementById('voice-bars'),
      avatarStatusText: document.getElementById('avatar-status-text')
    };

    this.updateInterval = null;
    this.lastStatus = null;
  }

  /**
   * Initialize the status indicator
   */
  init() {
    console.log('[DeepGram Status] Initializing status indicator...');

    // Start status updates
    this.startStatusUpdates();

    // Listen for voice mode changes
    document.addEventListener('voiceModeChanged', (e) => {
      this.handleModeChange(e.detail.mode);
    });

    // Listen for DeepGram agent events (if available)
    if (window.deepgramAgent) {
      this.watchDeepGramAgent();
    }

    console.log('[DeepGram Status] Status indicator initialized');
  }

  /**
   * Start periodic status updates
   */
  startStatusUpdates() {
    if (this.updateInterval) return;

    this.updateInterval = setInterval(async () => {
      await this.updateStatus();
    }, this.options.updateInterval);

    // Initial update
    this.updateStatus();
  }

  /**
   * Stop status updates
   */
  stopStatusUpdates() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
  }

  /**
   * Update all status indicators
   */
  async updateStatus() {
    // Get status from bridge if available
    if (window.voiceBridge) {
      const status = window.voiceBridge.getStatus();
      this.updateFromBridgeStatus(status);
    } else if (typeof eel !== 'undefined') {
      // Fallback to direct Eel call
      try {
        const status = await eel.get_deepgram_status()();
        this.updateFromDeepGramStatus(status);
      } catch (error) {
        // Silently fail - Eel might not be ready yet
      }
    }
  }

  /**
   * Update from voice bridge status
   */
  updateFromBridgeStatus(status) {
    if (!status) return;

    // Update voice status
    if (this.elements.voiceStatus) {
      if (status.mode === 'deepgram' && status.deepgramEnabled) {
        this.elements.voiceStatus.textContent = 'DeepGram Active';
        this.elements.voiceStatus.style.color = '#00ff88';
        this.animateVoiceBars(true);
      } else if (status.mode === 'browser' && status.browserActive) {
        this.elements.voiceStatus.textContent = 'Browser Active';
        this.elements.voiceStatus.style.color = '#00c8ff';
        this.animateVoiceBars(true);
      } else {
        this.elements.voiceStatus.textContent = 'Standby';
        this.elements.voiceStatus.style.color = '#666';
        this.animateVoiceBars(false);
      }
    }

    // Update mic status
    if (this.elements.micStatus) {
      if (status.mode === 'deepgram') {
        this.elements.micStatus.textContent = 'DeepGram';
        this.elements.micStatus.style.color = '#00ff88';
      } else {
        this.elements.micStatus.textContent = 'Browser';
        this.elements.micStatus.style.color = '#00c8ff';
      }
    }

    // Update speech status
    if (this.elements.speechStatus) {
      if (status.deepgramEnabled || status.browserActive) {
        this.elements.speechStatus.textContent = 'Listening';
        this.elements.speechStatus.style.color = '#00ff88';
      } else {
        this.elements.speechStatus.textContent = 'Ready';
        this.elements.speechStatus.style.color = '#00c8ff';
      }
    }

    // Update avatar status
    if (this.elements.avatarStatusText) {
      if (status.mode === 'deepgram' && status.deepgramEnabled) {
        this.elements.avatarStatusText.textContent = 'Listening (DeepGram)';
      } else if (status.mode === 'browser' && status.browserActive) {
        this.elements.avatarStatusText.textContent = 'Listening (Browser)';
      } else {
        this.elements.avatarStatusText.textContent = 'Ready';
      }
    }
  }

  /**
   * Update from DeepGram status
   */
  updateFromDeepGramStatus(status) {
    if (!status) return;

    // Update voice status
    if (this.elements.voiceStatus) {
      if (status.enabled && status.agent_running) {
        this.elements.voiceStatus.textContent = 'DeepGram Active';
        this.elements.voiceStatus.style.color = '#00ff88';
        this.animateVoiceBars(true);
      } else if (status.available) {
        this.elements.voiceStatus.textContent = 'DeepGram Ready';
        this.elements.voiceStatus.style.color = '#00c8ff';
        this.animateVoiceBars(false);
      } else if (status.fallback_mode) {
        this.elements.voiceStatus.textContent = 'Fallback Mode';
        this.elements.voiceStatus.style.color = '#ffaa00';
        this.animateVoiceBars(false);
      } else {
        this.elements.voiceStatus.textContent = 'Standby';
        this.elements.voiceStatus.style.color = '#666';
        this.animateVoiceBars(false);
      }
    }

    this.lastStatus = status;
  }

  /**
   * Handle voice mode change
   */
  handleModeChange(mode) {
    console.log('[DeepGram Status] Mode changed to:', mode);

    // Add visual feedback
    this.flashModeChange(mode);
  }

  /**
   * Flash visual feedback on mode change
   */
  flashModeChange(mode) {
    const color = mode === 'deepgram' ? '#00ff88' : '#00c8ff';
    
    // Flash all status elements
    Object.values(this.elements).forEach(el => {
      if (!el) return;
      
      el.style.transition = 'all 0.3s ease';
      el.style.backgroundColor = `${color}22`;
      el.style.boxShadow = `0 0 10px ${color}88`;
      
      setTimeout(() => {
        el.style.backgroundColor = '';
        el.style.boxShadow = '';
      }, 300);
    });
  }

  /**
   * Animate voice bars
   */
  animateVoiceBars(active) {
    if (!this.elements.voiceBars) return;

    const bars = this.elements.voiceBars.querySelectorAll('span');
    
    if (active) {
      bars.forEach((bar, i) => {
        bar.style.animation = `voice-bar-pulse 0.8s ease-in-out ${i * 0.1}s infinite`;
        bar.style.backgroundColor = '#00ff88';
      });
    } else {
      bars.forEach(bar => {
        bar.style.animation = '';
        bar.style.backgroundColor = '#00c8ff';
      });
    }
  }

  /**
   * Watch DeepGram agent for events
   */
  watchDeepGramAgent() {
    if (!window.deepgramAgent) return;

    // Monitor status changes
    setInterval(() => {
      const status = window.deepgramAgent.getStatus();
      if (JSON.stringify(status) !== JSON.stringify(this.lastStatus)) {
        this.updateFromDeepGramStatus(status);
      }
    }, 500);
  }

  /**
   * Add notification toast
   */
  showNotification(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `deepgram-notification deepgram-notification-${type}`;
    toast.innerHTML = `
      <span class="notification-icon">${this.getNotificationIcon(type)}</span>
      <span class="notification-message">${message}</span>
    `;

    // Add to body
    document.body.appendChild(toast);

    // Add styles if not already present
    this.ensureNotificationStyles();

    // Auto-remove after 3 seconds
    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  /**
   * Get notification icon
   */
  getNotificationIcon(type) {
    const icons = {
      info: 'ℹ️',
      success: '✅',
      warning: '⚠️',
      error: '❌'
    };
    return icons[type] || icons.info;
  }

  /**
   * Ensure notification styles exist
   */
  ensureNotificationStyles() {
    if (document.getElementById('deepgram-notification-styles')) return;

    const style = document.createElement('style');
    style.id = 'deepgram-notification-styles';
    style.textContent = `
      .deepgram-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px 20px;
        background: rgba(10, 15, 25, 0.95);
        border: 1px solid rgba(0, 200, 255, 0.3);
        border-radius: 6px;
        color: #fff;
        font-size: 13px;
        z-index: 10000;
        animation: slide-in 0.3s ease-out;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
      }

      .deepgram-notification-success {
        border-color: rgba(0, 255, 136, 0.5);
      }

      .deepgram-notification-warning {
        border-color: rgba(255, 170, 0, 0.5);
      }

      .deepgram-notification-error {
        border-color: rgba(255, 68, 68, 0.5);
      }

      .deepgram-notification.fade-out {
        animation: slide-out 0.3s ease-in;
      }

      @keyframes slide-in {
        from {
          transform: translateX(400px);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }

      @keyframes slide-out {
        from {
          transform: translateX(0);
          opacity: 1;
        }
        to {
          transform: translateX(400px);
          opacity: 0;
        }
      }

      @keyframes voice-bar-pulse {
        0%, 100% {
          transform: scaleY(0.5);
          opacity: 0.5;
        }
        50% {
          transform: scaleY(1.2);
          opacity: 1;
        }
      }
    `;

    document.head.appendChild(style);
  }

  /**
   * Destroy the indicator
   */
  destroy() {
    this.stopStatusUpdates();
  }
}

// Create global instance
window.deepgramStatusIndicator = new DeepGramStatusIndicator();

// Auto-initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.deepgramStatusIndicator.init();
  });
} else {
  window.deepgramStatusIndicator.init();
}

// Listen for mode changes and show notifications
document.addEventListener('voiceModeChanged', (e) => {
  const mode = e.detail.mode;
  const message = mode === 'deepgram' 
    ? '🎤 Switched to DeepGram Unified Voice Agent' 
    : '🌐 Switched to Browser Voice Input';
  
  window.deepgramStatusIndicator.showNotification(message, 'success');
});

// Export
window.DeepGramStatusIndicator = DeepGramStatusIndicator;
