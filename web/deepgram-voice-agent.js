/**
 * DeepGram Voice Agent Integration for PortAIOS Web Frontend
 * 
 * Provides UI controls and status indicators for the DeepGram unified voice agent.
 * Integrates with existing voice-input.js and avatar systems.
 */

class DeepGramVoiceAgent {
  constructor(options = {}) {
    this.options = {
      autoEnable: options.autoEnable ?? false,
      showUI: options.showUI ?? true,
      container: options.container || document.body,
      onStatusChange: options.onStatusChange || null,
      onResponse: options.onResponse || null,
      onError: options.onError || null,
      ...options
    };

    this.status = {
      available: false,
      enabled: false,
      fallback_mode: false,
      agent_running: false
    };

    this.ui = null;
    this.statusCheckInterval = null;
    this.initialized = false;
  }

  /**
   * Initialize the DeepGram voice agent
   */
  async init() {
    if (this.initialized) {
      console.warn('[DeepGram] Already initialized');
      return;
    }

    console.log('[DeepGram] Initializing voice agent...');

    // Check if Eel is available
    if (typeof eel === 'undefined') {
      console.error('[DeepGram] Eel not available');
      return false;
    }

    // Check DeepGram availability
    try {
      this.status = await eel.get_deepgram_status()();
      console.log('[DeepGram] Status:', this.status);
    } catch (error) {
      console.error('[DeepGram] Failed to get status:', error);
      this.status.available = false;
    }

    // Create UI if requested
    if (this.options.showUI) {
      this.createUI();
    }

    // Start status monitoring
    this.startStatusMonitoring();

    // Auto-enable if configured
    if (this.options.autoEnable && this.status.available) {
      await this.enable();
    }

    this.initialized = true;
    console.log('[DeepGram] Initialization complete');
    return true;
  }

  /**
   * Create the DeepGram UI panel
   */
  createUI() {
    // Check if UI already exists
    if (this.ui) {
      console.warn('[DeepGram] UI already created');
      return;
    }

    const panel = document.createElement('div');
    panel.id = 'deepgram-voice-panel';
    panel.className = 'holo-card glow-edge panel-box deepgram-panel';
    panel.innerHTML = `
      <div class="panel-corners">
        <span></span><span></span><span></span><span></span>
      </div>
      <div class="deepgram-header">
        <div class="deepgram-title">
          <span class="deepgram-icon">🎤</span>
          <span class="deepgram-label">DeepGram Voice Agent</span>
        </div>
        <div class="deepgram-status-badge" id="deepgram-status-badge">
          <span class="status-dot"></span>
          <span class="status-text">Checking...</span>
        </div>
      </div>
      
      <div class="deepgram-body">
        <div class="deepgram-info" id="deepgram-info">
          <div class="info-line">
            <span class="info-key">Status:</span>
            <span class="info-value" id="dg-status-text">Initializing...</span>
          </div>
          <div class="info-line">
            <span class="info-key">Mode:</span>
            <span class="info-value" id="dg-mode-text">-</span>
          </div>
          <div class="info-line">
            <span class="info-key">Agent:</span>
            <span class="info-value" id="dg-agent-text">-</span>
          </div>
        </div>

        <div class="deepgram-controls">
          <button id="dg-enable-btn" class="dg-btn dg-btn-primary" disabled>
            <span class="btn-icon">▶️</span>
            <span class="btn-text">Enable Agent</span>
          </button>
          <button id="dg-disable-btn" class="dg-btn dg-btn-secondary" style="display: none;">
            <span class="btn-icon">⏸️</span>
            <span class="btn-text">Disable Agent</span>
          </button>
          <button id="dg-test-btn" class="dg-btn dg-btn-outline">
            <span class="btn-icon">💬</span>
            <span class="btn-text">Test</span>
          </button>
        </div>

        <div class="deepgram-activity" id="deepgram-activity" style="display: none;">
          <div class="activity-indicator">
            <div class="activity-bars">
              <span></span><span></span><span></span><span></span><span></span>
            </div>
            <span class="activity-text" id="dg-activity-text">Listening...</span>
          </div>
        </div>

        <div class="deepgram-fallback-notice" id="deepgram-fallback-notice" style="display: none;">
          <span class="notice-icon">⚠️</span>
          <span class="notice-text">Using fallback TTS/STT (DeepGram unavailable)</span>
        </div>
      </div>
    `;

    // Add to container
    this.options.container.appendChild(panel);
    this.ui = panel;

    // Add styles
    this.injectStyles();

    // Setup event listeners
    this.setupUIEventListeners();

    // Update UI based on status
    this.updateUI();
  }

  /**
   * Inject CSS styles for DeepGram panel
   */
  injectStyles() {
    if (document.getElementById('deepgram-styles')) return;

    const style = document.createElement('style');
    style.id = 'deepgram-styles';
    style.textContent = `
      .deepgram-panel {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 350px;
        background: rgba(10, 15, 25, 0.95);
        border: 1px solid rgba(0, 200, 255, 0.3);
        border-radius: 8px;
        padding: 20px;
        z-index: 9999;
        font-family: 'Courier New', monospace;
        box-shadow: 0 8px 32px rgba(0, 200, 255, 0.2);
        backdrop-filter: blur(10px);
      }

      .deepgram-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(0, 200, 255, 0.2);
      }

      .deepgram-title {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .deepgram-icon {
        font-size: 20px;
      }

      .deepgram-label {
        color: #00c8ff;
        font-weight: bold;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
      }

      .deepgram-status-badge {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        background: rgba(0, 200, 255, 0.1);
        border: 1px solid rgba(0, 200, 255, 0.3);
        border-radius: 12px;
        font-size: 11px;
      }

      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #666;
      }

      .status-dot.active {
        background: #00ff88;
        box-shadow: 0 0 8px #00ff88;
        animation: pulse-dot 2s infinite;
      }

      .status-dot.error {
        background: #ff4444;
      }

      .status-text {
        color: #aaa;
        font-size: 11px;
      }

      @keyframes pulse-dot {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
      }

      .deepgram-info {
        margin-bottom: 16px;
      }

      .info-line {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        font-size: 12px;
        border-bottom: 1px solid rgba(0, 200, 255, 0.1);
      }

      .info-key {
        color: #00c8ff;
        font-weight: bold;
      }

      .info-value {
        color: #fff;
      }

      .deepgram-controls {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
      }

      .dg-btn {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 10px 12px;
        border: none;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.2s;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .dg-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .dg-btn-primary {
        background: linear-gradient(135deg, #00c8ff, #0088ff);
        color: white;
      }

      .dg-btn-primary:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 200, 255, 0.4);
      }

      .dg-btn-secondary {
        background: rgba(255, 100, 100, 0.8);
        color: white;
      }

      .dg-btn-secondary:hover:not(:disabled) {
        background: rgba(255, 100, 100, 1);
        transform: translateY(-2px);
      }

      .dg-btn-outline {
        background: transparent;
        border: 1px solid rgba(0, 200, 255, 0.5);
        color: #00c8ff;
      }

      .dg-btn-outline:hover:not(:disabled) {
        background: rgba(0, 200, 255, 0.1);
        border-color: #00c8ff;
      }

      .btn-icon {
        font-size: 14px;
      }

      .deepgram-activity {
        padding: 12px;
        background: rgba(0, 200, 255, 0.05);
        border: 1px solid rgba(0, 200, 255, 0.2);
        border-radius: 4px;
        margin-bottom: 12px;
      }

      .activity-indicator {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .activity-bars {
        display: flex;
        gap: 3px;
        align-items: flex-end;
        height: 20px;
      }

      .activity-bars span {
        width: 4px;
        background: #00c8ff;
        border-radius: 2px;
        animation: audio-bar 1s ease-in-out infinite;
      }

      .activity-bars span:nth-child(1) { animation-delay: 0s; height: 40%; }
      .activity-bars span:nth-child(2) { animation-delay: 0.1s; height: 60%; }
      .activity-bars span:nth-child(3) { animation-delay: 0.2s; height: 80%; }
      .activity-bars span:nth-child(4) { animation-delay: 0.3s; height: 60%; }
      .activity-bars span:nth-child(5) { animation-delay: 0.4s; height: 40%; }

      @keyframes audio-bar {
        0%, 100% { height: 40%; opacity: 0.5; }
        50% { height: 100%; opacity: 1; }
      }

      .activity-text {
        color: #00c8ff;
        font-size: 12px;
        font-weight: bold;
      }

      .deepgram-fallback-notice {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px;
        background: rgba(255, 170, 0, 0.1);
        border: 1px solid rgba(255, 170, 0, 0.3);
        border-radius: 4px;
        font-size: 11px;
        color: #ffaa00;
      }

      .notice-icon {
        font-size: 16px;
      }
    `;

    document.head.appendChild(style);
  }

  /**
   * Setup UI event listeners
   */
  setupUIEventListeners() {
    const enableBtn = document.getElementById('dg-enable-btn');
    const disableBtn = document.getElementById('dg-disable-btn');
    const testBtn = document.getElementById('dg-test-btn');

    if (enableBtn) {
      enableBtn.addEventListener('click', () => this.enable());
    }

    if (disableBtn) {
      disableBtn.addEventListener('click', () => this.disable());
    }

    if (testBtn) {
      testBtn.addEventListener('click', () => this.testAgent());
    }
  }

  /**
   * Update UI based on current status
   */
  updateUI() {
    if (!this.ui) return;

    const statusBadge = document.getElementById('deepgram-status-badge');
    const statusText = document.getElementById('dg-status-text');
    const modeText = document.getElementById('dg-mode-text');
    const agentText = document.getElementById('dg-agent-text');
    const enableBtn = document.getElementById('dg-enable-btn');
    const disableBtn = document.getElementById('dg-disable-btn');
    const activity = document.getElementById('deepgram-activity');
    const fallbackNotice = document.getElementById('deepgram-fallback-notice');

    // Update status badge
    const statusDot = statusBadge?.querySelector('.status-dot');
    const statusLabel = statusBadge?.querySelector('.status-text');
    
    if (this.status.enabled && this.status.agent_running) {
      statusDot?.classList.add('active');
      statusLabel.textContent = 'Active';
      statusText.textContent = 'Running';
      if (activity) activity.style.display = 'block';
    } else if (this.status.available) {
      statusDot?.classList.remove('active', 'error');
      statusLabel.textContent = 'Ready';
      statusText.textContent = 'Available';
      if (activity) activity.style.display = 'none';
    } else {
      statusDot?.classList.add('error');
      statusLabel.textContent = 'Unavailable';
      statusText.textContent = 'Not configured';
      if (activity) activity.style.display = 'none';
    }

    // Update mode
    if (modeText) {
      if (this.status.fallback_mode) {
        modeText.textContent = 'Fallback (Local TTS/STT)';
        if (fallbackNotice) fallbackNotice.style.display = 'flex';
      } else if (this.status.enabled) {
        modeText.textContent = 'DeepGram Unified Agent';
        if (fallbackNotice) fallbackNotice.style.display = 'none';
      } else {
        modeText.textContent = 'Disabled';
        if (fallbackNotice) fallbackNotice.style.display = 'none';
      }
    }

    // Update agent status
    if (agentText) {
      agentText.textContent = this.status.agent_running ? 'Listening' : 'Stopped';
    }

    // Update buttons
    if (enableBtn && disableBtn) {
      if (this.status.available) {
        enableBtn.disabled = false;
        
        if (this.status.enabled) {
          enableBtn.style.display = 'none';
          disableBtn.style.display = 'flex';
        } else {
          enableBtn.style.display = 'flex';
          disableBtn.style.display = 'none';
        }
      } else {
        enableBtn.disabled = true;
        enableBtn.style.display = 'flex';
        disableBtn.style.display = 'none';
      }
    }

    // Trigger callback
    if (this.options.onStatusChange) {
      this.options.onStatusChange(this.status);
    }
  }

  /**
   * Start monitoring status
   */
  startStatusMonitoring() {
    if (this.statusCheckInterval) return;

    this.statusCheckInterval = setInterval(async () => {
      try {
        const newStatus = await eel.get_deepgram_status()();
        this.status = newStatus;
        this.updateUI();
      } catch (error) {
        console.error('[DeepGram] Status check failed:', error);
      }
    }, 2000); // Check every 2 seconds
  }

  /**
   * Stop monitoring status
   */
  stopStatusMonitoring() {
    if (this.statusCheckInterval) {
      clearInterval(this.statusCheckInterval);
      this.statusCheckInterval = null;
    }
  }

  /**
   * Enable the DeepGram voice agent
   */
  async enable() {
    console.log('[DeepGram] Enabling voice agent...');
    
    try {
      this.status = await eel.enable_deepgram_voice()();
      console.log('[DeepGram] Enabled:', this.status);
      this.updateUI();
      return this.status.enabled;
    } catch (error) {
      console.error('[DeepGram] Enable failed:', error);
      if (this.options.onError) {
        this.options.onError(error);
      }
      return false;
    }
  }

  /**
   * Disable the DeepGram voice agent
   */
  async disable() {
    console.log('[DeepGram] Disabling voice agent...');
    
    try {
      this.status = await eel.disable_deepgram_voice()();
      console.log('[DeepGram] Disabled:', this.status);
      this.updateUI();
      return !this.status.enabled;
    } catch (error) {
      console.error('[DeepGram] Disable failed:', error);
      if (this.options.onError) {
        this.options.onError(error);
      }
      return false;
    }
  }

  /**
   * Test the agent with a sample message
   */
  async testAgent() {
    console.log('[DeepGram] Testing agent...');
    
    if (!this.status.enabled) {
      alert('Please enable the DeepGram agent first.');
      return;
    }

    const testMessage = prompt('Enter a test message:', 'Hello, how are you?');
    if (!testMessage) return;

    try {
      await eel.send_text_to_deepgram(testMessage)();
      console.log('[DeepGram] Test message sent');
      
      if (this.options.onResponse) {
        this.options.onResponse(testMessage);
      }
    } catch (error) {
      console.error('[DeepGram] Test failed:', error);
      if (this.options.onError) {
        this.options.onError(error);
      }
    }
  }

  /**
   * Destroy the voice agent UI and cleanup
   */
  destroy() {
    this.stopStatusMonitoring();
    
    if (this.ui) {
      this.ui.remove();
      this.ui = null;
    }

    this.initialized = false;
  }

  /**
   * Get current status
   */
  getStatus() {
    return { ...this.status };
  }
}

// Export for use in other modules
window.DeepGramVoiceAgent = DeepGramVoiceAgent;

// Auto-initialize if on main page
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => initDeepGramIfNeeded());
} else {
  initDeepGramIfNeeded();
}

function initDeepGramIfNeeded() {
  // Only auto-init on main index page, not onboarding
  const isMainPage = !window.location.pathname.includes('onboarding');
  
  if (isMainPage && typeof eel !== 'undefined') {
    console.log('[DeepGram] Auto-initializing on main page');
    window.deepgramAgent = new DeepGramVoiceAgent({
      autoEnable: false, // Don't auto-enable, let user control
      showUI: true
    });
    window.deepgramAgent.init();
  }
}
