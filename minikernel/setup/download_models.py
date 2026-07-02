#!/usr/bin/env python3
"""
MiniKernel Model Downloader

Downloads AI models required by the minikernel:
  - LLM  : Quantized GGUF models for llama.cpp (inference_engine.py)
  - STT  : Whisper .bin models for whisper.cpp (voice_pipeline.py)
  - TTS  : Piper .onnx voice models            (voice_pipeline.py)

Usage:
  python setup/download_models.py list
  python setup/download_models.py status
  python setup/download_models.py download             # default set
  python setup/download_models.py download -m whisper-base piper-amy
  python setup/download_models.py download --all
  python setup/download_models.py verify
"""

import argparse
import hashlib
import logging
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("MiniKernel.Setup")


# ── Model Registry ────────────────────────────────────────────────────────────

@dataclass
class ModelSpec:
    name: str
    url: str
    dest: str           # relative path inside models_dir
    sha256: str = ""    # full or prefix of hex digest (empty = skip check)
    description: str = ""
    size_mb: int = 0
    tags: List[str] = field(default_factory=list)


_HF_WHISPER = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
_HF_PIPER   = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

# Quantized LLMs ─ dest paths intentionally match inference_engine.py defaults
LLM_MODELS: Dict[str, ModelSpec] = {
    "phi3-mini-q4": ModelSpec(
        name="phi3-mini-q4",
        url=(
            "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf"
            "/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
        ),
        dest="phi3-mini-q4.gguf",
        description="Phi-3 Mini 4K Instruct Q4 (~2.2 GB) — best for low-RAM systems",
        size_mb=2200,
        tags=["llm", "default", "lightweight"],
    ),
    "llama3-8b-q4": ModelSpec(
        name="llama3-8b-q4",
        url=(
            "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF"
            "/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"
        ),
        dest="llama-3-8b-q4.gguf",   # matches inference_engine.py default path
        description="Llama 3 8B Instruct Q4_K_M (~4.9 GB) — higher quality, 8 GB+ RAM",
        size_mb=4900,
        tags=["llm", "quality"],
    ),
    "mistral-7b-q4": ModelSpec(
        name="mistral-7b-q4",
        url=(
            "https://huggingface.co/TheBloke/Mistral-7B-v0.1-GGUF"
            "/resolve/main/mistral-7b-v0.1.Q4_K_M.gguf"
        ),
        dest="mistral-7b-q4.gguf",
        description="Mistral 7B v0.1 Q4_K_M (~4.1 GB) — strong general-purpose model",
        size_mb=4100,
        tags=["llm"],
    ),
}

# Whisper STT models (whisper.cpp .bin format)
WHISPER_MODELS: Dict[str, ModelSpec] = {
    "whisper-tiny": ModelSpec(
        name="whisper-tiny",
        url=f"{_HF_WHISPER}/ggml-tiny.en.bin",
        dest="whisper/ggml-tiny.en.bin",
        sha256="bd577a113a864445d4c299885e0cb97d4ba92b5f",
        description="Whisper Tiny English (~75 MB) — fastest, lowest accuracy",
        size_mb=75,
        tags=["stt", "lightweight"],
    ),
    "whisper-base": ModelSpec(
        name="whisper-base",
        url=f"{_HF_WHISPER}/ggml-base.en.bin",
        dest="whisper/ggml-base.en.bin",
        sha256="137c40403d78fd54d454da0f9bd998f78703390",
        description="Whisper Base English (~142 MB) — recommended default for voice pipeline",
        size_mb=142,
        tags=["stt", "default"],
    ),
    "whisper-small": ModelSpec(
        name="whisper-small",
        url=f"{_HF_WHISPER}/ggml-small.en.bin",
        dest="whisper/ggml-small.en.bin",
        sha256="55356645c2b361a969dfd0ef2c5a50d530afd8d5",
        description="Whisper Small English (~466 MB) — better accuracy, slower",
        size_mb=466,
        tags=["stt", "quality"],
    ),
}

# Piper TTS models (.onnx + JSON config pairs)
PIPER_MODELS: Dict[str, ModelSpec] = {
    "piper-amy": ModelSpec(
        name="piper-amy",
        url=f"{_HF_PIPER}/en/en_US/amy/medium/en_US-amy-medium.onnx",
        dest="piper/en_US-amy-medium.onnx",
        description="Piper Amy US English medium (~63 MB) — default voice",
        size_mb=63,
        tags=["tts", "default"],
    ),
    "piper-amy-config": ModelSpec(
        name="piper-amy-config",
        url=f"{_HF_PIPER}/en/en_US/amy/medium/en_US-amy-medium.onnx.json",
        dest="piper/en_US-amy-medium.onnx.json",
        description="Piper Amy config (required alongside the .onnx file)",
        size_mb=0,
        tags=["tts", "config"],
    ),
    "piper-lessac": ModelSpec(
        name="piper-lessac",
        url=f"{_HF_PIPER}/en/en_US/lessac/high/en_US-lessac-high.onnx",
        dest="piper/en_US-lessac-high.onnx",
        description="Piper Lessac US English high quality (~61 MB)",
        size_mb=61,
        tags=["tts", "quality"],
    ),
    "piper-lessac-config": ModelSpec(
        name="piper-lessac-config",
        url=f"{_HF_PIPER}/en/en_US/lessac/high/en_US-lessac-high.onnx.json",
        dest="piper/en_US-lessac-high.onnx.json",
        description="Piper Lessac config (required alongside the .onnx file)",
        size_mb=0,
        tags=["tts", "config"],
    ),
}

ALL_MODELS: Dict[str, ModelSpec] = {**LLM_MODELS, **WHISPER_MODELS, **PIPER_MODELS}

# Downloaded when no specific model is requested
DEFAULT_MODELS = ["whisper-base", "piper-amy", "piper-amy-config"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _models_dir(override: Optional[Path] = None) -> Path:
    """Return the absolute models directory."""
    if override:
        return override.resolve()
    # This file lives at minikernel/setup/download_models.py
    return Path(__file__).resolve().parent.parent / "models"


def _fmt_size(mb: int) -> str:
    if mb == 0:
        return "—"
    return f"{mb} MB" if mb < 1024 else f"{mb / 1024:.1f} GB"


def _sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _progress(count: int, block_size: int, total_size: int) -> None:
    downloaded = min(count * block_size, total_size) if total_size > 0 else count * block_size
    if total_size > 0:
        pct = downloaded * 100 / total_size
        filled = int(30 * pct / 100)
        bar = "█" * filled + "░" * (30 - filled)
        mb_done  = downloaded   / (1024 * 1024)
        mb_total = total_size   / (1024 * 1024)
        print(f"\r  [{bar}] {pct:5.1f}%  {mb_done:.1f}/{mb_total:.1f} MB",
              end="", flush=True)
    else:
        print(f"\r  {downloaded / (1024*1024):.1f} MB downloaded",
              end="", flush=True)


def _download(url: str, dest: Path, sha256: str = "") -> bool:
    """Download *url* to *dest*, optionally verifying sha256."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest, reporthook=_progress)
        print()
    except Exception as exc:
        print()
        logger.error("Download error: %s", exc)
        if dest.exists():
            dest.unlink()
        return False

    if sha256:
        print("  Verifying checksum ...", end="", flush=True)
        actual = _sha256(dest)
        if not actual.startswith(sha256.lower()):
            print(f" FAIL\n    Expected: {sha256}\n    Got:      {actual}")
            dest.unlink()
            return False
        print(" OK")

    return True


# ── Sub-commands ──────────────────────────────────────────────────────────────

def cmd_list(args: argparse.Namespace) -> int:
    models_dir = _models_dir(args.models_dir)

    sections = [
        ("LLM — quantized GGUF (llama.cpp)", LLM_MODELS),
        ("STT — Whisper (whisper.cpp)",       WHISPER_MODELS),
        ("TTS — Piper voice models",           PIPER_MODELS),
    ]

    for title, group in sections:
        print(f"\n{title}")
        print("  " + "─" * 64)
        for key, spec in group.items():
            installed = (models_dir / spec.dest).exists()
            marker  = "✓" if installed else " "
            default = " [default]" if key in DEFAULT_MODELS else ""
            print(f"  [{marker}] {key:<30} {_fmt_size(spec.size_mb):<10}{default}")
            print(f"       {spec.description}")
    print()
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    models_dir = _models_dir(args.models_dir)
    print(f"\nModels directory: {models_dir}\n")

    total_bytes = 0
    for name, spec in ALL_MODELS.items():
        if "config" in spec.tags:
            continue
        dest = models_dir / spec.dest
        if dest.exists():
            sz = dest.stat().st_size
            total_bytes += sz
            print(f"  ✓  {name:<32} {sz / (1024*1024):.1f} MB")
        else:
            print(f"  ✗  {name:<32} not installed")

    print(f"\n  Disk usage: {total_bytes / (1024**3):.2f} GB\n")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    models_dir = _models_dir(args.models_dir)

    if args.all:
        to_download = list(ALL_MODELS.keys())
    elif getattr(args, "model", None):
        to_download = list(args.model)
    else:
        to_download = DEFAULT_MODELS[:]

    unknown = [m for m in to_download if m not in ALL_MODELS]
    if unknown:
        print(f"Unknown model(s): {', '.join(unknown)}")
        print("Run 'list' to see available models.")
        return 1

    total_mb = sum(ALL_MODELS[m].size_mb for m in to_download)
    print(f"\nModels directory : {models_dir}")
    print(f"Models requested : {', '.join(to_download)}")
    print(f"Estimated size   : ~{_fmt_size(total_mb)}\n")

    failed: List[str]  = []
    skipped: List[str] = []
    success: List[str] = []

    for name in to_download:
        spec = ALL_MODELS[name]
        dest = models_dir / spec.dest

        if dest.exists() and not args.force:
            print(f"  SKIP  {name}  (exists — use --force to re-download)")
            skipped.append(name)
            continue

        print(f"\n[{name}]  {spec.description}")
        ok = _download(spec.url, dest, spec.sha256)
        if ok:
            print(f"  Saved → {dest}")
            success.append(name)
        else:
            print(f"  ERROR downloading {name}")
            failed.append(name)

    print()
    if success:
        print(f"Downloaded : {', '.join(success)}")
    if skipped:
        print(f"Skipped    : {', '.join(skipped)}")
    if failed:
        print(f"Failed     : {', '.join(failed)}")
        return 1

    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    models_dir = _models_dir(args.models_dir)
    print(f"\nVerifying models in {models_dir}\n")

    errors = 0
    checked = 0

    for name, spec in ALL_MODELS.items():
        dest = models_dir / spec.dest
        if not dest.exists():
            continue
        if not spec.sha256:
            print(f"  {name:<32} no checksum defined — skip")
            continue

        print(f"  {name:<32} checking ...", end="", flush=True)
        actual = _sha256(dest)
        if actual.startswith(spec.sha256.lower()):
            print(" OK")
            checked += 1
        else:
            print(f" FAIL\n    expected: {spec.sha256}\n    got:      {actual}")
            errors += 1

    print()
    if errors:
        print(f"Verification failed for {errors} model(s).")
        return 1
    print(f"All {checked} verified model(s) OK.")
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python setup/download_models.py",
        description="Download AI models for MiniKernel (LLM / STT / TTS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--models-dir", type=Path, metavar="PATH",
        help="Override the models directory (default: minikernel/models/)",
    )
    p.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="WARNING",
    )

    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list",   help="Show available models and installation status")
    sub.add_parser("status", help="Show installed models and total disk usage")
    sub.add_parser("verify", help="Verify SHA-256 checksums for downloaded models")

    dl = sub.add_parser(
        "download",
        help="Download models (downloads the default set when no flags are given)",
    )
    dl.add_argument(
        "-m", "--model", nargs="+", metavar="NAME",
        help="Specific model name(s) to download",
    )
    dl.add_argument(
        "--all", action="store_true",
        help="Download every available model (warning: several GB)",
    )
    dl.add_argument(
        "--force", "-f", action="store_true",
        help="Re-download even if the file already exists",
    )

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    return {
        "list":     cmd_list,
        "status":   cmd_status,
        "download": cmd_download,
        "verify":   cmd_verify,
    }[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
