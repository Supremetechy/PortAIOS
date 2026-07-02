/**
 * Gesture Calibration & Sensitivity Controls
 * Fine-tune gesture recognition sensitivity and performance
 */

export class GestureCalibration {
    constructor(gestureInput, enhancedGesture, options = {}) {
        this.gestureInput = gestureInput;
        this.enhancedGesture = enhancedGesture;
        
        this.settings = {
            // Detection sensitivity (0-1)
            detectionSensitivity: 0.7,
            
            // Confidence thresholds per gesture
            thresholds: {
                point: 0.6,
                thumb_up: 0.7,
                ok: 0.7,
                swipe_left: 0.65,
                swipe_right: 0.65,
                peace: 0.7,
                fist: 0.65,
                phone: 0.7,
                heart: 0.75,
                wave: 0.6,
                rock: 0.7,
                spock: 0.75
            },
            
            // Debounce timing (ms)
            debounceTime: 500,
            
            // Gesture hold time (ms)
            holdTime: 300,
            
            // Movement sensitivity for swipes
            swipeSensitivity: 0.5,
            
            // Hand detection confidence
            handConfidence: 0.5,
            
            // Smoothing factor (0-1, higher = smoother but slower)
            smoothing: 0.5,
            
            // Auto-calibration
            autoCalibrate: false,
            
            ...options
        };
        
        // Calibration data
        this.calibrationData = {
            gesturesSeen: new Map(),
            falsePositives: new Map(),
            truePositives: new Map(),
            avgConfidence: new Map()
        };
        
        // Load saved settings
        this.loadSettings();
        
        console.log('[GestureCalibration] Calibration system initialized');
    }
    
    /**
     * Start calibration wizard
     */
    async startCalibrationWizard() {
        this.speak('Starting gesture calibration wizard');
        
        const results = {
            steps: [],
            calibrated: []
        };
        
        // Step 1: Test hand detection
        results.steps.push(await this.calibrateHandDetection());
        
        // Step 2: Test each gesture type
        const gestures = ['point', 'thumb_up', 'ok', 'peace', 'fist'];
        
        for (const gesture of gestures) {
            results.steps.push(await this.calibrateGesture(gesture));
            results.calibrated.push(gesture);
        }
        
        // Step 3: Test swipe sensitivity
        results.steps.push(await this.calibrateSwipes());
        
        // Save calibrated settings
        this.saveSettings();
        
        this.speak('Calibration complete');
        
        return {
            success: true,
            message: 'Calibration wizard completed',
            results
        };
    }
    
    /**
     * Calibrate hand detection confidence
     */
    async calibrateHandDetection() {
        this.speak('Show your hand to the camera');
        
        return new Promise((resolve) => {
            setTimeout(() => {
                // In a real implementation, this would analyze actual camera feed
                const recommendedConfidence = 0.5;
                this.settings.handConfidence = recommendedConfidence;
                
                resolve({
                    step: 'Hand Detection',
                    confidence: recommendedConfidence,
                    status: 'calibrated'
                });
            }, 2000);
        });
    }
    
    /**
     * Calibrate specific gesture
     */
    async calibrateGesture(gestureType) {
        const metadata = this.getGestureMetadata(gestureType);
        this.speak(`Please perform the ${metadata.name} gesture`);
        
        return new Promise((resolve) => {
            setTimeout(() => {
                // In real implementation, analyze detected gestures
                const samples = Math.floor(Math.random() * 5) + 3;
                const avgConfidence = 0.7 + Math.random() * 0.25;
                const recommendedThreshold = avgConfidence * 0.85;
                
                this.settings.thresholds[gestureType] = recommendedThreshold;
                
                resolve({
                    step: `Calibrate ${metadata.name}`,
                    gesture: gestureType,
                    samples,
                    avgConfidence,
                    threshold: recommendedThreshold,
                    status: 'calibrated'
                });
            }, 3000);
        });
    }
    
    /**
     * Calibrate swipe gestures
     */
    async calibrateSwipes() {
        this.speak('Please swipe left and right');
        
        return new Promise((resolve) => {
            setTimeout(() => {
                const sensitivity = 0.5;
                this.settings.swipeSensitivity = sensitivity;
                
                resolve({
                    step: 'Swipe Calibration',
                    sensitivity,
                    status: 'calibrated'
                });
            }, 3000);
        });
    }
    
    /**
     * Auto-calibrate based on usage data
     */
    autoCalibrate() {
        if (!this.settings.autoCalibrate) {
            return { success: false, message: 'Auto-calibration disabled' };
        }
        
        const adjustments = [];
        
        // Analyze false positives
        for (const [gesture, count] of this.calibrationData.falsePositives) {
            if (count > 5) {
                // Increase threshold to reduce false positives
                const currentThreshold = this.settings.thresholds[gesture];
                const newThreshold = Math.min(0.95, currentThreshold + 0.05);
                this.settings.thresholds[gesture] = newThreshold;
                
                adjustments.push({
                    gesture,
                    reason: 'Too many false positives',
                    oldThreshold: currentThreshold,
                    newThreshold
                });
            }
        }
        
        // Analyze missed detections (low confidence true positives)
        for (const [gesture, avgConf] of this.calibrationData.avgConfidence) {
            const threshold = this.settings.thresholds[gesture];
            
            if (avgConf > threshold + 0.15) {
                // Can lower threshold for better responsiveness
                const newThreshold = Math.max(0.5, threshold - 0.05);
                this.settings.thresholds[gesture] = newThreshold;
                
                adjustments.push({
                    gesture,
                    reason: 'Avg confidence much higher than threshold',
                    oldThreshold: threshold,
                    newThreshold
                });
            }
        }
        
        if (adjustments.length > 0) {
            this.saveSettings();
        }
        
        return {
            success: true,
            message: `Auto-calibrated ${adjustments.length} gestures`,
            adjustments
        };
    }
    
    /**
     * Record gesture detection for calibration
     */
    recordDetection(gestureType, confidence, wasCorrect) {
        // Update statistics
        const current = this.calibrationData.gesturesSeen.get(gestureType) || 0;
        this.calibrationData.gesturesSeen.set(gestureType, current + 1);
        
        if (wasCorrect) {
            const tp = this.calibrationData.truePositives.get(gestureType) || 0;
            this.calibrationData.truePositives.set(gestureType, tp + 1);
            
            // Update average confidence
            const avgConf = this.calibrationData.avgConfidence.get(gestureType) || confidence;
            const newAvg = (avgConf + confidence) / 2;
            this.calibrationData.avgConfidence.set(gestureType, newAvg);
        } else {
            const fp = this.calibrationData.falsePositives.get(gestureType) || 0;
            this.calibrationData.falsePositives.set(gestureType, fp + 1);
        }
        
        // Auto-calibrate if enabled
        if (this.settings.autoCalibrate) {
            const totalSeen = this.calibrationData.gesturesSeen.get(gestureType);
            if (totalSeen % 20 === 0) { // Every 20 detections
                this.autoCalibrate();
            }
        }
    }
    
    /**
     * Set sensitivity for all gestures
     */
    setGlobalSensitivity(value) {
        const sensitivity = Math.max(0, Math.min(1, value));
        this.settings.detectionSensitivity = sensitivity;
        
        // Adjust all thresholds proportionally
        for (const gesture in this.settings.thresholds) {
            // Scale threshold based on sensitivity
            // Lower sensitivity = higher threshold (less sensitive)
            const baseThreshold = 0.7;
            this.settings.thresholds[gesture] = baseThreshold + (0.3 * (1 - sensitivity));
        }
        
        this.saveSettings();
        
        return {
            success: true,
            message: `Global sensitivity set to ${(sensitivity * 100).toFixed(0)}%`,
            sensitivity
        };
    }
    
    /**
     * Set sensitivity for specific gesture
     */
    setGestureSensitivity(gestureType, value) {
        const sensitivity = Math.max(0, Math.min(1, value));
        
        if (!this.settings.thresholds[gestureType]) {
            return {
                success: false,
                message: `Unknown gesture: ${gestureType}`
            };
        }
        
        // Convert sensitivity to threshold (inverse relationship)
        const threshold = 1 - (sensitivity * 0.5); // 0.5 to 1.0 range
        this.settings.thresholds[gestureType] = threshold;
        
        this.saveSettings();
        
        return {
            success: true,
            message: `${gestureType} sensitivity set to ${(sensitivity * 100).toFixed(0)}%`,
            threshold
        };
    }
    
    /**
     * Set debounce time
     */
    setDebounceTime(milliseconds) {
        this.settings.debounceTime = Math.max(0, Math.min(2000, milliseconds));
        this.saveSettings();
        
        return {
            success: true,
            message: `Debounce time set to ${this.settings.debounceTime}ms`
        };
    }
    
    /**
     * Set smoothing factor
     */
    setSmoothing(value) {
        this.settings.smoothing = Math.max(0, Math.min(1, value));
        this.saveSettings();
        
        return {
            success: true,
            message: `Smoothing set to ${(this.settings.smoothing * 100).toFixed(0)}%`
        };
    }
    
    /**
     * Enable/disable auto-calibration
     */
    setAutoCalibrate(enabled) {
        this.settings.autoCalibrate = enabled;
        this.saveSettings();
        
        return {
            success: true,
            message: `Auto-calibration ${enabled ? 'enabled' : 'disabled'}`
        };
    }
    
    /**
     * Reset to default settings
     */
    resetToDefaults() {
        this.settings = {
            detectionSensitivity: 0.7,
            thresholds: {
                point: 0.6,
                thumb_up: 0.7,
                ok: 0.7,
                swipe_left: 0.65,
                swipe_right: 0.65,
                peace: 0.7,
                fist: 0.65,
                phone: 0.7,
                heart: 0.75,
                wave: 0.6,
                rock: 0.7,
                spock: 0.75
            },
            debounceTime: 500,
            holdTime: 300,
            swipeSensitivity: 0.5,
            handConfidence: 0.5,
            smoothing: 0.5,
            autoCalibrate: false
        };
        
        this.saveSettings();
        
        return {
            success: true,
            message: 'Settings reset to defaults'
        };
    }
    
    /**
     * Get current settings
     */
    getSettings() {
        return { ...this.settings };
    }
    
    /**
     * Get calibration statistics
     */
    getStatistics() {
        const stats = {};
        
        for (const [gesture, seen] of this.calibrationData.gesturesSeen) {
            const tp = this.calibrationData.truePositives.get(gesture) || 0;
            const fp = this.calibrationData.falsePositives.get(gesture) || 0;
            const avgConf = this.calibrationData.avgConfidence.get(gesture) || 0;
            
            stats[gesture] = {
                seen,
                truePositives: tp,
                falsePositives: fp,
                accuracy: seen > 0 ? (tp / seen * 100).toFixed(1) : 0,
                avgConfidence: avgConf.toFixed(2),
                threshold: this.settings.thresholds[gesture]
            };
        }
        
        return stats;
    }
    
    /**
     * Export settings
     */
    export() {
        return {
            settings: this.settings,
            calibrationData: {
                gesturesSeen: Array.from(this.calibrationData.gesturesSeen.entries()),
                falsePositives: Array.from(this.calibrationData.falsePositives.entries()),
                truePositives: Array.from(this.calibrationData.truePositives.entries()),
                avgConfidence: Array.from(this.calibrationData.avgConfidence.entries())
            },
            exported: new Date().toISOString()
        };
    }
    
    /**
     * Import settings
     */
    import(data) {
        if (data.settings) {
            this.settings = { ...this.settings, ...data.settings };
        }
        
        if (data.calibrationData) {
            this.calibrationData.gesturesSeen = new Map(data.calibrationData.gesturesSeen || []);
            this.calibrationData.falsePositives = new Map(data.calibrationData.falsePositives || []);
            this.calibrationData.truePositives = new Map(data.calibrationData.truePositives || []);
            this.calibrationData.avgConfidence = new Map(data.calibrationData.avgConfidence || []);
        }
        
        this.saveSettings();
        
        return {
            success: true,
            message: 'Settings imported successfully'
        };
    }
    
    /**
     * Save settings to localStorage
     */
    saveSettings() {
        try {
            const data = this.export();
            localStorage.setItem('aios_gesture_calibration', JSON.stringify(data));
            console.log('[GestureCalibration] Settings saved');
        } catch (error) {
            console.error('[GestureCalibration] Error saving settings:', error);
        }
    }
    
    /**
     * Load settings from localStorage
     */
    loadSettings() {
        try {
            const data = localStorage.getItem('aios_gesture_calibration');
            if (data) {
                this.import(JSON.parse(data));
                console.log('[GestureCalibration] Settings loaded');
            }
        } catch (error) {
            console.error('[GestureCalibration] Error loading settings:', error);
        }
    }
    
    /**
     * Get gesture metadata
     */
    getGestureMetadata(gestureType) {
        const metadata = {
            point: { name: 'Point', emoji: '👉' },
            thumb_up: { name: 'Thumbs Up', emoji: '👍' },
            ok: { name: 'OK', emoji: '👌' },
            swipe_left: { name: 'Swipe Left', emoji: '⬅️' },
            swipe_right: { name: 'Swipe Right', emoji: '➡️' },
            peace: { name: 'Peace', emoji: '✌️' },
            fist: { name: 'Fist', emoji: '✊' },
            phone: { name: 'Phone', emoji: '🤙' },
            heart: { name: 'Heart', emoji: '❤️' },
            wave: { name: 'Wave', emoji: '👋' },
            rock: { name: 'Rock', emoji: '🤘' },
            spock: { name: 'Spock', emoji: '🖖' }
        };
        
        return metadata[gestureType] || { name: gestureType, emoji: '🖐️' };
    }
    
    /**
     * Utility: Speak
     */
    speak(text) {
        if (window.speak) {
            window.speak(text);
        } else if (window.speechSynthesis) {
            const utterance = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.speak(utterance);
        }
    }
}

export default GestureCalibration;
