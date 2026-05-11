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
    python3 piper_viseme_server.py --model en_US-amy-medium.onnx --port 8765

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
from pathlib import Path

import numpy as np
import websockets
from websockets.http11 import Response
from websockets.datastructures import Headers

try:
    from piper import PiperVoice
except ImportError as _exc:
    raise ImportError(
        "piper-tts is not installed. Install with `pip install piper-tts` "
        "(the PyPI package is `piper-tts`; the import name is `piper`)."
    ) from _exc

# Default location of the bundled Piper voice. The .onnx model and its
# .onnx.json config must live in the same directory — Piper derives the
# config path by appending '.json' to the model path.
_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = _REPO_ROOT / "models" / "piper" / "en_US-amy-medium.onnx"


class VisemeSynth:
    """Wraps a PiperVoice and produces (wav_bytes, phoneme_timeline) pairs."""

    def __init__(self, model_path: str, config_path: str | None = None):
        """Load a Piper voice model from disk."""
        self.voice = PiperVoice.load(model_path, config_path=config_path)
        self.sample_rate = self.voice.config.sample_rate

    def synth(self, text: str):
        """Synthesize speech and return (wav_bytes, phoneme_timeline).

        Uses the PiperVoice.synthesize() streaming API (the older
        ``synthesize_ids_to_raw`` was removed in piper-tts 1.4). For each
        AudioChunk we ask for alignments, but most published Piper voices
        do not export per-phoneme sample counts (``phoneme_id_samples`` is
        None). When that's the case we fall back to distributing the chunk's
        duration uniformly across its IPA phonemes — coarse but adequate
        for jaw / lip blendshape coarticulation.
        """
        audio_chunks: list[np.ndarray] = []
        timeline: list[dict] = []
        cursor_samples = 0

        for chunk in self.voice.synthesize(text, include_alignments=True):
            phonemes = list(chunk.phonemes or [])
            samples_per_phoneme = chunk.phoneme_id_samples
            chunk_audio = chunk.audio_int16_array
            chunk_len = int(chunk_audio.shape[0])

            if samples_per_phoneme is not None and len(samples_per_phoneme) == len(phonemes):
                # Voice supports true alignment — use it.
                for ipa, nsamp in zip(phonemes, samples_per_phoneme):
                    nsamp = int(nsamp)
                    timeline.append({
                        'p': ipa,
                        't': round(cursor_samples / self.sample_rate, 4),
                        'd': round(nsamp / self.sample_rate, 4),
                    })
                    cursor_samples += nsamp
            elif phonemes:
                # Fallback: uniform distribution across the chunk's duration.
                per = chunk_len / max(1, len(phonemes))
                for i, ipa in enumerate(phonemes):
                    t = (cursor_samples + i * per) / self.sample_rate
                    timeline.append({
                        'p': ipa,
                        't': round(t, 4),
                        'd': round(per / self.sample_rate, 4),
                    })
                cursor_samples += chunk_len
            else:
                cursor_samples += chunk_len

            audio_chunks.append(chunk_audio)

        audio = (
            np.concatenate(audio_chunks)
            if audio_chunks
            else np.zeros(0, dtype=np.int16)
        )
        wav_bytes = self._to_wav(audio)
        return wav_bytes, timeline

    def _to_wav(self, pcm_i16: np.ndarray) -> bytes:
        """Wrap a mono int16 PCM array as a complete WAV byte stream."""
        buf = io.BytesIO()
        # `wave.open(..., 'wb')` returns Wave_write; the explicit annotation
        # silences pylint, which can't narrow the Wave_read | Wave_write union.
        w: wave.Wave_write = wave.open(buf, 'wb')
        try:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.sample_rate)
            w.writeframes(pcm_i16.tobytes())
        finally:
            w.close()
        return buf.getvalue()


def _normalize_connection_header(_connection, request):
    """Patch the WS handshake request so picky validators accept it.

    websockets >= 13 strictly requires the ``Connection`` header to contain
    the ``Upgrade`` token. Some clients (older Eel/Bottle, certain proxies,
    Safari in some configurations) send only ``Connection: keep-alive``,
    which trips ``InvalidUpgrade: invalid Connection header: keep-alive``.
    Re-write that header in-place so the validator finds the token it wants.

    If this port receives a plain HTTP request, return a small 426 response
    instead of letting websockets raise ``InvalidUpgrade: missing Upgrade
    header`` during handshake validation.
    """
    upgrade = request.headers.get('Upgrade', '')
    if 'websocket' not in upgrade.lower():
        body = b'This endpoint expects a WebSocket upgrade request.\n'
        headers = Headers()
        headers['Content-Type'] = 'text/plain; charset=utf-8'
        headers['Content-Length'] = str(len(body))
        headers['Connection'] = 'close'
        headers['Upgrade'] = 'websocket'
        return Response(426, 'Upgrade Required', headers, body)

    connection = request.headers.get('Connection', '')
    tokens = [t.strip() for t in connection.split(',') if t.strip()]
    if not any(t.lower() == 'upgrade' for t in tokens):
        tokens.append('Upgrade')
        request.headers['Connection'] = ', '.join(tokens) or 'Upgrade'
    return None


async def handler(ws, synth: VisemeSynth):
    """Per-connection request loop. Speaks two request/response protocols:

    1. Native (this server's own):
       → {"utterance_id": "u_1", "text": "..."}
       ← {"utterance_id": "u_1", "audio": "<b64 wav>", "phonemes": [...]}

    2. avatar-controller.js compat layer:
       → {"type": "tts_request", "text": "...", "emotion": "..."}
       ← {"type": "audio_data", "data": "<b64 wav>"}
       ← {"type": "phonemes", "phonemes": [...]}
       ← {"type": "tts_complete"}

    The browser controller times out after 10s waiting for `tts_complete`
    and falls back to Web Speech API; (2) keeps that path alive.
    """
    async for raw in ws:
        try:
            req = json.loads(raw)
        except json.JSONDecodeError as e:
            await ws.send(json.dumps({'error': f'bad request: {e}'}))
            continue

        # Detect which protocol the caller is using.
        is_browser_protocol = req.get('type') == 'tts_request'
        text = req.get('text')
        if not text:
            await ws.send(json.dumps({'error': 'missing text field'}))
            continue

        try:
            wav_bytes, timeline = await asyncio.to_thread(synth.synth, text)
        except Exception as e:  # noqa: BLE001 — surface synth failures to client
            err_payload = (
                {'type': 'tts_error', 'error': str(e)}
                if is_browser_protocol
                else {'utterance_id': req.get('utterance_id', ''), 'error': str(e)}
            )
            await ws.send(json.dumps(err_payload))
            continue

        audio_b64 = base64.b64encode(wav_bytes).decode('ascii')

        if is_browser_protocol:
            await ws.send(json.dumps({'type': 'audio_data', 'data': audio_b64}))
            await ws.send(json.dumps({'type': 'phonemes', 'phonemes': timeline}))
            await ws.send(json.dumps({'type': 'tts_complete'}))
        else:
            await ws.send(json.dumps({
                'utterance_id': req.get('utterance_id', ''),
                'audio': audio_b64,
                'phonemes': timeline,
            }))


async def main():
    """CLI entry point: parse args, load the Piper voice, and run the WebSocket server."""
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '--model',
        default=str(DEFAULT_MODEL),
        help=f'Path to the Piper .onnx model (default: {DEFAULT_MODEL})',
    )
    ap.add_argument(
        '--config',
        default=None,
        help='Path to the .onnx.json config (default: <model>.json next to the model)',
    )
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8765)
    args = ap.parse_args()

    model_path = Path(args.model).expanduser()
    if not model_path.is_absolute():
        # Resolve relative paths against the bundled models dir, not CWD.
        model_path = _REPO_ROOT / "models" / "piper" / model_path
    if not model_path.exists():
        raise FileNotFoundError(
            f"Piper model not found: {model_path}. "
            f"Pass --model <path> or place the .onnx file at {DEFAULT_MODEL}."
        )
    config_path = args.config
    if config_path is None:
        derived = model_path.with_suffix(model_path.suffix + ".json")
        if not derived.exists():
            raise FileNotFoundError(
                f"Piper config not found at {derived}. The .onnx.json file "
                f"must live in the same directory as the .onnx model."
            )
        config_path = str(derived)

    synth = VisemeSynth(str(model_path), config_path)
    print(f'[piper-viseme] loaded {model_path} @ {synth.sample_rate} Hz')

    async with websockets.serve(
        lambda ws: handler(ws, synth),
        args.host,
        args.port,
        process_request=_normalize_connection_header,
    ):
        print(f'[piper-viseme] listening ws://{args.host}:{args.port}')
        await asyncio.Future()  # run forever


if __name__ == '__main__':
    asyncio.run(main())
