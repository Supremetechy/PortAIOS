// useSpeechStream.js
// Manages a single active utterance for an agent avatar:
//   - decodes the Piper WAV into an AudioBuffer
//   - schedules playback on a shared AudioContext
//   - exposes getCurrentTime() (audio-clock seconds into the utterance)
//   - exposes getActiveVisemes(t) that cross-fades between adjacent phonemes
//
// Designed to be fed from your local Piper service over WebSocket.
// Expected server message shape per utterance:
//   {
//     utterance_id: "u_123",
//     audio: <ArrayBuffer | base64 WAV>,
//     phonemes: [{ p: "h", t: 0.00, d: 0.04 }, { p: "E", t: 0.04, d: 0.09 }, ...]
//   }

import { useRef, useCallback, useEffect } from 'react';

// Reuse the same mapping used by Avatar.jsx. Import it if you prefer.
import { PHONEME_TO_VISEME } from './phonemeMap'; // or inline the table

// Module-level shared context — one AudioContext per tab is best practice.
let sharedCtx = null;
function getCtx() {
  if (!sharedCtx) {
    sharedCtx = new (window.AudioContext || window.webkitAudioContext)({
      latencyHint: 'interactive',
    });
  }
  return sharedCtx;
}

export function useSpeechStream() {
  // The ref the <Avatar/> polls each frame.
  const streamRef = useRef(null);

  const stop = useCallback(() => {
    const s = streamRef.current;
    if (s?.source) {
      try { s.source.stop(); } catch {}
    }
    streamRef.current = null;
  }, []);

  const speak = useCallback(async ({ audio, phonemes, onEnd }) => {
    const ctx = getCtx();
    if (ctx.state === 'suspended') await ctx.resume();

    // Accept ArrayBuffer or base64 string
    let ab = audio;
    if (typeof audio === 'string') {
      const bin = atob(audio);
      ab = new ArrayBuffer(bin.length);
      const view = new Uint8Array(ab);
      for (let i = 0; i < bin.length; i++) view[i] = bin.charCodeAt(i);
    }

    const buffer = await ctx.decodeAudioData(ab.slice(0));
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);

    // Precompute viseme keyframes from phonemes.
    // Each keyframe has a center time + a triangular weight envelope that
    // overlaps with its neighbours. 60ms ramp works well for natural coarticulation.
    const RAMP = 0.06;
    const keyframes = phonemes.map(({ p, t, d }) => ({
      viseme: PHONEME_TO_VISEME[p] || 'viseme_sil',
      tStart: t,
      tPeak:  t + d * 0.5,
      tEnd:   t + d,
      ramp:   Math.min(RAMP, d * 0.5),
    }));

    // Schedule playback precisely on the audio clock.
    const startAt = ctx.currentTime + 0.02; // 20ms lookahead for scheduler safety
    source.start(startAt);

    const stream = {
      source,
      startAt,
      duration: buffer.duration,
      keyframes,

      getCurrentTime() {
        const t = ctx.currentTime - startAt;
        if (t < 0 || t > buffer.duration) return null;
        return t;
      },

      getActiveVisemes(t) {
        // Find all keyframes whose envelope covers t. Cheap linear scan
        // is fine for <1000 phonemes per utterance; upgrade to binary
        // search + windowed cursor if you stream long responses.
        const out = [];
        for (const kf of keyframes) {
          if (t < kf.tStart - kf.ramp || t > kf.tEnd + kf.ramp) continue;
          let w;
          if (t < kf.tStart)      w = (t - (kf.tStart - kf.ramp)) / kf.ramp;
          else if (t > kf.tEnd)   w = 1 - (t - kf.tEnd) / kf.ramp;
          else if (t < kf.tPeak)  w = (t - kf.tStart) / Math.max(1e-3, kf.tPeak - kf.tStart);
          else                    w = 1 - (t - kf.tPeak) / Math.max(1e-3, kf.tEnd - kf.tPeak);
          w = Math.max(0, Math.min(1, w));
          if (w > 0.01) out.push({ viseme: kf.viseme, weight: w });
        }
        return out;
      },
    };

    source.onended = () => {
      if (streamRef.current === stream) streamRef.current = null;
      onEnd?.();
    };

    streamRef.current = stream;
    return stream;
  }, []);

  useEffect(() => () => stop(), [stop]);

  return { streamRef, speak, stop };
}