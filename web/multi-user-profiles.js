/**
 * Multi-User Profile System
 * Manage multiple user profiles with individual settings, preferences, and customizations
 * Supports profile switching, import/export, and cloud sync preparation
 */

export class MultiUserProfiles {
    constructor(options = {}) {
        this.options = {
            enableAutoSave: true,
            enableProfilePictures: true,
            enableCloudSync: false,
            maxProfiles: 10,
            ...options
        };
        
        // Current user
        this.currentUser = null;
        
        // User profiles
        this.profiles = new Map();
        
        // Profile settings schema
        this.settingsSchema = this.getSettingsSchema();
        
        // Initialize
        this.initialize();
        
        console.log('[MultiUser] Multi-user profile system initialized');
    }
    
    /**
     * Initialize profile system
     */
    initialize() {
        // Load profiles
        this.loadProfiles();
        
        // Load or create default profile
        if (this.profiles.size === 0) {
            this.createDefaultProfile();
        }
        
        // Load current user
        this.loadCurrentUser();
    }
    
    /**
     * Create a new user profile
     */
    createProfile(config) {
        // Check max profiles
        if (this.profiles.size >= this.options.maxProfiles) {
            return {
                success: false,
                error: `Maximum ${this.options.maxProfiles} profiles allowed`
            };
        }
        
        // Check if username exists
        const usernameExists = Array.from(this.profiles.values()).some(
            p => p.username.toLowerCase() === config.username.toLowerCase()
        );
        
        if (usernameExists) {
            return {
                success: false,
                error: 'Username already exists'
            };
        }
        
        const profile = {
            id: config.id || this.generateId(),
            username: config.username,
            displayName: config.displayName || config.username,
            email: config.email || '',
            avatar: config.avatar || this.getDefaultAvatar(),
            
            // Settings
            settings: this.getDefaultSettings(config.settings),
            
            // Customizations
            customizations: {
                theme: config.customizations?.theme || 'cyberpunk',
                wakeWords: config.customizations?.wakeWords || ['hey aios'],
                macros: config.customizations?.macros || [],
                shortcuts: config.customizations?.shortcuts || [],
                gestures: config.customizations?.gestures || {}
            },
            
            // Statistics
            stats: {
                created: new Date().toISOString(),
                lastLogin: null,
                totalLogins: 0,
                commandsExecuted: 0,
                gesturesUsed: 0,
                macrosRun: 0
            },
            
            // Preferences
            preferences: {
                language: config.preferences?.language || 'en',
                timezone: config.preferences?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
                notifications: config.preferences?.notifications !== false,
                sounds: config.preferences?.sounds !== false,
                animations: config.preferences?.animations !== false
            }
        };
        
        this.profiles.set(profile.id, profile);
        this.saveProfiles();
        
        console.log(`[MultiUser] Created profile: ${profile.username}`);
        
        return {
            success: true,
            profile: this.sanitizeProfile(profile)
        };
    }
    
    /**
     * Switch to a different profile
     */
    switchProfile(profileId, password = null) {
        const profile = this.profiles.get(profileId);
        
        if (!profile) {
            return {
                success: false,
                error: 'Profile not found'
            };
        }
        
        // Check password if set
        if (profile.password && profile.password !== password) {
            return {
                success: false,
                error: 'Incorrect password'
            };
        }
        
        // Save current profile if exists
        if (this.currentUser) {
            this.saveCurrentProfile();
        }
        
        // Switch to new profile
        this.currentUser = profile;
        
        // Update stats
        profile.stats.lastLogin = new Date().toISOString();
        profile.stats.totalLogins++;
        
        // Save current user
        localStorage.setItem('aios_current_user', profileId);
        
        // Apply profile settings
        this.applyProfileSettings(profile);
        
        this.saveProfiles();
        
        console.log(`[MultiUser] Switched to profile: ${profile.username}`);
        
        return {
            success: true,
            profile: this.sanitizeProfile(profile)
        };
    }
    
    /**
     * Update profile settings
     */
    updateProfile(profileId, updates) {
        const profile = this.profiles.get(profileId);
        
        if (!profile) {
            return {
                success: false,
                error: 'Profile not found'
            };
        }
        
        // Update allowed fields
        const allowedUpdates = [
            'displayName', 'email', 'avatar', 'settings', 
            'customizations', 'preferences'
        ];
        
        allowedUpdates.forEach(field => {
            if (updates[field] !== undefined) {
                if (typeof updates[field] === 'object') {
                    profile[field] = { ...profile[field], ...updates[field] };
                } else {
                    profile[field] = updates[field];
                }
            }
        });
        
        this.saveProfiles();
        
        // Re-apply settings if current user
        if (this.currentUser?.id === profileId) {
            this.applyProfileSettings(profile);
        }
        
        return {
            success: true,
            profile: this.sanitizeProfile(profile)
        };
    }
    
    /**
     * Delete a profile
     */
    deleteProfile(profileId) {
        const profile = this.profiles.get(profileId);
        
        if (!profile) {
            return {
                success: false,
                error: 'Profile not found'
            };
        }
        
        // Cannot delete current user
        if (this.currentUser?.id === profileId) {
            return {
                success: false,
                error: 'Cannot delete current profile. Switch to another profile first.'
            };
        }
        
        // Cannot delete if only profile
        if (this.profiles.size === 1) {
            return {
                success: false,
                error: 'Cannot delete the only profile'
            };
        }
        
        this.profiles.delete(profileId);
        this.saveProfiles();
        
        return {
            success: true,
            message: `Deleted profile: ${profile.username}`
        };
    }
    
    /**
     * Get default settings
     */
    getDefaultSettings(customSettings = {}) {
        return {
            // Voice settings
            voice: {
                enabled: true,
                wakeWordEnabled: true,
                voiceSpeed: 1.0,
                voicePitch: 1.0,
                voiceVolume: 1.0,
                conversationMode: false,
                ...customSettings.voice
            },
            
            // Gesture settings
            gesture: {
                enabled: true,
                sensitivity: 0.7,
                debounceTime: 500,
                smoothing: 0.5,
                autoCalibrate: true,
                ...customSettings.gesture
            },
            
            // UI settings
            ui: {
                showTelemetry: true,
                showActivityLog: true,
                compactMode: false,
                sidebarPosition: 'right',
                ...customSettings.ui
            },
            
            // System settings
            system: {
                enableLogging: true,
                enableAnalytics: false,
                enableNotifications: true,
                enableAutoUpdate: true,
                ...customSettings.system
            },
            
            // Privacy settings
            privacy: {
                shareUsageData: false,
                saveCommandHistory: true,
                saveGestureHistory: true,
                ...customSettings.privacy
            }
        };
    }
    
    /**
     * Get settings schema
     */
    getSettingsSchema() {
        return {
            voice: {
                enabled: { type: 'boolean', default: true },
                wakeWordEnabled: { type: 'boolean', default: true },
                voiceSpeed: { type: 'number', min: 0.5, max: 2.0, default: 1.0 },
                voicePitch: { type: 'number', min: 0.5, max: 2.0, default: 1.0 },
                voiceVolume: { type: 'number', min: 0, max: 1.0, default: 1.0 },
                conversationMode: { type: 'boolean', default: false }
            },
            gesture: {
                enabled: { type: 'boolean', default: true },
                sensitivity: { type: 'number', min: 0, max: 1.0, default: 0.7 },
                debounceTime: { type: 'number', min: 0, max: 2000, default: 500 },
                smoothing: { type: 'number', min: 0, max: 1.0, default: 0.5 },
                autoCalibrate: { type: 'boolean', default: true }
            },
            ui: {
                showTelemetry: { type: 'boolean', default: true },
                showActivityLog: { type: 'boolean', default: true },
                compactMode: { type: 'boolean', default: false },
                sidebarPosition: { type: 'string', options: ['left', 'right'], default: 'right' }
            },
            system: {
                enableLogging: { type: 'boolean', default: true },
                enableAnalytics: { type: 'boolean', default: false },
                enableNotifications: { type: 'boolean', default: true },
                enableAutoUpdate: { type: 'boolean', default: true }
            },
            privacy: {
                shareUsageData: { type: 'boolean', default: false },
                saveCommandHistory: { type: 'boolean', default: true },
                saveGestureHistory: { type: 'boolean', default: true }
            }
        };
    }
    
    /**
     * Apply profile settings to the system
     */
    applyProfileSettings(profile) {
        // Apply voice settings
        if (window.AIOS?.voiceInput) {
            const voice = window.AIOS.voiceInput;
            voice.setSilenceDetection(profile.settings.voice.enabled);
            // Apply other voice settings...
        }
        
        // Apply gesture settings
        if (window.AIOS?.gestureCalibration) {
            const gesture = window.AIOS.gestureCalibration;
            gesture.setGlobalSensitivity(profile.settings.gesture.sensitivity);
            gesture.setDebounceTime(profile.settings.gesture.debounceTime);
            gesture.setSmoothing(profile.settings.gesture.smoothing);
            gesture.setAutoCalibrate(profile.settings.gesture.autoCalibrate);
        }
        
        // Apply theme
        if (window.AIOS?.themeSystem) {
            window.AIOS.themeSystem.applyTheme(profile.customizations.theme);
        }
        
        // Apply wake words
        if (window.AIOS?.voiceInput && profile.customizations.wakeWords) {
            profile.customizations.wakeWords.forEach(wakeWord => {
                window.AIOS.voiceInput.addWakeWord(wakeWord);
            });
        }
        
        // Apply macros and shortcuts
        if (window.AIOS?.voiceMacros) {
            // Load user's custom macros and shortcuts
            // Implementation depends on macro system structure
        }
        
        console.log(`[MultiUser] Applied settings for ${profile.username}`);
    }
    
    /**
     * Save current profile
     */
    saveCurrentProfile() {
        if (!this.currentUser) return;
        
        // Gather current customizations
        const customizations = {
            theme: localStorage.getItem('aios_current_theme'),
            wakeWords: [], // Get from voice system
            macros: [], // Get from macro system
            shortcuts: [], // Get from shortcut system
            gestures: {} // Get from gesture system
        };
        
        // Update profile
        this.updateProfile(this.currentUser.id, { customizations });
    }
    
    /**
     * Update profile statistics
     */
    updateStats(profileId, statUpdates) {
        const profile = this.profiles.get(profileId);
        if (!profile) return;
        
        Object.keys(statUpdates).forEach(key => {
            if (profile.stats[key] !== undefined) {
                if (typeof statUpdates[key] === 'number') {
                    profile.stats[key] += statUpdates[key];
                } else {
                    profile.stats[key] = statUpdates[key];
                }
            }
        });
        
        this.saveProfiles();
    }
    
    /**
     * Get current user
     */
    getCurrentUser() {
        return this.currentUser ? this.sanitizeProfile(this.currentUser) : null;
    }
    
    /**
     * List all profiles
     */
    listProfiles() {
        return Array.from(this.profiles.values()).map(p => this.sanitizeProfile(p));
    }
    
    /**
     * Export profile
     */
    exportProfile(profileId) {
        const profile = this.profiles.get(profileId);
        
        if (!profile) {
            return {
                success: false,
                error: 'Profile not found'
            };
        }
        
        // Remove sensitive data
        const exportData = {
            ...profile,
            password: undefined,
            exported: new Date().toISOString()
        };
        
        return {
            success: true,
            data: exportData
        };
    }
    
    /**
     * Import profile
     */
    importProfile(profileData) {
        // Validate data
        if (!profileData.username) {
            return {
                success: false,
                error: 'Invalid profile data'
            };
        }
        
        // Generate new ID to avoid conflicts
        const newProfile = {
            ...profileData,
            id: this.generateId(),
            stats: {
                ...profileData.stats,
                created: new Date().toISOString(),
                lastLogin: null,
                totalLogins: 0
            }
        };
        
        return this.createProfile(newProfile);
    }
    
    /**
     * Set profile password
     */
    setPassword(profileId, password) {
        const profile = this.profiles.get(profileId);
        
        if (!profile) {
            return {
                success: false,
                error: 'Profile not found'
            };
        }
        
        // In production, hash the password
        profile.password = password; // TODO: Hash this
        
        this.saveProfiles();
        
        return {
            success: true,
            message: 'Password set successfully'
        };
    }
    
    /**
     * Create default profile
     */
    createDefaultProfile() {
        return this.createProfile({
            username: 'default',
            displayName: 'Default User',
            avatar: this.getDefaultAvatar()
        });
    }
    
    /**
     * Get default avatar
     */
    getDefaultAvatar() {
        return 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="%2300ffff"/><circle cx="50" cy="40" r="15" fill="%23000"/><path d="M30 70 Q50 85 70 70" stroke="%23000" stroke-width="3" fill="none"/></svg>';
    }
    
    /**
     * Sanitize profile (remove sensitive data)
     */
    sanitizeProfile(profile) {
        return {
            id: profile.id,
            username: profile.username,
            displayName: profile.displayName,
            email: profile.email,
            avatar: profile.avatar,
            settings: profile.settings,
            customizations: profile.customizations,
            stats: profile.stats,
            preferences: profile.preferences
        };
    }
    
    /**
     * Save profiles to localStorage
     */
    saveProfiles() {
        try {
            const data = {
                profiles: Array.from(this.profiles.entries())
            };
            localStorage.setItem('aios_user_profiles', JSON.stringify(data));
        } catch (error) {
            console.error('[MultiUser] Error saving profiles:', error);
        }
    }
    
    /**
     * Load profiles from localStorage
     */
    loadProfiles() {
        try {
            const data = localStorage.getItem('aios_user_profiles');
            if (data) {
                const parsed = JSON.parse(data);
                this.profiles = new Map(parsed.profiles || []);
                console.log(`[MultiUser] Loaded ${this.profiles.size} profiles`);
            }
        } catch (error) {
            console.error('[MultiUser] Error loading profiles:', error);
        }
    }
    
    /**
     * Load current user
     */
    loadCurrentUser() {
        const userId = localStorage.getItem('aios_current_user');
        
        if (userId && this.profiles.has(userId)) {
            this.switchProfile(userId);
        } else {
            // Switch to first available profile
            const firstProfile = this.profiles.values().next().value;
            if (firstProfile) {
                this.switchProfile(firstProfile.id);
            }
        }
    }
    
    /**
     * Generate unique ID
     */
    generateId() {
        return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}

export default MultiUserProfiles;
