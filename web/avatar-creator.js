/**
 * Avatar Creator Controller
 * Handles UI interactions and backend communication for avatar generation
 */

export class AvatarCreatorController {
    constructor() {
        this.currentParams = {
            head_radius: 0.12,
            head_color: [0.9, 0.8, 0.7],
            smile_strength: 0.0,
            frown_strength: 0.0,
            surprise_strength: 0.0,
            wink_strength: 0.0,
            viseme_strength: 1.0
        };
        
        this.presets = {};
        this.generationInProgress = false;
        this.statusPollInterval = null;
        
        this.init();
    }
    
    async init() {
        console.log('[AvatarCreator] Initializing...');
        
        // Load presets from backend
        await this.loadPresets();
        
        // Setup event listeners
        this.setupEventListeners();
        
        console.log('[AvatarCreator] Ready');
    }
    
    async loadPresets() {
        try {
            if (typeof eel !== 'undefined' && eel.get_avatar_presets) {
                this.presets = await eel.get_avatar_presets()();
                this.renderPresets();
            } else {
                console.warn('[AvatarCreator] Eel not available, using default presets');
                this.presets = this.getDefaultPresets();
                this.renderPresets();
            }
        } catch (error) {
            console.error('[AvatarCreator] Failed to load presets:', error);
            this.presets = this.getDefaultPresets();
            this.renderPresets();
        }
    }
    
    getDefaultPresets() {
        return {
            neutral: {
                name: "Neutral",
                description: "Basic neutral expression",
                head_radius: 0.12,
                head_color: [0.9, 0.8, 0.7],
                smile_strength: 0.0,
                frown_strength: 0.0,
                surprise_strength: 0.0,
                wink_strength: 0.0,
                viseme_strength: 1.0
            },
            friendly: {
                name: "Friendly",
                description: "Warm and welcoming",
                head_radius: 0.12,
                head_color: [0.95, 0.85, 0.75],
                smile_strength: 0.6,
                frown_strength: 0.0,
                surprise_strength: 0.2,
                wink_strength: 0.0,
                viseme_strength: 1.0
            },
            professional: {
                name: "Professional",
                description: "Serious and focused",
                head_radius: 0.13,
                head_color: [0.85, 0.75, 0.65],
                smile_strength: 0.2,
                frown_strength: 0.1,
                surprise_strength: 0.0,
                wink_strength: 0.0,
                viseme_strength: 1.0
            },
            energetic: {
                name: "Energetic",
                description: "Excited and enthusiastic",
                head_radius: 0.11,
                head_color: [0.95, 0.9, 0.8],
                smile_strength: 0.8,
                frown_strength: 0.0,
                surprise_strength: 0.5,
                wink_strength: 0.0,
                viseme_strength: 1.0
            }
        };
    }
    
    renderPresets() {
        const grid = document.getElementById('preset-grid');
        if (!grid) return;
        
        grid.innerHTML = '';
        
        Object.entries(this.presets).forEach(([key, preset]) => {
            const card = document.createElement('div');
            card.className = 'preset-card';
            card.dataset.preset = key;
            
            card.innerHTML = `
                <div class="preset-name">${preset.name}</div>
                <div class="preset-desc">${preset.description}</div>
            `;
            
            card.addEventListener('click', () => this.applyPreset(key));
            grid.appendChild(card);
        });
    }
    
    applyPreset(presetKey) {
        const preset = this.presets[presetKey];
        if (!preset) return;
        
        console.log(`[AvatarCreator] Applying preset: ${preset.name}`);
        
        // Update current params
        this.currentParams = { ...preset };
        
        // Update UI
        document.getElementById('head-radius').value = preset.head_radius;
        document.getElementById('head-radius-value').textContent = preset.head_radius.toFixed(2);
        
        document.getElementById('smile').value = preset.smile_strength;
        document.getElementById('smile-value').textContent = preset.smile_strength.toFixed(1);
        
        document.getElementById('frown').value = preset.frown_strength;
        document.getElementById('frown-value').textContent = preset.frown_strength.toFixed(1);
        
        document.getElementById('surprise').value = preset.surprise_strength;
        document.getElementById('surprise-value').textContent = preset.surprise_strength.toFixed(1);
        
        document.getElementById('wink').value = preset.wink_strength;
        document.getElementById('wink-value').textContent = preset.wink_strength.toFixed(1);
        
        document.getElementById('viseme').value = preset.viseme_strength;
        document.getElementById('viseme-value').textContent = preset.viseme_strength.toFixed(1);
        
        // Convert RGB array to hex color
        const hexColor = this.rgbToHex(preset.head_color);
        document.getElementById('head-color').value = hexColor;
        
        // Highlight selected preset
        document.querySelectorAll('.preset-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-preset="${presetKey}"]`)?.classList.add('selected');
    }
    
    setupEventListeners() {
        // Slider updates
        const sliders = {
            'head-radius': (val) => {
                this.currentParams.head_radius = parseFloat(val);
                document.getElementById('head-radius-value').textContent = parseFloat(val).toFixed(2);
            },
            'smile': (val) => {
                this.currentParams.smile_strength = parseFloat(val);
                document.getElementById('smile-value').textContent = parseFloat(val).toFixed(1);
            },
            'frown': (val) => {
                this.currentParams.frown_strength = parseFloat(val);
                document.getElementById('frown-value').textContent = parseFloat(val).toFixed(1);
            },
            'surprise': (val) => {
                this.currentParams.surprise_strength = parseFloat(val);
                document.getElementById('surprise-value').textContent = parseFloat(val).toFixed(1);
            },
            'wink': (val) => {
                this.currentParams.wink_strength = parseFloat(val);
                document.getElementById('wink-value').textContent = parseFloat(val).toFixed(1);
            },
            'viseme': (val) => {
                this.currentParams.viseme_strength = parseFloat(val);
                document.getElementById('viseme-value').textContent = parseFloat(val).toFixed(1);
            }
        };
        
        Object.entries(sliders).forEach(([id, handler]) => {
            const slider = document.getElementById(id);
            if (slider) {
                slider.addEventListener('input', (e) => handler(e.target.value));
            }
        });
        
        // Color picker
        const colorPicker = document.getElementById('head-color');
        if (colorPicker) {
            colorPicker.addEventListener('input', (e) => {
                this.currentParams.head_color = this.hexToRgb(e.target.value);
            });
        }
        
        // Buttons
        const generateBtn = document.getElementById('generate-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generateAvatar());
        }
        
        const resetBtn = document.getElementById('reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.reset());
        }
        
        const loadAvatarBtn = document.getElementById('load-avatar-btn');
        if (loadAvatarBtn) {
            loadAvatarBtn.addEventListener('click', () => this.loadInViewer());
        }
    }
    
    async generateAvatar() {
        if (this.generationInProgress) {
            console.warn('[AvatarCreator] Generation already in progress');
            return;
        }
        
        console.log('[AvatarCreator] Starting avatar generation...', this.currentParams);
        
        // Show progress UI
        document.getElementById('progress-container').classList.add('active');
        document.getElementById('success-message').classList.remove('active');
        document.getElementById('error-message').classList.remove('active');
        document.getElementById('generate-btn').disabled = true;
        
        this.generationInProgress = true;
        
        try {
            if (typeof eel !== 'undefined' && eel.start_avatar_generation) {
                const result = await eel.start_avatar_generation(this.currentParams)();
                
                if (result.success) {
                    // Start polling for status
                    this.startStatusPolling();
                } else {
                    throw new Error(result.error || 'Failed to start generation');
                }
            } else {
                // Simulate generation for testing without backend
                console.warn('[AvatarCreator] Running in demo mode (no backend)');
                this.simulateGeneration();
            }
        } catch (error) {
            console.error('[AvatarCreator] Generation failed:', error);
            this.showError(error.message);
            this.generationInProgress = false;
            document.getElementById('generate-btn').disabled = false;
        }
    }
    
    startStatusPolling() {
        this.statusPollInterval = setInterval(async () => {
            try {
                if (typeof eel !== 'undefined' && eel.get_avatar_generation_status) {
                    const status = await eel.get_avatar_generation_status()();
                    this.updateProgress(status);
                    
                    if (!status.in_progress) {
                        this.stopStatusPolling();
                        
                        if (status.error) {
                            this.showError(status.error);
                        } else if (status.result_path) {
                            this.showSuccess(status.result_path);
                        }
                    }
                }
            } catch (error) {
                console.error('[AvatarCreator] Status polling error:', error);
                this.stopStatusPolling();
            }
        }, 500);
    }
    
    stopStatusPolling() {
        if (this.statusPollInterval) {
            clearInterval(this.statusPollInterval);
            this.statusPollInterval = null;
        }
        this.generationInProgress = false;
        document.getElementById('generate-btn').disabled = false;
    }
    
    updateProgress(status) {
        const progressBar = document.getElementById('progress-bar');
        const progressPercent = document.getElementById('progress-percent');
        const stageText = document.getElementById('stage-text');
        
        if (progressBar) {
            progressBar.style.width = `${status.progress}%`;
        }
        
        if (progressPercent) {
            progressPercent.textContent = `${status.progress}%`;
        }
        
        if (stageText && status.message) {
            stageText.textContent = status.message;
        }
    }
    
    simulateGeneration() {
        // Demo mode simulation
        let progress = 0;
        const stages = [
            { progress: 10, message: "Parsing parameters..." },
            { progress: 20, message: "Building base mesh..." },
            { progress: 40, message: "Creating morph targets for lip-sync..." },
            { progress: 60, message: "Generating GLB file..." },
            { progress: 80, message: "Validating morph targets..." },
            { progress: 95, message: "Finalizing avatar..." },
            { progress: 100, message: "Complete!" }
        ];
        
        let stageIndex = 0;
        const interval = setInterval(() => {
            if (stageIndex < stages.length) {
                this.updateProgress(stages[stageIndex]);
                stageIndex++;
            } else {
                clearInterval(interval);
                setTimeout(() => {
                    this.showSuccess('models/avatar_generated.glb');
                }, 500);
            }
        }, 800);
    }
    
    showSuccess(path) {
        document.getElementById('progress-container').classList.remove('active');
        document.getElementById('success-message').classList.add('active');
        document.getElementById('success-path').textContent = `Saved to: ${path}`;
        console.log('[AvatarCreator] Generation complete:', path);
    }
    
    showError(errorMsg) {
        document.getElementById('progress-container').classList.remove('active');
        document.getElementById('error-message').classList.add('active');
        document.getElementById('error-text').textContent = errorMsg;
        console.error('[AvatarCreator] Generation error:', errorMsg);
    }
    
    reset() {
        console.log('[AvatarCreator] Resetting to neutral preset');
        this.applyPreset('neutral');
    }
    
    loadInViewer() {
        console.log('[AvatarCreator] Loading avatar in 3D viewer');
        // Redirect to avatar integration page with generated model
        window.location.href = 'avatar-integration.html?model=avatar_generated.glb';
    }
    
    // Utility functions
    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? [
            parseInt(result[1], 16) / 255,
            parseInt(result[2], 16) / 255,
            parseInt(result[3], 16) / 255
        ] : [0.9, 0.8, 0.7];
    }
    
    rgbToHex(rgb) {
        const r = Math.round(rgb[0] * 255).toString(16).padStart(2, '0');
        const g = Math.round(rgb[1] * 255).toString(16).padStart(2, '0');
        const b = Math.round(rgb[2] * 255).toString(16).padStart(2, '0');
        return `#${r}${g}${b}`;
    }
}

// Expose progress update handler for backend callbacks
if (typeof eel !== 'undefined') {
    eel.expose(avatar_generation_progress, 'avatar_generation_progress');
}

function avatar_generation_progress(status) {
    if (window.avatarCreator) {
        window.avatarCreator.updateProgress(status);
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.avatarCreator = new AvatarCreatorController();
    });
} else {
    window.avatarCreator = new AvatarCreatorController();
}
