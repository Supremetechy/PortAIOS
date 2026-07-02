"""
Intent Engine - The bridge between natural language and kernel operations
"""

from minikernel.intent.intent_parser import IntentParser
from minikernel.intent.command_validator import CommandValidator
from minikernel.intent.execution_engine import ExecutionEngine

__all__ = ["IntentParser", "CommandValidator", "ExecutionEngine"]
