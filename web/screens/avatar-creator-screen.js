/**
 * Avatar Creator Pro - Screen component for creating custom avatars
 * Extracted from avatar-creator-pro.html and converted to screen module
 */

export function createAvatarCreatorScreen() {
  const content = document.createElement('div');
  content.className = 'avatar-creator-container';
  
  content.innerHTML = `
    <style>
      .avatar-creator-container {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 20px;
        height: 100%;
        max-height: calc(90vh - 140px);
      }
      
      .creator-panel {
        background: rgba(0, 255, 255, 0.05);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 8px;
        padding: 16px;
        display: flex;
        flex-direction: column;
        overflow-y: auto;
      }
      
      .panel-header {
        font-size: 16px;
        font-weight: 700;
        color: #0ff;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(0, 255, 255, 0.3);
        text-transform: uppercase;
        letter-spacing: 1px;
      }
      
      .control-group {
        margin-bottom: 16px;
      }
      
      .control-label {
        display: block;
        font-size: 12px;
        color: #0ff;
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      
      .control-input {
        width: 100%;
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(0, 255, 255, 0.4);
        color: #0ff;
        padding: 8px 12px;
        border-radius: 4px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 13px;
        transition: all 0.3s ease;
      }
      
      .control-input:focus {
        outline: none;
        border-color: #0ff;
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
      }
      
      .control-select {
        width: 100%;
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(0, 255, 255, 0.4);
        color: #0ff;
        padding: 8px 12px;
        border-radius: 4px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 13px;
        cursor: pointer;
      }
      
      .control-range {
        width: 100%;
        -webkit-appearance: none;
        background: rgba(0, 255, 255, 0.2);
        height: 4px;
        border-radius: 2px;
        outline: none;
      }
      
      .control-range::-webkit-slider-thumb {
        -webkit-appearance: none;
        width: 16px;
        height: 16px;
        background: #0ff;
        border-radius: 50%;
        cursor: pointer;
        box-shadow: 0 0 8px rgba(0, 255, 255, 0.6);
      }
      
      .range-value {
        display: inline-block;
        color: #0ff;
        font-size: 12px;
        margin-left: 8px;
      }
      
      .color-preview {
        width: 100%;
        height: 40px;
        border: 1px solid rgba(0, 255, 255, 0.4);
        border-radius: 4px;
        margin-top: 6px;
        cursor: pointer;
        transition: all 0.3s ease;
      }
      
      .color-preview:hover {
        border-color: #0ff;
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
      }
      
      .avatar-preview {
        background: rgba(0, 0, 0, 0.3);
        border: 2px solid rgba(0, 255, 255, 0.3);
        border-radius: 8px;
        height: 400px;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        overflow: hidden;
      }
      
      #preview-canvas {
        width: 100%;
        height: 100%;
      }
      
      .action-buttons {
        display: flex;
        gap: 12px;
        margin-top: 16px;
      }
      
      .btn-creator {
        flex: 1;
        background: rgba(0, 255, 255, 0.1);
        border: 1px solid #0ff;
        color: #0ff;
        padding: 12px 20px;
        border-radius: 6px;
        font-family: 'Orbitron', monospace;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
      }
      
      .btn-creator:hover {
        background: rgba(0, 255, 255, 0.2);
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.4);
      }
      
      .btn-creator.primary {
        background: rgba(0, 255, 255, 0.3);
      }
      
      .btn-creator.primary:hover {
        background: rgba(0, 255, 255, 0.4);
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.6);
      }
      
      .preset-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-top: 8px;
      }
      
      .preset-btn {
        background: rgba(0, 255, 255, 0.1);
        border: 1px solid rgba(0, 255, 255, 0.3);
        color: #0ff;
        padding: 8px;
        border-radius: 4px;
        font-size: 11px;
        cursor: pointer;
        transition: all 0.3s ease;
      }
      
      .preset-btn:hover {
        background: rgba(0, 255, 255, 0.2);
        border-color: #0ff;
      }
      
      @media (max-width: 1024px) {
        .avatar-creator-container {
          grid-template-columns: 1fr;
        }
        
        .avatar-preview {
          height: 300px;
        }
      }
    </style>
    
    <!-- Left Panel: Basic Settings -->
    <div class="creator-panel">
      <div class="panel-header">📝 Basic Settings</div>
      
      <div class="control-group">
        <label class="control-label">Avatar Name</label>
        <input type="text" class="control-input" id="avatar-name" placeholder="My Avatar" value="Custom Avatar">
      </div>
      
      <div class="control-group">
        <label class="control-label">Avatar Type</label>
        <select class="control-select" id="avatar-type">
          <option value="binary">Binary Particle</option>
          <option value="holographic">Holographic</option>
          <option value="realistic">Realistic 3D</option>
          <option value="geometric">Geometric</option>
        </select>
      </div>
      
      <div class="control-group">
        <label class="control-label">Size <span class="range-value" id="size-value">1.0</span></label>
        <input type="range" class="control-range" id="avatar-size" min="0.5" max="2.0" step="0.1" value="1.0">
      </div>
      
      <div class="control-group">
        <label class="control-label">Primary Color</label>
        <input type="color" class="control-input" id="primary-color" value="#00ffff">
        <div class="color-preview" id="primary-preview" style="background: #00ffff;"></div>
      </div>
      
      <div class="control-group">
        <label class="control-label">Secondary Color</label>
        <input type="color" class="control-input" id="secondary-color" value="#ff00ff">
        <div class="color-preview" id="secondary-preview" style="background: #ff00ff;"></div>
      </div>
      
      <div class="control-group">
        <label class="control-label">Animation Style</label>
        <select class="control-select" id="animation-style">
          <option value="idle">Idle</option>
          <option value="thinking">Thinking</option>
          <option value="speaking">Speaking</option>
          <option value="listening">Listening</option>
          <option value="processing">Processing</option>
        </select>
      </div>
      
      <div class="panel-header" style="margin-top: 20px;">🎨 Quick Presets</div>
      <div class="preset-grid">
        <button class="preset-btn" onclick="window.applyPreset('cyber')">Cyber</button>
        <button class="preset-btn" onclick="window.applyPreset('matrix')">Matrix</button>
        <button class="preset-btn" onclick="window.applyPreset('neon')">Neon</button>
        <button class="preset-btn" onclick="window.applyPreset('ghost')">Ghost</button>
        <button class="preset-btn" onclick="window.applyPreset('fire')">Fire</button>
        <button class="preset-btn" onclick="window.applyPreset('ice')">Ice</button>
      </div>
    </div>
    
    <!-- Middle Panel: Preview -->
    <div class="creator-panel">
      <div class="panel-header">👁️ Live Preview</div>
      <div class="avatar-preview">
        <canvas id="preview-canvas"></canvas>
      </div>
      
      <div class="action-buttons">
        <button class="btn-creator" id="refresh-preview">🔄 Refresh</button>
        <button class="btn-creator" id="randomize">🎲 Randomize</button>
      </div>
    </div>
    
    <!-- Right Panel: Advanced Settings -->
    <div class="creator-panel">
      <div class="panel-header">⚙️ Advanced Settings</div>
      
      <div class="control-group">
        <label class="control-label">Particle Count <span class="range-value" id="particles-value">2000</span></label>
        <input type="range" class="control-range" id="particle-count" min="500" max="5000" step="100" value="2000">
      </div>
      
      <div class="control-group">
        <label class="control-label">Glow Intensity <span class="range-value" id="glow-value">0.5</span></label>
        <input type="range" class="control-range" id="glow-intensity" min="0" max="1" step="0.1" value="0.5">
      </div>
      
      <div class="control-group">
        <label class="control-label">Rotation Speed <span class="range-value" id="rotation-value">1.0</span></label>
        <input type="range" class="control-range" id="rotation-speed" min="0" max="3" step="0.1" value="1.0">
      </div>
      
      <div class="control-group">
        <label class="control-label">Complexity <span class="range-value" id="complexity-value">3</span></label>
        <input type="range" class="control-range" id="complexity" min="1" max="5" step="1" value="3">
      </div>
      
      <div class="control-group">
        <label class="control-label">Enable Physics</label>
        <select class="control-select" id="enable-physics">
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      </div>
      
      <div class="control-group">
        <label class="control-label">Voice Reactivity <span class="range-value" id="voice-value">0.7</span></label>
        <input type="range" class="control-range" id="voice-reactivity" min="0" max="1" step="0.1" value="0.7">
      </div>
      
      <div class="action-buttons" style="margin-top: auto;">
        <button class="btn-creator" id="export-avatar">💾 Export</button>
        <button class="btn-creator primary" id="save-avatar">✓ Save & Apply</button>
      </div>
    </div>
  `;
  
  return content;
}

/**
 * Initialize avatar creator functionality
 */
export function initAvatarCreator() {
  // Update range value displays
  const ranges = document.querySelectorAll('.control-range');
  ranges.forEach(range => {
    const valueId = range.id + '-value';
    const valueEl = document.getElementById(valueId);
    if (valueEl) {
      range.addEventListener('input', (e) => {
        valueEl.textContent = e.target.value;
        updatePreview();
      });
    }
  });
  
  // Color preview sync
  ['primary', 'secondary'].forEach(type => {
    const colorInput = document.getElementById(`${type}-color`);
    const preview = document.getElementById(`${type}-preview`);
    if (colorInput && preview) {
      colorInput.addEventListener('input', (e) => {
        preview.style.background = e.target.value;
        updatePreview();
      });
    }
  });
  
  // All other controls trigger preview update
  document.querySelectorAll('.control-input, .control-select').forEach(el => {
    el.addEventListener('change', updatePreview);
  });
  
  // Button handlers
  const refreshBtn = document.getElementById('refresh-preview');
  if (refreshBtn) refreshBtn.addEventListener('click', updatePreview);
  
  const randomizeBtn = document.getElementById('randomize');
  if (randomizeBtn) randomizeBtn.addEventListener('click', randomizeAvatar);
  
  const exportBtn = document.getElementById('export-avatar');
  if (exportBtn) exportBtn.addEventListener('click', exportAvatar);
  
  const saveBtn = document.getElementById('save-avatar');
  if (saveBtn) saveBtn.addEventListener('click', saveAndApplyAvatar);
  
  // Initial preview
  updatePreview();
}

function updatePreview() {
  const canvas = document.getElementById('preview-canvas');
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  canvas.width = canvas.offsetWidth;
  canvas.height = canvas.offsetHeight;
  
  const config = getAvatarConfig();
  
  // Simple preview rendering
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2;
  const radius = Math.min(canvas.width, canvas.height) * 0.3 * config.size;
  
  // Draw gradient circle as placeholder
  const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
  gradient.addColorStop(0, config.primaryColor);
  gradient.addColorStop(1, config.secondaryColor);
  
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.fill();
  
  // Add glow effect
  ctx.shadowBlur = config.glowIntensity * 30;
  ctx.shadowColor = config.primaryColor;
  ctx.strokeStyle = config.primaryColor;
  ctx.lineWidth = 2;
  ctx.stroke();
}

function getAvatarConfig() {
  return {
    name: document.getElementById('avatar-name')?.value || 'Custom Avatar',
    type: document.getElementById('avatar-type')?.value || 'binary',
    size: parseFloat(document.getElementById('avatar-size')?.value || 1.0),
    primaryColor: document.getElementById('primary-color')?.value || '#00ffff',
    secondaryColor: document.getElementById('secondary-color')?.value || '#ff00ff',
    animationStyle: document.getElementById('animation-style')?.value || 'idle',
    particleCount: parseInt(document.getElementById('particle-count')?.value || 2000),
    glowIntensity: parseFloat(document.getElementById('glow-intensity')?.value || 0.5),
    rotationSpeed: parseFloat(document.getElementById('rotation-speed')?.value || 1.0),
    complexity: parseInt(document.getElementById('complexity')?.value || 3),
    enablePhysics: document.getElementById('enable-physics')?.value === 'true',
    voiceReactivity: parseFloat(document.getElementById('voice-reactivity')?.value || 0.7)
  };
}

function randomizeAvatar() {
  const randomColor = () => '#' + Math.floor(Math.random()*16777215).toString(16);
  
  document.getElementById('primary-color').value = randomColor();
  document.getElementById('secondary-color').value = randomColor();
  document.getElementById('avatar-size').value = (Math.random() * 1.5 + 0.5).toFixed(1);
  document.getElementById('particle-count').value = Math.floor(Math.random() * 4500 + 500);
  document.getElementById('glow-intensity').value = Math.random().toFixed(1);
  document.getElementById('rotation-speed').value = (Math.random() * 3).toFixed(1);
  document.getElementById('complexity').value = Math.floor(Math.random() * 5 + 1);
  
  // Trigger change events
  document.querySelectorAll('.control-range').forEach(el => {
    el.dispatchEvent(new Event('input'));
  });
  
  updatePreview();
  window.toast?.('Avatar randomized!');
}

function exportAvatar() {
  const config = getAvatarConfig();
  const json = JSON.stringify(config, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${config.name.replace(/\s+/g, '_')}.json`;
  a.click();
  URL.revokeObjectURL(url);
  window.toast?.('Avatar exported!');
}

async function saveAndApplyAvatar() {
  const config = getAvatarConfig();
  
  // Save to backend if available
  if (typeof eel !== 'undefined') {
    try {
      await eel.save_avatar_config(config)();
      window.toast?.('Avatar saved and applied!');
    } catch (err) {
      console.error('Failed to save avatar:', err);
      window.toast?.('Failed to save avatar');
    }
  }
  
  // Store in localStorage
  localStorage.setItem('aios_avatar_config', JSON.stringify(config));
  
  // Dispatch event for live update
  window.dispatchEvent(new CustomEvent('aios:avatarUpdate', { detail: config }));
  
  // Close the screen
  window.screenManager?.closeScreen('avatar-creator');
}

// Preset configurations
window.applyPreset = function(preset) {
  const presets = {
    cyber: { primary: '#00ffff', secondary: '#0099ff', particles: 3000, glow: 0.7 },
    matrix: { primary: '#00ff00', secondary: '#00cc00', particles: 4000, glow: 0.5 },
    neon: { primary: '#ff00ff', secondary: '#ff0099', particles: 2500, glow: 0.9 },
    ghost: { primary: '#ffffff', secondary: '#ccccff', particles: 1500, glow: 0.3 },
    fire: { primary: '#ff6600', secondary: '#ff0000', particles: 3500, glow: 0.8 },
    ice: { primary: '#00ccff', secondary: '#ffffff', particles: 2000, glow: 0.6 }
  };
  
  const config = presets[preset];
  if (config) {
    document.getElementById('primary-color').value = config.primary;
    document.getElementById('secondary-color').value = config.secondary;
    document.getElementById('particle-count').value = config.particles;
    document.getElementById('glow-intensity').value = config.glow;
    
    document.querySelectorAll('.control-range, .control-input').forEach(el => {
      el.dispatchEvent(new Event('input'));
      el.dispatchEvent(new Event('change'));
    });
    
    window.toast?.(`Applied ${preset} preset!`);
  }
};
