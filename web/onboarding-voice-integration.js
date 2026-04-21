/**
 * AIOS Onboarding Voice Integration
 * Connects voice commands to onboarding flow
 */

import { ExtendedVoiceCommands } from './voice-commands-extended.js';

class OnboardingVoiceIntegration {
  constructor(voiceController, avatar) {
    this.voiceController = voiceController;
    this.avatar = avatar;
    this.extendedCommands = new ExtendedVoiceCommands(voiceController);
    
    this.currentStep = 0;
    this.totalSteps = 0;
    this.stepData = null;
    
    this.setupIntegration();
  }

  setupIntegration() {
    // Extend the voice controller's command handler
    const originalOnCommand = this.voiceController.onCommand;
    
    this.voiceController.onCommand = async (commandData) => {
      console.log('[OnboardingVoice] Command:', commandData.command);
      
      // Try extended commands first
      const result = await this.extendedCommands.process(commandData.command);
      
      if (result) {
        await this.handleExtendedCommand(result);
      } else {
        // Fall back to original handler
        if (originalOnCommand) {
          originalOnCommand(commandData);
        }
      }
      
      // Process through backend if available
      if (typeof eel !== 'undefined') {
        try {
          const backendResult = await eel.process_voice_command(
            commandData.command,
            this.getStepContext()
          )();
          
          if (backendResult) {
            await this.handleBackendResult(backendResult);
          }
        } catch (error) {
          console.warn('[OnboardingVoice] Backend processing failed:', error);
        }
      }
    };

    // Update hints when step changes
    this.setupStepListener();
  }

  async handleExtendedCommand(result) {
    console.log('[OnboardingVoice] Extended command result:', result);
    
    switch (result.action) {
      case 'navigate':
        if (result.direction === 'next') {
          this.nextStep();
        } else if (result.direction === 'back') {
          this.previousStep();
        }
        break;
      
      case 'pause':
        this.pauseOnboarding();
        break;
      
      case 'resume':
        this.resumeOnboarding();
        break;
      
      case 'status':
        await this.announceStatus();
        break;
      
      case 'install':
        this.startInstallation();
        break;
      
      case 'enable':
      case 'disable':
        this.toggleFeature(result.feature, result.enabled);
        break;
      
      default:
        console.log('[OnboardingVoice] Unhandled action:', result.action);
    }
  }

  async handleBackendResult(result) {
    console.log('[OnboardingVoice] Backend result:', result);
    
    if (result.action === 'next') {
      this.nextStep();
    } else if (result.action === 'back') {
      this.previousStep();
    } else if (result.action === 'status') {
      const message = `Step ${result.step} of ${result.total}: ${result.title}`;
      if (this.avatar) {
        await this.avatar.speak(message, { emotion: 'neutral' });
      }
    } else if (result.action === 'help' && result.hints) {
      this.showHints(result.hints);
    }
  }

  setupStepListener() {
    // Listen for step changes
    const observer = new MutationObserver(() => {
      this.onStepChange();
    });

    const contentElement = document.getElementById('onboarding-content');
    if (contentElement) {
      observer.observe(contentElement, {
        childList: true,
        subtree: true
      });
    }
  }

  async onStepChange() {
    // Update step context
    if (typeof eel !== 'undefined') {
      try {
        this.stepData = await eel.get_current_step_data()();
        this.currentStep = this.stepData.index || 0;
        
        // Get and show hints for new step
        const hints = await eel.get_step_voice_hints(this.stepData)();
        this.showHints(hints);
        
        // Announce step if avatar is available
        if (this.avatar && this.stepData.speech) {
          await this.avatar.speak(this.stepData.speech, {
            emotion: this.stepData.emotion || 'neutral'
          });
        }
      } catch (error) {
        console.warn('[OnboardingVoice] Failed to get step data:', error);
      }
    }
  }

  showHints(hints) {
    if (window.AIOS?.voiceUI && hints && hints.length > 0) {
      window.AIOS.voiceUI.showHints(hints);
    }
  }

  getStepContext() {
    return {
      step: this.currentStep,
      type: this.stepData?.type || 'general',
      title: this.stepData?.title || ''
    };
  }

  // Navigation methods
  nextStep() {
    if (typeof eel !== 'undefined') {
      eel.next_step();
    } else {
      document.getElementById('next-button')?.click();
    }
  }

  previousStep() {
    if (typeof eel !== 'undefined') {
      eel.previous_step();
    }
  }

  // Control methods
  pauseOnboarding() {
    console.log('[OnboardingVoice] Pausing onboarding');
    // Implement pause logic
    window.onboardingPaused = true;
  }

  resumeOnboarding() {
    console.log('[OnboardingVoice] Resuming onboarding');
    window.onboardingPaused = false;
  }

  startInstallation() {
    console.log('[OnboardingVoice] Starting installation');
    // Trigger installation
    if (typeof eel !== 'undefined') {
      // Call backend installation function
    }
  }

  toggleFeature(feature, enabled) {
    console.log(`[OnboardingVoice] ${enabled ? 'Enabling' : 'Disabling'} feature:`, feature);
    
    // Find and toggle checkbox or setting
    const featureName = feature.toLowerCase().replace(/\s+/g, '-');
    const checkbox = document.querySelector(`input[name="${featureName}"]`);
    
    if (checkbox && checkbox.type === 'checkbox') {
      checkbox.checked = enabled !== undefined ? enabled : !checkbox.checked;
      checkbox.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }

  async announceStatus() {
    if (typeof eel !== 'undefined') {
      try {
        const stepData = await eel.get_current_step_data()();
        const message = `Currently on step ${stepData.index + 1}: ${stepData.title}`;
        
        if (this.avatar) {
          await this.avatar.speak(message, { emotion: 'neutral' });
        }
      } catch (error) {
        console.error('[OnboardingVoice] Failed to announce status:', error);
      }
    }
  }

  // Public API for external control
  setStep(stepIndex) {
    this.currentStep = stepIndex;
    this.onStepChange();
  }

  enableVoiceForStep(stepType) {
    // Enable voice input and show appropriate hints
    if (!this.voiceController.isListening) {
      this.voiceController.start();
    }
    
    const hints = this.extendedCommands.getHintsForStep(stepType);
    this.showHints(hints);
  }

  disableVoice() {
    if (this.voiceController.isListening) {
      this.voiceController.stop();
    }
  }
}

// Expose globally
if (typeof window !== 'undefined') {
  window.AIOS = window.AIOS || {};
  window.AIOS.OnboardingVoiceIntegration = OnboardingVoiceIntegration;
}

export { OnboardingVoiceIntegration };
