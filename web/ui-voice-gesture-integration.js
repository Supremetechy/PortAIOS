/**
 * UI Voice & Gesture Integration System
 * Provides unified voice command and gesture control for all UI elements
 */

export class UIVoiceGestureController {
    constructor(voiceInput, gestureInput, options = {}) {
        this.voiceInput = voiceInput;
        this.gestureInput = gestureInput;
        this.options = {
            enableVoiceControl: true,
            enableGestureControl: true,
            showVisualFeedback: true,
            confirmDestructiveActions: true,
            ...options
        };
        
        // UI element registry
        this.elements = new Map();
        
        // Command patterns
        this.voicePatterns = [];
        this.gesturePatterns = [];
        
        // Active target tracking
        this.activeTarget = null;
        this.targetHighlightTimeout = null;
        
        // State
        this.enabled = false;
        
        console.log('[UIVoiceGesture] Controller initialized');
    }
    
    /**
     * Initialize and register all UI elements
     */
    initialize() {
        console.log('[UIVoiceGesture] Initializing UI element registration...');
        
        // Register all buttons
        this.registerButtons();
        
        // Register all inputs
        this.registerInputs();
        
        // Register all selects/dropdowns
        this.registerSelects();
        
        // Register all sliders
        this.registerSliders();
        
        // Register special controls
        this.registerSpecialControls();
        
        // Setup voice command handlers
        if (this.options.enableVoiceControl && this.voiceInput) {
            this.setupVoiceCommands();
        }
        
        // Setup gesture handlers
        if (this.options.enableGestureControl && this.gestureInput) {
            this.setupGestureHandlers();
        }
        
        this.enabled = true;
        console.log(`[UIVoiceGesture] Registered ${this.elements.size} UI elements`);
    }
    
    /**
     * Register all button elements
     */
    registerButtons() {
        const buttons = [
            // Top-level buttons
            { id: 'theme-selector-btn', name: 'theme selector', aliases: ['themes', 'theme', 'colors'], action: 'click' },
            { id: 'ai-assistant-btn', name: 'AI assistant', aliases: ['assistant', 'AI', 'robot'], action: 'click' },
            { id: 'gesture-help-btn', name: 'gesture help', aliases: ['help', 'gestures', 'gesture guide'], action: 'click' },
            { id: 'gesture-trainer-btn', name: 'gesture trainer', aliases: ['train gestures', 'trainer', 'training'], action: 'click' },
            { id: 'voice-btn', name: 'voice button', aliases: ['voice', 'microphone'], action: 'click' },
            
            // Avatar mode
            { id: 'toggle-avatar-mode', name: 'toggle avatar mode', aliases: ['dynamic interface', 'switch mode', 'avatar mode'], action: 'click' },
            
            // Customizer button
            { id: 'cust-generate', name: 'generate avatar', aliases: ['generate', 'apply avatar', 'create avatar'], action: 'click' },
            
            // Quick action buttons
            { id: 'btn-demo', name: 'demo', aliases: ['demonstration', 'show demo'], action: 'click' },
            { id: 'btn-greet', name: 'greet', aliases: ['greeting', 'say hello'], action: 'click' },
            { id: 'btn-glitch', name: 'glitch', aliases: ['glitch effect', 'error effect'], action: 'click' },
            { id: 'btn-effects', name: 'toggle effects', aliases: ['effects', 'CRT', 'screen effects'], action: 'click' },
            
            // Speech test
            { id: 'btn-speak', name: 'speak', aliases: ['say', 'speak text'], action: 'click' },
            
            // Wake word
            { id: 'btn-add-wake', name: 'add wake word', aliases: ['add wake', 'new wake word'], action: 'click' },
            
            // MiniKernel buttons
            { id: 'mk-boot-btn', name: 'boot minikernel', aliases: ['boot', 'start minikernel', 'boot kernel'], action: 'click' },
            { id: 'mk-shut-btn', name: 'halt minikernel', aliases: ['halt', 'stop minikernel', 'shutdown kernel'], action: 'click' },
            { id: 'mk-clear-btn', name: 'clear minikernel', aliases: ['clear', 'clear output'], action: 'click' },
            
            // Bottom bar mic
            { id: 'mic-btn', name: 'microphone', aliases: ['mic', 'voice input', 'toggle mic'], action: 'click' }
        ];
        
        buttons.forEach(btn => this.registerElement(btn));
    }
    
    /**
     * Register all input elements
     */
    registerInputs() {
        const inputs = [
            { id: 'speech-text', name: 'speech input', aliases: ['speech text', 'text to speak', 'say text'], action: 'focus', type: 'text' },
            { id: 'new-wake-word', name: 'wake word input', aliases: ['wake word', 'new wake'], action: 'focus', type: 'text' },
            { id: 'command-input', name: 'command input', aliases: ['command', 'terminal', 'console'], action: 'focus', type: 'text' }
        ];
        
        inputs.forEach(input => this.registerElement(input));
    }
    
    /**
     * Register all select/dropdown elements
     */
    registerSelects() {
        const selects = [
            { id: 'palette-select', name: 'palette selector', aliases: ['palette', 'color palette', 'colors'], action: 'focus', type: 'select',
              options: ['matrix', 'cyan', 'cyber-magenta', 'amber', 'ice', 'red'] },
            { id: 'activity-select', name: 'activity selector', aliases: ['activity', 'avatar activity', 'state'], action: 'focus', type: 'select',
              options: ['idle', 'thinking', 'speaking', 'error'] },
            { id: 'voice-select', name: 'voice selector', aliases: ['voice', 'TTS voice', 'speech voice'], action: 'focus', type: 'select' }
        ];
        
        selects.forEach(select => this.registerElement(select));
    }
    
    /**
     * Register all slider/range elements
     */
    registerSliders() {
        const sliders = [
            { id: 'cust-smile', name: 'smile slider', aliases: ['smile', 'smile strength'], action: 'focus', type: 'range', min: 0, max: 1, step: 0.05 },
            { id: 'cust-frown', name: 'frown slider', aliases: ['frown', 'frown strength'], action: 'focus', type: 'range', min: 0, max: 1, step: 0.05 },
            { id: 'cust-surprise', name: 'surprise slider', aliases: ['surprise', 'surprise strength'], action: 'focus', type: 'range', min: 0, max: 1, step: 0.05 },
            { id: 'cust-wink', name: 'wink slider', aliases: ['wink', 'wink strength'], action: 'focus', type: 'range', min: 0, max: 1, step: 0.05 },
            { id: 'cust-viseme', name: 'viseme slider', aliases: ['viseme', 'viseme strength'], action: 'focus', type: 'range', min: 0, max: 1, step: 0.05 },
            { id: 'cust-subdivisions', name: 'detail slider', aliases: ['detail', 'subdivisions', 'avatar detail'], action: 'focus', type: 'range', min: 2, max: 6, step: 1 }
        ];
        
        sliders.forEach(slider => this.registerElement(slider));
    }
    
    /**
     * Register special controls (checkboxes, color pickers, etc.)
     */
    registerSpecialControls() {
        const controls = [
            { id: 'conversation-mode-toggle', name: 'conversation mode', aliases: ['continuous conversation', 'conversation'], action: 'toggle', type: 'checkbox' },
            { id: 'cust-skin', name: 'skin color', aliases: ['skin', 'avatar skin', 'skin tone'], action: 'focus', type: 'color' }
        ];
        
        controls.forEach(ctrl => this.registerElement(ctrl));
    }
    
    /**
     * Register a UI element for voice/gesture control
     */
    registerElement(config) {
        const element = document.getElementById(config.id);
        if (!element) {
            console.warn(`[UIVoiceGesture] Element not found: ${config.id}`);
            return;
        }
        
        this.elements.set(config.id, {
            element,
            config,
            voicePatterns: this.generateVoicePatterns(config),
            gesturePatterns: this.generateGesturePatterns(config)
        });
    }
    
    /**
     * Generate voice command patterns for an element
     */
    generateVoicePatterns(config) {
        const patterns = [];
        const allNames = [config.name, ...(config.aliases || [])];
        
        // Click/press patterns
        if (config.action === 'click') {
            allNames.forEach(name => {
                patterns.push(
                    new RegExp(`\\b(click|press|activate|trigger|tap)\\s+(the\\s+)?(${name})\\b`, 'i'),
                    new RegExp(`\\b(${name})\\s+(button|btn)\\b`, 'i'),
                    new RegExp(`\\b(${name})\\b`, 'i')
                );
            });
        }
        
        // Focus patterns
        if (config.action === 'focus') {
            allNames.forEach(name => {
                patterns.push(
                    new RegExp(`\\b(focus|select|go to|open)\\s+(the\\s+)?(${name})\\b`, 'i'),
                    new RegExp(`\\b(${name})\\b`, 'i')
                );
            });
        }
        
        // Toggle patterns
        if (config.action === 'toggle') {
            allNames.forEach(name => {
                patterns.push(
                    new RegExp(`\\b(toggle|switch|enable|disable|turn on|turn off)\\s+(the\\s+)?(${name})\\b`, 'i'),
                    new RegExp(`\\b(${name})\\s+(on|off)\\b`, 'i')
                );
            });
        }
        
        // Select option patterns
        if (config.type === 'select' && config.options) {
            allNames.forEach(name => {
                config.options.forEach(option => {
                    patterns.push(
                        new RegExp(`\\b(set|select|choose|change)\\s+(${name}\\s+to\\s+|the\\s+)?${option}\\b`, 'i'),
                        new RegExp(`\\b${option}\\s+(${name}|palette|mode)\\b`, 'i')
                    );
                });
            });
        }
        
        // Slider value patterns
        if (config.type === 'range') {
            allNames.forEach(name => {
                patterns.push(
                    new RegExp(`\\b(set|adjust|change)\\s+(the\\s+)?(${name})\\s+(to\\s+)?(\\d+\\.?\\d*)\\b`, 'i'),
                    new RegExp(`\\b(increase|raise|up)\\s+(the\\s+)?(${name})\\b`, 'i'),
                    new RegExp(`\\b(decrease|lower|down)\\s+(the\\s+)?(${name})\\b`, 'i'),
                    new RegExp(`\\b(${name})\\s+(up|down|increase|decrease|maximum|minimum|max|min)\\b`, 'i')
                );
            });
        }
        
        return patterns;
    }
    
    /**
     * Generate gesture patterns for an element
     */
    generateGesturePatterns(config) {
        // Map gestures to actions
        const patterns = [];
        
        // Pointing gesture for selection/focus
        if (config.action === 'click' || config.action === 'focus') {
            patterns.push({ gesture: 'point', action: 'highlight' });
            patterns.push({ gesture: 'thumb_up', action: 'activate' });
        }
        
        // Swipe gestures for sliders
        if (config.type === 'range') {
            patterns.push({ gesture: 'swipe_right', action: 'increase' });
            patterns.push({ gesture: 'swipe_left', action: 'decrease' });
        }
        
        // OK gesture for confirmation
        patterns.push({ gesture: 'ok', action: 'confirm' });
        
        return patterns;
    }
    
    /**
     * Setup voice command handlers
     */
    setupVoiceCommands() {
        if (!this.voiceInput) return;
        
        // Add custom command processor
        const originalProcessor = this.voiceInput.processCommand;
        this.voiceInput.processCommand = async (command) => {
            // Try UI element commands first
            const handled = await this.handleVoiceCommand(command);
            if (handled) return;
            
            // Fall back to original processor
            if (originalProcessor) {
                originalProcessor.call(this.voiceInput, command);
            }
        };
        
        console.log('[UIVoiceGesture] Voice command handlers registered');
    }
    
    /**
     * Handle voice command for UI elements
     */
    async handleVoiceCommand(command) {
        const lower = command.toLowerCase().trim();
        
        // Search through all registered elements
        for (const [id, data] of this.elements) {
            for (const pattern of data.voicePatterns) {
                const match = lower.match(pattern);
                if (match) {
                    console.log(`[UIVoiceGesture] Matched command "${command}" to element: ${id}`);
                    await this.executeAction(id, match, command);
                    return true;
                }
            }
        }
        
        return false;
    }
    
    /**
     * Execute action on a UI element
     */
    async executeAction(elementId, match, originalCommand) {
        const data = this.elements.get(elementId);
        if (!data) return;
        
        const { element, config } = data;
        
        // Show visual feedback
        if (this.options.showVisualFeedback) {
            this.highlightElement(element);
        }
        
        // Execute action based on type
        switch (config.action) {
            case 'click':
                element.click();
                this.speak(`Activated ${config.name}`);
                break;
                
            case 'focus':
                element.focus();
                if (config.type === 'select') {
                    // Check if command includes option selection
                    const optionMatch = this.extractOption(originalCommand, config.options);
                    if (optionMatch) {
                        element.value = optionMatch;
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                        this.speak(`Set ${config.name} to ${optionMatch}`);
                    } else {
                        this.speak(`Focused ${config.name}`);
                    }
                } else if (config.type === 'range') {
                    // Check if command includes value
                    const value = this.extractSliderValue(originalCommand, match, config);
                    if (value !== null) {
                        element.value = value;
                        element.dispatchEvent(new Event('input', { bubbles: true }));
                        this.speak(`Set ${config.name} to ${value}`);
                    } else {
                        this.speak(`Focused ${config.name}`);
                    }
                } else {
                    this.speak(`Focused ${config.name}`);
                }
                break;
                
            case 'toggle':
                if (config.type === 'checkbox') {
                    element.checked = !element.checked;
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    this.speak(`${element.checked ? 'Enabled' : 'Disabled'} ${config.name}`);
                }
                break;
        }
        
        // Log activity
        this.logActivity(`Voice: ${originalCommand} → ${config.name}`);
    }
    
    /**
     * Extract option from voice command
     */
    extractOption(command, options) {
        if (!options) return null;
        
        const lower = command.toLowerCase();
        for (const option of options) {
            if (lower.includes(option.toLowerCase())) {
                return option;
            }
        }
        return null;
    }
    
    /**
     * Extract slider value from voice command
     */
    extractSliderValue(command, match, config) {
        const lower = command.toLowerCase();
        
        // Check for explicit value
        const valueMatch = command.match(/(\d+\.?\d*)/);
        if (valueMatch) {
            const value = parseFloat(valueMatch[1]);
            // Clamp to min/max
            return Math.max(config.min, Math.min(config.max, value));
        }
        
        // Check for increase/decrease
        if (lower.includes('increase') || lower.includes('up') || lower.includes('raise')) {
            const currentValue = parseFloat(config.element?.value || config.min);
            return Math.min(config.max, currentValue + config.step);
        }
        
        if (lower.includes('decrease') || lower.includes('down') || lower.includes('lower')) {
            const currentValue = parseFloat(config.element?.value || config.min);
            return Math.max(config.min, currentValue - config.step);
        }
        
        // Check for max/min
        if (lower.includes('maximum') || lower.includes('max')) {
            return config.max;
        }
        
        if (lower.includes('minimum') || lower.includes('min')) {
            return config.min;
        }
        
        return null;
    }
    
    /**
     * Setup gesture handlers
     */
    setupGestureHandlers() {
        if (!this.gestureInput) return;
        
        // Register gesture callbacks
        this.gestureInput.registerGestureCallback('point', (gesture) => {
            this.handlePointGesture(gesture);
        });
        
        this.gestureInput.registerGestureCallback('thumb_up', (gesture) => {
            this.handleActivateGesture(gesture);
        });
        
        this.gestureInput.registerGestureCallback('ok', (gesture) => {
            this.handleConfirmGesture(gesture);
        });
        
        this.gestureInput.registerGestureCallback('swipe_right', (gesture) => {
            this.handleSwipeGesture('right', gesture);
        });
        
        this.gestureInput.registerGestureCallback('swipe_left', (gesture) => {
            this.handleSwipeGesture('left', gesture);
        });
        
        console.log('[UIVoiceGesture] Gesture handlers registered');
    }
    
    /**
     * Handle point gesture (hover/select)
     */
    handlePointGesture(gesture) {
        // Find element under gesture position
        const element = this.findElementAtPosition(gesture.position);
        if (element && this.elements.has(element.id)) {
            this.activeTarget = element.id;
            this.highlightElement(element);
        }
    }
    
    /**
     * Handle activate gesture (click)
     */
    handleActivateGesture(gesture) {
        if (this.activeTarget) {
            const data = this.elements.get(this.activeTarget);
            if (data && data.config.action === 'click') {
                data.element.click();
                this.speak(`Activated ${data.config.name}`);
            }
        }
    }
    
    /**
     * Handle confirm gesture
     */
    handleConfirmGesture(gesture) {
        if (this.activeTarget) {
            const data = this.elements.get(this.activeTarget);
            if (data) {
                if (data.config.action === 'click') {
                    data.element.click();
                } else if (data.config.action === 'focus') {
                    data.element.focus();
                }
                this.speak(`Confirmed ${data.config.name}`);
            }
        }
    }
    
    /**
     * Handle swipe gesture (for sliders)
     */
    handleSwipeGesture(direction, gesture) {
        if (this.activeTarget) {
            const data = this.elements.get(this.activeTarget);
            if (data && data.config.type === 'range') {
                const element = data.element;
                const currentValue = parseFloat(element.value);
                const step = data.config.step || 0.1;
                
                let newValue;
                if (direction === 'right') {
                    newValue = Math.min(data.config.max, currentValue + step);
                } else {
                    newValue = Math.max(data.config.min, currentValue - step);
                }
                
                element.value = newValue;
                element.dispatchEvent(new Event('input', { bubbles: true }));
                this.speak(`${data.config.name}: ${newValue.toFixed(2)}`);
            }
        }
    }
    
    /**
     * Find element at screen position
     */
    findElementAtPosition(position) {
        if (!position || !position.x || !position.y) return null;
        
        // Convert normalized coordinates to screen coordinates
        const x = position.x * window.innerWidth;
        const y = position.y * window.innerHeight;
        
        const element = document.elementFromPoint(x, y);
        return element;
    }
    
    /**
     * Highlight an element with visual feedback
     */
    highlightElement(element) {
        if (!element) return;
        
        // Clear previous highlight
        if (this.targetHighlightTimeout) {
            clearTimeout(this.targetHighlightTimeout);
        }
        
        // Remove previous highlights
        document.querySelectorAll('.voice-gesture-highlight').forEach(el => {
            el.classList.remove('voice-gesture-highlight');
        });
        
        // Add highlight
        element.classList.add('voice-gesture-highlight');
        
        // Auto-remove after 2 seconds
        this.targetHighlightTimeout = setTimeout(() => {
            element.classList.remove('voice-gesture-highlight');
        }, 2000);
    }
    
    /**
     * Speak feedback
     */
    speak(text) {
        // Use global speak function if available
        if (window.speak) {
            window.speak(text);
        } else if (window.speechSynthesis) {
            const utterance = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.speak(utterance);
        }
    }
    
    /**
     * Log activity
     */
    logActivity(message) {
        if (window.logActivity) {
            window.logActivity(message);
        } else {
            console.log(`[UIVoiceGesture] ${message}`);
        }
    }
    
    /**
     * Get list of available voice commands
     */
    getVoiceCommandList() {
        const commands = [];
        
        for (const [id, data] of this.elements) {
            const config = data.config;
            const examples = [];
            
            if (config.action === 'click') {
                examples.push(`Click ${config.name}`);
                examples.push(`Press ${config.name}`);
            } else if (config.action === 'focus') {
                examples.push(`Open ${config.name}`);
                examples.push(`Focus ${config.name}`);
            } else if (config.action === 'toggle') {
                examples.push(`Toggle ${config.name}`);
                examples.push(`Enable ${config.name}`);
            }
            
            if (config.type === 'select' && config.options) {
                config.options.forEach(opt => {
                    examples.push(`Set ${config.name} to ${opt}`);
                });
            }
            
            if (config.type === 'range') {
                examples.push(`Increase ${config.name}`);
                examples.push(`Set ${config.name} to 0.5`);
            }
            
            commands.push({
                element: config.name,
                id: id,
                examples: examples.slice(0, 3) // Limit to 3 examples
            });
        }
        
        return commands;
    }
    
    /**
     * Enable/disable the controller
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        console.log(`[UIVoiceGesture] ${enabled ? 'Enabled' : 'Disabled'}`);
    }
}

// Add CSS for visual feedback
const style = document.createElement('style');
style.textContent = `
    .voice-gesture-highlight {
        animation: voice-gesture-pulse 0.6s ease-in-out;
        outline: 2px solid rgba(0, 255, 255, 0.8) !important;
        outline-offset: 2px;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.6) !important;
    }
    
    @keyframes voice-gesture-pulse {
        0%, 100% {
            outline-color: rgba(0, 255, 255, 0.8);
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.6);
        }
        50% {
            outline-color: rgba(0, 255, 255, 1);
            box-shadow: 0 0 30px rgba(0, 255, 255, 1);
        }
    }
    
    .voice-gesture-target-indicator {
        position: fixed;
        width: 30px;
        height: 30px;
        border: 2px solid #00ffff;
        border-radius: 50%;
        pointer-events: none;
        z-index: 10000;
        animation: target-pulse 1s ease-in-out infinite;
    }
    
    @keyframes target-pulse {
        0%, 100% {
            transform: scale(1);
            opacity: 0.8;
        }
        50% {
            transform: scale(1.2);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);

export default UIVoiceGestureController;
