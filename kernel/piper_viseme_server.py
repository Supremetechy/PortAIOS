"""
piper_viseme_server.py

Wraps a local Piper TTS model and exposes a WebSocket endpoint that emits
both the synthesized WAV and a phoneme timeline the browser avatar can
consume for lip sync.

Piper's Python API exposes phoneme IDs + per-phoneme sample counts via
its `synthesize` streaming interface. We convert those to (phoneme, t, d)
triples against the model's sample rate.

Install:
    pip install piper-tts websockets numpy

Run:
    python piper_viseme_server.py --model en_US-amy-medium.onnx --port 8765

Client sends:   {"utterance_id": "u_1", "text": "Hello sir."}
Server returns: {"utterance_id": "u_1", "audio": "<base64 wav>",
                 "phonemes": [{"p": "h", "t": 0.0, "d": 0.04}, ...]}
"""

import argparse
import asyncio
import base64
import io
import json
import wave

import numpy as np
import websockets
from piper import PiperVoice


class VisemeSynth:
    def __init__(self, model_path: str, config_path: str | None = None):
        self.voice = PiperVoice.load(model_path, config_path=config_path)
        self.sample_rate = self.voice.config.sample_rate

    def synth(self, text: str):
        """Returns (wav_bytes, phoneme_timeline).

        Piper exposes a lower-level `synthesize_ids` path that gives us
        per-phoneme sample counts. We walk it to build the timeline while
        concatenating audio chunks.
        """
        audio_chunks: list[np.ndarray] = []
        timeline: list[dict] = []
        cursor_samples = 0

        # phonemize() returns list[list[str]] (one sub-list per sentence)
        sentence_phonemes = self.voice.phonemize(text)
        phoneme_ids_map = self.voice.config.phoneme_id_map

        for phonemes in sentence_phonemes:
            # Map IPA phonemes -> ids the model expects (BOS/EOS/PAD handled inside)
            phoneme_ids = self.voice.phonemes_to_ids(phonemes)

            # synthesize_ids_to_raw returns int16 mono PCM and, in recent
            # piper-tts builds, per-phoneme durations via phoneme_durations.
            audio_int16, durations = self.voice.synthesize_ids_to_raw(
                phoneme_ids, return_phoneme_durations=True
            )

            # durations is a list of sample counts aligned with phoneme_ids.
            # Skip special tokens (BOS/EOS/PAD) when mapping back to IPA.
            real_phonemes = iter(phonemes)
            for pid, nsamp in zip(phoneme_ids, durations):
                if pid in (phoneme_ids_map.get('^'), phoneme_ids_map.get('$'),
                           phoneme_ids_map.get('_'), phoneme_ids_map.get(' ')):
                    cursor_samples += nsamp
                    continue
                try:
                    ipa = next(real_phonemes)
                except StopIteration:
                    break
                t = cursor_samples / self.sample_rate
                d = nsamp / self.sample_rate
                timeline.append({'p': ipa, 't': round(t, 4), 'd': round(d, 4)})
                cursor_samples += nsamp

            audio_chunks.append(np.frombuffer(audio_int16, dtype=np.int16))

        audio = np.concatenate(audio_chunks) if audio_chunks else np.zeros(0, dtype=np.int16)
        wav_bytes = self._to_wav(audio)
        return wav_bytes, timeline

    def _to_wav(self, pcm_i16: np.ndarray) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.sample_rate)
            w.writeframes(pcm_i16.tobytes())
        return buf.getvalue()


async def handler(ws, synth: VisemeSynth):
    async for raw in ws:
        try:
            req = json.loads(raw)
            uid = req['utterance_id']
            text = req['text']
        except (json.JSONDecodeError, KeyError) as e:
            await ws.send(json.dumps({'error': f'bad request: {e}'}))
            continue

        # Offload blocking synth to a thread so the event loop stays responsive.
        wav_bytes, timeline = await asyncio.to_thread(synth.synth, text)
        await ws.send(json.dumps({
            'utterance_id': uid,
            'audio': base64.b64encode(wav_bytes).decode('ascii'),
            'phonemes': timeline,
        }))


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--config', default=None)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8765)
    args = ap.parse_args()

    synth = VisemeSynth(args.model, args.config)
    print(f'[piper-viseme] loaded {args.model} @ {synth.sample_rate} Hz')

    async with websockets.serve(lambda ws: handler(ws, synth), args.host, args.port):
        print(f'[piper-viseme] listening ws://{args.host}:{args.port}')
        await asyncio.Future()  # run forever


if __name__ == '__main__':
    asyncio.run(main())