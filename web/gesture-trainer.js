/**
 * PortAIOS Gesture Training Interface
 * Allows users to record and train custom gestures
 */

class GestureTrainer {
    constructor() {
        this.recording = false;
        this.recordedSamples = [];
        this.currentGestureName = '';
        this.trainingData = new Map();
        this.recognitionModel = null;
        
        // Load saved gestures
        this.loadSavedGestures();
    }
    
    async startRecording(gestureName) {
        if (!gestureName) {
            this.showNotification('Please enter a gesture name', 'error');
            return;
        }
        
        this.recording = true;
        this.currentGestureName = gestureName;
        this.recordedSamples = [];
        
        this.updateUI('recording');
        this.showNotification(`Recording "${gestureName}"... Perform the gesture 5 times`, 'info');
        
        // Start collecting gesture data
        this.startGestureCollection();
    }
    
    startGestureCollection() {
        // Poll for gestures from backend
        const pollInterval = setInterval(async () => {
            if (!this.recording) {
                clearInterval(pollInterval);
                return;
            }
            
            try {
                if (typeof eel !== 'undefined' && eel.get_gesture_status) {
                    const status = await eel.get_gesture_status()();
                    
                    if (status.current_gestures && status.current_gestures.length > 0) {
                        // Record the gesture
                        const gesture = status.current_gestures[0];
                        this.recordedSamples.push({
                            type: gesture.type,
                            confidence: gesture.confidence,
                            hand: gesture.hand,
                            position: gesture.position,
                            timestamp: Date.now()
                        });
                        
                        this.updateProgress(this.recordedSamples.length);
                        
                        // Stop after 5 samples
                        if (this.recordedSamples.length >= 5) {
                            this.stopRecording();
                        }
                    }
                }
            } catch (error) {
                console.error('[GestureTrainer] Collection error:', error);
            }
        }, 200); // Poll every 200ms
    }
    
    stopRecording() {
        this.recording = false;
        
        if (this.recordedSamples.length < 3) {
            this.showNotification('Not enough samples recorded. Please try again.', 'error');
            this.updateUI('idle');
            return;
        }
        
        // Save the recorded gesture
        this.saveGesture(this.currentGestureName, this.recordedSamples);
        
        this.showNotification(`Gesture "${this.currentGestureName}" saved successfully!`, 'success');
        this.updateUI('idle');
        this.refreshGestureList();
    }
    
    saveGesture(name, samples) {
        this.trainingData.set(name, {
            name: name,
            samples: samples,
            created: Date.now(),
            trained: false
        });
        
        // Save to localStorage
        const savedGestures = {};
        this.trainingData.forEach((value, key) => {
            savedGestures[key] = value;
        });
        localStorage.setItem('portaios_custom_gestures', JSON.stringify(savedGestures));
    }
    
    loadSavedGestures() {
        const saved = localStorage.getItem('portaios_custom_gestures');
        if (saved) {
            try {
                const gestures = JSON.parse(saved);
                Object.entries(gestures).forEach(([name, data]) => {
                    this.trainingData.set(name, data);
                });
                console.log(`[GestureTrainer] Loaded ${this.trainingData.size} custom gestures`);
            } catch (error) {
                console.error('[GestureTrainer] Failed to load gestures:', error);
            }
        }
    }
    
    async trainGesture(gestureName) {
        const gestureData = this.trainingData.get(gestureName);
        if (!gestureData) {
            this.showNotification('Gesture not found', 'error');
            return;
        }
        
        this.showNotification(`Training "${gestureName}"...`, 'info');
        
        // Send to backend for training
        try {
            if (typeof eel !== 'undefined' && eel.train_custom_gesture) {
                const result = await eel.train_custom_gesture(gestureName, gestureData.samples)();
                
                if (result.success) {
                    gestureData.trained = true;
                    this.saveGesture(gestureName, gestureData.samples);
                    this.showNotification(`Gesture "${gestureName}" trained successfully!`, 'success');
                    this.refreshGestureList();
                } else {
                    this.showNotification(`Training failed: ${result.error}`, 'error');
                }
            } else {
                // Fallback: mark as trained locally
                gestureData.trained = true;
                this.saveGesture(gestureName, gestureData.samples);
                this.showNotification(`Gesture "${gestureName}" saved (backend not available)`, 'warning');
            }
        } catch (error) {
            console.error('[GestureTrainer] Training error:', error);
            this.showNotification('Training error: ' + error.message, 'error');
        }
    }
    
    deleteGesture(gestureName) {
        if (confirm(`Delete custom gesture "${gestureName}"?`)) {
            this.trainingData.delete(gestureName);
            
            // Update localStorage
            const savedGestures = {};
            this.trainingData.forEach((value, key) => {
                savedGestures[key] = value;
            });
            localStorage.setItem('portaios_custom_gestures', JSON.stringify(savedGestures));
            
            this.showNotification(`Gesture "${gestureName}" deleted`, 'info');
            this.refreshGestureList();
        }
    }
    
    testGesture(gestureName) {
        this.showNotification(`Perform the "${gestureName}" gesture to test...`, 'info');
        
        let testTimeout;
        const testInterval = setInterval(async () => {
            try {
                if (typeof eel !== 'undefined' && eel.get_gesture_status) {
                    const status = await eel.get_gesture_status()();
                    
                    if (status.current_gestures && status.current_gestures.length > 0) {
                        const gesture = status.current_gestures[0];
                        
                        // Check if it matches our custom gesture
                        // (In a real implementation, this would use the trained model)
                        this.showNotification(`Detected: ${gesture.type} (${Math.round(gesture.confidence * 100)}%)`, 'success');
                        
                        clearInterval(testInterval);
                        clearTimeout(testTimeout);
                    }
                }
            } catch (error) {
                console.error('[GestureTrainer] Test error:', error);
            }
        }, 200);
        
        // Timeout after 10 seconds
        testTimeout = setTimeout(() => {
            clearInterval(testInterval);
            this.showNotification('Test timeout - no gesture detected', 'warning');
        }, 10000);
    }
    
    exportGestures() {
        const data = {};
        this.trainingData.forEach((value, key) => {
            data[key] = value;
        });
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'custom_gestures.json';
        a.click();
        URL.revokeObjectURL(url);
        
        this.showNotification('Gestures exported successfully', 'success');
    }
    
    importGestures(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                Object.entries(data).forEach(([name, gestureData]) => {
                    this.trainingData.set(name, gestureData);
                });
                
                // Save to localStorage
                this.saveGesture('', []); // Trigger save
                this.refreshGestureList();
                this.showNotification(`Imported ${Object.keys(data).length} gestures`, 'success');
            } catch (error) {
                this.showNotification('Import failed: Invalid file format', 'error');
            }
        };
        reader.readAsText(file);
    }
    
    updateUI(state) {
        const recordBtn = document.getElementById('gesture-record-btn');
        const progressBar = document.getElementById('gesture-progress');
        
        if (state === 'recording') {
            if (recordBtn) {
                recordBtn.disabled = true;
                recordBtn.textContent = 'Recording...';
                recordBtn.classList.add('recording');
            }
            if (progressBar) {
                progressBar.style.display = 'block';
                progressBar.querySelector('.progress-fill').style.width = '0%';
            }
        } else {
            if (recordBtn) {
                recordBtn.disabled = false;
                recordBtn.textContent = '🎥 Record Gesture';
                recordBtn.classList.remove('recording');
            }
            if (progressBar) {
                progressBar.style.display = 'none';
            }
        }
    }
    
    updateProgress(sampleCount) {
        const progressBar = document.getElementById('gesture-progress');
        if (progressBar) {
            const percent = (sampleCount / 5) * 100;
            progressBar.querySelector('.progress-fill').style.width = `${percent}%`;
            progressBar.querySelector('.progress-text').textContent = `${sampleCount}/5 samples`;
        }
    }
    
    refreshGestureList() {
        const listContainer = document.getElementById('custom-gestures-list');
        if (!listContainer) return;
        
        listContainer.innerHTML = '';
        
        if (this.trainingData.size === 0) {
            listContainer.innerHTML = '<div class="no-gestures">No custom gestures yet. Record one to get started!</div>';
            return;
        }
        
        this.trainingData.forEach((data, name) => {
            const item = document.createElement('div');
            item.className = 'gesture-item';
            item.innerHTML = `
                <div class="gesture-info">
                    <div class="gesture-name">${name}</div>
                    <div class="gesture-meta">
                        ${data.samples.length} samples
                        ${data.trained ? '<span class="trained-badge">✓ Trained</span>' : '<span class="untrained-badge">Not trained</span>'}
                    </div>
                </div>
                <div class="gesture-actions">
                    ${!data.trained ? `<button onclick="gestureTrainer.trainGesture('${name}')" class="btn-small">Train</button>` : ''}
                    <button onclick="gestureTrainer.testGesture('${name}')" class="btn-small">Test</button>
                    <button onclick="gestureTrainer.deleteGesture('${name}')" class="btn-small btn-danger">Delete</button>
                </div>
            `;
            listContainer.appendChild(item);
        });
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `trainer-notification trainer-notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => notification.classList.add('show'), 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    renderUI(container) {
        container.innerHTML = `
            <div class="gesture-trainer-panel">
                <h2>✋ Gesture Training Studio</h2>
                
                <div class="trainer-section">
                    <h3>Record New Gesture</h3>
                    <div class="record-controls">
                        <input 
                            type="text" 
                            id="gesture-name-input" 
                            placeholder="Enter gesture name (e.g., 'high five')"
                            class="gesture-input"
                        />
                        <button 
                            id="gesture-record-btn" 
                            class="btn-primary"
                            onclick="gestureTrainer.startRecording(document.getElementById('gesture-name-input').value)"
                        >
                            🎥 Record Gesture
                        </button>
                    </div>
                    
                    <div id="gesture-progress" class="progress-bar" style="display: none;">
                        <div class="progress-fill"></div>
                        <div class="progress-text">0/5 samples</div>
                    </div>
                    
                    <div class="trainer-instructions">
                        <p><strong>How to record:</strong></p>
                        <ol>
                            <li>Enter a name for your gesture</li>
                            <li>Click "Record Gesture"</li>
                            <li>Perform the gesture 5 times clearly</li>
                            <li>System will automatically save after 5 samples</li>
                        </ol>
                    </div>
                </div>
                
                <div class="trainer-section">
                    <h3>Your Custom Gestures</h3>
                    <div id="custom-gestures-list" class="gestures-list"></div>
                </div>
                
                <div class="trainer-section">
                    <h3>Import/Export</h3>
                    <div class="import-export-controls">
                        <button onclick="gestureTrainer.exportGestures()" class="btn-secondary">
                            📥 Export Gestures
                        </button>
                        <label class="btn-secondary">
                            📤 Import Gestures
                            <input 
                                type="file" 
                                accept=".json" 
                                style="display: none;"
                                onchange="gestureTrainer.importGestures(this.files[0])"
                            />
                        </label>
                    </div>
                </div>
            </div>
        `;
        
        this.refreshGestureList();
    }
}

// CSS Styles
const trainerStyles = document.createElement('style');
trainerStyles.textContent = `
    .gesture-trainer-panel {
        padding: 20px;
        max-width: 800px;
        margin: 0 auto;
    }
    
    .gesture-trainer-panel h2 {
        color: #0ff;
        margin-bottom: 20px;
        font-size: 24px;
    }
    
    .trainer-section {
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }
    
    .trainer-section h3 {
        color: #0ff;
        margin-bottom: 15px;
        font-size: 18px;
    }
    
    .record-controls {
        display: flex;
        gap: 10px;
        margin-bottom: 15px;
    }
    
    .gesture-input {
        flex: 1;
        padding: 10px;
        background: rgba(0, 0, 0, 0.7);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 4px;
        color: white;
        font-size: 14px;
    }
    
    .gesture-input:focus {
        outline: none;
        border-color: #0ff;
    }
    
    .btn-primary, .btn-secondary, .btn-small {
        padding: 10px 20px;
        background: rgba(0, 255, 255, 0.2);
        border: 1px solid #0ff;
        color: #0ff;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.2s;
    }
    
    .btn-primary:hover, .btn-secondary:hover, .btn-small:hover {
        background: rgba(0, 255, 255, 0.3);
    }
    
    .btn-primary.recording {
        background: rgba(255, 0, 0, 0.3);
        border-color: #f00;
        color: #f00;
        animation: pulse 1s infinite;
    }
    
    .btn-small {
        padding: 5px 10px;
        font-size: 12px;
    }
    
    .btn-danger {
        border-color: #f00;
        color: #f00;
    }
    
    .progress-bar {
        position: relative;
        height: 30px;
        background: rgba(0, 0, 0, 0.7);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 4px;
        overflow: hidden;
        margin-bottom: 15px;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #0ff, #0af);
        transition: width 0.3s;
        width: 0%;
    }
    
    .progress-text {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        color: white;
        font-size: 12px;
        font-weight: bold;
    }
    
    .trainer-instructions {
        background: rgba(0, 255, 255, 0.05);
        border-left: 3px solid #0ff;
        padding: 10px 15px;
        margin-top: 15px;
    }
    
    .trainer-instructions p {
        color: #0ff;
        margin-bottom: 5px;
    }
    
    .trainer-instructions ol {
        color: white;
        margin-left: 20px;
        font-size: 13px;
    }
    
    .gestures-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    
    .gesture-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        background: rgba(0, 255, 255, 0.05);
        border: 1px solid rgba(0, 255, 255, 0.2);
        border-radius: 4px;
    }
    
    .gesture-info {
        flex: 1;
    }
    
    .gesture-name {
        color: white;
        font-weight: bold;
        margin-bottom: 4px;
    }
    
    .gesture-meta {
        color: rgba(255, 255, 255, 0.6);
        font-size: 12px;
    }
    
    .trained-badge {
        color: #0f0;
        margin-left: 10px;
    }
    
    .untrained-badge {
        color: #fa0;
        margin-left: 10px;
    }
    
    .gesture-actions {
        display: flex;
        gap: 5px;
    }
    
    .no-gestures {
        color: rgba(255, 255, 255, 0.5);
        text-align: center;
        padding: 30px;
        font-style: italic;
    }
    
    .import-export-controls {
        display: flex;
        gap: 10px;
    }
    
    .trainer-notification {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%) translateY(100px);
        padding: 12px 24px;
        background: rgba(0, 0, 0, 0.9);
        border-radius: 8px;
        color: white;
        font-size: 14px;
        opacity: 0;
        transition: all 0.3s;
        z-index: 10002;
    }
    
    .trainer-notification.show {
        transform: translateX(-50%) translateY(0);
        opacity: 1;
    }
    
    .trainer-notification-success {
        border: 2px solid #0f0;
        box-shadow: 0 4px 15px rgba(0, 255, 0, 0.3);
    }
    
    .trainer-notification-error {
        border: 2px solid #f00;
        box-shadow: 0 4px 15px rgba(255, 0, 0, 0.3);
    }
    
    .trainer-notification-info {
        border: 2px solid #0ff;
        box-shadow: 0 4px 15px rgba(0, 255, 255, 0.3);
    }
    
    .trainer-notification-warning {
        border: 2px solid #fa0;
        box-shadow: 0 4px 15px rgba(255, 170, 0, 0.3);
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
`;
document.head.appendChild(trainerStyles);

// Create global instance
window.gestureTrainer = new GestureTrainer();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GestureTrainer;
}
