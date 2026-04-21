// script.js
// AIOS onboarding wizard — drives step flow via Eel, speaks each step
// through the live avatar (window.AIOS.avatar from avatar.js).

document.addEventListener('DOMContentLoaded', () => {
  const app               = document.getElementById('app');
  const agentAvatar       = document.getElementById('agent-avatar');
  const avatarPlaceholder = document.getElementById('avatar-placeholder');
  const onboardingContent = document.getElementById('onboarding-content');
  const nextButton        = document.getElementById('next-button');

  // Back-compat: the old <video> tag may or may not exist in the new HTML.
  // If it's there, we keep it for steps that still specify video_url.
  const avatarVideo = document.getElementById('avatar-video');

  // Back button
  const prevButton = document.createElement('button');
  prevButton.textContent = '← Back';
  prevButton.id = 'prev-button';
  prevButton.style.marginRight = '10px';
  prevButton.style.display = 'none';
  onboardingContent.insertBefore(prevButton, nextButton);

  // ─── Speech gating ──────────────────────────────────────────────────
  // AudioContext requires a user gesture before it can produce sound, so
  // the first step's narration is queued and fires on the first click.
  let gestureUnlocked = false;
  let pendingUtterance = null;  // { text, emotion }

  function queueOrSpeak(text, emotion = 'neutral') {
    if (!window.AIOS?.avatar) return;   // avatar.js not loaded yet
    if (!gestureUnlocked) {
      pendingUtterance = { text, emotion };
      return;
    }
    window.AIOS.avatar.stop();          // barge-in: cancel whatever's playing
    window.AIOS.avatar.speak(text, { emotion });
  }

  // Any click anywhere in the app unlocks audio; we then flush the queue.
  app.addEventListener('click', () => {
    if (gestureUnlocked) return;
    gestureUnlocked = true;
    if (pendingUtterance) {
      const { text, emotion } = pendingUtterance;
      pendingUtterance = null;
      window.AIOS?.avatar?.speak(text, { emotion });
    }
  }, { once: true });

  // ─── Step rendering ─────────────────────────────────────────────────
  // Map your step metadata to an emotion. You can drive this from Python
  // instead by adding an `emotion` field to get_current_step_data().
  function emotionForStep(stepData) {
    if (stepData.emotion) return stepData.emotion;        // explicit wins
    if (stepData.index === 0) return 'happy';              // greeting
    if (stepData.index === stepData.total_steps - 1) return 'happy'; // launch
    return 'neutral';
  }

  function eelReady() {
    return typeof eel !== 'undefined' &&
           typeof eel.get_current_step_data === 'function' &&
           typeof eel.next_step === 'function' &&
           typeof eel.previous_step === 'function';
  }

  async function waitForEel(timeout = 8000) {
    const start = Date.now();
    while (!eelReady()) {
      if (Date.now() - start > timeout) {
        console.warn('[AIOS] Eel bridge not available — running in standalone mode');
        return false;
      }
      await new Promise(r => setTimeout(r, 150));
    }
    return true;
  }

  async function loadStepData() {
    if (!eelReady()) {
      if (!(await waitForEel())) {
        // Standalone mode — avatar still works, just no step navigation
        console.log('[AIOS] Running without Eel — avatar-only mode');
        nextButton.style.display = 'none';
        return;
      }
    }
    const stepData = await eel.get_current_step_data()();
    if (!stepData) return;

    // Update step title/description — support both id-based and tag-based elements
    const h1 = document.querySelector('h1');
    if (h1) h1.textContent = `AIOS Setup Wizard - Step ${stepData.index + 1} of ${stepData.total_steps}`;

    const h2 = document.getElementById('step-title') || onboardingContent.querySelector('h2');
    if (h2) h2.textContent = stepData.title;

    const desc = document.getElementById('agent-line') || onboardingContent.querySelector('p');
    if (desc) desc.textContent = stepData.description;

    // Avatar source of truth: prefer live avatar, fall back to video if a
    // step explicitly specifies video_url (back-compat with your old data).
    const useVideoFallback = !!stepData.video_url && avatarVideo;

    if (useVideoFallback) {
      avatarVideo.src = stepData.video_url;
      avatarVideo.style.display = 'block';
      if (avatarPlaceholder) avatarPlaceholder.style.display = 'none';
      avatarVideo.load();
      avatarVideo.play().catch(() => {}); // ignore autoplay rejection
      // Stop any live speech so the video's audio track isn't doubled up.
      window.AIOS?.avatar?.stop();
    } else {
      if (avatarVideo) {
        avatarVideo.style.display = 'none';
        avatarVideo.pause();
        avatarVideo.removeAttribute('src');
      }
      // Speak the step's narration. Prefer an explicit `speech` field from
      // Python if present; otherwise fall back to the description text.
      const line = stepData.speech || stepData.description;
      if (line) queueOrSpeak(line, emotionForStep(stepData));
    }

    // Nav buttons
    prevButton.style.display = stepData.index === 0 ? 'none' : 'inline-block';
    nextButton.textContent =
      stepData.index === stepData.total_steps - 1 ? '🚀 Launch AI-OS' : 'Next →';
  }

  // ─── Navigation ─────────────────────────────────────────────────────
  nextButton.addEventListener('click', async () => {
    if (!eelReady()) return;
    const newStepData = await eel.next_step()();
    if (newStepData) {
      loadStepData();
    } else {
      window.AIOS?.avatar?.stop();
      if (typeof eel.launch_aios === 'function') {
        await eel.launch_aios()();
      } else {
        alert('Onboarding complete! Launching AI-OS...');
      }
    }
  });

  prevButton.addEventListener('click', async () => {
    if (!eelReady()) return;
    const newStepData = await eel.previous_step()();
    if (newStepData) loadStepData();
  });

  // Initial load
  loadStepData();
});