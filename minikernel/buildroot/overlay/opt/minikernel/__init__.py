"""
MiniKernel - AI-First Voice-Controlled Operating System
A lightweight microkernel with LLM-as-an-Interface architecture
"""

__version__ = "0.1.0"
__author__ = "MiniKernel Project"

from minikernel.core.microkernel import MicroKernel
from minikernel.intent.intent_parser import IntentParser
from minikernel.ai.voice_pipeline import VoicePipeline

__all__ = ["MicroKernel", "IntentParser", "VoicePipeline"]
