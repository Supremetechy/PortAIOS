/**
 * AIOS Dynamic UI Theme System
 * Multiple visual themes for the dynamic UI interface
 */

const UI_THEMES = {
  // Classic AIOS Cyan
  cyan: {
    name: 'Cyan Matrix',
    primary: '#00ffff',
    secondary: '#0099cc',
    accent: '#00ff99',
    background: 'rgba(0, 10, 20, 0.95)',
    backgroundAlt: 'rgba(0, 0, 0, 0.3)',
    text: '#00ffff',
    textAlt: '#ffffff',
    border: 'rgba(0, 255, 255, 0.3)',
    glow: 'rgba(0, 255, 255, 0.5)',
    gradient: 'linear-gradient(135deg, rgba(0, 255, 255, 0.1), rgba(0, 153, 204, 0.1))',
    shadow: '0 0 20px rgba(0, 255, 255, 0.3)',
    palette: 'cyan' // for avatar
  },

  // Purple Neon
  purple: {
    name: 'Purple Neon',
    primary: '#ff00ff',
    secondary: '#9933ff',
    accent: '#ff66ff',
    background: 'rgba(20, 0, 30, 0.95)',
    backgroundAlt: 'rgba(30, 0, 40, 0.3)',
    text: '#ff00ff',
    textAlt: '#ffccff',
    border: 'rgba(255, 0, 255, 0.3)',
    glow: 'rgba(255, 0, 255, 0.5)',
    gradient: 'linear-gradient(135deg, rgba(255, 0, 255, 0.1), rgba(153, 51, 255, 0.1))',
    shadow: '0 0 20px rgba(255, 0, 255, 0.3)',
    palette: 'magenta'
  },

  // Green Terminal
  green: {
    name: 'Green Terminal',
    primary: '#00ff00',
    secondary: '#00cc00',
    accent: '#33ff33',
    background: 'rgba(0, 10, 0, 0.95)',
    backgroundAlt: 'rgba(0, 20, 0, 0.3)',
    text: '#00ff00',
    textAlt: '#ccffcc',
    border: 'rgba(0, 255, 0, 0.3)',
    glow: 'rgba(0, 255, 0, 0.5)',
    gradient: 'linear-gradient(135deg, rgba(0, 255, 0, 0.1), rgba(0, 204, 0, 0.1))',
    shadow: '0 0 20px rgba(0, 255, 0, 0.3)',
    palette: 'green'
  },

  // Matrix Code Rain
  matrix: {
    name: 'Matrix',
    primary: '#00ff41',
    secondary: '#008f11',
    accent: '#00ff66',
    background: 'rgba(0, 0, 0, 0.98)',
    backgroundAlt: 'rgba(0, 20, 0, 0.4)',
    text: '#00ff41',
    textAlt: '#33ff66',
    border: 'rgba(0, 255, 65, 0.3)',
    glow: 'rgba(0, 255, 65, 0.6)',
    gradient: 'linear-gradient(135deg, rgba(0, 255, 65, 0.1), rgba(0, 143, 17, 0.1))',
    shadow: '0 0 25px rgba(0, 255, 65, 0.4)',
    palette: 'green'
  },

  // Amber Terminal
  amber: {
    name: 'Amber Retro',
    primary: '#ffb000',
    secondary: '#ff9500',
    accent: '#ffc733',
    background: 'rgba(20, 10, 0, 0.95)',
    backgroundAlt: 'rgba(30, 15, 0, 0.3)',
    text: '#ffb000',
    textAlt: '#ffd480',
    border: 'rgba(255, 176, 0, 0.3)',
    glow: 'rgba(255, 176, 0, 0.5)',
    gradient: 'linear-gradient(135deg, rgba(255, 176, 0, 0.1), rgba(255, 149, 0, 0.1))',
    shadow: '0 0 20px rgba(255, 176, 0, 0.3)',
    palette: 'amber'
  },

  // Red Alert
  red: {
    name: 'Red Alert',
    primary: '#ff0000',
    secondary: '#cc0000',
    accent: '#ff3333',
    background: 'rgba(20, 0, 0, 0.95)',
    backgroundAlt: 'rgba(30, 0, 0, 0.3)',
    text: '#ff0000',
    textAlt: '#ffcccc',
    border: 'rgba(255, 0, 0, 0.3)',
    glow: 'rgba(255, 0, 0, 0.5)',
    gradient: 'linear-gradient(135deg, rgba(255, 0, 0, 0.1), rgba(204, 0, 0, 0.1))',
    shadow: '0 0 20px rgba(255, 0, 0, 0.3)',
    palette: 'red'
  },

  // Blue Ice
  blue: {
    name: 'Blue Ice',
    primary: '#0099ff',
    secondary: '#0066cc',
    accent: '#33aaff',
    background: 'rgba(0, 10, 30, 0.95)',
    backgroundAlt: 'rgba(0, 0, 40, 0.3)',
    text: '#0099ff',
    textAlt: '#cce6ff',
    border: 'rgba(0, 153, 255, 0.3)',
    glow: 'rgba(0, 153, 255, 0.5)',
    gradient: 'linear-gradient(135deg, rgba(0, 153, 255, 0.1), rgba(0, 102, 204, 0.1))',
    shadow: '0 0 20px rgba(0, 153, 255, 0.3)',
    palette: 'blue'
  },

  // Dark Mode (minimal colors)
  dark: {
    name: 'Dark',
    primary: '#ffffff',
    secondary: '#cccccc',
    accent: '#aaaaaa',
    background: 'rgba(10, 10, 10, 0.98)',
    backgroundAlt: 'rgba(20, 20, 20, 0.5)',
    text: '#ffffff',
    textAlt: '#cccccc',
    border: 'rgba(255, 255, 255, 0.2)',
    glow: 'rgba(255, 255, 255, 0.3)',
    gradient: 'linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(200, 200, 200, 0.05))',
    shadow: '0 0 15px rgba(255, 255, 255, 0.2)',
    palette: 'gray'
  }
};

class UIThemeManager {
  constructor(dynamicUI, avatarRenderer) {
    this.dynamicUI = dynamicUI;
    this.avatarRenderer = avatarRenderer;
    this.currentTheme = 'cyan';
    this.styleElement = null;
    
    this._init();
  }

  _init() {
    // Create style element for theme CSS
    this.styleElement = document.createElement('style');
    this.styleElement.id = 'aios-theme-styles';
    document.head.appendChild(this.styleElement);
    
    // Apply default theme
    this.applyTheme('cyan');
    
    console.log('[ThemeManager] Initialized with themes:', Object.keys(UI_THEMES));
  }

  /**
   * Apply a theme
   */
  applyTheme(themeName) {
    const theme = UI_THEMES[themeName];
    if (!theme) {
      console.warn(`[ThemeManager] Theme '${themeName}' not found`);
      return false;
    }

    console.log(`[ThemeManager] Applying theme: ${theme.name}`);
    this.currentTheme = themeName;

    // Generate CSS for the theme
    const css = this._generateThemeCSS(theme);
    this.styleElement.textContent = css;

    // Update avatar palette if available
    if (this.avatarRenderer && this.avatarRenderer.setColorPalette) {
      this.avatarRenderer.setColorPalette(theme.palette);
    }

    // Update CSS variables
    this._updateCSSVariables(theme);

    // Emit theme change event
    this._emitEvent('themeChanged', { theme: themeName, config: theme });

    return true;
  }

  /**
   * Generate complete CSS for a theme
   */
  _generateThemeCSS(theme) {
    return `
      /* AIOS Dynamic UI Theme: ${theme.name} */
      
      /* UI Mode Containers */
      .ui-mode-container {
        background: ${theme.background} !important;
        color: ${theme.text} !important;
      }

      .ui-mode-container h1,
      .ui-mode-container h2,
      .ui-mode-container h3,
      .ui-mode-container h4 {
        color: ${theme.primary} !important;
      }

      /* Desktop Mode */
      .desktop-header,
      .document-header,
      .media-header {
        border-bottom: 1px solid ${theme.border} !important;
      }

      .desktop-footer {
        border-top: 1px solid ${theme.border} !important;
        color: ${theme.text} !important;
      }

      .breadcrumb {
        color: ${theme.text} !important;
      }

      /* File Items */
      .file-item {
        border: 1px solid ${theme.border} !important;
        background: ${theme.gradient} !important;
      }

      .file-item:hover {
        background: ${theme.backgroundAlt} !important;
        box-shadow: ${theme.shadow} !important;
        border-color: ${theme.primary} !important;
      }

      /* Buttons */
      .ui-btn,
      .doc-btn,
      .media-close,
      button {
        background: ${theme.gradient} !important;
        border: 1px solid ${theme.primary} !important;
        color: ${theme.primary} !important;
      }

      .ui-btn:hover,
      .doc-btn:hover,
      button:hover {
        background: ${theme.backgroundAlt} !important;
        box-shadow: ${theme.shadow} !important;
      }

      /* Text Elements */
      .glitch-text {
        color: ${theme.primary} !important;
      }

      /* Mode Badge */
      .mode-badge {
        background: ${theme.gradient} !important;
        border: 1px solid ${theme.primary} !important;
        color: ${theme.primary} !important;
      }

      /* Voice Indicator */
      .voice-indicator {
        background: ${theme.gradient} !important;
        border: 2px solid ${theme.primary} !important;
      }

      .voice-indicator:hover {
        background: ${theme.backgroundAlt} !important;
      }

      .voice-indicator.active {
        animation: voicePulse-${this.currentTheme} 1s infinite !important;
      }

      @keyframes voicePulse-${this.currentTheme} {
        0%, 100% { box-shadow: 0 0 20px ${theme.glow}; }
        50% { box-shadow: 0 0 40px ${theme.glow}, 0 0 60px ${theme.glow}; }
      }

      /* Terminal */
      .terminal-header {
        background: ${theme.gradient} !important;
        border-bottom: 1px solid ${theme.primary} !important;
        color: ${theme.primary} !important;
      }

      .terminal-output {
        color: ${theme.accent} !important;
      }

      .terminal-input-container {
        background: ${theme.backgroundAlt} !important;
        border-top: 1px solid ${theme.border} !important;
      }

      #terminal-input {
        color: ${theme.accent} !important;
      }

      #terminal-input::placeholder {
        color: ${theme.border} !important;
      }

      /* Document Viewer */
      #document-viewer {
        color: ${theme.text} !important;
      }

      #document-viewer code {
        background: ${theme.backgroundAlt} !important;
        color: ${theme.accent} !important;
      }

      #document-viewer pre {
        background: ${theme.backgroundAlt} !important;
        border: 1px solid ${theme.border} !important;
      }

      /* Scrollbars */
      .ui-mode-container::-webkit-scrollbar-track {
        background: ${theme.backgroundAlt} !important;
      }

      .ui-mode-container::-webkit-scrollbar-thumb {
        background: ${theme.border} !important;
      }

      .ui-mode-container::-webkit-scrollbar-thumb:hover {
        background: ${theme.glow} !important;
      }

      /* Links */
      a {
        color: ${theme.primary} !important;
      }

      a:hover {
        color: ${theme.accent} !important;
      }

      /* Status Bar */
      .status-value {
        color: ${theme.primary} !important;
      }

      /* Telemetry */
      .tel-dot {
        background: ${theme.primary} !important;
        box-shadow: 0 0 10px ${theme.glow} !important;
      }

      /* Background Grid */
      .bg-grid {
        background-image: 
          linear-gradient(${theme.border} 1px, transparent 1px),
          linear-gradient(90deg, ${theme.border} 1px, transparent 1px) !important;
      }

      /* Selection */
      ::selection {
        background: ${theme.glow} !important;
        color: ${theme.background} !important;
      }

      /* Loading Spinner */
      .loading-spinner {
        border: 3px solid ${theme.backgroundAlt} !important;
        border-top: 3px solid ${theme.primary} !important;
      }

      /* Table Styles */
      table {
        border: 1px solid ${theme.border} !important;
      }

      th {
        background: ${theme.gradient} !important;
        color: ${theme.primary} !important;
        border-bottom: 2px solid ${theme.glow} !important;
      }

      td {
        border-bottom: 1px solid ${theme.border} !important;
        color: ${theme.text} !important;
      }

      tr:hover {
        background: ${theme.backgroundAlt} !important;
      }

      /* Code Blocks */
      pre code {
        color: ${theme.text} !important;
      }

      .language-javascript .keyword { color: ${theme.accent} !important; }
      .language-python .keyword { color: ${theme.accent} !important; }
    `;
  }

  /**
   * Update CSS variables for dynamic usage
   */
  _updateCSSVariables(theme) {
    const root = document.documentElement;
    root.style.setProperty('--theme-primary', theme.primary);
    root.style.setProperty('--theme-secondary', theme.secondary);
    root.style.setProperty('--theme-accent', theme.accent);
    root.style.setProperty('--theme-background', theme.background);
    root.style.setProperty('--theme-background-alt', theme.backgroundAlt);
    root.style.setProperty('--theme-text', theme.text);
    root.style.setProperty('--theme-border', theme.border);
    root.style.setProperty('--theme-glow', theme.glow);
    root.style.setProperty('--theme-shadow', theme.shadow);
  }

  /**
   * Get available themes
   */
  getAvailableThemes() {
    return Object.keys(UI_THEMES).map(key => ({
      id: key,
      name: UI_THEMES[key].name,
      primary: UI_THEMES[key].primary
    }));
  }

  /**
   * Get current theme
   */
  getCurrentTheme() {
    return {
      id: this.currentTheme,
      config: UI_THEMES[this.currentTheme]
    };
  }

  /**
   * Cycle to next theme
   */
  nextTheme() {
    const themes = Object.keys(UI_THEMES);
    const currentIndex = themes.indexOf(this.currentTheme);
    const nextIndex = (currentIndex + 1) % themes.length;
    this.applyTheme(themes[nextIndex]);
    return themes[nextIndex];
  }

  /**
   * Cycle to previous theme
   */
  previousTheme() {
    const themes = Object.keys(UI_THEMES);
    const currentIndex = themes.indexOf(this.currentTheme);
    const prevIndex = (currentIndex - 1 + themes.length) % themes.length;
    this.applyTheme(themes[prevIndex]);
    return themes[prevIndex];
  }

  /**
   * Create theme selector UI
   */
  createThemeSelector(container) {
    const selector = document.createElement('div');
    selector.className = 'theme-selector';
    selector.style.cssText = `
      display: flex;
      gap: 10px;
      padding: 20px;
      background: var(--theme-background-alt);
      border: 1px solid var(--theme-border);
      border-radius: 8px;
      flex-wrap: wrap;
    `;

    const title = document.createElement('h3');
    title.textContent = 'Theme Selector';
    title.style.cssText = `
      width: 100%;
      margin: 0 0 10px 0;
      color: var(--theme-primary);
      font-size: 1.2em;
    `;
    selector.appendChild(title);

    const themes = this.getAvailableThemes();
    themes.forEach(theme => {
      const btn = document.createElement('button');
      btn.textContent = theme.name;
      btn.className = 'theme-btn';
      btn.style.cssText = `
        padding: 10px 20px;
        background: ${theme.id === this.currentTheme ? 'var(--theme-gradient)' : 'transparent'};
        border: 2px solid ${theme.primary};
        color: ${theme.primary};
        cursor: pointer;
        border-radius: 6px;
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
      `;

      // Color indicator
      const indicator = document.createElement('span');
      indicator.style.cssText = `
        position: absolute;
        left: 5px;
        top: 50%;
        transform: translateY(-50%);
        width: 8px;
        height: 8px;
        background: ${theme.primary};
        border-radius: 50%;
        box-shadow: 0 0 10px ${theme.primary};
      `;
      btn.appendChild(indicator);

      btn.addEventListener('click', () => {
        this.applyTheme(theme.id);
        // Update active state
        selector.querySelectorAll('.theme-btn').forEach(b => {
          b.style.background = 'transparent';
        });
        btn.style.background = 'var(--theme-gradient)';
      });

      btn.addEventListener('mouseenter', () => {
        if (theme.id !== this.currentTheme) {
          btn.style.background = `${theme.primary}22`;
          btn.style.transform = 'translateY(-2px)';
        }
      });

      btn.addEventListener('mouseleave', () => {
        if (theme.id !== this.currentTheme) {
          btn.style.background = 'transparent';
          btn.style.transform = 'translateY(0)';
        }
      });

      selector.appendChild(btn);
    });

    if (container) {
      container.appendChild(selector);
    }

    return selector;
  }

  _emitEvent(name, data) {
    const event = new CustomEvent(`theme:${name}`, { detail: data });
    window.dispatchEvent(event);
  }

  destroy() {
    if (this.styleElement) {
      this.styleElement.remove();
    }
  }
}

// Make available globally
if (typeof window !== 'undefined') {
  window.UIThemeManager = UIThemeManager;
  window.UI_THEMES = UI_THEMES;
}

export { UIThemeManager, UI_THEMES };
