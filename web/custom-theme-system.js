/**
 * Custom Theme System
 * Create, customize, and apply beautiful themes to PortAIOS
 * Supports real-time preview, import/export, and theme marketplace
 */

export class CustomThemeSystem {
    constructor(options = {}) {
        this.options = {
            enableRealTimePreview: true,
            enableAnimations: true,
            enableGradients: true,
            enableParticles: true,
            ...options
        };
        
        // Current theme
        this.currentTheme = null;
        
        // Theme library
        this.themes = new Map();
        
        // Theme elements cache
        this.themeElements = {
            root: document.documentElement,
            body: document.body,
            styleSheet: null
        };
        
        // Initialize
        this.initialize();
        
        console.log('[CustomTheme] Theme system initialized');
    }
    
    /**
     * Initialize theme system
     */
    initialize() {
        // Create dynamic stylesheet
        this.themeElements.styleSheet = document.createElement('style');
        this.themeElements.styleSheet.id = 'aios-custom-theme';
        document.head.appendChild(this.themeElements.styleSheet);
        
        // Load predefined themes
        this.loadPredefinedThemes();
        
        // Load saved themes
        this.loadSavedThemes();
        
        // Load current theme
        this.loadCurrentTheme();
    }
    
    /**
     * Load predefined themes
     */
    loadPredefinedThemes() {
        const predefined = CustomThemeSystem.getPredefinedThemes();
        
        const defaults = {
            colors: {
                textSecondary: '#ffffff',
                success: '#00ff9d',
                warning: '#ffaa00',
                error: '#ff0055'
            },
            typography: {
                fontFamily: "'Courier New', monospace",
                fontSize: '14px',
                headingFont: "'Orbitron', sans-serif",
                monoFont: "'Courier New', monospace"
            },
            effects: {
                blur: true,
                blurAmount: '10px',
                gradientAngle: 135
            },
            animations: {
                enabled: true,
                speed: 'normal',
                easing: 'ease-in-out'
            },
            advanced: {
                customCSS: '',
                borderRadius: '10px',
                spacing: '1',
                opacity: '0.9'
            }
        };

        Object.entries(predefined).forEach(([id, theme]) => {
            this.themes.set(id, {
                ...theme,
                colors: { ...defaults.colors, ...theme.colors },
                typography: { ...defaults.typography, ...theme.typography },
                effects: { ...defaults.effects, ...theme.effects },
                animations: { ...defaults.animations, ...theme.animations },
                advanced: { ...defaults.advanced, ...theme.advanced },
                id,
                predefined: true,
                created: new Date().toISOString()
            });
        });
        
        console.log(`[CustomTheme] Loaded ${this.themes.size} predefined themes`);
    }
    
    /**
     * Create a custom theme
     */
    createTheme(config) {
        const theme = {
            id: config.id || this.generateId(),
            name: config.name,
            description: config.description || '',
            category: config.category || 'custom',
            
            // Color scheme
            colors: {
                primary: config.colors?.primary || '#00ffff',
                secondary: config.colors?.secondary || '#00ff9d',
                accent: config.colors?.accent || '#ff00ff',
                background: config.colors?.background || '#0a0a1f',
                backgroundSecondary: config.colors?.backgroundSecondary || '#1a1a3f',
                text: config.colors?.text || '#00ffff',
                textSecondary: config.colors?.textSecondary || '#ffffff',
                border: config.colors?.border || '#00ffff',
                success: config.colors?.success || '#00ff9d',
                warning: config.colors?.warning || '#ffaa00',
                error: config.colors?.error || '#ff0055',
                ...config.colors
            },
            
            // Typography
            typography: {
                fontFamily: config.typography?.fontFamily || "'Courier New', monospace",
                fontSize: config.typography?.fontSize || '14px',
                headingFont: config.typography?.headingFont || "'Orbitron', sans-serif",
                monoFont: config.typography?.monoFont || "'Courier New', monospace",
                ...config.typography
            },
            
            // Effects
            effects: {
                glow: config.effects?.glow !== false,
                glowIntensity: config.effects?.glowIntensity || 0.5,
                blur: config.effects?.blur !== false,
                blurAmount: config.effects?.blurAmount || '10px',
                scanlines: config.effects?.scanlines !== false,
                chromatic: config.effects?.chromatic || false,
                particles: config.effects?.particles || false,
                gradient: config.effects?.gradient !== false,
                gradientAngle: config.effects?.gradientAngle || 135,
                ...config.effects
            },
            
            // Animations
            animations: {
                enabled: config.animations?.enabled !== false,
                speed: config.animations?.speed || 'normal', // 'slow', 'normal', 'fast'
                easing: config.animations?.easing || 'ease-in-out',
                ...config.animations
            },
            
            // Advanced
            advanced: {
                customCSS: config.advanced?.customCSS || '',
                borderRadius: config.advanced?.borderRadius || '10px',
                spacing: config.advanced?.spacing || '1',
                opacity: config.advanced?.opacity || '0.9',
                ...config.advanced
            },
            
            created: new Date().toISOString(),
            modified: new Date().toISOString(),
            predefined: false
        };
        
        this.themes.set(theme.id, theme);
        this.saveThemes();
        
        console.log(`[CustomTheme] Created theme: ${theme.name}`);
        
        return theme;
    }
    
    /**
     * Apply a theme
     */
    applyTheme(themeId, preview = false) {
        const theme = this.themes.get(themeId);
        if (!theme) {
            console.error(`[CustomTheme] Theme not found: ${themeId}`);
            return { success: false, error: 'Theme not found' };
        }
        
        // Generate CSS
        const css = this.generateCSS(theme);
        
        // Apply CSS
        this.themeElements.styleSheet.textContent = css;
        
        // Update current theme
        if (!preview) {
            this.currentTheme = theme;
            localStorage.setItem('aios_current_theme', themeId);
        }
        
        // Apply special effects
        this.applyEffects(theme);
        
        console.log(`[CustomTheme] Applied theme: ${theme.name}${preview ? ' (preview)' : ''}`);
        
        return {
            success: true,
            theme: theme.name,
            preview
        };
    }
    
    /**
     * Generate CSS from theme
     */
    generateCSS(theme) {
        const { colors, typography, effects, animations, advanced } = theme;
        
        // Animation speeds
        const animationSpeeds = {
            slow: '0.5s',
            normal: '0.3s',
            fast: '0.15s'
        };
        
        const animationSpeed = animationSpeeds[animations.speed] || '0.3s';
        
        return `
            /* ===== Custom Theme: ${theme.name} ===== */
            
            :root {
                /* Colors */
                --color-primary: ${colors.primary};
                --color-secondary: ${colors.secondary};
                --color-accent: ${colors.accent};
                --color-background: ${colors.background};
                --color-background-secondary: ${colors.backgroundSecondary};
                --color-text: ${colors.text};
                --color-text-secondary: ${colors.textSecondary};
                --color-border: ${colors.border};
                --color-success: ${colors.success};
                --color-warning: ${colors.warning};
                --color-error: ${colors.error};
                
                /* Typography */
                --font-family: ${typography.fontFamily};
                --font-size: ${typography.fontSize};
                --font-heading: ${typography.headingFont};
                --font-mono: ${typography.monoFont};
                
                /* Effects */
                --glow-intensity: ${effects.glowIntensity};
                --blur-amount: ${effects.blurAmount};
                --gradient-angle: ${effects.gradientAngle}deg;
                
                /* Advanced */
                --border-radius: ${advanced.borderRadius};
                --spacing: ${advanced.spacing};
                --opacity: ${advanced.opacity};
                
                /* Animations */
                --animation-speed: ${animationSpeed};
                --animation-easing: ${animations.easing};
            }
            
            /* Background gradient */
            body {
                background: ${effects.gradient 
                    ? `linear-gradient(${effects.gradientAngle}deg, ${colors.background}, ${colors.backgroundSecondary})`
                    : colors.background
                } !important;
                color: ${colors.text} !important;
                font-family: var(--font-family) !important;
                font-size: var(--font-size) !important;
                ${effects.scanlines ? 'background-image: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 255, 255, 0.03) 2px, rgba(0, 255, 255, 0.03) 4px);' : ''}
            }
            
            /* Headings */
            h1, h2, h3, h4, h5, h6 {
                font-family: var(--font-heading) !important;
                color: var(--color-secondary) !important;
                ${effects.glow ? `text-shadow: 0 0 ${20 * effects.glowIntensity}px var(--color-secondary);` : ''}
            }
            
            /* Primary elements */
            .hud, .panel-box, .holo-card {
                background: rgba(${this.hexToRgb(colors.background)}, ${advanced.opacity}) !important;
                border-color: var(--color-border) !important;
                border-radius: var(--border-radius) !important;
                ${effects.glow ? `box-shadow: 0 0 ${20 * effects.glowIntensity}px rgba(${this.hexToRgb(colors.primary)}, 0.3);` : ''}
                ${effects.blur ? `backdrop-filter: blur(${effects.blurAmount});` : ''}
            }
            
            /* Buttons */
            button, .btn {
                background: rgba(${this.hexToRgb(colors.primary)}, 0.1) !important;
                border-color: var(--color-primary) !important;
                color: var(--color-primary) !important;
                border-radius: calc(var(--border-radius) / 2) !important;
                transition: all var(--animation-speed) var(--animation-easing) !important;
            }
            
            button:hover, .btn:hover {
                background: rgba(${this.hexToRgb(colors.primary)}, 0.2) !important;
                ${effects.glow ? `box-shadow: 0 0 ${15 * effects.glowIntensity}px rgba(${this.hexToRgb(colors.primary)}, 0.5);` : ''}
                transform: ${animations.enabled ? 'translateY(-2px)' : 'none'};
            }
            
            /* Inputs */
            input, textarea, select {
                background: rgba(${this.hexToRgb(colors.backgroundSecondary)}, 0.5) !important;
                border-color: var(--color-border) !important;
                color: var(--color-text) !important;
                border-radius: calc(var(--border-radius) / 2) !important;
            }
            
            input:focus, textarea:focus, select:focus {
                border-color: var(--color-primary) !important;
                ${effects.glow ? `box-shadow: 0 0 ${10 * effects.glowIntensity}px rgba(${this.hexToRgb(colors.primary)}, 0.3);` : ''}
            }
            
            /* Links */
            a {
                color: var(--color-primary) !important;
                transition: color var(--animation-speed) var(--animation-easing);
            }
            
            a:hover {
                color: var(--color-secondary) !important;
                ${effects.glow ? `text-shadow: 0 0 ${10 * effects.glowIntensity}px var(--color-secondary);` : ''}
            }
            
            /* Status indicators */
            .stat-dot {
                ${effects.glow ? `box-shadow: 0 0 ${10 * effects.glowIntensity}px currentColor;` : ''}
            }
            
            /* Panel titles */
            .panel-title {
                color: var(--color-secondary) !important;
                ${effects.glow ? `text-shadow: 0 0 ${10 * effects.glowIntensity}px var(--color-secondary);` : ''}
            }
            
            /* Logo */
            .logo {
                color: var(--color-secondary) !important;
                ${effects.glow ? `text-shadow: 0 0 ${15 * effects.glowIntensity}px var(--color-secondary);` : ''}
            }
            
            /* Accent elements */
            .glow-edge {
                border-color: var(--color-primary) !important;
                ${effects.glow ? `box-shadow: 0 0 ${10 * effects.glowIntensity}px rgba(${this.hexToRgb(colors.primary)}, 0.2);` : ''}
            }
            
            /* Chromatic aberration effect */
            ${effects.chromatic ? `
            .logo, h1 {
                position: relative;
            }
            .logo::before, h1::before {
                content: attr(data-text);
                position: absolute;
                left: -2px;
                text-shadow: 2px 0 #ff0000;
                opacity: 0.7;
                animation: chromatic 2s infinite;
            }
            .logo::after, h1::after {
                content: attr(data-text);
                position: absolute;
                left: 2px;
                text-shadow: -2px 0 #00ffff;
                opacity: 0.7;
                animation: chromatic 2s infinite reverse;
            }
            @keyframes chromatic {
                0%, 100% { left: -2px; }
                50% { left: 2px; }
            }
            ` : ''}
            
            /* Custom CSS */
            ${advanced.customCSS}
        `;
    }
    
    /**
     * Apply special effects
     */
    applyEffects(theme) {
        // Particle effect
        if (theme.effects.particles && this.options.enableParticles) {
            this.enableParticles(theme);
        } else {
            this.disableParticles();
        }
        
        // Add chromatic aberration data attributes
        if (theme.effects.chromatic) {
            document.querySelectorAll('.logo, h1').forEach(el => {
                el.setAttribute('data-text', el.textContent);
            });
        }
    }
    
    /**
     * Enable particle background
     */
    enableParticles(theme) {
        if (document.getElementById('theme-particles')) return;
        
        const canvas = document.createElement('canvas');
        canvas.id = 'theme-particles';
        canvas.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
        `;
        document.body.insertBefore(canvas, document.body.firstChild);
        
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        const particles = [];
        const particleCount = 50;
        
        for (let i = 0; i < particleCount; i++) {
            particles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                radius: Math.random() * 2 + 1
            });
        }
        
        const animate = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = theme.colors.primary;
            ctx.globalAlpha = 0.3;
            
            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                
                if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
                if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
                
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                ctx.fill();
            });
            
            requestAnimationFrame(animate);
        };
        
        animate();
    }
    
    /**
     * Disable particles
     */
    disableParticles() {
        const canvas = document.getElementById('theme-particles');
        if (canvas) canvas.remove();
    }
    
    /**
     * Get predefined themes
     */
    static getPredefinedThemes() {
        return {
            cyberpunk: {
                name: 'Cyberpunk',
                description: 'Classic cyberpunk aesthetic',
                category: 'dark',
                colors: {
                    primary: '#00ffff',
                    secondary: '#ff00ff',
                    accent: '#ffff00',
                    background: '#0a0a1f',
                    backgroundSecondary: '#1a0a2e',
                    text: '#00ffff',
                    border: '#00ffff'
                },
                effects: {
                    glow: true,
                    glowIntensity: 0.7,
                    scanlines: true,
                    chromatic: true
                }
            },
            
            matrix: {
                name: 'Matrix',
                description: 'The Matrix green theme',
                category: 'dark',
                colors: {
                    primary: '#00ff00',
                    secondary: '#00ff9d',
                    accent: '#00ffaa',
                    background: '#000000',
                    backgroundSecondary: '#0a1a0a',
                    text: '#00ff00',
                    border: '#00ff00'
                },
                effects: {
                    glow: true,
                    glowIntensity: 0.8,
                    particles: true
                }
            },
            
            neon: {
                name: 'Neon City',
                description: 'Vibrant neon colors',
                category: 'dark',
                colors: {
                    primary: '#ff1493',
                    secondary: '#00ffff',
                    accent: '#ffff00',
                    background: '#0f0015',
                    backgroundSecondary: '#1a0025',
                    text: '#ff1493',
                    border: '#ff1493'
                },
                effects: {
                    glow: true,
                    glowIntensity: 1.0,
                    gradient: true,
                    gradientAngle: 45
                }
            },
            
            oceanic: {
                name: 'Ocean Deep',
                description: 'Deep ocean blues',
                category: 'dark',
                colors: {
                    primary: '#00bfff',
                    secondary: '#1e90ff',
                    accent: '#00ffff',
                    background: '#001a33',
                    backgroundSecondary: '#003366',
                    text: '#00bfff',
                    border: '#00bfff'
                },
                effects: {
                    glow: true,
                    glowIntensity: 0.5,
                    gradient: true,
                    gradientAngle: 180
                }
            },
            
            sunset: {
                name: 'Sunset',
                description: 'Warm sunset colors',
                category: 'warm',
                colors: {
                    primary: '#ff6b6b',
                    secondary: '#ffa500',
                    accent: '#ffff00',
                    background: '#1a0a00',
                    backgroundSecondary: '#2a1500',
                    text: '#ff6b6b',
                    border: '#ff6b6b'
                },
                effects: {
                    glow: true,
                    glowIntensity: 0.6,
                    gradient: true,
                    gradientAngle: 135
                }
            },
            
            minimal: {
                name: 'Minimal',
                description: 'Clean and minimal',
                category: 'light',
                colors: {
                    primary: '#333333',
                    secondary: '#666666',
                    accent: '#999999',
                    background: '#ffffff',
                    backgroundSecondary: '#f5f5f5',
                    text: '#333333',
                    border: '#cccccc'
                },
                effects: {
                    glow: false,
                    scanlines: false,
                    blur: false
                }
            },
            
            synthwave: {
                name: 'Synthwave',
                description: '80s synthwave vibes',
                category: 'retro',
                colors: {
                    primary: '#ff00ff',
                    secondary: '#00ffff',
                    accent: '#ff00aa',
                    background: '#200040',
                    backgroundSecondary: '#350060',
                    text: '#ff00ff',
                    border: '#ff00ff'
                },
                effects: {
                    glow: true,
                    glowIntensity: 0.9,
                    gradient: true,
                    gradientAngle: 90,
                    chromatic: true
                }
            },
            
            terminal: {
                name: 'Terminal',
                description: 'Classic terminal green',
                category: 'retro',
                colors: {
                    primary: '#33ff33',
                    secondary: '#00ff00',
                    accent: '#66ff66',
                    background: '#000000',
                    backgroundSecondary: '#001100',
                    text: '#33ff33',
                    border: '#33ff33'
                },
                effects: {
                    glow: true,
                    glowIntensity: 0.4,
                    scanlines: true
                },
                typography: {
                    fontFamily: "'Courier New', monospace"
                }
            }
        };
    }
    
    /**
     * Utility: Hex to RGB
     */
    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result 
            ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
            : '0, 255, 255';
    }
    
    /**
     * List all themes
     */
    list(category = null) {
        const list = [];
        
        for (const [id, theme] of this.themes) {
            if (!category || theme.category === category) {
                list.push({
                    id: theme.id,
                    name: theme.name,
                    description: theme.description,
                    category: theme.category,
                    predefined: theme.predefined
                });
            }
        }
        
        return list;
    }
    
    /**
     * Delete theme
     */
    delete(themeId) {
        const theme = this.themes.get(themeId);
        if (!theme) {
            return { success: false, error: 'Theme not found' };
        }
        
        if (theme.predefined) {
            return { success: false, error: 'Cannot delete predefined theme' };
        }
        
        this.themes.delete(themeId);
        this.saveThemes();
        
        return {
            success: true,
            message: `Deleted theme: ${theme.name}`
        };
    }
    
    /**
     * Export theme
     */
    export(themeId) {
        const theme = this.themes.get(themeId);
        if (!theme) {
            return { success: false, error: 'Theme not found' };
        }
        
        return {
            ...theme,
            exported: new Date().toISOString()
        };
    }
    
    /**
     * Import theme
     */
    import(themeData) {
        return this.createTheme(themeData);
    }
    
    /**
     * Save themes to localStorage
     */
    saveThemes() {
        try {
            const customThemes = [];
            
            for (const [id, theme] of this.themes) {
                if (!theme.predefined) {
                    customThemes.push([id, theme]);
                }
            }
            
            localStorage.setItem('aios_custom_themes', JSON.stringify(customThemes));
        } catch (error) {
            console.error('[CustomTheme] Error saving themes:', error);
        }
    }
    
    /**
     * Load saved themes
     */
    loadSavedThemes() {
        try {
            const data = localStorage.getItem('aios_custom_themes');
            if (data) {
                const themes = JSON.parse(data);
                themes.forEach(([id, theme]) => {
                    this.themes.set(id, theme);
                });
                console.log(`[CustomTheme] Loaded ${themes.length} custom themes`);
            }
        } catch (error) {
            console.error('[CustomTheme] Error loading themes:', error);
        }
    }
    
    /**
     * Load current theme
     */
    loadCurrentTheme() {
        const themeId = localStorage.getItem('aios_current_theme');
        if (themeId && this.themes.has(themeId)) {
            this.applyTheme(themeId);
        } else {
            // Apply default (cyberpunk)
            this.applyTheme('cyberpunk');
        }
    }
    
    /**
     * Generate unique ID
     */
    generateId() {
        return `theme_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}

export default CustomThemeSystem;
