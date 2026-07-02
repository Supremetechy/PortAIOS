/**
 * PortAIOS Gesture Input System
 * Frontend camera capture, visual feedback, and gesture integration
 */

class GestureInput {
    constructor() {
        this.enabled = false;
        this.cameraActive = false;
        this.stream = null;
        this.videoElement = null;
        this.canvasElement = null;
        this.ctx = null;
        this.overlayElement = null;
        
        // Gesture state
        this.currentGestures = [];
        this.lastGestureTime = 0;
        this.gestureCallbacks = new Map();
        
        // Visual feedback
        this.showFeedback = true;
        this.showLandmarks = true;
        this.feedbackTimeout = null;
        
        // Privacy controls
        this.privacyMode = false;
        this.cameraIndicator = null;
        
        // Performance
        this.fps = 0;
        this.frameCount = 0;
        this.lastFpsUpdate = Date.now();
        
        // Initialize UI
        this.initializeUI();
        
        // Poll for gesture updates if backend is running
        this.startPolling();
    }
    
    initializeUI() {
        // Create gesture UI container
        const container = document.createElement('div');
        container.id = 'gesture-input-container';
        container.className = 'gesture-input-container';
        container.innerHTML = `
            <div class="gesture-camera-view" style="display: none;">
                <video id="gesture-video" autoplay playsinline></video>
                <canvas id="gesture-canvas"></canvas>
                <div id="gesture-overlay" class="gesture-overlay"></div>
                
                <!-- Camera indicator (privacy LED) -->
                <div id="camera-indicator" class="camera-indicator">
                    <span class="indicator-dot"></span>
                    Camera Active
                </div>
                
                <!-- FPS counter -->
                <div id="gesture-fps" class="gesture-fps">0 FPS</div>
                
                <!-- Gesture feedback panel -->
                <div id="gesture-feedback" class="gesture-feedback">
                    <div class="feedback-title">Detected Gestures</div>
                    <div id="gesture-list" class="gesture-list"></div>
                </div>
                
                <!-- Control buttons -->
                <div class="gesture-controls">
                    <button id="toggle-gesture-camera" class="btn-gesture" title="Toggle Camera">
                        📷 Toggle Camera
                    </button>
                    <button id="toggle-landmarks" class="btn-gesture" title="Toggle Landmarks">
                        ✋ Landmarks
                    </button>
                    <button id="toggle-feedback" class="btn-gesture" title="Toggle Feedback">
                        💬 Feedback
                    </button>
                    <button id="privacy-mode" class="btn-gesture" title="Privacy Mode">
                        🔒 Privacy
                    </button>
                </div>
            </div>
            
            <!-- Gesture activation button -->
            <button id="activate-gestures" class="btn-activate-gestures">
                ✋ Enable Gesture Control
            </button>
        `;
        
        document.body.appendChild(container);
        
        // Get elements
        this.videoElement = document.getElementById('gesture-video');
        this.canvasElement = document.getElementById('gesture-canvas');
        this.overlayElement = document.getElementById('gesture-overlay');
        this.cameraIndicator = document.getElementById('camera-indicator');
        
        if (this.canvasElement) {
            this.ctx = this.canvasElement.getContext('2d');
        }
        
        // Setup event listeners
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Activation button
        const activateBtn = document.getElementById('activate-gestures');
        if (activateBtn) {
            activateBtn.addEventListener('click', () => this.toggleGestureSystem());
        }
        
        // Camera toggle
        const cameraBtn = document.getElementById('toggle-gesture-camera');
        if (cameraBtn) {
            cameraBtn.addEventListener('click', () => this.toggleCamera());
        }
        
        // Landmarks toggle
        const landmarksBtn = document.getElementById('toggle-landmarks');
        if (landmarksBtn) {
            landmarksBtn.addEventListener('click', () => {
                this.showLandmarks = !this.showLandmarks;
                landmarksBtn.classList.toggle('active', this.showLandmarks);
            });
        }
        
        // Feedback toggle
        const feedbackBtn = document.getElementById('toggle-feedback');
        if (feedbackBtn) {
            feedbackBtn.addEventListener('click', () => {
                this.showFeedback = !this.showFeedback;
                feedbackBtn.classList.toggle('active', this.showFeedback);
                const feedbackPanel = document.getElementById('gesture-feedback');
                if (feedbackPanel) {
                    feedbackPanel.style.display = this.showFeedback ? 'block' : 'none';
                }
            });
        }
        
        // Privacy mode
        const privacyBtn = document.getElementById('privacy-mode');
        if (privacyBtn) {
            privacyBtn.addEventListener('click', () => this.togglePrivacyMode());
        }
    }
    
    async toggleGestureSystem() {
        if (!this.enabled) {
            await this.enable();
        } else {
            await this.disable();
        }
    }
    
    async enable() {
        try {
            console.log('[GestureInput] Enabling gesture system...');
            
            // Show camera view
            const cameraView = document.querySelector('.gesture-camera-view');
            if (cameraView) {
                cameraView.style.display = 'block';
            }
            
            // Hide activation button
            const activateBtn = document.getElementById('activate-gestures');
            if (activateBtn) {
                activateBtn.style.display = 'none';
            }
            
            // Start camera
            await this.startCamera();
            
            // Start backend gesture processing if available
            if (typeof eel !== 'undefined' && eel.start_gesture_camera) {
                const result = await eel.start_gesture_camera(0)();
                console.log('[GestureInput] Backend started:', result);
            }
            
            this.enabled = true;
            this.showToast('Gesture control enabled', 'success');
            
        } catch (error) {
            console.error('[GestureInput] Failed to enable:', error);
            this.showToast('Failed to enable gesture control', 'error');
        }
    }
    
    async disable() {
        try {
            console.log('[GestureInput] Disabling gesture system...');
            
            // Stop camera
            this.stopCamera();
            
            // Stop backend
            if (typeof eel !== 'undefined' && eel.stop_gesture_camera) {
                await eel.stop_gesture_camera()();
            }
            
            // Hide camera view
            const cameraView = document.querySelector('.gesture-camera-view');
            if (cameraView) {
                cameraView.style.display = 'none';
            }
            
            // Show activation button
            const activateBtn = document.getElementById('activate-gestures');
            if (activateBtn) {
                activateBtn.style.display = 'block';
            }
            
            this.enabled = false;
            this.showToast('Gesture control disabled', 'info');
            
        } catch (error) {
            console.error('[GestureInput] Failed to disable:', error);
        }
    }
    
    async startCamera() {
        try {
            // Request camera access
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    frameRate: { ideal: 30 }
                }
            });
            
            // Attach to video element
            if (this.videoElement) {
                this.videoElement.srcObject = this.stream;
                await this.videoElement.play();
                
                // Setup canvas size
                this.canvasElement.width = this.videoElement.videoWidth || 640;
                this.canvasElement.height = this.videoElement.videoHeight || 480;
            }
            
            this.cameraActive = true;
            
            // Show camera indicator
            if (this.cameraIndicator) {
                this.cameraIndicator.style.display = 'flex';
            }
            
            console.log('[GestureInput] Camera started');
            
        } catch (error) {
            console.error('[GestureInput] Camera error:', error);
            this.showToast('Camera access denied. Please allow camera permissions.', 'error');
            throw error;
        }
    }
    
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
        
        this.cameraActive = false;
        
        // Hide camera indicator
        if (this.cameraIndicator) {
            this.cameraIndicator.style.display = 'none';
        }
        
        console.log('[GestureInput] Camera stopped');
    }
    
    toggleCamera() {
        if (this.cameraActive) {
            this.stopCamera();
        } else {
            this.startCamera();
        }
    }
    
    togglePrivacyMode() {
        this.privacyMode = !this.privacyMode;
        
        const privacyBtn = document.getElementById('privacy-mode');
        if (privacyBtn) {
            privacyBtn.classList.toggle('active', this.privacyMode);
        }
        
        if (this.privacyMode) {
            // Blur video feed
            if (this.videoElement) {
                this.videoElement.style.filter = 'blur(20px)';
            }
            this.showToast('Privacy mode ON - Video feed blurred', 'info');
        } else {
            if (this.videoElement) {
                this.videoElement.style.filter = 'none';
            }
            this.showToast('Privacy mode OFF', 'info');
        }
    }
    
    startPolling() {
        // Poll for gesture updates from backend
        setInterval(async () => {
            if (!this.enabled || typeof eel === 'undefined') return;
            
            try {
                if (eel.get_gesture_status) {
                    const status = await eel.get_gesture_status()();
                    this.updateStatus(status);
                }
            } catch (error) {
                // Backend not available, silent fail
            }
        }, 100); // 10 times per second
    }
    
    updateStatus(status) {
        if (!status) return;
        
        // Update FPS
        this.fps = status.fps || 0;
        const fpsElement = document.getElementById('gesture-fps');
        if (fpsElement) {
            fpsElement.textContent = `${this.fps} FPS`;
        }
        
        // Update gestures
        if (status.current_gestures && status.current_gestures.length > 0) {
            this.currentGestures = status.current_gestures;
            this.displayGestures(status.current_gestures);
            
            // Trigger callbacks
            status.current_gestures.forEach(gesture => {
                this.triggerGestureCallback(gesture);
            });
        }
    }
    
    displayGestures(gestures) {
        if (!this.showFeedback) return;
        
        const listElement = document.getElementById('gesture-list');
        if (!listElement) return;
        
        // Clear old gestures
        listElement.innerHTML = '';
        
        // Display current gestures
        gestures.forEach(gesture => {
            const item = document.createElement('div');
            item.className = 'gesture-item';
            
            const emoji = this.getGestureEmoji(gesture.type);
            const confidence = Math.round(gesture.confidence * 100);
            
            item.innerHTML = `
                <span class="gesture-emoji">${emoji}</span>
                <span class="gesture-name">${this.formatGestureName(gesture.type)}</span>
                <span class="gesture-confidence">${confidence}%</span>
                ${gesture.hand ? `<span class="gesture-hand">${gesture.hand}</span>` : ''}
            `;
            
            listElement.appendChild(item);
        });
        
        // Auto-hide after 2 seconds
        clearTimeout(this.feedbackTimeout);
        this.feedbackTimeout = setTimeout(() => {
            listElement.innerHTML = '<div class="no-gestures">No gestures detected</div>';
        }, 2000);
    }
    
    getGestureEmoji(gestureType) {
        const emojiMap = {
            'thumbs_up': '👍',
            'thumbs_down': '👎',
            'peace_sign': '✌️',
            'ok_sign': '👌',
            'pointing': '👉',
            'fist': '✊',
            'open_palm': '🖐️',
            'pinch': '🤏',
            'wave': '👋',
            'swipe_left': '⬅️',
            'swipe_right': '➡️',
            'swipe_up': '⬆️',
            'swipe_down': '⬇️',
            'smile': '😊',
            'frown': '😔',
            'head_nod': '🙂',
            'head_shake': '🙅',
            'look_left': '👀⬅️',
            'look_right': '👀➡️',
            'blink': '😉',
        };
        
        return emojiMap[gestureType] || '✋';
    }
    
    formatGestureName(gestureType) {
        return gestureType
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
    
    registerGestureCallback(gestureType, callback) {
        if (!this.gestureCallbacks.has(gestureType)) {
            this.gestureCallbacks.set(gestureType, []);
        }
        this.gestureCallbacks.get(gestureType).push(callback);
        console.log(`[GestureInput] Registered callback for: ${gestureType}`);
    }
    
    triggerGestureCallback(gesture) {
        const callbacks = this.gestureCallbacks.get(gesture.type);
        if (callbacks) {
            callbacks.forEach(callback => {
                try {
                    callback(gesture);
                } catch (error) {
                    console.error('[GestureInput] Callback error:', error);
                }
            });
        }
    }
    
    showToast(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `gesture-toast gesture-toast-${type}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Remove after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

// CSS Styles
const gestureStyles = document.createElement('style');
gestureStyles.textContent = `
    .gesture-input-container {
        position: fixed;
        z-index: 10000;
    }
    
    .gesture-camera-view {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 400px;
        background: rgba(0, 0, 0, 0.9);
        border: 2px solid rgba(0, 255, 255, 0.5);
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0, 255, 255, 0.3);
    }
    
    #gesture-video {
        width: 100%;
        height: auto;
        display: block;
        transform: scaleX(-1); /* Mirror effect */
    }
    
    #gesture-canvas {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: auto;
        pointer-events: none;
        transform: scaleX(-1);
    }
    
    .gesture-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        pointer-events: none;
    }
    
    .camera-indicator {
        position: absolute;
        top: 10px;
        left: 10px;
        display: none;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        background: rgba(255, 0, 0, 0.8);
        color: white;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        animation: pulse 2s infinite;
    }
    
    .indicator-dot {
        width: 8px;
        height: 8px;
        background: white;
        border-radius: 50%;
        animation: blink 1s infinite;
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.3; }
    }
    
    .gesture-fps {
        position: absolute;
        top: 10px;
        right: 10px;
        padding: 4px 8px;
        background: rgba(0, 0, 0, 0.7);
        color: #0ff;
        border-radius: 4px;
        font-size: 11px;
        font-family: monospace;
    }
    
    .gesture-feedback {
        position: absolute;
        bottom: 60px;
        left: 10px;
        right: 10px;
        max-height: 150px;
        overflow-y: auto;
        background: rgba(0, 0, 0, 0.8);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 8px;
        padding: 8px;
    }
    
    .feedback-title {
        font-size: 11px;
        color: #0ff;
        margin-bottom: 6px;
        font-weight: bold;
        text-transform: uppercase;
    }
    
    .gesture-list {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    
    .gesture-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px;
        background: rgba(0, 255, 255, 0.1);
        border-radius: 4px;
        font-size: 12px;
        color: white;
    }
    
    .gesture-emoji {
        font-size: 16px;
    }
    
    .gesture-name {
        flex: 1;
        font-weight: 500;
    }
    
    .gesture-confidence {
        color: #0ff;
        font-size: 11px;
    }
    
    .gesture-hand {
        color: #ff0;
        font-size: 10px;
        text-transform: uppercase;
    }
    
    .no-gestures {
        color: rgba(255, 255, 255, 0.5);
        font-size: 11px;
        text-align: center;
        padding: 8px;
    }
    
    .gesture-controls {
        display: flex;
        gap: 4px;
        padding: 8px;
        background: rgba(0, 0, 0, 0.8);
    }
    
    .btn-gesture {
        flex: 1;
        padding: 8px;
        background: rgba(0, 255, 255, 0.2);
        border: 1px solid rgba(0, 255, 255, 0.5);
        color: #0ff;
        border-radius: 4px;
        cursor: pointer;
        font-size: 11px;
        transition: all 0.2s;
    }
    
    .btn-gesture:hover {
        background: rgba(0, 255, 255, 0.3);
        border-color: #0ff;
    }
    
    .btn-gesture.active {
        background: rgba(0, 255, 255, 0.5);
        border-color: #0ff;
    }
    
    .btn-activate-gestures {
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 24px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s;
        z-index: 9999;
    }
    
    .btn-activate-gestures:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    .gesture-toast {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%) translateY(100px);
        padding: 12px 24px;
        background: rgba(0, 0, 0, 0.9);
        color: white;
        border-radius: 8px;
        font-size: 14px;
        opacity: 0;
        transition: all 0.3s;
        z-index: 10001;
    }
    
    .gesture-toast.show {
        transform: translateX(-50%) translateY(0);
        opacity: 1;
    }
    
    .gesture-toast-success {
        border: 2px solid #0f0;
        box-shadow: 0 4px 15px rgba(0, 255, 0, 0.3);
    }
    
    .gesture-toast-error {
        border: 2px solid #f00;
        box-shadow: 0 4px 15px rgba(255, 0, 0, 0.3);
    }
    
    .gesture-toast-info {
        border: 2px solid #0ff;
        box-shadow: 0 4px 15px rgba(0, 255, 255, 0.3);
    }
`;
document.head.appendChild(gestureStyles);

// Create global instance
window.gestureInput = new GestureInput();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GestureInput;
}
