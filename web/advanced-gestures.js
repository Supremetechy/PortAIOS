/**
 * Advanced Custom Gestures
 * Recognition for numbers, letters, symbols, and complex gesture sequences
 * Supports: Counting (1-5), Letters (A-Z), Symbols, and custom combos
 */

export class AdvancedGestures {
    constructor(options = {}) {
        this.options = {
            enableCounting: true,
            enableLetters: true,
            enableSymbols: true,
            enableSequences: true,
            sequenceTimeout: 2000, // ms
            ...options
        };
        
        // Gesture definitions
        this.countingGestures = new Map();
        this.letterGestures = new Map();
        this.symbolGestures = new Map();
        this.sequenceGestures = new Map();
        
        // Sequence tracking
        this.currentSequence = [];
        this.sequenceTimer = null;
        
        // Callbacks
        this.callbacks = new Map();
        
        // Initialize
        this.initialize();
        
        console.log('[AdvancedGestures] Advanced gesture system initialized');
    }
    
    /**
     * Initialize gesture definitions
     */
    initialize() {
        if (this.options.enableCounting) {
            this.initializeCountingGestures();
        }
        
        if (this.options.enableLetters) {
            this.initializeLetterGestures();
        }
        
        if (this.options.enableSymbols) {
            this.initializeSymbolGestures();
        }
        
        if (this.options.enableSequences) {
            this.initializeSequenceGestures();
        }
    }
    
    /**
     * Initialize counting gestures (1-10)
     */
    initializeCountingGestures() {
        const counts = [
            { number: 1, name: 'One', emoji: '☝️', pattern: 'index_up' },
            { number: 2, name: 'Two', emoji: '✌️', pattern: 'peace' },
            { number: 3, name: 'Three', emoji: '🤟', pattern: 'three_fingers' },
            { number: 4, name: 'Four', emoji: '🖖', pattern: 'four_fingers' },
            { number: 5, name: 'Five', emoji: '🖐️', pattern: 'open_palm' },
            { number: 6, name: 'Six', emoji: '🤙', pattern: 'phone_plus_one' },
            { number: 7, name: 'Seven', emoji: '🤘', pattern: 'rock_plus_one' },
            { number: 8, name: 'Eight', emoji: '👌', pattern: 'ok_plus_fingers' },
            { number: 9, name: 'Nine', emoji: '🤏', pattern: 'pinch_plus_fingers' },
            { number: 10, name: 'Ten', emoji: '👐', pattern: 'two_palms' }
        ];
        
        counts.forEach(count => {
            this.countingGestures.set(count.number, {
                ...count,
                type: 'counting',
                action: `count_${count.number}`
            });
        });
        
        console.log(`[AdvancedGestures] Loaded ${counts.length} counting gestures`);
    }
    
    /**
     * Initialize letter gestures (ASL alphabet subset)
     */
    initializeLetterGestures() {
        const letters = [
            // Common easy-to-detect letters
            { letter: 'A', name: 'Letter A', emoji: '🤜', pattern: 'closed_fist_thumb_side' },
            { letter: 'B', name: 'Letter B', emoji: '🖐️', pattern: 'flat_palm_thumb_in' },
            { letter: 'C', name: 'Letter C', emoji: '👌', pattern: 'c_shape' },
            { letter: 'D', name: 'Letter D', emoji: '☝️', pattern: 'd_shape' },
            { letter: 'F', name: 'Letter F', emoji: '👌', pattern: 'f_shape' },
            { letter: 'I', name: 'Letter I', emoji: '🤙', pattern: 'pinky_up' },
            { letter: 'L', name: 'Letter L', emoji: '👍', pattern: 'l_shape' },
            { letter: 'O', name: 'Letter O', emoji: '👌', pattern: 'o_shape' },
            { letter: 'V', name: 'Letter V', emoji: '✌️', pattern: 'v_shape' },
            { letter: 'Y', name: 'Letter Y', emoji: '🤙', pattern: 'y_shape' }
        ];
        
        letters.forEach(letter => {
            this.letterGestures.set(letter.letter, {
                ...letter,
                type: 'letter',
                action: `letter_${letter.letter.toLowerCase()}`
            });
        });
        
        console.log(`[AdvancedGestures] Loaded ${letters.length} letter gestures`);
    }
    
    /**
     * Initialize symbol gestures
     */
    initializeSymbolGestures() {
        const symbols = [
            { symbol: '+', name: 'Plus', emoji: '➕', pattern: 'cross_fingers', action: 'symbol_plus' },
            { symbol: '-', name: 'Minus', emoji: '➖', pattern: 'flat_palm', action: 'symbol_minus' },
            { symbol: '=', name: 'Equals', emoji: '🟰', pattern: 'two_flat_palms', action: 'symbol_equals' },
            { symbol: '✓', name: 'Checkmark', emoji: '✅', pattern: 'thumb_up', action: 'symbol_check' },
            { symbol: '✗', name: 'X Mark', emoji: '❌', pattern: 'crossed_arms', action: 'symbol_x' },
            { symbol: '?', name: 'Question', emoji: '❓', pattern: 'shrug', action: 'symbol_question' },
            { symbol: '!', name: 'Exclamation', emoji: '❗', pattern: 'point_up', action: 'symbol_exclaim' },
            { symbol: '♥', name: 'Heart', emoji: '❤️', pattern: 'heart_hands', action: 'symbol_heart' }
        ];
        
        symbols.forEach(symbol => {
            this.symbolGestures.set(symbol.symbol, {
                ...symbol,
                type: 'symbol'
            });
        });
        
        console.log(`[AdvancedGestures] Loaded ${symbols.length} symbol gestures`);
    }
    
    /**
     * Initialize gesture sequences
     */
    initializeSequenceGestures() {
        const sequences = [
            {
                name: 'Secret Handshake',
                sequence: ['wave', 'fist', 'peace'],
                action: 'unlock_secret',
                description: 'Wave → Fist → Peace'
            },
            {
                name: 'Power Up',
                sequence: ['fist', 'fist', 'open_palm'],
                action: 'power_up',
                description: 'Fist → Fist → Open Palm'
            },
            {
                name: 'Emergency',
                sequence: ['wave', 'wave', 'wave'],
                action: 'emergency_call',
                description: 'Wave 3 times'
            },
            {
                name: 'Screenshot Sequence',
                sequence: ['peace', 'ok'],
                action: 'screenshot_annotate',
                description: 'Peace → OK (Screenshot & Annotate)'
            },
            {
                name: 'Quick Save',
                sequence: ['thumb_up', 'fist'],
                action: 'quick_save',
                description: 'Thumbs Up → Fist'
            }
        ];
        
        sequences.forEach(seq => {
            this.sequenceGestures.set(seq.name, {
                ...seq,
                type: 'sequence'
            });
        });
        
        console.log(`[AdvancedGestures] Loaded ${sequences.length} gesture sequences`);
    }
    
    /**
     * Process detected gesture
     */
    processGesture(gestureType, confidence = 1.0) {
        // Check for counting gesture
        if (this.options.enableCounting) {
            const countMatch = this.detectCounting(gestureType);
            if (countMatch) {
                this.triggerGesture('counting', countMatch, confidence);
                return countMatch;
            }
        }
        
        // Check for letter gesture
        if (this.options.enableLetters) {
            const letterMatch = this.detectLetter(gestureType);
            if (letterMatch) {
                this.triggerGesture('letter', letterMatch, confidence);
                return letterMatch;
            }
        }
        
        // Check for symbol gesture
        if (this.options.enableSymbols) {
            const symbolMatch = this.detectSymbol(gestureType);
            if (symbolMatch) {
                this.triggerGesture('symbol', symbolMatch, confidence);
                return symbolMatch;
            }
        }
        
        // Add to sequence
        if (this.options.enableSequences) {
            this.addToSequence(gestureType);
        }
        
        return null;
    }
    
    /**
     * Detect counting gesture
     */
    detectCounting(gestureType) {
        for (const [number, gesture] of this.countingGestures) {
            if (gesture.pattern === gestureType || gesture.emoji === gestureType) {
                return gesture;
            }
        }
        return null;
    }
    
    /**
     * Detect letter gesture
     */
    detectLetter(gestureType) {
        for (const [letter, gesture] of this.letterGestures) {
            if (gesture.pattern === gestureType) {
                return gesture;
            }
        }
        return null;
    }
    
    /**
     * Detect symbol gesture
     */
    detectSymbol(gestureType) {
        for (const [symbol, gesture] of this.symbolGestures) {
            if (gesture.pattern === gestureType || gesture.action === gestureType) {
                return gesture;
            }
        }
        return null;
    }
    
    /**
     * Add gesture to sequence
     */
    addToSequence(gestureType) {
        // Add to current sequence
        this.currentSequence.push(gestureType);
        
        // Clear existing timer
        if (this.sequenceTimer) {
            clearTimeout(this.sequenceTimer);
        }
        
        // Check for sequence match
        const match = this.checkSequenceMatch();
        if (match) {
            this.triggerGesture('sequence', match, 1.0);
            this.currentSequence = [];
            return;
        }
        
        // Set timeout to clear sequence
        this.sequenceTimer = setTimeout(() => {
            this.currentSequence = [];
        }, this.options.sequenceTimeout);
    }
    
    /**
     * Check if current sequence matches any defined sequence
     */
    checkSequenceMatch() {
        for (const [name, gesture] of this.sequenceGestures) {
            if (this.sequencesMatch(this.currentSequence, gesture.sequence)) {
                return gesture;
            }
        }
        return null;
    }
    
    /**
     * Compare two sequences
     */
    sequencesMatch(seq1, seq2) {
        if (seq1.length !== seq2.length) return false;
        
        for (let i = 0; i < seq1.length; i++) {
            if (seq1[i] !== seq2[i]) return false;
        }
        
        return true;
    }
    
    /**
     * Trigger gesture callback
     */
    triggerGesture(type, gesture, confidence) {
        console.log(`[AdvancedGestures] ${type}: ${gesture.name} (${(confidence * 100).toFixed(0)}%)`);
        
        // Show visual feedback
        this.showFeedback(gesture);
        
        // Execute callbacks
        const callbacks = this.callbacks.get(type) || [];
        callbacks.forEach(callback => {
            try {
                callback({ gesture, confidence, type });
            } catch (error) {
                console.error('[AdvancedGestures] Callback error:', error);
            }
        });
        
        // Emit global event
        if (window.AIOS?.externalIntegrations) {
            window.AIOS.externalIntegrations.emit('advanced_gesture', {
                type,
                gesture: gesture.name,
                action: gesture.action,
                confidence
            });
        }
    }
    
    /**
     * Show visual feedback
     */
    showFeedback(gesture) {
        const feedback = document.createElement('div');
        feedback.className = 'advanced-gesture-feedback';
        feedback.innerHTML = `
            <div class="gesture-icon">${gesture.emoji}</div>
            <div class="gesture-name">${gesture.name}</div>
            <div class="gesture-type">${gesture.type.toUpperCase()}</div>
        `;
        
        document.body.appendChild(feedback);
        
        setTimeout(() => {
            feedback.classList.add('fade-out');
            setTimeout(() => feedback.remove(), 300);
        }, 1500);
    }
    
    /**
     * Register callback for gesture type
     */
    on(type, callback) {
        if (!this.callbacks.has(type)) {
            this.callbacks.set(type, []);
        }
        this.callbacks.get(type).push(callback);
    }
    
    /**
     * Create custom gesture
     */
    createCustomGesture(config) {
        const gesture = {
            name: config.name,
            emoji: config.emoji || '🖐️',
            pattern: config.pattern,
            action: config.action || `custom_${config.name.toLowerCase().replace(/\s+/g, '_')}`,
            type: config.type || 'custom',
            description: config.description || ''
        };
        
        // Add to appropriate collection
        switch (config.type) {
            case 'counting':
                this.countingGestures.set(config.value, gesture);
                break;
            case 'letter':
                this.letterGestures.set(config.letter, gesture);
                break;
            case 'symbol':
                this.symbolGestures.set(config.symbol, gesture);
                break;
            case 'sequence':
                this.sequenceGestures.set(config.name, gesture);
                break;
        }
        
        return {
            success: true,
            gesture
        };
    }
    
    /**
     * Get all gestures by type
     */
    list(type = null) {
        const gestures = [];
        
        if (!type || type === 'counting') {
            this.countingGestures.forEach(g => gestures.push(g));
        }
        
        if (!type || type === 'letter') {
            this.letterGestures.forEach(g => gestures.push(g));
        }
        
        if (!type || type === 'symbol') {
            this.symbolGestures.forEach(g => gestures.push(g));
        }
        
        if (!type || type === 'sequence') {
            this.sequenceGestures.forEach(g => gestures.push(g));
        }
        
        return gestures;
    }
    
    /**
     * Get statistics
     */
    getStatistics() {
        return {
            counting: this.countingGestures.size,
            letters: this.letterGestures.size,
            symbols: this.symbolGestures.size,
            sequences: this.sequenceGestures.size,
            total: this.countingGestures.size + this.letterGestures.size + 
                   this.symbolGestures.size + this.sequenceGestures.size
        };
    }
}

// Add CSS for advanced gesture feedback
const style = document.createElement('style');
style.textContent = `
    .advanced-gesture-feedback {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(0, 0, 0, 0.95);
        border: 3px solid #00ffff;
        border-radius: 20px;
        padding: 40px 60px;
        z-index: 10002;
        text-align: center;
        animation: advanced-gesture-appear 0.3s ease-out;
        pointer-events: none;
    }
    
    .advanced-gesture-feedback.fade-out {
        animation: advanced-gesture-disappear 0.3s ease-out forwards;
    }
    
    .advanced-gesture-feedback .gesture-icon {
        font-size: 80px;
        margin-bottom: 15px;
        animation: advanced-gesture-bounce 0.6s ease-out;
    }
    
    .advanced-gesture-feedback .gesture-name {
        font-family: 'Courier New', monospace;
        font-size: 24px;
        color: #00ffff;
        font-weight: bold;
        letter-spacing: 2px;
        margin-bottom: 8px;
    }
    
    .advanced-gesture-feedback .gesture-type {
        font-family: 'Courier New', monospace;
        font-size: 12px;
        color: #00ff9d;
        letter-spacing: 3px;
        opacity: 0.7;
    }
    
    @keyframes advanced-gesture-appear {
        from {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.5);
        }
        to {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
        }
    }
    
    @keyframes advanced-gesture-disappear {
        from {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
        }
        to {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.8);
        }
    }
    
    @keyframes advanced-gesture-bounce {
        0%, 100% {
            transform: scale(1);
        }
        25% {
            transform: scale(1.3);
        }
        50% {
            transform: scale(0.9);
        }
        75% {
            transform: scale(1.1);
        }
    }
`;
document.head.appendChild(style);

export default AdvancedGestures;
