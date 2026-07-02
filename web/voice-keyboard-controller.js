/**
 * Voice-controlled keyboard, annotation, and dictation system for AIOS
 * Frontend controller that integrates with voice input and provides visual feedback
 */

class VoiceKeyboardController {
  constructor(voiceInput, options = {}) {
    this.voiceInput = voiceInput;
    this.options = {
      showVisualFeedback: true,
      enableAnnotations: true,
      enableDictation: true,
      annotationContainer: null,
      dictationDisplay: null,
      ...options
    };
    
    this.currentMode = 'keyboard';
    this.annotations = [];
    this.dictationBuffer = '';
    this.activeKeys = new Set();
    this.visualFeedbackTimeout = null;
    
    this.init();
  }
  
  init() {
    console.log('[VoiceKeyboard] Initializing voice keyboard controller');
    
    // Setup annotation UI if enabled
    if (this.options.enableAnnotations) {
      this.setupAnnotationUI();
    }
    
    // Setup dictation UI if enabled
    if (this.options.enableDictation) {
      this.setupDictationUI();
    }
    
    // Setup visual feedback overlay
    if (this.options.showVisualFeedback) {
      this.setupVisualFeedback();
    }
    
    // Setup mode indicator
    this.setupModeIndicator();
    
    console.log('[VoiceKeyboard] Initialization complete');
  }
  
  // ========== Command Processing ==========
  
  async processCommand(text) {
    console.log(`[VoiceKeyboard] Processing command: "${text}"`);
    
    try {
      // Check if eel is available
      if (typeof eel !== 'undefined' && eel.process_keyboard_voice_command) {
        const result = await eel.process_keyboard_voice_command(text)();
        
        if (result && result.success) {
          await this.executeAction(result);
          return result;
        } else {
          console.warn('[VoiceKeyboard] Command not recognized:', text);
          return null;
        }
      } else {
        // Fallback to client-side processing
        const result = this.processCommandLocal(text);
        
        if (result && result.success) {
          await this.executeAction(result);
          return result;
        }
        return null;
      }
    } catch (error) {
      console.error('[VoiceKeyboard] Error processing command:', error);
      return null;
    }
  }
  
  processCommandLocal(text) {
    /**
     * Client-side command processing fallback
     * Handles basic commands when backend is not available
     */
    const lower = text.toLowerCase().trim();
    
    // Mode switching
    if (lower.match(/^(?:enter|start|begin)\s+(keyboard|annotation|dictation)\s+mode$/)) {
      const mode = lower.match(/keyboard|annotation|dictation/)[0];
      return { action: 'mode_switch', new_mode: mode, success: true };
    }
    
    // Keyboard commands
    if (lower.startsWith('press ')) {
      return this.parseKeyPress(text);
    }
    
    if (lower.startsWith('type ')) {
      return {
        action: 'type_text',
        text: text.substring(5).trim(),
        success: true
      };
    }
    
    // Annotation commands
    if (lower.startsWith('annotate ')) {
      return {
        action: 'annotate',
        text: text.substring(9).trim(),
        timestamp: new Date().toISOString(),
        success: true
      };
    }
    
    if (lower === 'show annotations') {
      return { action: 'show_annotations', success: true };
    }
    
    if (lower.startsWith('highlight ')) {
      return {
        action: 'highlight_text',
        text: text.substring(10).trim(),
        success: true
      };
    }
    
    // Dictation commands
    if (lower === 'start dictation') {
      return { action: 'start_dictation', success: true };
    }
    
    if (lower === 'stop dictation') {
      return { 
        action: 'stop_dictation', 
        buffer: this.dictationBuffer,
        success: true 
      };
    }
    
    if (lower === 'insert dictation') {
      return {
        action: 'insert_dictation',
        text: this.dictationBuffer,
        success: true
      };
    }
    
    // If in dictation mode, treat as dictation input
    if (this.currentMode === 'dictation') {
      return {
        action: 'dictation_input',
        text: text,
        success: true
      };
    }
    
    return null;
  }
  
  parseKeyPress(text) {
    /**
     * Parse "press [modifier] plus [key]" commands
     */
    const pressMatch = text.match(/^press\s+(.+?)(?:\s+(\d+)\s+times?)?$/i);
    if (!pressMatch) return null;
    
    const keyPhrase = pressMatch[1].toLowerCase();
    const repeatCount = pressMatch[2] ? parseInt(pressMatch[2]) : 1;
    
    // Parse modifiers and key
    const parts = keyPhrase.split('plus').map(p => p.trim());
    const modifiers = [];
    let key = null;
    
    const modifierMap = {
      'control': 'Control', 'ctrl': 'Control',
      'shift': 'Shift',
      'alt': 'Alt', 'option': 'Alt',
      'windows': 'Meta', 'command': 'Meta', 'win': 'Meta'
    };
    
    const keyMap = {
      'enter': 'Enter', 'return': 'Enter',
      'escape': 'Escape', 'esc': 'Escape',
      'tab': 'Tab',
      'space': ' ', 'spacebar': ' ',
      'backspace': 'Backspace',
      'delete': 'Delete', 'del': 'Delete',
      'up': 'ArrowUp', 'down': 'ArrowDown',
      'left': 'ArrowLeft', 'right': 'ArrowRight',
      'home': 'Home', 'end': 'End',
      'page up': 'PageUp', 'page down': 'PageDown',
    };
    
    for (const part of parts) {
      if (modifierMap[part]) {
        modifiers.push(modifierMap[part]);
      } else if (keyMap[part]) {
        key = keyMap[part];
      } else if (part.length === 1) {
        key = part;
      } else {
        key = part;
      }
    }
    
    return {
      action: 'press_key',
      key: key,
      modifiers: modifiers,
      repeat: repeatCount,
      success: true,
      original: text
    };
  }
  
  // ========== Action Execution ==========
  
  async executeAction(result) {
    console.log('[VoiceKeyboard] Executing action:', result.action);
    
    switch (result.action) {
      case 'mode_switch':
      case 'mode_exit':
        this.switchMode(result.new_mode);
        this.showFeedback(`Switched to ${result.new_mode} mode`, 'mode');
        break;
        
      case 'press_key':
        await this.simulateKeyPress(result);
        this.showFeedback(this.formatKeyCombo(result), 'key');
        break;
        
      case 'type_text':
        await this.typeText(result.text);
        this.showFeedback(`Typed: "${result.text}"`, 'text');
        break;
        
      case 'hold_key':
        this.holdKey(result.key);
        this.showFeedback(`Holding: ${result.key}`, 'key');
        break;
        
      case 'release_key':
        this.releaseKey(result.key);
        this.showFeedback(`Released: ${result.key}`, 'key');
        break;
        
      case 'annotate':
      case 'add_annotation':
        this.addAnnotation(result.text, result.timestamp);
        this.showFeedback(`Annotation added`, 'annotation');
        break;
        
      case 'show_annotations':
        this.showAnnotations();
        break;
        
      case 'clear_annotations':
        this.clearAnnotations(result.target);
        this.showFeedback(`Annotations cleared`, 'annotation');
        break;
        
      case 'highlight_text':
        this.highlightText(result.text);
        this.showFeedback(`Highlighted: "${result.text}"`, 'highlight');
        break;
        
      case 'start_dictation':
        this.startDictation();
        this.showFeedback(`Dictation started`, 'dictation');
        break;
        
      case 'stop_dictation':
        this.stopDictation();
        this.showFeedback(`Dictation stopped (${result.buffer?.length || 0} chars)`, 'dictation');
        break;
        
      case 'clear_dictation':
        this.clearDictation();
        this.showFeedback(`Dictation buffer cleared`, 'dictation');
        break;
        
      case 'insert_dictation':
        await this.insertDictation(result.text);
        this.showFeedback(`Dictation inserted`, 'dictation');
        break;
        
      case 'dictation_input':
        this.appendDictation(result.text);
        this.updateDictationDisplay();
        break;
        
      case 'dictation_newline':
        this.appendDictation(result.type === 'paragraph' ? '\n\n' : '\n');
        this.updateDictationDisplay();
        break;
        
      case 'dictation_punctuation':
        // Punctuation is handled in backend, just update display
        this.updateDictationDisplay();
        break;
        
      case 'show_files':
        this.showFeedback('Opening file manager...', 'mode');
        break;

      case 'open_browser':
        this.showFeedback('Opening browser...', 'mode');
        break;

      case 'help':
        this.showHelp(result.commands, result.mode);
        break;

      default:
        console.warn('[VoiceKeyboard] Unknown action:', result.action);
    }
  }

  showHelp(commands, mode) {
    const existing = document.getElementById('voice-keyboard-help');
    if (existing) { existing.remove(); return; }

    const panel = document.createElement('div');
    panel.id = 'voice-keyboard-help';
    panel.style.cssText = `
      position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
      background: rgba(0,20,40,0.97); border: 1px solid #0ff; border-radius: 10px;
      padding: 20px; min-width: 320px; max-width: 480px; z-index: 100000;
      font-family: 'Share Tech Mono', monospace; font-size: 12px; color: #0ff;
      box-shadow: 0 0 30px rgba(0,255,255,0.4);
    `;
    panel.innerHTML = `
      <div style="display:flex;justify-content:space-between;margin-bottom:12px;border-bottom:1px solid #0ff;padding-bottom:8px;">
        <strong style="font-size:14px;">Voice Commands — ${(mode || 'keyboard').toUpperCase()}</strong>
        <button onclick="document.getElementById('voice-keyboard-help').remove()"
          style="background:none;border:1px solid #0ff;color:#0ff;padding:2px 10px;cursor:pointer;border-radius:4px;">✕</button>
      </div>
      ${(commands || []).map(c => `<div style="margin:4px 0;padding:4px 8px;background:rgba(0,255,255,0.07);border-radius:4px;">${this.escapeHtml(c)}</div>`).join('')}
      <div style="margin-top:10px;font-size:10px;color:#0aa;">Say "help" again to dismiss.</div>
    `;
    document.body.appendChild(panel);
    this.showFeedback('Showing help', 'mode');
  }
  
  // ========== Keyboard Simulation ==========
  
  async simulateKeyPress(result) {
    const { key, modifiers = [], repeat = 1 } = result;
    
    for (let i = 0; i < repeat; i++) {
      // Simulate key press on the focused element or document
      const target = document.activeElement || document.body;
      
      // Create keyboard event
      const eventOptions = {
        key: key,
        code: this.getKeyCode(key),
        bubbles: true,
        cancelable: true,
        ctrlKey: modifiers.includes('Control'),
        shiftKey: modifiers.includes('Shift'),
        altKey: modifiers.includes('Alt'),
        metaKey: modifiers.includes('Meta')
      };
      
      // Dispatch keydown
      target.dispatchEvent(new KeyboardEvent('keydown', eventOptions));
      
      // Dispatch keypress (for character keys)
      if (key.length === 1) {
        target.dispatchEvent(new KeyboardEvent('keypress', eventOptions));
      }
      
      // Dispatch keyup
      target.dispatchEvent(new KeyboardEvent('keyup', eventOptions));
      
      // Small delay between repeats
      if (i < repeat - 1) {
        await this.sleep(50);
      }
    }
    
    // Show visual feedback
    this.showKeyVisual(key, modifiers);
  }
  
  async typeText(text) {
    const target = document.activeElement;
    
    if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
      // Insert text at cursor position
      if (target.isContentEditable) {
        document.execCommand('insertText', false, text);
      } else {
        const start = target.selectionStart;
        const end = target.selectionEnd;
        const currentValue = target.value;
        
        target.value = currentValue.substring(0, start) + text + currentValue.substring(end);
        target.selectionStart = target.selectionEnd = start + text.length;
        
        // Trigger input event
        target.dispatchEvent(new Event('input', { bubbles: true }));
      }
    } else {
      console.warn('[VoiceKeyboard] No active text input to type into');
    }
  }
  
  holdKey(key) {
    this.activeKeys.add(key);
    this.updateActiveKeysDisplay();
  }
  
  releaseKey(key) {
    this.activeKeys.delete(key);
    this.updateActiveKeysDisplay();
  }
  
  getKeyCode(key) {
    const codeMap = {
      'Enter': 'Enter',
      'Escape': 'Escape',
      'Tab': 'Tab',
      ' ': 'Space',
      'Backspace': 'Backspace',
      'Delete': 'Delete',
      'ArrowUp': 'ArrowUp',
      'ArrowDown': 'ArrowDown',
      'ArrowLeft': 'ArrowLeft',
      'ArrowRight': 'ArrowRight',
      'Home': 'Home',
      'End': 'End',
      'PageUp': 'PageUp',
      'PageDown': 'PageDown',
      'Control': 'ControlLeft',
      'Shift': 'ShiftLeft',
      'Alt': 'AltLeft',
      'Meta': 'MetaLeft'
    };
    
    return codeMap[key] || `Key${key.toUpperCase()}`;
  }
  
  formatKeyCombo(result) {
    const parts = [];
    if (result.modifiers) {
      parts.push(...result.modifiers);
    }
    parts.push(result.key);
    
    let combo = parts.join('+');
    if (result.repeat > 1) {
      combo += ` (×${result.repeat})`;
    }
    
    return combo;
  }
  
  // ========== Annotation System ==========
  
  setupAnnotationUI() {
    if (!this.options.annotationContainer) {
      // Create default annotation container
      const container = document.createElement('div');
      container.id = 'voice-annotation-container';
      container.className = 'voice-annotation-container';
      container.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        max-width: 300px;
        max-height: 400px;
        overflow-y: auto;
        background: rgba(0, 20, 40, 0.95);
        border: 1px solid #0ff;
        border-radius: 8px;
        padding: 12px;
        display: none;
        z-index: 10000;
        font-family: 'Share Tech Mono', monospace;
        font-size: 11px;
        color: #0ff;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
      `;
      
      document.body.appendChild(container);
      this.options.annotationContainer = container;
    }
  }
  
  addAnnotation(text, timestamp) {
    const annotation = {
      id: Date.now(),
      text: text,
      timestamp: timestamp || new Date().toISOString(),
      highlighted: false
    };
    
    this.annotations.push(annotation);
    this.updateAnnotationDisplay();
    
    console.log('[VoiceKeyboard] Annotation added:', annotation);
  }
  
  updateAnnotationDisplay() {
    const container = this.options.annotationContainer;
    if (!container) return;
    
    if (this.annotations.length === 0) {
      container.style.display = 'none';
      return;
    }
    
    container.innerHTML = `
      <div style="display: flex; justify-content: space-between; margin-bottom: 10px; border-bottom: 1px solid #0ff; padding-bottom: 6px;">
        <strong>📝 Annotations (${this.annotations.length})</strong>
        <button onclick="voiceKeyboard.clearAnnotations()" style="background: none; border: 1px solid #0ff; color: #0ff; padding: 2px 8px; cursor: pointer; border-radius: 3px; font-size: 10px;">Clear</button>
      </div>
      ${this.annotations.map(ann => `
        <div style="margin-bottom: 8px; padding: 6px; background: rgba(0, 255, 255, 0.1); border-left: 2px solid #0ff; border-radius: 4px;">
          <div style="font-size: 9px; color: #0aa; margin-bottom: 3px;">${new Date(ann.timestamp).toLocaleTimeString()}</div>
          <div>${this.escapeHtml(ann.text)}</div>
        </div>
      `).join('')}
    `;
    
    container.style.display = 'block';
  }
  
  showAnnotations() {
    const container = this.options.annotationContainer;
    if (container) {
      container.style.display = this.annotations.length > 0 ? 'block' : 'none';
      this.updateAnnotationDisplay();
    }
  }
  
  clearAnnotations(target) {
    if (target) {
      // Clear specific annotation (future feature)
      console.log('[VoiceKeyboard] Clearing annotation:', target);
    } else {
      this.annotations = [];
      this.updateAnnotationDisplay();
    }
  }
  
  highlightText(text) {
    // Find and highlight text in the active element
    const target = document.activeElement;
    
    if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
      const value = target.value;
      const index = value.toLowerCase().indexOf(text.toLowerCase());
      
      if (index !== -1) {
        target.setSelectionRange(index, index + text.length);
        target.focus();
        this.showFeedback(`Highlighted "${text}"`, 'highlight');
      } else {
        this.showFeedback(`Text "${text}" not found`, 'error');
      }
    } else {
      // Try to highlight in document
      if (window.find) {
        window.find(text);
      }
    }
  }
  
  // ========== Dictation System ==========
  
  setupDictationUI() {
    if (!this.options.dictationDisplay) {
      // Create dictation display
      const display = document.createElement('div');
      display.id = 'voice-dictation-display';
      display.className = 'voice-dictation-display';
      display.style.cssText = `
        position: fixed;
        bottom: 80px;
        left: 50%;
        transform: translateX(-50%);
        min-width: 400px;
        max-width: 600px;
        max-height: 200px;
        overflow-y: auto;
        background: rgba(0, 20, 40, 0.95);
        border: 2px solid #f0f;
        border-radius: 8px;
        padding: 12px;
        display: none;
        z-index: 10000;
        font-family: 'Share Tech Mono', monospace;
        font-size: 12px;
        color: #fff;
        box-shadow: 0 0 20px rgba(255, 0, 255, 0.3);
      `;
      
      document.body.appendChild(display);
      this.options.dictationDisplay = display;
    }
  }
  
  startDictation() {
    this.dictationBuffer = '';
    this.currentMode = 'dictation';
    this.updateDictationDisplay();
    this.updateModeIndicator();
    
    const display = this.options.dictationDisplay;
    if (display) {
      display.style.display = 'block';
    }
  }
  
  stopDictation() {
    this.currentMode = 'keyboard';
    this.updateModeIndicator();
    
    const display = this.options.dictationDisplay;
    if (display) {
      display.style.display = 'none';
    }
  }
  
  clearDictation() {
    this.dictationBuffer = '';
    this.updateDictationDisplay();
  }
  
  appendDictation(text) {
    this.dictationBuffer += text + ' ';
    this.updateDictationDisplay();
  }
  
  async insertDictation(text) {
    await this.typeText(text);
    this.clearDictation();
  }
  
  updateDictationDisplay() {
    const display = this.options.dictationDisplay;
    if (!display) return;
    
    const charCount = this.dictationBuffer.length;
    const wordCount = this.dictationBuffer.trim().split(/\s+/).filter(w => w.length > 0).length;
    
    display.innerHTML = `
      <div style="display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #f0f; padding-bottom: 6px;">
        <strong>🎙️ Dictation Mode</strong>
        <div style="font-size: 10px;">
          <span style="margin-right: 12px;">${wordCount} words</span>
          <span>${charCount} chars</span>
        </div>
      </div>
      <div style="min-height: 60px; max-height: 120px; overflow-y: auto; padding: 8px; background: rgba(255, 0, 255, 0.1); border-radius: 4px; line-height: 1.5;">
        ${this.escapeHtml(this.dictationBuffer) || '<span style="color: #999;">Start speaking to dictate...</span>'}
      </div>
      <div style="margin-top: 8px; display: flex; gap: 8px; font-size: 10px;">
        <button onclick="voiceKeyboard.insertDictation('${this.escapeHtml(this.dictationBuffer)}')" style="background: #f0f; border: none; color: #000; padding: 4px 12px; cursor: pointer; border-radius: 3px; flex: 1;">Insert</button>
        <button onclick="voiceKeyboard.clearDictation()" style="background: none; border: 1px solid #f0f; color: #f0f; padding: 4px 12px; cursor: pointer; border-radius: 3px;">Clear</button>
        <button onclick="voiceKeyboard.stopDictation()" style="background: none; border: 1px solid #f0f; color: #f0f; padding: 4px 12px; cursor: pointer; border-radius: 3px;">Stop</button>
      </div>
    `;
  }
  
  // ========== Visual Feedback ==========
  
  setupVisualFeedback() {
    // Create feedback overlay
    const overlay = document.createElement('div');
    overlay.id = 'voice-keyboard-feedback';
    overlay.className = 'voice-keyboard-feedback';
    overlay.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(0, 255, 255, 0.95);
      color: #000;
      padding: 20px 40px;
      border-radius: 12px;
      font-family: 'Orbitron', sans-serif;
      font-size: 24px;
      font-weight: bold;
      display: none;
      z-index: 99999;
      box-shadow: 0 0 40px rgba(0, 255, 255, 0.8);
      pointer-events: none;
      text-align: center;
    `;
    
    document.body.appendChild(overlay);
    this.feedbackOverlay = overlay;
  }
  
  showFeedback(message, type = 'default') {
    if (!this.feedbackOverlay) return;
    
    const colors = {
      key: 'rgba(0, 255, 255, 0.95)',
      text: 'rgba(0, 255, 100, 0.95)',
      annotation: 'rgba(255, 200, 0, 0.95)',
      dictation: 'rgba(255, 0, 255, 0.95)',
      mode: 'rgba(100, 200, 255, 0.95)',
      highlight: 'rgba(255, 255, 0, 0.95)',
      error: 'rgba(255, 50, 50, 0.95)',
      default: 'rgba(0, 255, 255, 0.95)'
    };
    
    this.feedbackOverlay.style.background = colors[type] || colors.default;
    this.feedbackOverlay.textContent = message;
    this.feedbackOverlay.style.display = 'block';
    
    // Clear previous timeout
    if (this.visualFeedbackTimeout) {
      clearTimeout(this.visualFeedbackTimeout);
    }
    
    // Hide after delay
    this.visualFeedbackTimeout = setTimeout(() => {
      this.feedbackOverlay.style.display = 'none';
    }, 1500);
  }
  
  showKeyVisual(key, modifiers = []) {
    // Create a temporary key visualization
    const visual = document.createElement('div');
    visual.className = 'key-visual';
    visual.style.cssText = `
      position: fixed;
      bottom: 120px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(0, 0, 0, 0.9);
      border: 2px solid #0ff;
      border-radius: 8px;
      padding: 12px 24px;
      font-family: 'Orbitron', sans-serif;
      font-size: 18px;
      color: #0ff;
      z-index: 99998;
      box-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
      pointer-events: none;
    `;
    
    const parts = [...modifiers, key];
    visual.textContent = parts.join(' + ');
    
    document.body.appendChild(visual);
    
    // Animate and remove
    setTimeout(() => {
      visual.style.transition = 'opacity 0.3s, transform 0.3s';
      visual.style.opacity = '0';
      visual.style.transform = 'translateX(-50%) translateY(-20px)';
      
      setTimeout(() => {
        visual.remove();
      }, 300);
    }, 1000);
  }
  
  updateActiveKeysDisplay() {
    // Update display of currently held keys
    if (this.activeKeys.size > 0) {
      console.log('[VoiceKeyboard] Active keys:', Array.from(this.activeKeys));
    }
  }
  
  // ========== Mode Management ==========
  
  setupModeIndicator() {
    // Create mode indicator badge
    const badge = document.createElement('div');
    badge.id = 'voice-keyboard-mode-badge';
    badge.className = 'voice-keyboard-mode-badge';
    badge.style.cssText = `
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(0, 255, 255, 0.9);
      color: #000;
      padding: 8px 20px;
      border-radius: 20px;
      font-family: 'Orbitron', sans-serif;
      font-size: 12px;
      font-weight: bold;
      z-index: 10001;
      box-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
      display: none;
      text-transform: uppercase;
    `;
    
    document.body.appendChild(badge);
    this.modeBadge = badge;
    this.updateModeIndicator();
  }
  
  switchMode(mode) {
    this.currentMode = mode;
    this.updateModeIndicator();
    
    // Update backend mode if available
    if (typeof eel !== 'undefined' && eel.set_keyboard_command_mode) {
      eel.set_keyboard_command_mode(mode);
    }
  }
  
  updateModeIndicator() {
    if (!this.modeBadge) return;
    
    const modeIcons = {
      keyboard: '⌨️',
      annotation: '📝',
      dictation: '🎙️'
    };
    
    const modeColors = {
      keyboard: 'rgba(0, 255, 255, 0.9)',
      annotation: 'rgba(255, 200, 0, 0.9)',
      dictation: 'rgba(255, 0, 255, 0.9)'
    };
    
    const icon = modeIcons[this.currentMode] || '⌨️';
    const color = modeColors[this.currentMode] || 'rgba(0, 255, 255, 0.9)';
    
    this.modeBadge.textContent = `${icon} ${this.currentMode.toUpperCase()} MODE`;
    this.modeBadge.style.background = color;
    this.modeBadge.style.display = this.currentMode !== 'keyboard' ? 'block' : 'none';
  }
  
  // ========== Utility Methods ==========
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  destroy() {
    // Clean up UI elements
    if (this.feedbackOverlay) {
      this.feedbackOverlay.remove();
    }
    
    if (this.modeBadge) {
      this.modeBadge.remove();
    }
    
    if (this.options.annotationContainer && this.options.annotationContainer.id === 'voice-annotation-container') {
      this.options.annotationContainer.remove();
    }
    
    if (this.options.dictationDisplay && this.options.dictationDisplay.id === 'voice-dictation-display') {
      this.options.dictationDisplay.remove();
    }
    
    if (this.visualFeedbackTimeout) {
      clearTimeout(this.visualFeedbackTimeout);
    }
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = VoiceKeyboardController;
}

// ES6 export for module systems
export { VoiceKeyboardController };
