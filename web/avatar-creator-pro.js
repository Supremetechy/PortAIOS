/**
 * Avatar Creator Pro Controller
 * Integrates 3D preview, animations, and save/load functionality
 */

import { AvatarPreview3D } from './avatar-preview-3d.js';
import { AnimationPlayer, EXPRESSION_ANIMATIONS, LIPSYNC_ANIMATIONS } from './avatar-animations.js';

export class AvatarCreatorPro {
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
        this.preview3D = null;
        this.animationPlayer = null;
        this.generationInProgress = false;
        this.statusPollInterval = null;
        this.currentAvatarId = null;
        
        // Initialize asynchronously with error handling
        this.init().catch(error => {
            console.error('[AvatarCreatorPro] Initialization failed:', error);
            // Still setup event listeners even if init fails
            this.setupEventListeners();
        });
    }
    
    async init() {
        console.log('[AvatarCreatorPro] Initializing...');
        
        try {
            // Setup event listeners FIRST before any async operations
            // This ensures buttons work even if initialization fails
            this.setupEventListeners();
            console.log('[AvatarCreatorPro] Event listeners attached');
            
            // Initialize 3D preview
            const previewContainer = document.getElementById('preview-3d');
            if (previewContainer) {
                try {
                    this.preview3D = new AvatarPreview3D(previewContainer);
                    this.animationPlayer = new AnimationPlayer(this.preview3D);
                    
                    // Load default avatar
                    await this.preview3D.loadAvatar('/models/avatar_generated.glb');
                    console.log('[AvatarCreatorPro] Default avatar loaded');
                } catch (error) {
                    console.warn('[AvatarCreatorPro] Could not load default avatar:', error);
                    // Continue initialization even if 3D preview fails
                }
            }
            
            // Load presets
            await this.loadPresets();
            
            // Load saved avatars
            await this.loadSavedAvatars();
            
            // Setup tabs
            this.setupTabs();
            
            console.log('[AvatarCreatorPro] Ready');
        } catch (error) {
            console.error('[AvatarCreatorPro] Initialization error:', error);
            // Event listeners already set up, so buttons will still work
        }
    }
    
    setupTabs() {
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                
                // Update active tab
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                e.target.classList.add('active');
                
                // Show corresponding content
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.getElementById(`${tabName}-tab`).classList.add('active');
            });
        });
    }
    
    async loadPresets() {
        try {
            if (typeof eel !== 'undefined' && eel.get_avatar_presets) {
                this.presets = await eel.get_avatar_presets()();
                this.renderPresets();
            } else {
                console.warn('[AvatarCreatorPro] Eel not available, using default presets');
                this.presets = this.getDefaultPresets();
                this.renderPresets();
            }
        } catch (error) {
            console.error('[AvatarCreatorPro] Failed to load presets:', error);
            this.presets = this.getDefaultPresets();
            this.renderPresets();
        }
    }
    
    getDefaultPresets() {
        return {
            neutral: {
                name: "Neutral",
                description: "Basic neutral",
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
                description: "Warm & welcoming",
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
                description: "Serious & focused",
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
                description: "Excited & enthusiastic",
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
        
        console.log(`[AvatarCreatorPro] Applying preset: ${preset.name}`);
        
        // Update params
        this.currentParams = { ...preset };
        
        // Update UI
        this.updateUIFromParams(this.currentParams);
        
        // Update 3D preview
        if (this.preview3D) {
            this.preview3D.updateFromParams(this.currentParams);
        }
        
        // Highlight selected
        document.querySelectorAll('.preset-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-preset="${presetKey}"]`)?.classList.add('selected');
    }
    
    updateUIFromParams(params) {
        document.getElementById('head-radius').value = params.head_radius;
        document.getElementById('head-radius-value').textContent = params.head_radius.toFixed(2);
        
        document.getElementById('smile').value = params.smile_strength;
        document.getElementById('smile-value').textContent = params.smile_strength.toFixed(1);
        
        document.getElementById('frown').value = params.frown_strength;
        document.getElementById('frown-value').textContent = params.frown_strength.toFixed(1);
        
        document.getElementById('surprise').value = params.surprise_strength;
        document.getElementById('surprise-value').textContent = params.surprise_strength.toFixed(1);
        
        document.getElementById('wink').value = params.wink_strength;
        document.getElementById('wink-value').textContent = params.wink_strength.toFixed(1);
        
        document.getElementById('viseme').value = params.viseme_strength;
        document.getElementById('viseme-value').textContent = params.viseme_strength.toFixed(1);
        
        const hexColor = this.rgbToHex(params.head_color);
        document.getElementById('head-color').value = hexColor;
    }
    
    setupEventListeners() {
        // Sliders
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
        document.getElementById('update-preview-btn')?.addEventListener('click', () => {
            if (this.preview3D) {
                this.preview3D.updateFromParams(this.currentParams);
            }
        });
        
        document.getElementById('generate-btn')?.addEventListener('click', () => this.generateAvatar());
        document.getElementById('save-avatar-btn')?.addEventListener('click', () => this.showSaveDialog());
        document.getElementById('refresh-avatars-btn')?.addEventListener('click', () => this.loadSavedAvatars());
        document.getElementById('import-avatar-btn')?.addEventListener('click', () => this.importAvatar());
        
        document.getElementById('reset-view-btn')?.addEventListener('click', () => {
            if (this.preview3D && this.preview3D.controls) {
                this.preview3D.controls.reset();
            }
        });
        
        // Animation buttons
        document.querySelectorAll('.animation-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const animation = e.currentTarget.dataset.animation;
                const category = e.currentTarget.dataset.category;
                
                if (this.animationPlayer) {
                    this.animationPlayer.play(animation, category);
                }
            });
        });
    }
    
    async generateAvatar() {
        if (this.generationInProgress) return;
        
        console.log('[AvatarCreatorPro] Starting generation...', this.currentParams);
        
        // Show progress
        document.getElementById('progress-container').classList.add('active');
        document.getElementById('success-message').classList.remove('active');
        document.getElementById('error-message').classList.remove('active');
        document.getElementById('generate-btn').disabled = true;
        
        this.generationInProgress = true;
        this.generationTimeout = null;
        
        try {
            if (typeof eel !== 'undefined' && eel.start_avatar_generation) {
                console.log('[AvatarCreatorPro] Starting backend generation...');
                
                const result = await eel.start_avatar_generation(this.currentParams)();
                
                console.log('[AvatarCreatorPro] Start result:', result);
                
                if (result.success) {
                    this.startStatusPolling();
                    
                    // Add safety timeout (2 minutes)
                    this.generationTimeout = setTimeout(() => {
                        console.warn('[AvatarCreatorPro] Generation timeout');
                        this.stopStatusPolling();
                        this.showError('Generation timed out after 2 minutes');
                    }, 120000);
                } else {
                    throw new Error(result.error || 'Failed to start generation');
                }
            } else {
                console.warn('[AvatarCreatorPro] Demo mode - Eel not available');
                this.simulateGeneration();
            }
        } catch (error) {
            console.error('[AvatarCreatorPro] Generation failed:', error);
            this.showError(error.message || 'Generation failed');
            this.generationInProgress = false;
            document.getElementById('generate-btn').disabled = false;
        }
    }
    
    startStatusPolling() {
        console.log('[AvatarCreatorPro] Starting status polling...');
        let consecutiveErrors = 0;
        const maxErrors = 5;
        
        this.statusPollInterval = setInterval(async () => {
            try {
                if (typeof eel !== 'undefined' && eel.get_avatar_generation_status) {
                    const status = await eel.get_avatar_generation_status()();
                    
                    console.log('[AvatarCreatorPro] Status:', status);
                    consecutiveErrors = 0; // Reset error counter on success
                    
                    this.updateProgress(status);
                    
                    if (!status.in_progress) {
                        this.stopStatusPolling();
                        
                        if (this.generationTimeout) {
                            clearTimeout(this.generationTimeout);
                            this.generationTimeout = null;
                        }
                        
                        if (status.error) {
                            this.showError(status.error);
                        } else if (status.result_path) {
                            this.showSuccess(status.result_path);
                            // Load new avatar in preview
                            if (this.preview3D) {
                                await this.preview3D.loadAvatar(status.result_path);
                            }
                        } else {
                            this.showError('Generation completed but no result path');
                        }
                    }
                }
            } catch (error) {
                consecutiveErrors++;
                console.error(`[AvatarCreatorPro] Status polling error (${consecutiveErrors}/${maxErrors}):`, error);
                
                if (consecutiveErrors >= maxErrors) {
                    console.error('[AvatarCreatorPro] Too many polling errors, stopping');
                    this.stopStatusPolling();
                    this.showError('Lost connection to backend during generation');
                }
            }
        }, 1000); // Poll every 1 second instead of 500ms
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
        // Demo mode
        let progress = 0;
        const stages = [
            { progress: 10, message: "Parsing parameters..." },
            { progress: 20, message: "Building base mesh..." },
            { progress: 40, message: "Creating morph targets..." },
            { progress: 60, message: "Generating GLB..." },
            { progress: 80, message: "Validating..." },
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
        document.getElementById('success-text').textContent = `Saved to: ${path}`;
        console.log('[AvatarCreatorPro] Generation complete:', path);
    }
    
    showError(errorMsg) {
        document.getElementById('progress-container').classList.remove('active');
        document.getElementById('error-message').classList.add('active');
        document.getElementById('error-text').textContent = errorMsg;
        console.error('[AvatarCreatorPro] Error:', errorMsg);
    }
    
    async showSaveDialog() {
        const name = prompt('Enter a name for this avatar:');
        if (!name) return;
        
        const tags = prompt('Enter tags (comma-separated, optional):');
        const tagArray = tags ? tags.split(',').map(t => t.trim()) : [];
        
        try {
            if (typeof eel !== 'undefined' && eel.save_custom_avatar) {
                const result = await eel.save_custom_avatar(name, this.currentParams, tagArray)();
                
                if (result.success) {
                    alert(`✅ Avatar "${name}" saved successfully!`);
                    this.currentAvatarId = result.avatar_id;
                    await this.loadSavedAvatars();
                } else {
                    alert(`❌ Failed to save: ${result.error}`);
                }
            } else {
                console.warn('[AvatarCreatorPro] Save not available in demo mode');
                alert('⚠️ Save feature requires backend connection');
            }
        } catch (error) {
            console.error('[AvatarCreatorPro] Save failed:', error);
            alert(`❌ Save failed: ${error.message}`);
        }
    }
    
    async loadSavedAvatars() {
        const container = document.getElementById('saved-avatars-list');
        if (!container) return;
        
        try {
            if (typeof eel !== 'undefined' && eel.list_saved_avatars) {
                const result = await eel.list_saved_avatars()();
                
                if (result.success && result.avatars.length > 0) {
                    container.innerHTML = '';
                    
                    result.avatars.forEach(avatar => {
                        const card = this.createAvatarCard(avatar);
                        container.appendChild(card);
                    });
                } else {
                    container.innerHTML = '<p style="text-align: center; color: #00ffff66; padding: 20px;">No saved avatars yet</p>';
                }
            }
        } catch (error) {
            console.error('[AvatarCreatorPro] Failed to load saved avatars:', error);
        }
    }
    
    createAvatarCard(avatar) {
        const card = document.createElement('div');
        card.className = 'saved-avatar-card';
        
        const created = new Date(avatar.created).toLocaleDateString();
        
        card.innerHTML = `
            <div class="saved-avatar-name">${avatar.name}</div>
            <div class="saved-avatar-meta">
                <span>Created: ${created}</span>
                <span>${avatar.tags.length > 0 ? avatar.tags.join(', ') : 'No tags'}</span>
            </div>
            <div class="saved-avatar-actions">
                <button class="avatar-action-btn load-btn" data-id="${avatar.id}">Load</button>
                <button class="avatar-action-btn export-btn" data-id="${avatar.id}">Export</button>
                <button class="avatar-action-btn delete-btn" data-id="${avatar.id}">Delete</button>
            </div>
        `;
        
        // Load button
        card.querySelector('.load-btn').addEventListener('click', () => this.loadSavedAvatar(avatar.id));
        
        // Export button
        card.querySelector('.export-btn').addEventListener('click', () => this.exportAvatar(avatar.id));
        
        // Delete button
        card.querySelector('.delete-btn').addEventListener('click', () => this.deleteSavedAvatar(avatar.id, avatar.name));
        
        return card;
    }
    
    async loadSavedAvatar(avatarId) {
        try {
            if (typeof eel !== 'undefined' && eel.load_custom_avatar) {
                const result = await eel.load_custom_avatar(avatarId)();
                
                if (result.success && result.avatar) {
                    this.currentParams = result.avatar.params;
                    this.currentAvatarId = avatarId;
                    this.updateUIFromParams(this.currentParams);
                    
                    if (this.preview3D) {
                        this.preview3D.updateFromParams(this.currentParams);
                        
                        if (result.avatar.glb_path) {
                            await this.preview3D.loadAvatar(result.avatar.glb_path);
                        }
                    }
                    
                    console.log('[AvatarCreatorPro] Loaded avatar:', result.avatar.name);
                } else {
                    alert(`❌ Failed to load: ${result.error}`);
                }
            }
        } catch (error) {
            console.error('[AvatarCreatorPro] Load failed:', error);
            alert(`❌ Load failed: ${error.message}`);
        }
    }
    
    async deleteSavedAvatar(avatarId, name) {
        if (!confirm(`Delete avatar "${name}"?`)) return;
        
        try {
            if (typeof eel !== 'undefined' && eel.delete_custom_avatar) {
                const result = await eel.delete_custom_avatar(avatarId)();
                
                if (result.success) {
                    await this.loadSavedAvatars();
                } else {
                    alert(`❌ Failed to delete: ${result.error}`);
                }
            }
        } catch (error) {
            console.error('[AvatarCreatorPro] Delete failed:', error);
            alert(`❌ Delete failed: ${error.message}`);
        }
    }
    
    async exportAvatar(avatarId) {
        const path = prompt('Enter export path (e.g., ~/Desktop/my_avatar):');
        if (!path) return;
        
        try {
            if (typeof eel !== 'undefined' && eel.export_avatar) {
                const result = await eel.export_avatar(avatarId, path)();
                
                if (result.success) {
                    alert(`✅ Exported to: ${result.path}`);
                } else {
                    alert(`❌ Export failed: ${result.error}`);
                }
            }
        } catch (error) {
            console.error('[AvatarCreatorPro] Export failed:', error);
            alert(`❌ Export failed: ${error.message}`);
        }
    }
    
    async importAvatar() {
        const path = prompt('Enter import path (e.g., ~/Desktop/avatar.zip):');
        if (!path) return;
        
        try {
            if (typeof eel !== 'undefined' && eel.import_avatar) {
                const result = await eel.import_avatar(path)();
                
                if (result.success) {
                    alert(`✅ Avatar imported successfully!`);
                    await this.loadSavedAvatars();
                } else {
                    alert(`❌ Import failed: ${result.error}`);
                }
            }
        } catch (error) {
            console.error('[AvatarCreatorPro] Import failed:', error);
            alert(`❌ Import failed: ${error.message}`);
        }
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

// Expose for eel callbacks
if (typeof eel !== 'undefined') {
    eel.expose(avatar_generation_progress, 'avatar_generation_progress');
}

function avatar_generation_progress(status) {
    if (window.avatarCreatorPro) {
        window.avatarCreatorPro.updateProgress(status);
    }
}

// Initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.avatarCreatorPro = new AvatarCreatorPro();
    });
} else {
    window.avatarCreatorPro = new AvatarCreatorPro();
}
