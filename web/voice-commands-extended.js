/**
 * Extended Voice Commands for AIOS Onboarding
 * Custom commands specific to installation and setup
 */

class ExtendedVoiceCommands {
  constructor(voiceController) {
    this.voiceController = voiceController;
    this.customHandlers = {};
    
    this.registerDefaultCommands();
  }

  registerDefaultCommands() {
    // System control
    this.register('pause', this.handlePause.bind(this));
    this.register('resume', this.handleResume.bind(this));
    this.register('cancel', this.handleCancel.bind(this));
    this.register('restart', this.handleRestart.bind(this));
    
    // Installation specific
    this.register('install', this.handleInstall.bind(this));
    this.register('configure', this.handleConfigure.bind(this));
    this.register('customize', this.handleCustomize.bind(this));
    this.register('default', this.handleDefault.bind(this));
    
    // Information
    this.register('status', this.handleStatus.bind(this));
    this.register('progress', this.handleProgress.bind(this));
    this.register('details', this.handleDetails.bind(this));
    
    // Preferences
    this.register('enable', this.handleEnable.bind(this));
    this.register('disable', this.handleDisable.bind(this));
    this.register('toggle', this.handleToggle.bind(this));
    
    // Navigation shortcuts
    this.register('first', this.handleFirst.bind(this));
    this.register('last', this.handleLast.bind(this));
    this.register('summary', this.handleSummary.bind(this));
  }

  register(commandType, handler) {
    this.customHandlers[commandType] = handler;
    console.log(`[ExtendedCommands] Registered: ${commandType}`);
  }

  async process(command) {
    const lowerCommand = command.toLowerCase().trim();
    
    // Check for registered commands
    for (const [type, handler] of Object.entries(this.customHandlers)) {
      if (lowerCommand.includes(type)) {
        console.log(`[ExtendedCommands] Matched: ${type}`);
        return await handler(command, lowerCommand);
      }
    }
    
    // Parse complex commands
    return this.parseComplexCommand(command);
  }

  parseComplexCommand(command) {
    const lower = command.toLowerCase();
    
    // "Enable X" / "Disable X"
    const enableMatch = lower.match(/enable\s+(.+)/);
    if (enableMatch) {
      return { action: 'enable', feature: enableMatch[1] };
    }
    
    const disableMatch = lower.match(/disable\s+(.+)/);
    if (disableMatch) {
      return { action: 'disable', feature: disableMatch[1] };
    }
    
    // "Go to X" / "Jump to X"
    const gotoMatch = lower.match(/(?:go to|jump to|show me)\s+(.+)/);
    if (gotoMatch) {
      return { action: 'navigate', target: gotoMatch[1] };
    }
    
    // "What is X" / "Tell me about X"
    const infoMatch = lower.match(/(?:what is|tell me about|explain)\s+(.+)/);
    if (infoMatch) {
      return { action: 'info', topic: infoMatch[1] };
    }
    
    return null;
  }

  // System Control Handlers
  async handlePause(command, lower) {
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak("Pausing the process.", { emotion: 'neutral' });
    }
    
    // Pause any ongoing installation
    if (window.pauseOnboarding) {
      window.pauseOnboarding();
    }
    
    return { action: 'pause', status: 'paused' };
  }

  async handleResume(command, lower) {
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak("Resuming.", { emotion: 'neutral' });
    }
    
    if (window.resumeOnboarding) {
      window.resumeOnboarding();
    }
    
    return { action: 'resume', status: 'resumed' };
  }

  async handleCancel(command, lower) {
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak("Are you sure you want to cancel?", { emotion: 'neutral' });
    }
    
    // Request confirmation
    if (window.requestVoiceInput) {
      window.requestVoiceInput('yes_no');
    }
    
    return { action: 'cancel_confirm', awaiting: 'yes_no' };
  }

  async handleRestart(command, lower) {
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak("Restarting from the beginning.", { emotion: 'neutral' });
    }
    
    if (window.restartOnboarding) {
      window.restartOnboarding();
    }
    
    return { action: 'restart' };
  }

  // Installation Handlers
  async handleInstall(command, lower) {
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak("Starting installation.", { emotion: 'happy' });
    }
    
    if (window.startInstallation) {
      window.startInstallation();
    }
    
    return { action: 'install', status: 'starting' };
  }

  async handleConfigure(command, lower) {
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak("Opening configuration.", { emotion: 'neutral' });
    }
    
    if (window.showConfiguration) {
      window.showConfiguration();
    }
    
    return { action: 'configure' };
  }

  async handleCustomize(command, lower) {
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak("Let's customize your settings.", { emotion: 'happy' });
    }
    
    if (window.showCustomization) {
      window.showCustomization();
    }
    
    return { action: 'customize' };
  }

  async handleDefault(command, lower) {
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak("Using default settings.", { emotion: 'neutral' });
    }
    
    if (window.useDefaults) {
      window.useDefaults();
    }
    
    return { action: 'defaults', applied: true };
  }

  // Information Handlers
  async handleStatus(command, lower) {
    const status = window.getCurrentStatus ? window.getCurrentStatus() : 'In progress';
    
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak(`Current status: ${status}`, { emotion: 'neutral' });
    }
    
    return { action: 'status', value: status };
  }

  async handleProgress(command, lower) {
    const progress = window.getProgress ? window.getProgress() : '0%';
    
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak(`Progress: ${progress}`, { emotion: 'neutral' });
    }
    
    return { action: 'progress', value: progress };
  }

  async handleDetails(command, lower) {
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak("Showing detailed information.", { emotion: 'neutral' });
    }
    
    if (window.showDetails) {
      window.showDetails();
    }
    
    return { action: 'details', shown: true };
  }

  // Preference Handlers
  async handleEnable(command, lower) {
    const feature = this.extractFeature(lower, 'enable');
    
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak(`Enabling ${feature}.`, { emotion: 'neutral' });
    }
    
    if (window.toggleFeature) {
      window.toggleFeature(feature, true);
    }
    
    return { action: 'enable', feature: feature, enabled: true };
  }

  async handleDisable(command, lower) {
    const feature = this.extractFeature(lower, 'disable');
    
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak(`Disabling ${feature}.`, { emotion: 'neutral' });
    }
    
    if (window.toggleFeature) {
      window.toggleFeature(feature, false);
    }
    
    return { action: 'disable', feature: feature, enabled: false };
  }

  async handleToggle(command, lower) {
    const feature = this.extractFeature(lower, 'toggle');
    
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak(`Toggling ${feature}.`, { emotion: 'neutral' });
    }
    
    if (window.toggleFeature) {
      window.toggleFeature(feature);
    }
    
    return { action: 'toggle', feature: feature };
  }

  // Navigation Handlers
  async handleFirst(command, lower) {
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak("Going to the first step.", { emotion: 'neutral' });
    }
    
    if (window.goToStep) {
      window.goToStep(0);
    }
    
    return { action: 'navigate', target: 'first' };
  }

  async handleLast(command, lower) {
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak("Going to the last step.", { emotion: 'neutral' });
    }
    
    if (window.goToLastStep) {
      window.goToLastStep();
    }
    
    return { action: 'navigate', target: 'last' };
  }

  async handleSummary(command, lower) {
    if (window.AIOS?.avatar) {
      await window.AIOS.avatar.speak("Showing summary.", { emotion: 'neutral' });
    }
    
    if (window.showSummary) {
      window.showSummary();
    }
    
    return { action: 'summary', shown: true };
  }

  // Utility Methods
  extractFeature(command, prefix) {
    const parts = command.split(prefix);
    if (parts.length > 1) {
      return parts[1].trim();
    }
    return 'feature';
  }

  // Get available commands for current context
  getAvailableCommands(context = {}) {
    const commands = {
      navigation: ['next', 'back', 'skip', 'first', 'last'],
      responses: ['yes', 'no'],
      control: ['pause', 'resume', 'cancel', 'restart'],
      information: ['status', 'progress', 'details', 'summary'],
      installation: ['install', 'configure', 'customize', 'default'],
      utility: ['help', 'repeat']
    };

    // Filter based on context
    if (context.step === 'installation') {
      commands.primary = commands.installation;
    } else if (context.step === 'configuration') {
      commands.primary = ['enable', 'disable', 'toggle'];
    } else {
      commands.primary = commands.navigation;
    }

    return commands;
  }

  // Generate hints based on current step
  getHintsForStep(stepType) {
    const hintMap = {
      'welcome': [
        'next',
        'help',
        'skip'
      ],
      'installation': [
        'install',
        'customize',
        'default settings',
        'cancel'
      ],
      'configuration': [
        'enable [feature]',
        'disable [feature]',
        'next',
        'skip'
      ],
      'progress': [
        'status',
        'pause',
        'cancel'
      ],
      'confirmation': [
        'yes',
        'no',
        'back'
      ],
      'complete': [
        'restart',
        'summary',
        'finish'
      ]
    };

    return hintMap[stepType] || ['next', 'back', 'help'];
  }
}

// Voice command patterns for specific scenarios
const VOICE_PATTERNS = {
  // Package management
  packages: {
    patterns: [
      /install (?:all|everything)/i,
      /install (.+)/i,
      /(?:don't|do not) install (.+)/i,
      /skip (?:package|installation)/i
    ],
    handler: 'handlePackageCommand'
  },
  
  // Configuration
  settings: {
    patterns: [
      /set (.+) to (.+)/i,
      /change (.+) to (.+)/i,
      /update (.+)/i
    ],
    handler: 'handleSettingCommand'
  },
  
  // Feature selection
  features: {
    patterns: [
      /(?:i want|add|include) (.+)/i,
      /(?:i don't want|remove|exclude) (.+)/i,
      /(?:with|without) (.+)/i
    ],
    handler: 'handleFeatureCommand'
  }
};

// Export
export { ExtendedVoiceCommands, VOICE_PATTERNS };

// Global API
if (typeof window !== 'undefined') {
  window.AIOS = window.AIOS || {};
  window.AIOS.ExtendedVoiceCommands = ExtendedVoiceCommands;
  window.AIOS.VOICE_PATTERNS = VOICE_PATTERNS;
}
