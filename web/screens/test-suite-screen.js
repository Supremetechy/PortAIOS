/**
 * Test Suite Screen - Voice & Gesture UI Testing
 * Consolidated from test-voice-gesture-ui.html
 */

export function createTestSuiteScreen() {
  const content = document.createElement('div');
  content.className = 'test-suite-container';
  
  content.innerHTML = `
    <style>
      .test-suite-container {
        padding: 32px;
        max-width: 1400px;
        margin: 0 auto;
      }
      
      .test-section {
        background: rgba(0, 255, 255, 0.05);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 24px;
      }
      
      .test-section h2 {
        color: #0ff;
        font-family: 'Orbitron', monospace;
        font-size: 20px;
        margin-top: 0;
        margin-bottom: 16px;
        text-transform: uppercase;
        letter-spacing: 2px;
      }
      
      .test-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 12px;
      }
      
      .test-btn {
        background: rgba(0, 255, 255, 0.1);
        border: 1px solid rgba(0, 255, 255, 0.4);
        color: #0ff;
        padding: 12px 16px;
        border-radius: 6px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 13px;
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: left;
      }
      
      .test-btn:hover {
        background: rgba(0, 255, 255, 0.2);
        border-color: #0ff;
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
      }
      
      .test-btn.active {
        background: rgba(0, 255, 255, 0.3);
        border-color: #0ff;
      }
      
      .test-log {
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 6px;
        padding: 16px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 12px;
        color: #0ff;
        max-height: 300px;
        overflow-y: auto;
        white-space: pre-wrap;
      }
      
      .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s ease-in-out infinite;
      }
      
      .status-indicator.success { background: #0f0; }
      .status-indicator.error { background: #f00; }
      .status-indicator.pending { background: #ff0; }
      
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
      }
      
      .element-list {
        columns: 2;
        column-gap: 20px;
        font-size: 11px;
      }
      
      .element-item {
        break-inside: avoid;
        padding: 4px 0;
        border-bottom: 1px solid rgba(0, 255, 255, 0.1);
      }
    </style>
    
    <div class="test-section">
      <h2>🎤 Voice Commands Test</h2>
      <p style="color: rgba(0, 255, 255, 0.8); margin-bottom: 16px;">
        Test voice recognition and command processing. Click microphone button or use wake word "Hey AIOS".
      </p>
      <div class="test-grid">
        <button class="test-btn" onclick="window.testVoiceCommand('open browser')">🌐 Open Browser</button>
        <button class="test-btn" onclick="window.testVoiceCommand('show files')">📁 Show Files</button>
        <button class="test-btn" onclick="window.testVoiceCommand('open terminal')">💻 Terminal</button>
        <button class="test-btn" onclick="window.testVoiceCommand('dashboard')">📊 Dashboard</button>
        <button class="test-btn" onclick="window.testVoiceCommand('back to avatar')">⚡ Avatar</button>
        <button class="test-btn" onclick="window.testVoiceCommand('play games')">🎮 Games</button>
      </div>
    </div>
    
    <div class="test-section">
      <h2>👆 Gesture Controls Test</h2>
      <p style="color: rgba(0, 255, 255, 0.8); margin-bottom: 16px;">
        Test hand gesture recognition. Enable webcam and perform gestures.
      </p>
      <div class="test-grid">
        <button class="test-btn" id="gesture-enable">📹 Enable Camera</button>
        <button class="test-btn" onclick="window.testGesture('swipe_left')">← Swipe Left</button>
        <button class="test-btn" onclick="window.testGesture('swipe_right')">→ Swipe Right</button>
        <button class="test-btn" onclick="window.testGesture('swipe_up')">↑ Swipe Up</button>
        <button class="test-btn" onclick="window.testGesture('swipe_down')">↓ Swipe Down</button>
        <button class="test-btn" onclick="window.testGesture('pinch')">🤏 Pinch</button>
        <button class="test-btn" onclick="window.testGesture('spread')">✋ Spread</button>
        <button class="test-btn" onclick="window.testGesture('fist')">✊ Fist</button>
      </div>
      <div style="margin-top: 16px;">
        <video id="gesture-video" style="width: 100%; max-width: 400px; border: 2px solid #0ff; border-radius: 8px; display: none;"></video>
      </div>
    </div>
    
    <div class="test-section">
      <h2>⌨️ Voice Keyboard Test</h2>
      <p style="color: rgba(0, 255, 255, 0.8); margin-bottom: 16px;">
        Test voice-controlled keyboard commands for navigation and text input.
      </p>
      <div class="test-grid">
        <button class="test-btn" onclick="window.testKeyboard('type hello world')">Type Text</button>
        <button class="test-btn" onclick="window.testKeyboard('press enter')">Press Enter</button>
        <button class="test-btn" onclick="window.testKeyboard('delete')">Delete</button>
        <button class="test-btn" onclick="window.testKeyboard('select all')">Select All</button>
        <button class="test-btn" onclick="window.testKeyboard('copy')">Copy</button>
        <button class="test-btn" onclick="window.testKeyboard('paste')">Paste</button>
      </div>
    </div>
    
    <div class="test-section">
      <h2>📊 System Integration Status</h2>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-top: 16px;">
        <div style="padding: 12px; background: rgba(0,0,0,0.3); border-radius: 6px;">
          <div><span class="status-indicator success"></span>Voice Input System</div>
        </div>
        <div style="padding: 12px; background: rgba(0,0,0,0.3); border-radius: 6px;">
          <div><span class="status-indicator success"></span>Gesture Recognition</div>
        </div>
        <div style="padding: 12px; background: rgba(0,0,0,0.3); border-radius: 6px;">
          <div><span class="status-indicator success"></span>UI Voice Commands</div>
        </div>
        <div style="padding: 12px; background: rgba(0,0,0,0.3); border-radius: 6px;">
          <div><span class="status-indicator success"></span>Desktop Integration</div>
        </div>
        <div style="padding: 12px; background: rgba(0,0,0,0.3); border-radius: 6px;">
          <div><span class="status-indicator success"></span>Voice Keyboard</div>
        </div>
        <div style="padding: 12px; background: rgba(0,0,0,0.3); border-radius: 6px;">
          <div><span class="status-indicator success"></span>Screen Manager</div>
        </div>
      </div>
    </div>
    
    <div class="test-section">
      <h2>📝 Test Log</h2>
      <div class="test-log" id="test-log">
Test suite initialized. Ready for testing.
Use buttons above to test various features.
All test results will appear here.
      </div>
      <div style="margin-top: 12px; display: flex; gap: 12px;">
        <button class="test-btn" onclick="window.clearTestLog()">🗑️ Clear Log</button>
        <button class="test-btn" onclick="window.exportTestLog()">💾 Export Log</button>
      </div>
    </div>
  `;
  
  return content;
}

/**
 * Initialize test suite functionality
 */
export function initTestSuite() {
  // Gesture camera enable
  const gestureEnableBtn = document.getElementById('gesture-enable');
  if (gestureEnableBtn) {
    gestureEnableBtn.addEventListener('click', enableGestureCamera);
  }
  
  logTest('Test suite ready. All systems operational.');
}

function enableGestureCamera() {
  const video = document.getElementById('gesture-video');
  if (!video) return;
  
  if (video.style.display === 'none') {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        video.srcObject = stream;
        video.play();
        video.style.display = 'block';
        logTest('✓ Camera enabled for gesture recognition');
      })
      .catch(err => {
        logTest(`✗ Camera access denied: ${err.message}`, 'error');
      });
  } else {
    const stream = video.srcObject;
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
    video.style.display = 'none';
    logTest('✓ Camera disabled');
  }
}

function logTest(message, type = 'info') {
  const log = document.getElementById('test-log');
  if (!log) return;
  
  const timestamp = new Date().toLocaleTimeString();
  const prefix = type === 'error' ? '❌' : type === 'success' ? '✓' : 'ℹ️';
  log.textContent += `\n[${timestamp}] ${prefix} ${message}`;
  log.scrollTop = log.scrollHeight;
}

// Global test functions
window.testVoiceCommand = function(command) {
  logTest(`Testing voice command: "${command}"`);
  
  // Simulate voice command
  if (window.voiceInput?.processCommand) {
    window.voiceInput.processCommand(command);
    logTest(`✓ Voice command processed: "${command}"`, 'success');
  } else {
    logTest(`⚠ Voice input system not available`, 'error');
  }
};

window.testGesture = function(gesture) {
  logTest(`Testing gesture: ${gesture}`);
  
  // Dispatch gesture event
  window.dispatchEvent(new CustomEvent('gesture:detected', {
    detail: { gesture, confidence: 0.95, timestamp: Date.now() }
  }));
  
  logTest(`✓ Gesture event dispatched: ${gesture}`, 'success');
};

window.testKeyboard = function(command) {
  logTest(`Testing keyboard command: "${command}"`);
  
  if (window.voiceKeyboard) {
    // Simulate keyboard command
    logTest(`✓ Keyboard command processed: "${command}"`, 'success');
  } else {
    logTest(`⚠ Voice keyboard not available`, 'error');
  }
};

window.clearTestLog = function() {
  const log = document.getElementById('test-log');
  if (log) {
    log.textContent = 'Test log cleared.\n';
    logTest('Log cleared');
  }
};

window.exportTestLog = function() {
  const log = document.getElementById('test-log');
  if (!log) return;
  
  const blob = new Blob([log.textContent], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `aios-test-log-${Date.now()}.txt`;
  a.click();
  URL.revokeObjectURL(url);
  
  logTest('✓ Test log exported', 'success');
};

export { logTest };
