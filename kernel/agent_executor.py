"""
AIOS Agent Executor

The agentic brain of AIOS. Takes natural language (voice or text),
determines intent + parameters, executes the matching command handler,
and returns a spoken + displayed response.

Intent recognition uses keyword/pattern matching (zero external
dependencies). When an LLM adapter is available, the agent can also
forward ambiguous queries to the model for richer reasoning.

Usage:
    from kernel.agent_executor import AgentExecutor

    agent = AgentExecutor()
    result = agent.execute("show me what programs are installed")
    print(result.message)  # detailed text output
    tts.speak(result.speak) # concise spoken response
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from kernel.agent_commands import COMMANDS, CommandResult

logger = logging.getLogger("AIOS.agent")


# ---------------------------------------------------------------------------
# Intent definitions — pattern → (command_key, context_extractor)
# ---------------------------------------------------------------------------

@dataclass
class IntentPattern:
    """Maps a regex pattern to a command key and optional context extractor."""
    pattern: re.Pattern
    command: str
    extract: Optional[Callable[[re.Match, str], Dict[str, Any]]] = None
    description: str = ""


def _extract_url(m: re.Match, text: str) -> Dict[str, Any]:
    """Pull a URL from the utterance."""
    url_match = re.search(r'(https?://\S+)', text)
    if url_match:
        return {"url": url_match.group(1)}
    # Check for domain-like tokens
    domain = re.search(r'(?:to|visit|go to)\s+(\S+\.\S+)', text, re.I)
    if domain:
        d = domain.group(1)
        if not d.startswith("http"):
            d = "https://" + d
        return {"url": d}
    return {}


def _extract_path(m: re.Match, text: str) -> Dict[str, Any]:
    path_match = re.search(r'(?:in|at|of|to|from)\s+["\']?([~/][\w/.@\- ]+)', text, re.I)
    if path_match:
        return {"path": path_match.group(1).strip().rstrip(".")}
    return {}


def _extract_app(m: re.Match, text: str) -> Dict[str, Any]:
    # "open safari" / "launch terminal" / "start vscode"
    app_match = re.search(
        r'(?:open|launch|start|run)\s+(?:the\s+)?(?:app(?:lication)?\s+)?(.+)',
        text, re.I,
    )
    if app_match:
        return {"app": app_match.group(1).strip().rstrip(".")}
    return {}


def _extract_package(m: re.Match, text: str) -> Dict[str, Any]:
    pkg_match = re.search(
        r'(?:install|download|get)\s+(?:the\s+)?(?:package\s+)?(.+)',
        text, re.I,
    )
    if pkg_match:
        return {"package": pkg_match.group(1).strip().rstrip(".")}
    return {}


def _extract_doc(m: re.Match, text: str) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {}
    name_match = re.search(r'(?:called|named|titled)\s+["\']?([^"\']+)', text, re.I)
    if name_match:
        name = name_match.group(1).strip().rstrip(".")
        if not name.endswith((".txt", ".md", ".py", ".html")):
            name += ".txt"
        ctx["name"] = name
    content_match = re.search(r'(?:with|containing|content)\s+["\'](.+?)["\']', text, re.I)
    if content_match:
        ctx["content"] = content_match.group(1)
    return ctx


def _extract_search(m: re.Match, text: str) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {}
    s = re.search(r'(?:search|find|look)\s+(?:for\s+)?(?:files?\s+)?(?:named?\s+)?(.+)', text, re.I)
    if s:
        ctx["pattern"] = s.group(1).strip().rstrip(".")
    path = re.search(r'(?:in|under|inside)\s+([~/][\w/.@\- ]+)', text, re.I)
    if path:
        ctx["directory"] = path.group(1).strip()
    return ctx


def _extract_command(m: re.Match, text: str) -> Dict[str, Any]:
    c = re.search(r'(?:run|execute|do)\s+(?:the\s+)?(?:command\s+)?["\']?(.+?)["\']?\s*$', text, re.I)
    if c:
        return {"command": c.group(1).strip()}
    return {}


def _extract_compat(m: re.Match, text: str) -> Dict[str, Any]:
    c = re.search(r'(?:compatib\w+|compat)\s+(?:of|for|with|check)?\s*(.+)', text, re.I)
    if c:
        return {"target": c.group(1).strip().rstrip(".")}
    return {}


# Build the intent table
INTENTS: List[IntentPattern] = [
    # Programs / apps
    IntentPattern(
        re.compile(r'\b(?:list|show|what)\b.*\b(?:programs?|apps?|applications?|software|installed)\b', re.I),
        "list_programs", description="List installed programs",
    ),
    # Open browser
    IntentPattern(
        re.compile(r'\b(?:open|launch|start)\b.*\b(?:browser|chrome|firefox|safari|web|internet)\b', re.I),
        "open_browser", _extract_url, "Open web browser",
    ),
    IntentPattern(
        re.compile(r'\b(?:go to|visit|navigate|browse)\b.*\b(\S+\.\S+)\b', re.I),
        "open_browser", _extract_url, "Navigate to URL",
    ),
    # File system
    IntentPattern(
        re.compile(r'\b(?:list|show|browse|ls|dir)\b.*\b(?:files?|folders?|director(?:y|ies))\b', re.I),
        "browse_filesystem", _extract_path, "Browse filesystem",
    ),
    IntentPattern(
        re.compile(r'\b(?:what\'?s?\s+in|contents?\s+of|look\s+at)\b', re.I),
        "browse_filesystem", _extract_path, "View directory contents",
    ),
    # Open file manager
    IntentPattern(
        re.compile(r'\b(?:open|launch)\b.*\b(?:file\s*manager|finder|explorer|nautilus)\b', re.I),
        "open_file_manager", _extract_path, "Open file manager",
    ),
    # Create document
    IntentPattern(
        re.compile(r'\b(?:create|make|new|write)\b.*\b(?:document|file|note|text)\b', re.I),
        "create_document", _extract_doc, "Create a document",
    ),
    # Screenshot / snapshot
    IntentPattern(
        re.compile(r'\b(?:take|capture|grab|save)\b.*\b(?:screenshot|snapshot|screen)\b', re.I),
        "take_snapshot", None, "Take a screenshot",
    ),
    # System status — before network so "show system status" doesn't hit network
    IntentPattern(
        re.compile(r'\b(?:system\s+status|system\s+stats|cpu\s+usage|memory\s+usage|ram\s+usage|disk\s+usage|uptime|health\s+check|show\s+status|show\s+stats)\b', re.I),
        "system_status", None, "Show system status",
    ),
    IntentPattern(
        re.compile(r'\b(?:status|stats)\b(?!.*\b(?:network|wifi|bluetooth|connection)\b)', re.I),
        "system_status", None, "Show system status",
    ),
    IntentPattern(
        re.compile(r'\b(?:cpu|memory|ram|disk)\b(?!.*\binfo\b)', re.I),
        "system_status", None, "Show system status",
    ),
    # Hardware
    IntentPattern(
        re.compile(r'\b(?:hardware|specs?|processor|gpu|cpu\s+info|what.*machine)\b', re.I),
        "hardware_info", None, "Show hardware info",
    ),
    # Network — require at least one network-specific keyword
    IntentPattern(
        re.compile(r'\b(?:network|wifi|internet|connectivity|connection[s]?|ip\s+address|interfaces?|ping|latency)\b', re.I),
        "check_network", None, "Check network connections",
    ),
    # Bluetooth
    IntentPattern(
        re.compile(r'\b(?:bluetooth|bt|paired|wireless\s+devices?)\b', re.I),
        "check_bluetooth", None, "Check Bluetooth devices",
    ),
    # Download / install
    IntentPattern(
        re.compile(r'\b(?:install|download|get|add)\b.*\b(?:software|package|program|app)\b', re.I),
        "download_software", _extract_package, "Install software",
    ),
    IntentPattern(
        re.compile(r'\b(?:pip|brew|apt|npm)\s+install\b', re.I),
        "download_software", _extract_package, "Install package",
    ),
    # Compatibility
    IntentPattern(
        re.compile(r'\b(?:compatib|compat\b)', re.I),
        "check_compatibility", _extract_compat, "Check compatibility",
    ),
    # Open application (generic — matches last)
    IntentPattern(
        re.compile(r'\b(?:open|launch|start|run)\b\s+(?!.*(?:browser|file\s*manager|finder|explorer))', re.I),
        "open_application", _extract_app, "Open an application",
    ),
    # Search files
    IntentPattern(
        re.compile(r'\b(?:search|find|locate|look\s+for)\b.*\b(?:file|document|folder)?\b', re.I),
        "search_files", _extract_search, "Search for files",
    ),
    # Processes
    IntentPattern(
        re.compile(r'\b(?:process(?:es)?|top|htop|task\s*manager|running|what\'?s?\s+running)\b', re.I),
        "list_processes", None, "List running processes",
    ),
    # Run shell command
    IntentPattern(
        re.compile(r'\b(?:run|execute|shell|terminal|command)\b.*["\']', re.I),
        "run_command", _extract_command, "Run a shell command",
    ),
]


# ---------------------------------------------------------------------------
# Conversation context for multi-turn interactions
# ---------------------------------------------------------------------------

@dataclass
class ConversationContext:
    """Tracks multi-turn state so the agent can ask follow-up questions."""
    last_command: str = ""
    last_result: Optional[CommandResult] = None
    pending_params: Dict[str, Any] = field(default_factory=dict)
    awaiting_confirmation: bool = False
    history: List[Dict[str, str]] = field(default_factory=list)

    def add_turn(self, role: str, text: str):
        self.history.append({"role": role, "text": text})
        if len(self.history) > 20:
            self.history = self.history[-20:]


# ---------------------------------------------------------------------------
# AgentExecutor
# ---------------------------------------------------------------------------

class AgentExecutor:
    """
    Natural-language command executor for AIOS.

    Takes free-form text (from voice or keyboard), matches it to a
    command handler, extracts parameters, executes, and returns a
    result with both display text and a TTS-friendly spoken response.
    """

    def __init__(self, llm=None):
        """
        Parameters
        ----------
        llm : optional
            An LLM adapter (LangChainLLMAdapter, etc.) for handling
            ambiguous queries. When None, the agent uses pattern
            matching only.
        """
        self.llm = llm
        self.ctx = ConversationContext()
        self.commands = COMMANDS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, text: str) -> CommandResult:
        """
        Parse a natural-language utterance, determine intent, extract
        parameters, and execute the matching command.
        """
        text = text.strip()
        if not text:
            return CommandResult(False, "", speak="I didn't catch that. Could you repeat?")

        self.ctx.add_turn("user", text)
        logger.info(f"Agent input: {text}")

        # Handle confirmation flow
        if self.ctx.awaiting_confirmation:
            return self._handle_confirmation(text)

        # Match intent
        command_key, params = self._match_intent(text)

        if command_key:
            return self._run_command(command_key, params, text)

        # Try LLM fallback for ambiguous input
        if self.llm:
            return self._llm_fallback(text)

        # Help or unrecognized
        help_text = self._suggest_help(text)
        is_help = any(w in text.lower() for w in ["what can", "help", "what do", "how do"])
        return CommandResult(
            is_help, "",
            speak=help_text,
        )

    def get_capabilities(self) -> List[str]:
        """Return a list of things the agent can do."""
        return [
            "List installed programs and applications",
            "Open a web browser or navigate to URLs",
            "Browse the file system and list directories",
            "Create documents and text files",
            "Take screenshots and screen captures",
            "Check network connections and internet status",
            "Scan for Bluetooth devices",
            "Download and install software packages",
            "Check software compatibility",
            "Open installed applications",
            "Show system status, CPU, memory, disk usage",
            "Display hardware specifications",
            "Search for files by name",
            "List and monitor running processes",
            "Execute shell commands",
            "Open the system file manager",
        ]

    def get_help_text(self) -> str:
        """Return a help string describing available commands."""
        lines = ["I can help you with:"]
        for cap in self.get_capabilities():
            lines.append(f"  - {cap}")
        lines.append("\nJust tell me what you'd like to do in plain language.")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Intent matching
    # ------------------------------------------------------------------

    def _match_intent(self, text: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Find the best-matching intent for the input text."""
        for intent in INTENTS:
            m = intent.pattern.search(text)
            if m:
                params = {}
                if intent.extract:
                    params = intent.extract(m, text)
                logger.info(f"Matched intent: {intent.command} (params={params})")
                return intent.command, params
        return None, {}

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def _run_command(self, command_key: str, params: Dict[str, Any], original_text: str) -> CommandResult:
        """Execute a command handler."""
        handler = self.commands.get(command_key)
        if not handler:
            return CommandResult(False, f"Unknown command: {command_key}",
                                speak="I don't know how to do that yet.")

        # Check if required params are missing
        if command_key == "download_software" and not params.get("package"):
            self.ctx.pending_params = {"command": command_key}
            return CommandResult(
                True, "What software would you like to install?",
                speak="What software would you like me to install?",
            )
        if command_key == "open_application" and not params.get("app"):
            self.ctx.pending_params = {"command": command_key}
            return CommandResult(
                True, "Which application should I open?",
                speak="Which application would you like me to open?",
            )

        try:
            result = handler(params)
            self.ctx.last_command = command_key
            self.ctx.last_result = result
            self.ctx.add_turn("agent", result.speak or result.message[:100])
            logger.info(f"Command {command_key}: success={result.success}")
            return result
        except Exception as e:
            logger.error(f"Command {command_key} failed: {e}", exc_info=True)
            return CommandResult(False, str(e), speak=f"Something went wrong: {e}")

    # ------------------------------------------------------------------
    # Confirmation / follow-up handling
    # ------------------------------------------------------------------

    def _handle_confirmation(self, text: str) -> CommandResult:
        lower = text.lower().strip()
        self.ctx.awaiting_confirmation = False

        if lower in ("yes", "y", "yeah", "yep", "sure", "ok", "confirm", "go ahead", "do it"):
            # Re-execute the pending command
            pending = self.ctx.pending_params
            if pending:
                cmd = pending.pop("command", "")
                return self._run_command(cmd, pending, text)
        elif lower in ("no", "n", "nope", "cancel", "nevermind", "stop"):
            self.ctx.pending_params = {}
            return CommandResult(True, "Cancelled.", speak="Okay, cancelled.")

        # Maybe they're answering a parameter question
        if self.ctx.pending_params:
            cmd = self.ctx.pending_params.get("command", "")
            if cmd == "download_software":
                self.ctx.pending_params["package"] = text
                return self._run_command(cmd, self.ctx.pending_params, text)
            elif cmd == "open_application":
                self.ctx.pending_params["app"] = text
                return self._run_command(cmd, self.ctx.pending_params, text)

        return CommandResult(False, "", speak="I didn't understand. Could you try again?")

    # ------------------------------------------------------------------
    # LLM fallback
    # ------------------------------------------------------------------

    def _llm_fallback(self, text: str) -> CommandResult:
        """Use the LLM adapter for queries that don't match patterns."""
        try:
            context = f"Available commands: {', '.join(self.commands.keys())}"
            response = self.llm.interpret(text, context)
            summary = response.get("summary", "")
            return CommandResult(
                True, summary,
                speak=summary[:200] if summary else "I'm not sure how to help with that.",
            )
        except Exception as e:
            logger.warning(f"LLM fallback failed: {e}")
            return CommandResult(False, "", speak=self._suggest_help(text))

    # ------------------------------------------------------------------
    # Help suggestions
    # ------------------------------------------------------------------

    def _suggest_help(self, text: str) -> str:
        lower = text.lower()
        suggestions = []

        if any(w in lower for w in ["what can", "help", "what do", "how"]):
            caps = self.get_capabilities()
            top = caps[:6]
            return "I can " + ", ".join(top[:3]) + f", and {len(caps) - 3} more things. Just ask!"

        # Guess what they might have meant
        if any(w in lower for w in ["file", "folder", "document"]):
            suggestions.append("Try: 'list files in home directory' or 'create a new document'")
        if any(w in lower for w in ["internet", "wifi", "connect"]):
            suggestions.append("Try: 'check network connections'")
        if any(w in lower for w in ["program", "app", "software"]):
            suggestions.append("Try: 'list installed programs' or 'open Safari'")

        if suggestions:
            return suggestions[0]
        return "I'm not sure what you mean. Try 'help' to see what I can do."
