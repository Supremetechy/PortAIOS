import { AvatarController } from './avatar-controller.js';
import { VoiceInputController, VoiceCommandParser } from './voice-input.js';
import { VoiceUI } from './voice-ui.js';

const state = {
  onboarding: null,
  gestureUnlocked: false,
  pendingSpeech: null,
  telemetryTimer: null,
};

const elements = {};

function bindElements() {
  elements.app = document.getElementById('app');
  elements.binaryAvatarContainer = document.getElementById('binary-avatar-container');
  elements.avatarPlaceholder = document.getElementById('avatar-placeholder');
  elements.avatarStatusText = document.getElementById('avatar-status-text');
  elements.voiceStatus = document.getElementById('voice-status');
  elements.speechStatus = document.getElementById('speech-status');
  elements.voiceBars = document.getElementById('voice-bars');
  elements.stepKeyLabel = document.getElementById('step-key-label');
  elements.progressFill = document.getElementById('progress-fill');
  elements.progressReadout = document.getElementById('progress-readout');
  elements.progressTotal = document.getElementById('progress-total');
  elements.stepCounter = document.getElementById('step-counter');
  elements.stepTitle = document.getElementById('step-title');
  elements.agentLine = document.getElementById('agent-line');
  elements.stepBody = document.getElementById('step-body');
  elements.prevButton = document.getElementById('prev-button');
  elements.nextButton = document.getElementById('next-button');
  elements.nextButtonLabel = document.getElementById('next-button-label');
  elements.wizardStatus = document.getElementById('wizard-status');
  elements.voiceHintFooter = document.getElementById('voice-hint-footer');
  elements.restartOnboardingButton = document.getElementById('restart-onboarding-button');
  elements.telemetryCpu = document.getElementById('telemetry-cpu');
  elements.telemetryMemory = document.getElementById('telemetry-memory');
  elements.telemetryDisk = document.getElementById('telemetry-disk');
  elements.telemetryClock = document.getElementById('telemetry-clock');
  elements.systemNameLabel = document.getElementById('system-name-label');
  elements.installPathLabel = document.getElementById('install-path-label');
  elements.voiceUiContainer = document.getElementById('voice-ui-container');
}

function eelReady() {
  return typeof eel !== 'undefined'
    && typeof eel.get_onboarding_state === 'function'
    && typeof eel.next_step === 'function'
    && typeof eel.previous_step === 'function'
    && typeof eel.update_onboarding_config === 'function'
    && typeof eel.detect_hardware === 'function'
    && typeof eel.reset_onboarding === 'function'
    && typeof eel.complete_onboarding === 'function';
}

async function waitForEel(timeoutMs = 8000) {
  const startedAt = Date.now();
  while (!eelReady()) {
    if (Date.now() - startedAt > timeoutMs) {
      return false;
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  return true;
}

function setWizardStatus(message, tone = 'neutral') {
  elements.wizardStatus.textContent = message;
  elements.wizardStatus.dataset.tone = tone;
}

function queueOrSpeak(text, emotion = 'neutral') {
  if (!window.AIOS?.avatar || !text) {
    return;
  }
  if (!state.gestureUnlocked) {
    state.pendingSpeech = { text, emotion };
    return;
  }
  try {
    window.AIOS.avatar.stop?.();
    window.AIOS.avatar.speak(text, { emotion });
  } catch (error) {
    console.warn('[Onboarding] Avatar speech failed', error);
  }
}

function flushQueuedSpeech() {
  if (!state.pendingSpeech) {
    return;
  }
  const { text, emotion } = state.pendingSpeech;
  state.pendingSpeech = null;
  queueOrSpeak(text, emotion);
}

function installGestureUnlock() {
  const unlock = () => {
    state.gestureUnlocked = true;
    flushQueuedSpeech();
  };
  window.addEventListener('pointerdown', unlock, { once: true });
  window.addEventListener('keydown', unlock, { once: true });
}

function updateClock() {
  elements.telemetryClock.textContent = new Date().toLocaleTimeString();
}

async function refreshTelemetry() {
  updateClock();
  if (!eelReady() || typeof eel.get_system_stats !== 'function') {
    return;
  }
  try {
    const stats = await eel.get_system_stats()();
    elements.telemetryCpu.textContent = `${Math.round(stats.cpu_usage || 0)}%`;
    elements.telemetryMemory.textContent = `${Math.round(stats.memory_usage || 0)}%`;
    elements.telemetryDisk.textContent = `${Math.round(stats.disk_usage || 0)}%`;
  } catch (error) {
    console.warn('[Onboarding] Telemetry unavailable', error);
  }
}

function startTelemetryLoop() {
  refreshTelemetry();
  state.telemetryTimer = window.setInterval(refreshTelemetry, 4000);
}

async function initAvatar() {
  elements.avatarStatusText.textContent = 'Initializing';
  try {
    // Wait for AI Guardian 3D from onboarding-guardian.js
    console.log('[Onboarding] Waiting for AI Guardian 3D...');
    let attempts = 0;
    while (!window.AIOS?.guardian && attempts < 50) {
      await new Promise(r => setTimeout(r, 100));
      attempts++;
    }
    
    if (window.AIOS?.guardian) {
      console.log('[Onboarding] ✓ Using AI Guardian 3D avatar');
      elements.avatarPlaceholder.style.display = 'none';
      elements.avatarStatusText.textContent = 'Online';
      elements.speechStatus.textContent = 'Ready';
      // Set window.AIOS.avatar for backward compatibility
      window.AIOS.avatar = window.AIOS.guardian;
      return;
    }
    
    // Fallback to binary avatar if Guardian fails
    console.warn('[Onboarding] AI Guardian not available, using binary avatar fallback');
    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    window.AIOS = window.AIOS || {};
    window.AIOS.avatar = new AvatarController(elements.binaryAvatarContainer, {
      colorPalette: 'matrix',
      digitCount: isMobile ? 3000 : 6000,
      enableCRT: !isMobile,
      enableChromatic: !isMobile,
      enableBloom: true,
    });
    elements.avatarPlaceholder.style.display = 'none';
    elements.avatarStatusText.textContent = 'Online';
    elements.speechStatus.textContent = 'Ready';
  } catch (error) {
    console.error('[Onboarding] Avatar initialization failed', error);
    elements.avatarPlaceholder.style.display = 'flex';
    elements.avatarStatusText.textContent = 'Fallback';
    elements.speechStatus.textContent = 'Browser';
  }
}

function initVoice() {
  if (!VoiceInputController.isSupported()) {
    elements.voiceStatus.textContent = 'Unsupported';
    return;
  }

  const voiceUI = new VoiceUI(elements.voiceUiContainer, {
    position: 'bottom-center',
    showTranscript: true,
    showWaveform: true,
  });

  const voiceInput = new VoiceInputController({
    wakeWords: ['hey aios', 'aios', 'computer'],
    continuous: true,
    autoStart: false,
    onTranscript: (data) => {
      voiceUI.updateTranscript(data.interim, data.final);
    },
    onCommand: ({ command }) => {
      handleVoiceCommand(command);
    },
    onWakeWord: () => {
      elements.voiceStatus.textContent = 'Listening';
      elements.voiceBars.classList.add('active');
      queueOrSpeak('Listening. Say next, back, detect hardware, or repeat.', 'happy');
    },
    onStateChange: (value) => {
      voiceUI.setState(value);
      elements.voiceStatus.textContent = value;
      elements.voiceBars.classList.toggle('active', value === 'listening' || value === 'processing');
    },
    onError: (error) => {
      console.warn('[Onboarding] Voice error', error);
      elements.voiceStatus.textContent = 'Error';
      elements.voiceBars.classList.remove('active');
    },
  });

  voiceInput.setAvatar?.(window.AIOS?.avatar);
  voiceUI.onMicClick(async () => {
    try {
      const granted = await VoiceInputController.requestPermission();
      if (!granted) {
        setWizardStatus('Microphone permission is required for voice setup.', 'warn');
        return;
      }
      if (voiceInput.isListening) {
        voiceInput.stop();
      } else {
        voiceInput.start();
      }
    } catch (error) {
      console.warn('[Onboarding] Voice start failed', error);
    }
  });

  window.AIOS.voiceUI = voiceUI;
  window.AIOS.voiceInput = voiceInput;
  elements.voiceStatus.textContent = 'Standby';
}

function renderWelcomeStep() {
  return `
    <div class="step-grid">
      <div class="step-card">
        <h3>What we will configure</h3>
        <ul class="step-list">
          <li>Detect your hardware and AI acceleration options</li>
          <li>Choose GPU usage for local AI workloads</li>
          <li>Set your identity, system name, and install path</li>
          <li>Finalize your AIOS environment and open the main interface</li>
        </ul>
      </div>
      <div class="step-card">
        <h3>Voice shortcuts</h3>
        <p class="inline-note">You can say <strong>next</strong>, <strong>back</strong>, <strong>repeat</strong>, or <strong>detect hardware</strong> at any time after enabling the microphone.</p>
      </div>
    </div>
    <div class="voice-hint">Click anywhere once to enable spoken guidance, then use the mic control to speak commands.</div>
  `;
}

function hardwareSummaryMarkup(hardware) {
  if (!hardware) {
    return `
      <div class="status-banner">
        <strong>No hardware report yet.</strong>
        <span>Run detection now to tailor AIOS to this machine.</span>
      </div>
    `;
  }

  const accelerators = hardware.processors
    .filter((processor) => processor.processor_type !== 'cpu')
    .map((processor) => `${processor.vendor.toUpperCase()} ${processor.model}`);

  return `
    <div class="summary-grid">
      <div class="summary-item"><span class="summary-key">Host</span><span class="summary-value">${hardware.hostname}</span></div>
      <div class="summary-item"><span class="summary-key">OS</span><span class="summary-value">${hardware.os_type} ${hardware.architecture}</span></div>
      <div class="summary-item"><span class="summary-key">Memory</span><span class="summary-value">${hardware.memory.total_gb} GB total</span></div>
      <div class="summary-item"><span class="summary-key">GPUs</span><span class="summary-value">${hardware.gpu_count}</span></div>
    </div>
    <div class="step-card compact">
      <h3>Detected accelerators</h3>
      <p class="inline-note">${accelerators.length ? accelerators.join(' • ') : 'No dedicated GPU, TPU, or NPU detected.'}</p>
    </div>
  `;
}

function renderHardwareStep(config) {
  return `
    <div class="response-options">
      <button type="button" class="response-btn" id="detect-hardware-btn">Run Hardware Detection</button>
      <button type="button" class="response-btn subtle" id="refresh-telemetry-btn">Refresh Live Stats</button>
    </div>
    ${hardwareSummaryMarkup(config.hardware_summary)}
    <div class="voice-hint">Recommended: run detection before continuing so GPU and acceleration settings match this system.</div>
  `;
}

function renderGpuStep(config) {
  const hardware = config.hardware_summary;
  const gpuAvailable = Boolean(hardware?.has_gpu);
  const gpuDetails = gpuAvailable
    ? hardware.processors.filter((processor) => processor.processor_type === 'gpu')
        .map((processor) => `${processor.vendor.toUpperCase()} ${processor.model}`).join(' • ')
    : 'No supported GPU detected. AIOS will default to CPU execution.';

  return `
    <div class="step-card">
      <h3>Acceleration profile</h3>
      <p class="inline-note">${gpuDetails}</p>
    </div>
    <label class="toggle-row ${gpuAvailable ? '' : 'disabled'}">
      <input type="checkbox" id="gpu-enabled" ${config.gpu_enabled ? 'checked' : ''} ${gpuAvailable ? '' : 'disabled'}>
      <span>
        <strong>Enable GPU acceleration</strong>
        <small>Use local hardware acceleration for supported AI workloads.</small>
      </span>
    </label>
    <div class="voice-hint">${gpuAvailable ? 'Say next to keep this selection or back to review detection.' : 'You can continue without a GPU. AIOS will remain fully usable on CPU.'}</div>
  `;
}

function renderSystemStep(config) {
  return `
    <div class="wizard-form">
      <label class="field">
        <span>Your name</span>
        <input type="text" id="user-name" value="${escapeHtml(config.user_name || '')}" placeholder="Enter your name">
      </label>
      <label class="field">
        <span>System name</span>
        <input type="text" id="system-name" value="${escapeHtml(config.system_name || '')}" placeholder="e.g. atlas-aios">
      </label>
      <label class="field">
        <span>Installation path</span>
        <input type="text" id="install-path" value="${escapeHtml(config.install_path || '')}" placeholder="/path/to/aios">
      </label>
      <label class="toggle-row">
        <input type="checkbox" id="auto-start" ${config.auto_start ? 'checked' : ''}>
        <span>
          <strong>Start AIOS automatically on boot</strong>
          <small>Useful on a dedicated workstation or always-on home lab machine.</small>
        </span>
      </label>
      <label class="toggle-row">
        <input type="checkbox" id="telemetry-enabled" ${config.telemetry_enabled ? 'checked' : ''}>
        <span>
          <strong>Enable anonymous telemetry</strong>
          <small>Share non-personal usage signals to improve future AIOS iterations.</small>
        </span>
      </label>
    </div>
  `;
}

function renderCompleteStep(config) {
  const hardware = config.hardware_summary;
  return `
    <div class="step-card">
      <h3>Ready to launch</h3>
      <ul class="step-list compact">
        <li>User profile: ${escapeHtml(config.user_name || 'Not set')}</li>
        <li>System name: ${escapeHtml(config.system_name || 'Not set')}</li>
        <li>Install path: ${escapeHtml(config.install_path || 'Not set')}</li>
        <li>Acceleration: ${config.gpu_enabled ? 'GPU enabled' : 'CPU only'}</li>
        <li>Telemetry: ${config.telemetry_enabled ? 'Enabled' : 'Disabled'}</li>
        <li>Hardware scan: ${hardware ? `Completed on ${hardware.hostname}` : 'Skipped'}</li>
      </ul>
    </div>
    <div class="status-banner success">
      <strong>Final step.</strong>
      <span>Select launch to open the main avatar-integration.html workspace.</span>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderStepBody(step, config) {
  switch (step.key) {
    case 'welcome':
      return renderWelcomeStep();
    case 'hardware_setup':
      return renderHardwareStep(config);
    case 'gpu_config':
      return renderGpuStep(config);
    case 'system':
      return renderSystemStep(config);
    case 'complete':
      return renderCompleteStep(config);
    default:
      return `<div class="status-banner"><strong>Unknown step.</strong><span>This onboarding step is not implemented.</span></div>`;
  }
}

function updateSummaryLabels(config) {
  elements.systemNameLabel.textContent = config.system_name || 'AIOS setup session';
  elements.installPathLabel.textContent = config.install_path || 'Install path pending';
}

function renderStep() {
  const onboarding = state.onboarding;
  const step = onboarding.step;
  const config = onboarding.config;

  const progressPercent = ((step.index + 1) / step.total_steps) * 100;
  elements.progressFill.style.width = `${progressPercent}%`;
  elements.progressReadout.textContent = String(step.index + 1);
  elements.progressTotal.textContent = String(step.total_steps);
  elements.stepCounter.textContent = `${step.index + 1} of ${step.total_steps}`;
  elements.stepKeyLabel.textContent = step.title;
  elements.stepTitle.textContent = step.title;
  elements.agentLine.textContent = step.description;
  elements.stepBody.innerHTML = renderStepBody(step, config);
  elements.prevButton.style.display = step.index === 0 ? 'none' : 'inline-flex';
  elements.nextButtonLabel.textContent = step.key === 'complete' ? 'Launch AIOS' : 'Next';
  elements.restartOnboardingButton.style.display = config.onboarding_complete ? 'inline-flex' : 'none';
  elements.voiceHintFooter.textContent = step.key === 'hardware_setup'
    ? 'Voice commands: detect hardware, next, back, repeat'
    : 'Voice commands: next, back, repeat, help';
  updateSummaryLabels(config);
  bindDynamicControls();
  queueOrSpeak(step.speech || step.description, step.emotion || 'neutral');
}

function bindDynamicControls() {
  document.getElementById('detect-hardware-btn')?.addEventListener('click', async () => {
    await runHardwareDetection();
  });
  document.getElementById('refresh-telemetry-btn')?.addEventListener('click', async () => {
    await refreshTelemetry();
    setWizardStatus('Live stats refreshed.', 'ok');
  });
}

async function refreshOnboardingState() {
  const onboarding = await eel.get_onboarding_state()();
  state.onboarding = onboarding;
  renderStep();
  if (onboarding.config.onboarding_complete) {
    setWizardStatus('Onboarding is already marked complete. Review the steps or press launch when ready.', 'ok');
  }
}

async function restartOnboarding() {
  try {
    const result = await eel.reset_onboarding()();
    if (!result.success) {
      setWizardStatus(result.error || 'Unable to restart onboarding.', 'error');
      return;
    }
    state.onboarding = result;
    renderStep();
    setWizardStatus('Onboarding reset. Starting again from step one.', 'ok');
    queueOrSpeak('Onboarding reset. Starting again from the beginning.', 'happy');
  } catch (error) {
    console.error('[Onboarding] Restart failed', error);
    setWizardStatus(error.message || 'Unable to restart onboarding.', 'error');
  }
}

function collectCurrentStepUpdates() {
  const stepKey = state.onboarding.step.key;
  if (stepKey === 'gpu_config') {
    return {
      gpu_enabled: document.getElementById('gpu-enabled')?.checked ?? false,
    };
  }
  if (stepKey === 'system') {
    return {
      user_name: document.getElementById('user-name')?.value || '',
      system_name: document.getElementById('system-name')?.value || '',
      install_path: document.getElementById('install-path')?.value || '',
      auto_start: document.getElementById('auto-start')?.checked ?? false,
      telemetry_enabled: document.getElementById('telemetry-enabled')?.checked ?? true,
    };
  }
  return null;
}

function validateCurrentStep() {
  if (state.onboarding.step.key !== 'system') {
    return true;
  }

  const updates = collectCurrentStepUpdates();
  if (!updates.user_name.trim() || !updates.system_name.trim() || !updates.install_path.trim()) {
    setWizardStatus('Name, system name, and install path are required.', 'warn');
    queueOrSpeak('Please fill in your name, system name, and install path before continuing.', 'neutral');
    return false;
  }

  return true;
}

async function persistCurrentStep() {
  const updates = collectCurrentStepUpdates();
  if (!updates) {
    return;
  }
  const response = await eel.update_onboarding_config(updates)();
  if (!response.success) {
    throw new Error(response.error || 'Failed to save onboarding settings.');
  }
  state.onboarding = response;
}

async function runHardwareDetection() {
  setWizardStatus('Detecting hardware...', 'neutral');
  queueOrSpeak('Scanning your hardware now.', 'neutral');
  const response = await eel.detect_hardware()();
  if (!response.success) {
    setWizardStatus(response.error || 'Hardware detection failed.', 'error');
    queueOrSpeak('Hardware detection failed. You can continue manually.', 'neutral');
    return;
  }
  state.onboarding = response;
  renderStep();
  setWizardStatus('Hardware detection complete.', 'ok');
  queueOrSpeak('Hardware detection complete. Your accelerator profile has been updated.', 'happy');
}

async function handleNext() {
  if (!validateCurrentStep()) {
    return;
  }

  try {
    await persistCurrentStep();

    if (state.onboarding.step.key === 'complete') {
      setWizardStatus('Finalizing setup...', 'neutral');
      const result = await eel.complete_onboarding()();
      if (!result.success) {
        setWizardStatus(result.error || 'Unable to complete onboarding.', 'error');
        return;
      }
      redirectToMainUi(result.redirect_url);
      return;
    }

    const nextStep = await eel.next_step()();
    if (!nextStep) {
      setWizardStatus('No further onboarding steps are available.', 'warn');
      return;
    }
    await refreshOnboardingState();
    setWizardStatus('Step saved.', 'ok');
  } catch (error) {
    console.error('[Onboarding] Next step failed', error);
    setWizardStatus(error.message || 'Could not continue to the next step.', 'error');
  }
}

async function handleBack() {
  try {
    await persistCurrentStep();
    const previousStep = await eel.previous_step()();
    if (!previousStep) {
      return;
    }
    await refreshOnboardingState();
    setWizardStatus('Returned to previous step.', 'ok');
  } catch (error) {
    console.error('[Onboarding] Previous step failed', error);
    setWizardStatus(error.message || 'Could not go back.', 'error');
  }
}

function redirectToMainUi(target) {
  const redirectUrl = target || 'avatar-integration.html';
  setWizardStatus('Setup complete. Opening the main AIOS workspace...', 'ok');
  queueOrSpeak('Setup complete. Opening your AIOS workspace now.', 'happy');
  window.setTimeout(() => {
    window.location.assign(redirectUrl);
  }, 900);
}

function currentStepSpeech() {
  const step = state.onboarding?.step;
  if (!step) {
    return;
  }
  queueOrSpeak(step.speech || step.description, step.emotion || 'neutral');
}

async function handleVoiceCommand(command) {
  const parsed = VoiceCommandParser.parse(command);
  const raw = command.toLowerCase();

  if (raw.includes('detect hardware') || raw.includes('scan hardware') || parsed.type === 'detect') {
    await runHardwareDetection();
    return;
  }

  switch (parsed.type) {
    case 'next':
    case 'yes':
    case 'launch':
      await handleNext();
      break;
    case 'back':
    case 'no':
      await handleBack();
      break;
    case 'repeat':
      currentStepSpeech();
      break;
    case 'help':
      queueOrSpeak('You can say next, back, repeat, or detect hardware during setup.', 'neutral');
      break;
    default:
      queueOrSpeak('I did not understand that onboarding command. Try saying next, back, or detect hardware.', 'neutral');
  }
}

function bindEvents() {
  elements.nextButton.addEventListener('click', handleNext);
  elements.prevButton.addEventListener('click', handleBack);
  elements.restartOnboardingButton.addEventListener('click', restartOnboarding);
}

async function init() {
  bindElements();
  bindEvents();
  installGestureUnlock();
  updateClock();
  await initAvatar();
  initVoice();
  startTelemetryLoop();

  if (!(await waitForEel())) {
    setWizardStatus('Backend bridge unavailable. Start onboarding through the PortAIOS launcher.', 'error');
    elements.stepTitle.textContent = 'Backend Unavailable';
    elements.agentLine.textContent = 'This onboarding page needs the PortAIOS kernel bridge to save setup choices and continue into AIOS.';
    elements.stepBody.innerHTML = `
      <div class="status-banner error">
        <strong>Connection required.</strong>
        <span>Launch this page from the PortAIOS app so the onboarding wizard can talk to the kernel.</span>
      </div>
    `;
    elements.nextButton.disabled = true;
    return;
  }

  await refreshOnboardingState();
  setWizardStatus('Backend connected.', 'ok');
}

window.addEventListener('beforeunload', () => {
  if (state.telemetryTimer) {
    window.clearInterval(state.telemetryTimer);
  }
  window.AIOS?.avatar?.destroy?.();
  window.AIOS?.voiceInput?.destroy?.();
  window.AIOS?.voiceUI?.destroy?.();
});

init().catch((error) => {
  console.error('[Onboarding] Fatal initialization error', error);
  setWizardStatus('Failed to initialize onboarding.', 'error');
});
