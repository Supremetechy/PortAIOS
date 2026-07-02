// Avatar.jsx
// Drop-in 3D agent avatar for the AIOS GUI.
// Renders a Ready Player Me glTF head, drives ARKit blendshapes from a
// viseme keyframe stream synchronized to a Web Audio AudioBufferSourceNode.
//
// NOTE: written with React.createElement instead of JSX so it can be loaded
// directly by the browser via the project's importmap with no build step.
// The file keeps the .jsx extension for editor association only.

import React, { useRef, useEffect, useMemo, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { useGLTF, Environment } from '@react-three/drei';
import * as THREE from 'three';
import { PHONEME_TO_VISEME, VISEME_FALLBACK_MAP } from './phonemeMap.js';
//import { useAudio } from './Audio.jsx';
//import { useGLTFModel } from './GLTF.jsx';
//import { ARKit } from 'react-native-arkit';

//import ARKit blendshapes: https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocationnamingconvention


const DEFAULT_EXPRESSION = 'neutral';

const EMOTION_PRESETS = {
  neutral:   {},
  happy:     { mouthSmileLeft: 0.6, mouthSmileRight: 0.6, cheekSquintLeft: 0.3, cheekSquintRight: 0.3, browInnerUp: 0.15 },
  focused:   { browDownLeft: 0.4, browDownRight: 0.4, eyeSquintLeft: 0.2, eyeSquintRight: 0.2 },
  concerned: { browInnerUp: 0.7, mouthFrownLeft: 0.3, mouthFrownRight: 0.3 },
  thinking:  { browDownLeft: 0.25, browDownRight: 0.25, mouthPucker: 0.15 },
};

// Critically-damped spring; ~50ms half-life avoids robotic snap-to-target.
function springStep(current, target, velocity, dt, halfLife = 0.045) {
  const omega = Math.log(2) / halfLife;
  const dx = target - current;
  const accel = omega * omega * dx - 2 * omega * velocity;
  const newVel = velocity + accel * dt;
  const newPos = current + newVel * dt;
  return [newPos, newVel];
}

function AvatarHead({ modelUrl, speechStream, emotion, customMorphs = {} }) {
  const { scene } = useGLTF(modelUrl);
  const headRef = useRef();

  // RPM splits the head across multiple meshes (head/teeth/tongue);
  // every mesh with a morphTargetDictionary must be driven.
  const morphMeshes = useMemo(() => {
    const meshes = [];
    scene.traverse((obj) => {
      if (obj.isMesh && obj.morphTargetDictionary) meshes.push(obj);
    });
    return meshes;
  }, [scene]);

  // Diagnostic on first load: log which morphs the GLB actually has and
  // which phonemeMap targets are missing. If this prints "missing 15/15"
  // it means the GLB doesn't have RPM/Oculus viseme blendshapes and
  // lip sync will be silent (mouth won't move) regardless of the audio.
  useEffect(() => {
    if (morphMeshes.length === 0) {
      console.warn('[Avatar] Loaded GLB has no morph targets — lip sync is impossible');
      return;
    }
    const present = new Set();
    for (const mesh of morphMeshes) {
      for (const name of Object.keys(mesh.morphTargetDictionary || {})) {
        present.add(name);
      }
    }
    const expected = new Set(Object.values(PHONEME_TO_VISEME));
    const missing = [...expected].filter((n) => !present.has(n));
    const found = [...expected].filter((n) => present.has(n));
    console.log('[Avatar] morph targets present on GLB:', [...present].sort());
    console.log(
      `[Avatar] phoneme-map coverage: ${found.length}/${expected.size}` +
      (missing.length ? ` — missing: ${missing.join(', ')}` : ' — all visemes present ✓')
    );
    const arkitProbes = ['jawOpen', 'eyeBlinkLeft', 'eyeBlinkRight', 'mouthSmileLeft', 'browInnerUp'];
    const arkitMissing = arkitProbes.filter((n) => !present.has(n));
    if (arkitMissing.length === arkitProbes.length) {
      console.warn('[Avatar] No ARKit blendshapes detected — emotions/blink/jaw drive will be no-ops');
    }
  }, [morphMeshes]);

  const stateRef = useRef({});
  const blinkRef = useRef({ next: performance.now() + 3000, closing: false, phase: 0 });

  useFrame((_, dt) => {
    if (!speechStream || !speechStream.current) return;

    const audioT = speechStream.current.getCurrentTime();

    const targets = { ...(EMOTION_PRESETS[emotion] || {}) };
    const smile = Math.max(0, Math.min(1, customMorphs.smile ?? 0));
    const frown = Math.max(0, Math.min(1, customMorphs.frown ?? 0));
    const surprise = Math.max(0, Math.min(1, customMorphs.surprise ?? 0));
    const wink = Math.max(0, Math.min(1, customMorphs.wink ?? 0));
    const visemeGain = 0.35 + Math.max(0, Math.min(1, customMorphs.viseme ?? 0.5)) * 1.3;

    targets.mouthSmileLeft = Math.max(targets.mouthSmileLeft || 0, smile * 0.75);
    targets.mouthSmileRight = Math.max(targets.mouthSmileRight || 0, smile * 0.75);
    targets.mouthFrownLeft = Math.max(targets.mouthFrownLeft || 0, frown * 0.65);
    targets.mouthFrownRight = Math.max(targets.mouthFrownRight || 0, frown * 0.65);
    targets.browInnerUp = Math.max(targets.browInnerUp || 0, surprise * 0.8);
    targets.eyeWideLeft = Math.max(targets.eyeWideLeft || 0, surprise * 0.55);
    targets.eyeWideRight = Math.max(targets.eyeWideRight || 0, surprise * 0.55);
    targets.jawOpen = Math.max(targets.jawOpen || 0, surprise * 0.35);
    targets.eyeBlinkLeft = Math.max(targets.eyeBlinkLeft || 0, wink);

    if (audioT != null) {
      const kf = speechStream.current.getActiveVisemes(audioT);
      for (const { viseme, weight } of kf) {
        // Use fallback if viseme is missing from GLB
        const targetViseme = VISEME_FALLBACK_MAP[viseme] || viseme;
        targets[targetViseme] = (targets[targetViseme] || 0) + weight * visemeGain;
      }
      // Apply fallbacks for jaw drive calculation too
      const viseme_aa = VISEME_FALLBACK_MAP['viseme_aa'] || 'viseme_aa';
      const viseme_O = VISEME_FALLBACK_MAP['viseme_O'] || 'viseme_O';
      const viseme_E = VISEME_FALLBACK_MAP['viseme_E'] || 'viseme_E';
      const jawDrive = (targets[viseme_aa] || 0) * 0.9
                     + (targets[viseme_O]  || 0) * 0.7
                     + (targets[viseme_E]  || 0) * 0.4;
      targets['jawOpen'] = Math.min(1, Math.max(targets.jawOpen || 0, jawDrive));
    }

    const now = performance.now();
    const blink = blinkRef.current;
    if (now >= blink.next && !blink.closing) {
      blink.closing = true;
      blink.phase = 0;
    }
    if (blink.closing) {
      blink.phase += dt / 0.12;
      const b = blink.phase < 0.5
        ? blink.phase * 2
        : (1 - (blink.phase - 0.5) * 2);
      targets['eyeBlinkLeft']  = Math.max(targets['eyeBlinkLeft']  || 0, b);
      targets['eyeBlinkRight'] = Math.max(targets['eyeBlinkRight'] || 0, b);
      if (blink.phase >= 1) {
        blink.closing = false;
        blink.next = now + 2500 + Math.random() * 3500;
      }
    }

    for (const mesh of morphMeshes) {
      const dict = mesh.morphTargetDictionary;
      const influences = mesh.morphTargetInfluences;
      for (const name in dict) {
        const idx = dict[name];
        const target = targets[name] || 0;
        const s = stateRef.current[name] || { value: 0, velocity: 0 };
        const [v, vel] = springStep(s.value, target, s.velocity, dt);
        s.value = v;
        s.velocity = vel;
        stateRef.current[name] = s;
        influences[idx] = v;
      }
    }
  });

  return React.createElement('primitive', {
    ref: headRef,
    object: scene,
    position: [0, -1.55, 0],
  });
}

export default function Avatar({ agentId, modelUrl, speechStream, emotion = 'neutral', customMorphs = {} }) {
  return React.createElement(
    Canvas,
    {
      camera: { position: [0, 0.05, 0.75], fov: 18, near: 0.1, far: 1000 },
      gl: { antialias: true, powerPreference: 'high-performance' },
      dpr: [1, 2],
    },
    React.createElement('ambientLight', { intensity: 0.5 }),
    React.createElement('directionalLight', { position: [2, 3, 2], intensity: 1.1 }),
    React.createElement(
      Suspense,
      { fallback: null },
      React.createElement(AvatarHead, { modelUrl, speechStream, emotion, customMorphs }),
      React.createElement(Environment, { preset: 'studio' })
    )
  );
}

export { EMOTION_PRESETS, springStep, AvatarHead };
