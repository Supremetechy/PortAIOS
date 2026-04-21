// Avatar.jsx
// Drop-in 3D agent avatar for the AIOS GUI.
// Renders a Ready Player Me glTF head, drives ARKit blendshapes from a
// viseme keyframe stream synchronized to a Web Audio AudioBufferSourceNode.
//
// Usage:
//   <Avatar
//     agentId="grahm"
//     modelUrl="/avatars/grahm.glb"
//     speechStream={speechStream}   // see useSpeechStream hook below
//     emotion="neutral"             // 'neutral' | 'happy' | 'focused' | 'concerned'
//   />

import React, { useRef, useEffect, useMemo, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { useGLTF, Environment } from '@react-three/drei';
import * as THREE from 'three';
import { PHONEME_TO_VISEME } from './phonemeMap';

// ─── Emotion presets → blendshape weight targets ──────────────────────
const EMOTION_PRESETS = {
  neutral:   {},
  happy:     { mouthSmileLeft: 0.6, mouthSmileRight: 0.6, cheekSquintLeft: 0.3, cheekSquintRight: 0.3, browInnerUp: 0.15 },
  focused:   { browDownLeft: 0.4, browDownRight: 0.4, eyeSquintLeft: 0.2, eyeSquintRight: 0.2 },
  concerned: { browInnerUp: 0.7, mouthFrownLeft: 0.3, mouthFrownRight: 0.3 },
  thinking:  { browDownLeft: 0.25, browDownRight: 0.25, mouthPucker: 0.15 },
};

// ─── Critically-damped spring for blendshape smoothing ────────────────
// Avoids "robotic" snap-to-target; gives ~50ms coarticulation blur.
function springStep(current, target, velocity, dt, halfLife = 0.045) {
  const omega = Math.log(2) / halfLife;
  const dx = target - current;
  const accel = omega * omega * dx - 2 * omega * velocity;
  const newVel = velocity + accel * dt;
  const newPos = current + newVel * dt;
  return [newPos, newVel];
}

function AvatarHead({ modelUrl, speechStream, emotion }) {
  const { scene } = useGLTF(modelUrl);
  const headRef = useRef();

  // Collect every mesh that has morph targets (RPM splits head/teeth/tongue).
  const morphMeshes = useMemo(() => {
    const meshes = [];
    scene.traverse((obj) => {
      if (obj.isMesh && obj.morphTargetDictionary) meshes.push(obj);
    });
    return meshes;
  }, [scene]);

  // Per-blendshape state: { name: { value, velocity } }
  const stateRef = useRef({});
  const blinkRef = useRef({ next: performance.now() + 3000, closing: false, phase: 0 });

  useFrame((_, dt) => {
    if (!speechStream.current) return;

    // 1. Resolve current audio time in the speech stream's clock domain.
    //    This is the single source of truth for lip-sync timing.
    const audioT = speechStream.current.getCurrentTime(); // seconds, or null if idle

    // 2. Compute target viseme weights at this audio time.
    const targets = { ...EMOTION_PRESETS[emotion] || {} };

    if (audioT != null) {
      const kf = speechStream.current.getActiveVisemes(audioT);
      // kf is [{ viseme, weight }, ...] already cross-faded between adjacent phonemes
      for (const { viseme, weight } of kf) {
        targets[viseme] = (targets[viseme] || 0) + weight;
      }
      // Jaw openness derived from vowel visemes for extra liveliness
      const jawDrive = (targets['viseme_aa'] || 0) * 0.9
                     + (targets['viseme_O']  || 0) * 0.7
                     + (targets['viseme_E']  || 0) * 0.4;
      targets['jawOpen'] = Math.min(1, jawDrive);
    }

    // 3. Blink scheduler (independent of speech).
    const now = performance.now();
    const blink = blinkRef.current;
    if (now >= blink.next && !blink.closing) {
      blink.closing = true;
      blink.phase = 0;
    }
    if (blink.closing) {
      blink.phase += dt / 0.12; // 120ms full blink
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

    // 4. Apply to every mesh with a morphTargetDictionary.
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

  return <primitive ref={headRef} object={scene} position={[0, -1.55, 0]} />;
}

export default function Avatar({ agentId, modelUrl, speechStream, emotion = 'neutral' }) {
  return (
    <Canvas
      camera={{ position: [0, 0.05, 0.75], fov: 22 }}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      dpr={[1, 2]}
    >
      <ambientLight intensity={0.5} />
      <directionalLight position={[2, 3, 2]} intensity={1.1} />
      <Suspense fallback={null}>
        <AvatarHead modelUrl={modelUrl} speechStream={speechStream} emotion={emotion} />
        <Environment preset="studio" />
      </Suspense>
    </Canvas>
  );
}