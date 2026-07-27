"""
Agent Loop

Multi-step autonomous execution: plans a natural-language goal into
discrete steps, executes each through the validated intent pipeline
(parser -> validator -> confirmation -> execution engine), observes the
result, and self-corrects a small set of known failure patterns (e.g. a
missing package) before retrying the step.

This does not bypass the existing security model: every generated
corrective action re-enters the same parser/validator/confirmation path
as a user-issued command, so a self-correction that installs a package
still requires the same confirmation a human-issued install would.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from minikernel.intent.intent_parser import IntentParser, IntentResult
from minikernel.intent.command_validator import CommandValidator, ValidationResult
from minikernel.intent.execution_engine import ExecutionEngine, ExecutionResult

logger = logging.getLogger("MiniKernel.AgentLoop")

# Split a compound goal into ordered steps on common connective phrases.
# The ";\s*then\s+" alternative must come before the bare ";" one so a
# "step one; then step two" chain consumes the connective "then" too,
# rather than leaving it stuck on the front of the next step.
_STEP_SPLIT_RE = re.compile(
    r"\s*(?:,?\s+and then\s+|,?\s+then\s+|\s*;\s*then\s+|\s*;\s*)\s*",
    re.IGNORECASE,
)

# Known failure signatures -> what's missing, so a corrective step can be built.
_MODULE_NOT_FOUND_RE = re.compile(r"no module named ['\"]?([\w.]+)['\"]?", re.IGNORECASE)
_FILE_NOT_FOUND_RE = re.compile(r"no such file or directory:?\s*'?([\w./\-]+)'?", re.IGNORECASE)


@dataclass
class CorrectionAttempt:
    """A single self-correction generated in response to a failed step."""
    reason: str
    action: str
    result: Optional[ExecutionResult] = None


@dataclass
class AgentStep:
    """One planned step of an agent run, with its execution trace."""
    text: str
    intent: Optional[IntentResult] = None
    validation: Optional[ValidationResult] = None
    result: Optional[ExecutionResult] = None
    corrections: List[CorrectionAttempt] = field(default_factory=list)
    confirmed: bool = False

    @property
    def success(self) -> bool:
        return bool(self.result and self.result.success)


@dataclass
class AgentRunResult:
    """Full trace of a multi-step agent run."""
    goal: str
    steps: List[AgentStep] = field(default_factory=list)
    stopped_reason: Optional[str] = None

    @property
    def success(self) -> bool:
        return bool(self.steps) and self.stopped_reason is None and all(s.success for s in self.steps)

    def summary(self) -> str:
        lines = [f"Goal: {self.goal}"]
        for i, step in enumerate(self.steps, 1):
            status = "OK" if step.success else "FAILED"
            lines.append(f"  {i}. [{status}] {step.text}")
            for correction in step.corrections:
                outcome = "OK" if correction.result and correction.result.success else "FAILED"
                lines.append(f"       -> self-correction [{outcome}]: {correction.reason} => {correction.action}")
            if step.result and not step.result.success and step.result.error:
                lines.append(f"       error: {step.result.error}")
        if self.stopped_reason:
            lines.append(f"Stopped: {self.stopped_reason}")
        return "\n".join(lines)


class AgentLoop:
    """
    Autonomous multi-step execution loop for MiniKernel.

    plan     -> split a goal into ordered step strings.
    act      -> run each step through parser -> validator -> confirmation -> executor.
    observe  -> inspect the resulting ExecutionResult for known failure signatures.
    correct  -> execute a corrective step (e.g. install a missing package) through
                the same validated pipeline, then retry the original step once.

    `confirm_fn(prompt, risk_level) -> bool` gates any step the validator marks
    as requiring confirmation, including self-generated corrections. It
    defaults to always denying, so nothing destructive runs unattended unless
    the caller explicitly wires up a confirmation channel (CLI prompt, voice
    confirmation loop, etc).
    """

    def __init__(
        self,
        kernel,
        confirm_fn: Optional[Callable[[str, str], bool]] = None,
        max_steps: int = 12,
        max_corrections_per_step: int = 2,
    ):
        self.kernel = kernel
        self.parser: IntentParser = kernel.get_service("intent_parser") or IntentParser()
        self.validator: CommandValidator = kernel.get_service("validator") or CommandValidator()
        self.executor: ExecutionEngine = kernel.get_service("execution_engine") or ExecutionEngine(kernel)
        self.confirm_fn = confirm_fn or (lambda prompt, risk_level: False)
        self.max_steps = max_steps
        self.max_corrections_per_step = max_corrections_per_step

    def plan(self, goal: str) -> List[str]:
        """Split a compound natural-language goal into ordered step strings."""
        parts = [p.strip() for p in _STEP_SPLIT_RE.split(goal) if p.strip()]
        return parts or [goal.strip()]

    def run(self, goal: str) -> AgentRunResult:
        """Plan and execute a (possibly multi-step) goal, self-correcting where possible."""
        run_result = AgentRunResult(goal=goal)
        step_texts = self.plan(goal)

        if len(step_texts) > self.max_steps:
            step_texts = step_texts[: self.max_steps]
            run_result.stopped_reason = f"Goal truncated to {self.max_steps} steps"

        logger.info(f"Agent loop planned {len(step_texts)} step(s) for goal: {goal!r}")

        for step_text in step_texts:
            step = self._execute_step(step_text)
            run_result.steps.append(step)

            if not step.success:
                run_result.stopped_reason = f"Step failed and could not be corrected: {step_text!r}"
                logger.warning(run_result.stopped_reason)
                break

        return run_result

    def _execute_step(self, text: str) -> AgentStep:
        step = AgentStep(text=text)
        result = self._run_intent(text, step, record=True)
        step.result = result

        attempts = 0
        while not result.success and attempts < self.max_corrections_per_step:
            correction = self._diagnose(result)
            if not correction:
                break

            attempts += 1
            logger.info(f"Self-correcting step {text!r}: {correction.reason} -> {correction.action}")

            correction_step = AgentStep(text=correction.action)
            correction.result = self._run_intent(correction.action, correction_step, record=False)
            step.corrections.append(correction)

            if not correction.result.success:
                # Correction itself failed (denied, package not found, etc.) —
                # no point retrying the original step against the same gap.
                break

            # Correction succeeded; retry the original step.
            result = self._run_intent(text, step, record=True)
            step.result = result

        return step

    def _run_intent(self, text: str, step: AgentStep, record: bool) -> ExecutionResult:
        """Parse -> validate -> confirm -> execute a single step of text."""
        intent = self.parser.parse(text)
        validation = self.validator.validate(intent)

        if record:
            step.intent = intent
            step.validation = validation

        confirmed = False
        if validation.is_valid:
            if validation.requires_confirmation:
                confirmed = self.confirm_fn(validation.confirmation_prompt or text, validation.risk_level.value)
            else:
                confirmed = True

        if record:
            step.confirmed = confirmed

        return self.executor.execute(intent, validation, confirmed=confirmed)

    def _diagnose(self, result: ExecutionResult) -> Optional[CorrectionAttempt]:
        """Inspect a failed ExecutionResult for a known, auto-correctable cause."""
        error_text = result.error or ""

        if match := _MODULE_NOT_FOUND_RE.search(error_text):
            package = match.group(1).split(".")[0]
            return CorrectionAttempt(
                reason=f"missing Python module '{package}'",
                action=f"install {package}",
            )

        if match := _FILE_NOT_FOUND_RE.search(error_text):
            command = os.path.basename(match.group(1))
            return CorrectionAttempt(
                reason=f"missing command or file '{command}'",
                action=f"install {command}",
            )

        return None
