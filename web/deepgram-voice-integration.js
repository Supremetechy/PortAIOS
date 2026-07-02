/**
 * DeepGram Voice Integration Bridge
 * 
 * Integrates DeepGram voice agent with existing voice-input.js
 * Provides seamless switching between browser-based voice and DeepGram agent
 */

class DeepGramVoiceIntegrationBridge {
  constructor(voiceInputController = null) {
    this.voiceInputController = voiceInputController;
    this.deepgramAgent = null;
    this.mode = 'browser'; // 'browser' or 'deepgram'
    this.preferDeepGram = true; // Prefer DeepGram when available
    
    this.callbacks = {
      onTranscript: null,
      onResponse: null,
      onModeChange: null,
      onError: null
    };
  }

  /**
   * Initialize the integration bridge
   */
  async init(options = {}) {
    console.log('[DeepGram Bridge] Initializing...');

    // Merge options
    this.preferDeepGram = options.preferDeepGram ?? true;
    Object.assign(this.callbacks, options);

    // Check if DeepGram is available
    if (typeof eel !== 'undefined') {
      try {
        const status = await eel.get_deepgram_status()();
        
        if (status.available && this.preferDeepGram) {
          console.log('[DeepGram Bridge] DeepGram available, setting as preferred mode');
          this.mode = 'deepgram';
          
          // Initialize DeepGram agent if not already done
          if (window.DeepGramVoiceAgent && !this.deepgramAgent) {
            this.deepgramAgent = new window.DeepGramVoiceAgent({
              autoEnable: options.autoEnableDeepGram ?? false,
              showUI: options.showDeepGramUI ?? true,
              onResponse: (response) => this.handleDeepGramResponse(response),
              onError: (error) => this.handleError(error)
            });
            await this.deepgramAgent.init();
          }
        } else {
          console.log('[DeepGram Bridge] Using browser-based voice input');
          this.mode = 'browser';
        }
      } catch (error) {
        console.warn('[DeepGram Bridge] DeepGram not available:', error);
        this.mode = 'browser';
      }
    } else {
      console.log('[DeepGram Bridge] Eel not available, using browser mode');
      this.mode = 'browser';
    }

    // Notify mode change
    this.notifyModeChange();
    
    console.log('[DeepGram Bridge] Initialized in', this.mode, 'mode');
    return this.mode;
  }

  /**
   * Handle DeepGram response
   */
  handleDeepGramResponse(response) {
    console.log('[DeepGram Bridge] Response:', response);
    
    if (this.callbacks.onResponse) {
      this.callbacks.onResponse(response);
    }

    // Also trigger avatar if available
    if (window.AIOS?.avatar) {
      window.AIOS.avatar.speak(response);
    }
  }

  /**
   * Handle errors
   */
  handleError(error) {
    console.error('[DeepGram Bridge] Error:', error);
    
    if (this.callbacks.onError) {
      this.callbacks.onError(error);
    }
  }

  /**
   * Notify mode change
   */
  notifyModeChange() {
    if (this.callbacks.onModeChange) {
      this.callbacks.onModeChange(this.mode);
    }

    // Update UI indicators
    this.updateModeIndicators();
  }

  /**
   * Update UI mode indicators
   */
  updateModeIndicators() {
    // Update voice status
    const voiceStatus = document.getElementById('voice-status');
    const micStatus = document.getElementById('mic-status');
    
    if (voiceStatus) {
      if (this.mode === 'deepgram') {
        voiceStatus.textContent = 'DeepGram Agent';
        voiceStatus.style.color = '#00ff88';
      } else {
        voiceStatus.textContent = 'Browser';
        voiceStatus.style.color = '#00c8ff';
      }
    }

    if (micStatus) {
      if (this.mode === 'deepgram') {
        micStatus.textContent = 'DeepGram';
      } else {
        micStatus.textContent = 'Browser';
      }
    }

    // Dispatch custom event
    document.dispatchEvent(new CustomEvent('voiceModeChanged', {
      detail: { mode: this.mode }
    }));
  }

  /**
   * Switch between modes
   */
  async switchMode(newMode) {
    if (newMode === this.mode) {
      console.log('[DeepGram Bridge] Already in', newMode, 'mode');
      return;
    }

    console.log('[DeepGram Bridge] Switching to', newMode, 'mode');

    // Disable current mode
    if (this.mode === 'deepgram' && this.deepgramAgent) {
      await this.deepgramAgent.disable();
    } else if (this.mode === 'browser' && this.voiceInputController) {
      this.voiceInputController.stop();
    }

    // Switch mode
    this.mode = newMode;

    // Enable new mode
    if (this.mode === 'deepgram' && this.deepgramAgent) {
      await this.deepgramAgent.enable();
    } else if (this.mode === 'browser' && this.voiceInputController) {
      this.voiceInputController.start();
    }

    this.notifyModeChange();
  }

  /**
   * Start voice input (either mode)
   */
  async start() {
    console.log('[DeepGram Bridge] Starting voice input in', this.mode, 'mode');

    if (this.mode === 'deepgram' && this.deepgramAgent) {
      return await this.deepgramAgent.enable();
    } else if (this.voiceInputController) {
      return this.voiceInputController.start();
    }

    return false;
  }

  /**
   * Stop voice input (either mode)
   */
  async stop() {
    console.log('[DeepGram Bridge] Stopping voice input');

    if (this.mode === 'deepgram' && this.deepgramAgent) {
      return await this.deepgramAgent.disable();
    } else if (this.voiceInputController) {
      return this.voiceInputController.stop();
    }

    return false;
  }

  /**
   * Send text (for testing or manual input)
   */
  async sendText(text) {
    console.log('[DeepGram Bridge] Sending text:', text);

    if (this.mode === 'deepgram' && this.deepgramAgent) {
      try {
        await eel.send_text_to_deepgram(text)();
        return true;
      } catch (error) {
        console.error('[DeepGram Bridge] Failed to send text:', error);
        return false;
      }
    } else {
      // For browser mode, trigger command processing
      if (this.voiceInputController) {
        this.voiceInputController.processTranscript(text);
        return true;
      }
    }

    return false;
  }

  /**
   * Get current mode
   */
  getMode() {
    return this.mode;
  }

  /**
   * Check if DeepGram is available
   */
  isDeepGramAvailable() {
    return this.deepgramAgent?.getStatus().available || false;
  }

  /**
   * Get status
   */
  getStatus() {
    return {
      mode: this.mode,
      deepgramAvailable: this.isDeepGramAvailable(),
      deepgramEnabled: this.mode === 'deepgram' && this.deepgramAgent?.getStatus().enabled,
      browserActive: this.mode === 'browser' && this.voiceInputController?.isMicrophoneActive()
    };
  }
}

// Export
window.DeepGramVoiceIntegrationBridge = DeepGramVoiceIntegrationBridge;

// Initialize bridge on page load
let voiceBridge = null;

document.addEventListener('DOMContentLoaded', async () => {
  console.log('[DeepGram Bridge] Page loaded, initializing...');
  
  // Wait for voice input controller if it exists
  if (window.voiceInputController) {
    voiceBridge = new DeepGramVoiceIntegrationBridge(window.voiceInputController);
  } else {
    voiceBridge = new DeepGramVoiceIntegrationBridge();
  }

  // Initialize
  await voiceBridge.init({
    preferDeepGram: true,
    autoEnableDeepGram: false,
    showDeepGramUI: true,
    onResponse: (text) => {
      console.log('[Voice Bridge] Response:', text);
      
      // Update agent line if on onboarding page
      const agentLine = document.getElementById('agent-line');
      if (agentLine) {
        agentLine.textContent = text;
      }
    },
    onModeChange: (mode) => {
      console.log('[Voice Bridge] Mode changed to:', mode);
    },
    onError: (error) => {
      console.error('[Voice Bridge] Error:', error);
    }
  });

  // Make globally available
  window.voiceBridge = voiceBridge;
  
  console.log('[DeepGram Bridge] Ready in', voiceBridge.getMode(), 'mode');
});

// Add helper function for toggling modes
window.toggleVoiceMode = async function() {
  if (!window.voiceBridge) {
    console.warn('Voice bridge not initialized');
    return;
  }

  const currentMode = window.voiceBridge.getMode();
  const newMode = currentMode === 'deepgram' ? 'browser' : 'deepgram';
  
  await window.voiceBridge.switchMode(newMode);
  
  console.log('Switched to', newMode, 'mode');
  return newMode;
};
