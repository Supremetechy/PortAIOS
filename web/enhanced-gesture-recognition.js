/**
 * Enhanced Gesture Recognition System
 * Adds new gesture types: peace, fist, phone, heart, wave, rock, spock
 */

export class EnhancedGestureRecognition {
    constructor(gestureInput, options = {}) {
        this.gestureInput = gestureInput;
        this.options = {
            enablePeaceGesture: true,
            enableFistGesture: true,
            enablePhoneGesture: true,
            enableHeartGesture: true,
            enableWaveGesture: true,
            enableRockGesture: true,
            enableSpockGesture: true,
            sensitivity: 0.7,
            ...options
        };
        
        // Gesture callbacks
        this.callbacks = new Map();
        
        // Gesture state
        this.lastGesture = null;
        this.lastGestureTime = 0;
        this.gestureHistory = [];
        
        console.log('[EnhancedGesture] Enhanced gesture recognition initialized');
    }
    
    /**
     * Initialize enhanced gestures
     */
    initialize() {
        this.registerEnhancedGestures();
        console.log('[EnhancedGesture] Enhanced gestures registered');
    }
    
    /**
     * Register all enhanced gesture types
     */
    registerEnhancedGestures() {
        // Peace sign (✌️) - Screenshot or confirm
        this.registerGesture('peace', {
            name: 'Peace Sign',
            emoji: '✌️',
            description: 'Take screenshot or confirm action',
            action: 'screenshot',
            color: '#00ff00'
        });
        
        // Fist (✊) - Select or grab
        this.registerGesture('fist', {
            name: 'Fist',
            emoji: '✊',
            description: 'Select, grab, or hold',
            action: 'select',
            color: '#ff9900'
        });
        
        // Phone (🤙) - Open communication
        this.registerGesture('phone', {
            name: 'Phone',
            emoji: '🤙',
            description: 'Open browser or communication',
            action: 'open_browser',
            color: '#00ffff'
        });
        
        // Heart (❤️) - Favorite or like
        this.registerGesture('heart', {
            name: 'Heart',
            emoji: '❤️',
            description: 'Favorite, like, or bookmark',
            action: 'favorite',
            color: '#ff0055'
        });
        
        // Wave (👋) - Hello or dismiss
        this.registerGesture('wave', {
            name: 'Wave',
            emoji: '👋',
            description: 'Greet, dismiss, or cancel',
            action: 'dismiss',
            color: '#ffff00'
        });
        
        // Rock (🤘) - Metal/rock gesture
        this.registerGesture('rock', {
            name: 'Rock',
            emoji: '🤘',
            description: 'Activate special mode',
            action: 'special_mode',
            color: '#ff00ff'
        });
        
        // Spock (🖖) - Vulcan salute
        this.registerGesture('spock', {
            name: 'Spock',
            emoji: '🖖',
            description: 'Live long and prosper',
            action: 'easter_egg',
            color: '#0099ff'
        });
    }
    
    /**
     * Register a gesture with metadata
     */
    registerGesture(type, metadata) {
        if (!this.callbacks.has(type)) {
            this.callbacks.set(type, []);
        }
        
        // Store metadata
        if (!this.gestures) {
            this.gestures = new Map();
        }
        this.gestures.set(type, metadata);
        
        console.log(`[EnhancedGesture] Registered: ${metadata.emoji} ${metadata.name}`);
    }
    
    /**
     * Process gesture detection
     */
    processGesture(gestureType, confidence = 1.0, position = null) {
        // Check if gesture is enabled
        const enabledKey = `enable${gestureType.charAt(0).toUpperCase() + gestureType.slice(1)}Gesture`;
        if (this.options[enabledKey] === false) {
            return;
        }
        
        // Check sensitivity threshold
        if (confidence < this.options.sensitivity) {
            return;
        }
        
        // Debounce - prevent duplicate detections
        const now = Date.now();
        if (this.lastGesture === gestureType && (now - this.lastGestureTime) < 1000) {
            return;
        }
        
        this.lastGesture = gestureType;
        this.lastGestureTime = now;
        
        // Add to history
        this.gestureHistory.push({
            type: gestureType,
            confidence,
            position,
            timestamp: now
        });
        
        // Keep only last 10 gestures
        if (this.gestureHistory.length > 10) {
            this.gestureHistory.shift();
        }
        
        // Execute callbacks
        this.executeCallbacks(gestureType, { confidence, position, timestamp: now });
        
        // Show visual feedback
        this.showGestureFeedback(gestureType);
        
        console.log(`[EnhancedGesture] Detected: ${gestureType} (${(confidence * 100).toFixed(0)}%)`);
    }
    
    /**
     * Execute callbacks for gesture
     */
    executeCallbacks(gestureType, data) {
        const callbacks = this.callbacks.get(gestureType);
        if (callbacks) {
            callbacks.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[EnhancedGesture] Callback error for ${gestureType}:`, error);
                }
            });
        }
    }
    
    /**
     * Register callback for gesture type
     */
    on(gestureType, callback) {
        if (!this.callbacks.has(gestureType)) {
            this.callbacks.set(gestureType, []);
        }
        this.callbacks.get(gestureType).push(callback);
    }
    
    /**
     * Show visual feedback for gesture
     */
    showGestureFeedback(gestureType) {
        const metadata = this.gestures?.get(gestureType);
        if (!metadata) return;
        
        // Create feedback element
        const feedback = document.createElement('div');
        feedback.className = 'enhanced-gesture-feedback';
        feedback.innerHTML = `
            <div class="gesture-icon" style="color: ${metadata.color}">${metadata.emoji}</div>
            <div class="gesture-name">${metadata.name}</div>
        `;
        
        document.body.appendChild(feedback);
        
        // Animate and remove
        setTimeout(() => {
            feedback.classList.add('fade-out');
            setTimeout(() => feedback.remove(), 300);
        }, 1500);
        
        // Play sound if available
        this.playGestureSound(gestureType);
    }
    
    /**
     * Play sound for gesture
     */
    playGestureSound(gestureType) {
        // Simple beep using Web Audio API
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            // Different frequencies for different gestures
            const frequencies = {
                peace: 800,
                fist: 400,
                phone: 600,
                heart: 900,
                wave: 500,
                rock: 300,
                spock: 700
            };
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = frequencies[gestureType] || 500;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (error) {
            console.warn('[EnhancedGesture] Audio feedback not available:', error);
        }
    }
    
    /**
     * Get gesture statistics
     */
    getStatistics() {
        const stats = {};
        
        this.gestureHistory.forEach(gesture => {
            if (!stats[gesture.type]) {
                stats[gesture.type] = {
                    count: 0,
                    avgConfidence: 0,
                    lastSeen: null
                };
            }
            
            stats[gesture.type].count++;
            stats[gesture.type].avgConfidence += gesture.confidence;
            stats[gesture.type].lastSeen = gesture.timestamp;
        });
        
        // Calculate averages
        Object.keys(stats).forEach(type => {
            stats[type].avgConfidence /= stats[type].count;
        });
        
        return stats;
    }
    
    /**
     * Get all registered gestures
     */
    getGestureList() {
        const list = [];
        
        if (this.gestures) {
            for (const [type, metadata] of this.gestures) {
                list.push({
                    type,
                    ...metadata,
                    enabled: this.options[`enable${type.charAt(0).toUpperCase() + type.slice(1)}Gesture`] !== false
                });
            }
        }
        
        return list;
    }
    
    /**
     * Enable/disable specific gesture
     */
    setGestureEnabled(gestureType, enabled) {
        const key = `enable${gestureType.charAt(0).toUpperCase() + gestureType.slice(1)}Gesture`;
        this.options[key] = enabled;
        console.log(`[EnhancedGesture] ${gestureType}: ${enabled ? 'enabled' : 'disabled'}`);
    }
    
    /**
     * Set sensitivity threshold
     */
    setSensitivity(value) {
        this.options.sensitivity = Math.max(0, Math.min(1, value));
        console.log(`[EnhancedGesture] Sensitivity: ${(this.options.sensitivity * 100).toFixed(0)}%`);
    }
    
    /**
     * Clear gesture history
     */
    clearHistory() {
        this.gestureHistory = [];
        console.log('[EnhancedGesture] History cleared');
    }
}

// Default gesture action handlers
export class GestureActionHandlers {
    constructor(enhancedGesture) {
        this.gesture = enhancedGesture;
        this.setupDefaultHandlers();
    }
    
    setupDefaultHandlers() {
        // Peace sign - Screenshot
        this.gesture.on('peace', () => {
            console.log('[GestureAction] Peace: Taking screenshot...');
            if (window.AIOS?.advancedDesktop?.takeScreenshot) {
                window.AIOS.advancedDesktop.takeScreenshot();
            }
            this.speak('Screenshot captured');
        });
        
        // Fist - Select/Grab mode
        this.gesture.on('fist', () => {
            console.log('[GestureAction] Fist: Select mode activated');
            this.speak('Select mode');
        });
        
        // Phone - Open browser
        this.gesture.on('phone', () => {
            console.log('[GestureAction] Phone: Opening browser...');
            window.open('https://www.google.com', '_blank');
            this.speak('Opening browser');
        });
        
        // Heart - Favorite/Bookmark
        this.gesture.on('heart', () => {
            console.log('[GestureAction] Heart: Added to favorites');
            this.speak('Added to favorites');
        });
        
        // Wave - Greet or dismiss
        this.gesture.on('wave', () => {
            console.log('[GestureAction] Wave: Greeting...');
            if (document.getElementById('btn-greet')) {
                document.getElementById('btn-greet').click();
            } else {
                this.speak('Hello there!');
            }
        });
        
        // Rock - Special mode
        this.gesture.on('rock', () => {
            console.log('[GestureAction] Rock: Activating rock mode...');
            this.speak('Rock mode activated');
            if (document.getElementById('btn-glitch')) {
                document.getElementById('btn-glitch').click();
            }
        });
        
        // Spock - Easter egg
        this.gesture.on('spock', () => {
            console.log('[GestureAction] Spock: Live long and prosper');
            this.speak('Live long and prosper');
            this.triggerSpockEasterEgg();
        });
    }
    
    triggerSpockEasterEgg() {
        // Change theme to "Enterprise" style
        const body = document.body;
        body.style.transition = 'all 1s ease';
        body.style.filter = 'hue-rotate(180deg)';
        
        setTimeout(() => {
            body.style.filter = '';
        }, 3000);
    }
    
    speak(text) {
        if (window.speak) {
            window.speak(text);
        } else if (window.speechSynthesis) {
            const utterance = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.speak(utterance);
        }
    }
}

// Add CSS for gesture feedback
const style = document.createElement('style');
style.textContent = `
    .enhanced-gesture-feedback {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(0, 0, 0, 0.9);
        border: 2px solid #00ffff;
        border-radius: 20px;
        padding: 30px 50px;
        z-index: 10001;
        text-align: center;
        animation: gesture-appear 0.3s ease-out;
        pointer-events: none;
    }
    
    .enhanced-gesture-feedback.fade-out {
        animation: gesture-disappear 0.3s ease-out forwards;
    }
    
    .gesture-icon {
        font-size: 64px;
        margin-bottom: 10px;
        animation: gesture-bounce 0.5s ease-out;
    }
    
    .gesture-name {
        font-family: 'Courier New', monospace;
        font-size: 18px;
        color: #00ffff;
        font-weight: bold;
        letter-spacing: 2px;
    }
    
    @keyframes gesture-appear {
        from {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.5);
        }
        to {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
        }
    }
    
    @keyframes gesture-disappear {
        from {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
        }
        to {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.8);
        }
    }
    
    @keyframes gesture-bounce {
        0%, 100% {
            transform: scale(1);
        }
        50% {
            transform: scale(1.2);
        }
    }
`;
document.head.appendChild(style);

export default EnhancedGestureRecognition;
