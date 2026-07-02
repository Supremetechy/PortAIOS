/**
 * react-avatar-bridge.js
 * Mounts the React-based <Avatar/> component (assets/avatar/Avatar.jsx)
 * into a plain DOM container and exposes an imperative speak()/stop() API
 * compatible with the existing AvatarController surface.
 *
 * Source-of-truth files (loaded LAZILY in init() — if any of them fail to
 * load, only REACT_3D mode breaks; the rest of the page stays alive):
 *   - assets/avatar/Avatar.jsx         — three.js renderer + blendshape driver
 *   - assets/avatar/useSpeechStream.js — audio decode + viseme keyframe engine
 *   - assets/avatar/phonemeMap.js      — IPA phoneme → viseme blendshape map
 *
 * IMPORTANT: This module has NO top-level imports of those files. The static
 * import below for react/react-dom is intentional — those are stable peers
 * already in the importmap and must be available before any React work.
 * Do not promote the lazy imports back to static; doing so re-couples the
 * binary-avatar / switcher / telemetry init to the React 3D dep graph.
 */

import React from 'react';
import { createRoot } from 'react-dom/client';

let _AvatarComponent = null;
let _useSpeechStream = null;
let _PHONEME_TO_VISEME = null;

// Per-module load report — populated by _loadDeps() so init()'s error
// reporter can show exactly where the chain broke.
const _loadReport = {
  avatar: { loaded: false, error: null, exports: null },
  speechStream: { loaded: false, error: null, exports: null },
  phonemeMap: { loaded: false, error: null, exports: null },
};

const _LAZY_MODULES = [
  {
    key: 'avatar',
    name: 'Avatar.jsx',
    url: '../assets/avatar/Avatar.jsx',
    binding: 'default',
    assign: (val) => { _AvatarComponent = val; },
    expectedType: 'function',
  },
  {
    key: 'speechStream',
    name: 'useSpeechStream.js',
    url: '../assets/avatar/useSpeechStream.js',
    binding: 'useSpeechStream',
    assign: (val) => { _useSpeechStream = val; },
    expectedType: 'function',
  },
  {
    key: 'phonemeMap',
    name: 'phonemeMap.js',
    url: '../assets/avatar/phonemeMap.js',
    binding: 'PHONEME_TO_VISEME',
    assign: (val) => { _PHONEME_TO_VISEME = val; },
    expectedType: 'object',
  },
];

/**
 * Load each dependency individually so a failure tells us exactly which file
 * broke and why. Throws a rich Error annotated with which module failed.
 */
async function _loadDeps() {
  if (_AvatarComponent && _useSpeechStream && _PHONEME_TO_VISEME) return;

  for (const mod of _LAZY_MODULES) {
    if (_loadReport[mod.key].loaded) continue;
    let imported;
    try {
      imported = await import(mod.url);
    } catch (err) {
      _loadReport[mod.key].error = err;
      const wrapped = new Error(
        `Failed to import ${mod.name} from ${mod.url}: ${err?.message ?? err}`
      );
      wrapped.cause = err;
      wrapped.moduleName = mod.name;
      wrapped.moduleUrl = mod.url;
      wrapped.phase = 'fetch';
      throw wrapped;
    }
    _loadReport[mod.key].exports = Object.keys(imported || {});
    const value = imported?.[mod.binding];
    if (value === undefined) {
      const err = new Error(
        `${mod.name} loaded from ${mod.url} but does not export '${mod.binding}'. ` +
        `Available exports: [${_loadReport[mod.key].exports.join(', ') || '<none>'}]`
      );
      err.moduleName = mod.name;
      err.moduleUrl = mod.url;
      err.phase = 'binding';
      _loadReport[mod.key].error = err;
      throw err;
    }
    if (typeof value !== mod.expectedType) {
      const err = new Error(
        `${mod.name}'s '${mod.binding}' has wrong type — expected ${mod.expectedType}, got ${typeof value}`
      );
      err.moduleName = mod.name;
      err.moduleUrl = mod.url;
      err.phase = 'type-check';
      _loadReport[mod.key].error = err;
      throw err;
    }
    mod.assign(value);
    _loadReport[mod.key].loaded = true;
  }
}

function _buildAvatarBridge() {
  const Avatar = _AvatarComponent;
  const useSpeechStream = _useSpeechStream;
  if (!Avatar) {
    const err = new Error('_buildAvatarBridge: Avatar component is null/undefined');
    err.phase = 'build';
    throw err;
  }
  if (typeof useSpeechStream !== 'function') {
    const err = new Error(
      '_buildAvatarBridge: useSpeechStream is not a function (got ' + typeof useSpeechStream + ')'
    );
    err.phase = 'build';
    throw err;
  }
  return React.forwardRef(function AvatarBridge(props, ref) {
    const { modelUrl, emotion, agentId, customMorphs } = props;
    const { streamRef, speak, stop } = useSpeechStream();
    React.useImperativeHandle(ref, () => ({ speak, stop }), [speak, stop]);
    return React.createElement(Avatar, {
      agentId,
      modelUrl,
      emotion,
      customMorphs,
      speechStream: streamRef,
    });
  });
}

/**
 * React Error Boundary — surfaces render-time errors that init's try/catch
 * can never see (createRoot.render is asynchronous; errors thrown inside
 * functional components reach React, not us). Without this, a bug inside
 * Avatar.jsx's useFrame or useGLTF would manifest as "the GLB never appears"
 * with no console output at all.
 */
class _AvatarErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    console.group('[ReactAvatarController] React render error caught by ErrorBoundary');
    console.error('Error:', error);
    console.error('Message:', error?.message);
    console.error('Component stack:', info?.componentStack);
    if (error?.stack) console.error('Stack:', error.stack);
    console.groupEnd();
  }
  render() {
    if (this.state.hasError) return null;
    return this.props.children;
  }
}

/**
 * Map an unknown error to a one-line actionable hint. Returns null if the
 * error doesn't match any known shape.
 */
function _classifyInitError(err) {
  const msg = String(err?.message ?? err ?? '');
  const name = err?.name ?? '';

  if (msg.includes('text/html') || msg.includes('not a valid JavaScript MIME')) {
    return 'A JS module was served as text/html. Restart the Python server (kernel/onboarding_gui.py) so the .jsx MIME-type fix in serve_static_assets() takes effect.';
  }
  if (msg.includes('Importing binding name') && msg.includes('LinearEncoding')) {
    return 'three is on r158+ but @react-three/drei expects LinearEncoding (removed in r158). Pin three to 0.157.0 in the importmap and add ?external=three to drei/fiber URLs.';
  }
  if (msg.includes('Importing binding name')) {
    return 'A library expects an export that the resolved version of its dependency does not provide. Check importmap version pins for that dependency.';
  }
  if (name === 'TypeError' && /undefined is not an object|cannot read.*of undefined/i.test(msg)) {
    // The "S" property is React 18's minified Scheduler internals reference.
    // If we hit it before createRoot (i.e. during a module *load*), the cause
    // is fiber/drei bundling their own react-dom. If we hit it AT createRoot,
    // the cause is react-dom bundling its own react. Both fix the same way:
    // externalise these deps in the importmap so everyone shares one instance.
    if (/reading\s+'S'|reading\s+"S"/i.test(msg) || /D\.S/i.test(err?.stack ?? '')) {
      return (
        'Multiple-React-instances bug. The importmap must externalise react/react-dom/scheduler ' +
        'across every consumer:\n' +
        '  react-dom@…             ?external=react,scheduler\n' +
        '  react-dom/client@…      ?external=react,scheduler\n' +
        '  @react-three/fiber@…    ?external=react,react-dom,three,scheduler\n' +
        '  @react-three/drei@…     ?external=react,react-dom,three,scheduler,@react-three/fiber\n' +
        'Common cause if seen DURING module load (not at createRoot): fiber/drei is ' +
        'missing react-dom from its external list, so it ships its own react-dom + react.'
      );
    }
    if (/react-dom-client|react-reconciler/i.test(err?.stack ?? '')) {
      return 'Probable multiple-React-instances bug at React tree create/render time. Verify ?external=react,scheduler on react-dom and react-dom/client URLs.';
    }
    return 'A module is loaded but missing a binding the caller expected. Could be importmap mis-resolution or a peer-dep version mismatch.';
  }
  if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || msg.includes('Could not connect')) {
    return 'Module fetch failed. Check that the static-file server (kernel/onboarding_gui.py) is running on port 8001 and that the importmap URLs resolve.';
  }
  if (msg.includes('container') && err?.phase === 'preflight') {
    return 'The DOM element passed as container is missing or not a valid Element. Confirm #react-avatar-container exists in the HTML and is reachable when init() runs.';
  }
  if (err?.phase === 'fetch' && err?.moduleName) {
    return `Dynamic import of ${err.moduleName} failed. Verify the file exists at ${err.moduleUrl} and is served with Content-Type: application/javascript.`;
  }
  if (err?.phase === 'binding' && err?.moduleName) {
    return `${err.moduleName} loaded but does not export the expected symbol. The file may have been modified or is the wrong file.`;
  }
  return null;
}

export class ReactAvatarController {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      modelUrl: options.modelUrl || '/models/avatar.glb',
      agentId: options.agentId || 'aios',
      initialEmotion: options.emotion || 'neutral',
      ...options,
    };

    this.currentEmotion = this.options.initialEmotion;
    this.customMorphs = {
      smile: 0.25,
      frown: 0,
      surprise: 0,
      wink: 0,
      viseme: 0.5,
      subdivisions: 4,
      skinColor: [216, 184, 153],
    };
    this.reactRoot = null;
    this.bridgeRef = React.createRef();
    this.AvatarBridge = null;
    this.isInitialized = false;
    this.initError = null;
    this.lastInitPhase = null;
  }

  /**
   * Capture a snapshot of the container element for diagnostics. Useful when
   * init fails and we need to know whether the container was even valid.
   */
  _describeContainer() {
    const c = this.container;
    if (!c) return { ok: false, reason: 'container is null/undefined' };
    if (!(c instanceof Element)) {
      return { ok: false, reason: `container is not a DOM Element (got ${typeof c})` };
    }
    let computed = null;
    try { computed = window.getComputedStyle(c); } catch {}
    return {
      ok: true,
      tag: c.tagName,
      id: c.id || null,
      inDocument: document.contains(c),
      width: c.clientWidth,
      height: c.clientHeight,
      offsetParent: c.offsetParent ? c.offsetParent.tagName + (c.offsetParent.id ? '#' + c.offsetParent.id : '') : null,
      inlineDisplay: c.style?.display || '<none>',
      computedDisplay: computed?.display || null,
      computedVisibility: computed?.visibility || null,
    };
  }

  async init() {
    if (this.isInitialized) return;

    console.group('[ReactAvatarController] init()');
    this.lastInitPhase = 'preflight';

    try {
      // ---- Preflight: container sanity --------------------------------
      const desc = this._describeContainer();
      console.log('container:', desc);
      if (!desc.ok) {
        const err = new Error(`Preflight failed: ${desc.reason}`);
        err.phase = 'preflight';
        throw err;
      }
      if (desc.computedDisplay === 'none') {
        // Not fatal — switcher.showReactAvatar() flips display to block before
        // calling init(), but warn loudly because R3F's first render with a
        // hidden container can produce "Framebuffer is incomplete" errors.
        console.warn(
          '[ReactAvatarController] container is display:none at init time. ' +
          'R3F may report zero-size framebuffer errors until the container is shown.'
        );
      }
      if (desc.computedDisplay === 'none' || desc.width === 0 || desc.height === 0) {
        if (!this._initRetryId) {
          console.warn('[ReactAvatarController] deferring init until the container has size');
          this._initRetryId = requestAnimationFrame(() => {
            this._initRetryId = null;
            this.init().catch((retryErr) => {
              console.warn('[ReactAvatarController] deferred init retry failed:', retryErr);
            });
          });
        }
        return;
      }

      // ---- Phase 1: dynamic deps --------------------------------------
      this.lastInitPhase = 'load-deps';
      console.log('Phase 1: loading lazy avatar deps…');
      await _loadDeps();
      console.log('  deps loaded:', {
        Avatar: typeof _AvatarComponent,
        useSpeechStream: typeof _useSpeechStream,
        PHONEME_TO_VISEME_keys: _PHONEME_TO_VISEME ? Object.keys(_PHONEME_TO_VISEME).length : 0,
      });

      // ---- Phase 2: build the React component --------------------------
      this.lastInitPhase = 'build-bridge';
      console.log('Phase 2: building AvatarBridge component…');
      this.AvatarBridge = _buildAvatarBridge();
      console.log('  AvatarBridge built (forwardRef component).');

      // ---- Phase 3: createRoot ----------------------------------------
      this.lastInitPhase = 'create-root';
      console.log('Phase 3: createRoot()…');
      this.reactRoot = createRoot(this.container);
      console.log('  React root created.');

      // ---- Phase 4: first render --------------------------------------
      this.lastInitPhase = 'render';
      console.log('Phase 4: rendering tree (wrapped in ErrorBoundary)…');
      this.render();
      console.log('  Initial render dispatched. (Render-time errors surface async via the ErrorBoundary.)');

      this.isInitialized = true;
      this.lastInitPhase = 'ready';
      console.log('init() complete — REACT_3D mode is live.');
    } catch (err) {
      this.initError = err;
      console.group('[ReactAvatarController] init FAILED — REACT_3D mode disabled');
      console.error('Phase reached:', this.lastInitPhase);
      console.error('Error name:   ', err?.name);
      console.error('Error message:', err?.message);
      if (err?.moduleName) console.error('Module:       ', err.moduleName, '(' + err.moduleUrl + ')');
      if (err?.phase)      console.error('Subphase:     ', err.phase);
      if (err?.cause)      console.error('Underlying:   ', err.cause);
      console.error('Stack:');
      console.error(err?.stack || '<no stack>');
      console.error('Per-module load report:', _loadReport);
      const hint = _classifyInitError(err);
      if (hint) console.warn('Hint:        ', hint);
      console.warn(
        'The rest of the page should keep working. Inspect via:\n' +
        '  window.reactAvatar.initError\n' +
        '  window.reactAvatar.lastInitPhase'
      );
      console.groupEnd();
    } finally {
      console.groupEnd();
    }
  }

  render() {
    if (!this.reactRoot || !this.AvatarBridge) {
      console.warn('[ReactAvatarController] render() called before reactRoot/AvatarBridge are ready');
      return;
    }
    try {
      this.reactRoot.render(
        React.createElement(_AvatarErrorBoundary, null,
          React.createElement(this.AvatarBridge, {
            ref: this.bridgeRef,
            modelUrl: this.options.modelUrl,
            emotion: this.currentEmotion,
            customMorphs: this.customMorphs,
            agentId: this.options.agentId,
          })
        )
      );
    } catch (err) {
      console.error('[ReactAvatarController] render() threw synchronously:', err);
      throw err;
    }
  }

  /**
   * Speak with phoneme-driven lip sync.
   * speechData: { audio: base64 WAV | ArrayBuffer, phonemes: [{p,t,d}, ...] }
   */
  async speak(text, speechData) {
    if (!this.isInitialized) {
      console.warn('[ReactAvatarController] speak() before init — calling init() now');
      await this.init();
      if (!this.isInitialized) {
        console.warn('[ReactAvatarController] speak() aborting — init() did not succeed (see initError)');
        return;
      }
    }
    if (!speechData || !speechData.audio || !speechData.phonemes) {
      console.warn('[ReactAvatarController] speak() called without {audio, phonemes}');
      return;
    }
    const handle = this.bridgeRef.current;
    if (!handle) {
      console.warn(
        '[ReactAvatarController] React tree not mounted yet — speak() ignored. ' +
        'This happens when the GLB is still loading; try again once useGLTF resolves.'
      );
      return;
    }
    console.log('[ReactAvatarController] Speaking,', speechData.phonemes.length, 'phonemes');
    return await handle.speak({
      audio: speechData.audio,
      phonemes: speechData.phonemes,
      onEnd: () => console.log('[ReactAvatarController] Speech ended'),
    });
  }

  setEmotion(emotion) {
    if (this.currentEmotion === emotion) return;
    this.currentEmotion = emotion;
    this.render();
  }

  setCustomization(next = {}) {
    this.customMorphs = {
      ...this.customMorphs,
      ...next,
    };
    this.render();
  }

  stopSpeaking() {
    this.bridgeRef.current?.stop();
  }

  destroy() {
    if (this._initRetryId) cancelAnimationFrame(this._initRetryId);
    this.bridgeRef.current?.stop();
    if (this.reactRoot) {
      try { this.reactRoot.unmount(); } catch (err) {
        console.warn('[ReactAvatarController] reactRoot.unmount() threw:', err);
      }
      this.reactRoot = null;
    }
    this.isInitialized = false;
  }

  // Compatibility shims for the existing AvatarController interface.
  setState(_state) {}
  setActivity(activity) {
    const map = { idle: 'neutral', thinking: 'thinking', speaking: 'happy', error: 'concerned' };
    this.setEmotion(map[activity] || 'neutral');
  }
  setVolume(_volume) {}
}
