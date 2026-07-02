"""
Intent Parser

Converts natural language commands into structured Intermediate Representation (IR)
This is the "translation layer" between the LLM and the kernel API
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger("MiniKernel.Intent")


class IntentType(Enum):
    """Types of user intents"""
    FILE_OPERATION = "file_operation"
    PROCESS_CONTROL = "process_control"
    SYSTEM_INFO = "system_info"
    PACKAGE_MANAGEMENT = "package_management"
    NETWORK_CONFIG = "network_config"
    SEARCH = "search"
    HELP = "help"
    UNKNOWN = "unknown"


class FileAction(Enum):
    """File operation actions"""
    FIND = "find"
    MOVE = "move"
    COPY = "copy"
    DELETE = "delete"
    CREATE = "create"
    RENAME = "rename"
    LIST = "list"
    OPEN = "open"


class ProcessAction(Enum):
    """Process control actions"""
    START = "start"
    STOP = "stop"
    KILL = "kill"
    LIST = "list"
    PRIORITY = "priority"
    STATUS = "status"


@dataclass
class IntentResult:
    """Structured intent representation (IR)"""
    intent_type: IntentType
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    raw_text: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "intent_type": self.intent_type.value,
            "action": self.action,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "raw_text": self.raw_text,
            "timestamp": self.timestamp.isoformat()
        }


class IntentParser:
    """
    Intent Parser - Natural Language → Intermediate Representation
    
    Parsing Strategy:
    1. Pattern matching for common commands (fast path)
    2. LLM-based parsing for complex queries (slow path)
    3. Context-aware resolution
    
    This implementation focuses on pattern matching with LLM fallback capability
    """
    
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self.llm = None  # Will be set if LLM is available
        
        # Compile regex patterns for fast matching
        self._patterns = self._compile_patterns()
        
        # Context for resolving pronouns, references
        self.context: Dict[str, Any] = {}
        
        logger.info(f"Intent Parser initialized (LLM={use_llm})")
    
    def parse(self, text: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        """
        Parse natural language text into structured intent
        
        Args:
            text: Natural language command
            context: Additional context for resolution
            
        Returns:
            IntentResult with parsed intent
        """
        text = text.strip().lower()
        
        # Update context
        if context:
            self.context.update(context)
        
        # Try pattern matching first (fast path)
        intent = self._pattern_match(text)
        if intent.confidence > 0.7:
            logger.debug(f"Pattern match: {intent.intent_type.value} ({intent.confidence:.2f})")
            return intent
        
        # Fall back to LLM if available and enabled
        if self.use_llm and self.llm:
            intent = self._llm_parse(text)
            if intent.confidence > 0.5:
                logger.debug(f"LLM parse: {intent.intent_type.value} ({intent.confidence:.2f})")
                return intent
        
        # Unknown intent
        logger.warning(f"Could not parse: {text}")
        return IntentResult(
            intent_type=IntentType.UNKNOWN,
            action="unknown",
            raw_text=text,
            confidence=0.0
        )
    
    def _pattern_match(self, text: str) -> IntentResult:
        """Pattern-based intent matching"""
        
        # Try each pattern category — system/process before file ops to avoid
        # "list processes" being captured by the generic file LIST pattern.
        for pattern_func in [
            self._match_system_info,
            self._match_process_control,
            self._match_package_management,
            self._match_file_operations,
            self._match_search,
        ]:
            result = pattern_func(text)
            if result:
                return result
        
        return IntentResult(
            intent_type=IntentType.UNKNOWN,
            action="unknown",
            raw_text=text,
            confidence=0.0
        )
    
    def _match_file_operations(self, text: str) -> Optional[IntentResult]:
        """Match file operation patterns"""
        
        # Find file — "find", "locate", "search", and time-based queries like
        # "what files did I edit/modify/change today"
        if match := re.search(
            r"find|locate|search for.*?(?:file|document)"
            r"|(?:what|which)\s+files?.*?(?:edit|modif|chang)"
            r"|files?\s+(?:i\s+)?(?:edit|modif|chang)",
            text,
        ):
            file_query = self._extract_file_query(text)
            time_filter = self._extract_time_filter(text)
            
            return IntentResult(
                intent_type=IntentType.FILE_OPERATION,
                action=FileAction.FIND.value,
                parameters={
                    "query": file_query,
                    "time_filter": time_filter,
                    "location": self._extract_location(text)
                },
                confidence=0.9,
                raw_text=text
            )
        
        # Move file
        if match := re.search(r"move|mv", text):
            return IntentResult(
                intent_type=IntentType.FILE_OPERATION,
                action=FileAction.MOVE.value,
                parameters={
                    "source": self._extract_file_query(text),
                    "destination": self._extract_destination(text)
                },
                confidence=0.85,
                raw_text=text
            )
        
        # Copy file
        if match := re.search(r"copy|cp|duplicate", text):
            return IntentResult(
                intent_type=IntentType.FILE_OPERATION,
                action=FileAction.COPY.value,
                parameters={
                    "source": self._extract_file_query(text),
                    "destination": self._extract_destination(text)
                },
                confidence=0.85,
                raw_text=text
            )
        
        # Delete file
        if match := re.search(r"delete|remove|rm|trash", text):
            return IntentResult(
                intent_type=IntentType.FILE_OPERATION,
                action=FileAction.DELETE.value,
                parameters={
                    "target": self._extract_file_query(text),
                    "confirm_required": True
                },
                confidence=0.9,
                raw_text=text
            )
        
        # List files
        if match := re.search(r"list|show.*?files|ls", text):
            return IntentResult(
                intent_type=IntentType.FILE_OPERATION,
                action=FileAction.LIST.value,
                parameters={
                    "path": self._extract_location(text) or ".",
                    "recursive": "recursive" in text or "all" in text
                },
                confidence=0.85,
                raw_text=text
            )
        
        return None
    
    def _match_process_control(self, text: str) -> Optional[IntentResult]:
        """Match process control patterns"""
        
        # Kill/stop process
        if match := re.search(r"kill|stop|terminate|close", text):
            return IntentResult(
                intent_type=IntentType.PROCESS_CONTROL,
                action=ProcessAction.STOP.value,
                parameters={
                    "process": self._extract_process_name(text),
                    "force": "force" in text or "kill" in text
                },
                confidence=0.9,
                raw_text=text
            )
        
        # Start process
        if match := re.search(r"start|launch|run|open", text):
            return IntentResult(
                intent_type=IntentType.PROCESS_CONTROL,
                action=ProcessAction.START.value,
                parameters={
                    "program": self._extract_process_name(text),
                    "args": []
                },
                confidence=0.85,
                raw_text=text
            )
        
        # List processes
        if match := re.search(r"list.*?processes?|show.*?(?:running|processes?)|ps\b|top\b", text):
            return IntentResult(
                intent_type=IntentType.PROCESS_CONTROL,
                action=ProcessAction.LIST.value,
                parameters={
                    "filter": self._extract_process_name(text) if "filter" in text else None
                },
                confidence=0.9,
                raw_text=text
            )
        
        # Change priority
        if match := re.search(r"prioritize|priority|nice", text):
            return IntentResult(
                intent_type=IntentType.PROCESS_CONTROL,
                action=ProcessAction.PRIORITY.value,
                parameters={
                    "process": self._extract_process_name(text),
                    "priority": self._extract_priority(text)
                },
                confidence=0.8,
                raw_text=text
            )
        
        return None
    
    def _match_system_info(self, text: str) -> Optional[IntentResult]:
        """Match system info queries"""
        
        if match := re.search(r"memory|ram|usage", text):
            return IntentResult(
                intent_type=IntentType.SYSTEM_INFO,
                action="memory_info",
                parameters={},
                confidence=0.9,
                raw_text=text
            )
        
        if match := re.search(r"disk|storage|space", text):
            return IntentResult(
                intent_type=IntentType.SYSTEM_INFO,
                action="disk_info",
                parameters={},
                confidence=0.9,
                raw_text=text
            )
        
        if match := re.search(r"cpu|processor|load", text):
            return IntentResult(
                intent_type=IntentType.SYSTEM_INFO,
                action="cpu_info",
                parameters={},
                confidence=0.9,
                raw_text=text
            )
        
        if match := re.search(r"status|health|uptime", text):
            return IntentResult(
                intent_type=IntentType.SYSTEM_INFO,
                action="system_status",
                parameters={},
                confidence=0.9,
                raw_text=text
            )

        if match := re.search(r"system\s+info|show\s+system|sysinfo|hardware\s+info", text):
            return IntentResult(
                intent_type=IntentType.SYSTEM_INFO,
                action="system_status",
                parameters={},
                confidence=0.9,
                raw_text=text
            )

        return None
    
    def _match_package_management(self, text: str) -> Optional[IntentResult]:
        """Match package management commands"""
        
        if match := re.search(r"install|download.*?(?:and install)", text):
            return IntentResult(
                intent_type=IntentType.PACKAGE_MANAGEMENT,
                action="install",
                parameters={
                    "package": self._extract_package_name(text)
                },
                confidence=0.9,
                raw_text=text
            )
        
        if match := re.search(r"uninstall|remove.*?package", text):
            return IntentResult(
                intent_type=IntentType.PACKAGE_MANAGEMENT,
                action="uninstall",
                parameters={
                    "package": self._extract_package_name(text)
                },
                confidence=0.9,
                raw_text=text
            )
        
        if match := re.search(r"update.*?(?:all|packages|software)", text):
            return IntentResult(
                intent_type=IntentType.PACKAGE_MANAGEMENT,
                action="update_all",
                parameters={},
                confidence=0.95,
                raw_text=text
            )
        
        return None
    
    def _match_search(self, text: str) -> Optional[IntentResult]:
        """Match search queries"""
        
        if match := re.search(r"search|look for|find", text):
            return IntentResult(
                intent_type=IntentType.SEARCH,
                action="search",
                parameters={
                    "query": self._extract_search_query(text)
                },
                confidence=0.7,
                raw_text=text
            )
        
        return None
    
    # Helper extraction methods
    
    def _extract_file_query(self, text: str) -> str:
        """Extract file/document reference from text"""
        # Quoted strings have highest priority
        if match := re.search(r'"([^"]+)"', text):
            return match.group(1)
        if match := re.search(r"'([^']+)'", text):
            return match.group(1)

        # Absolute or home-relative paths (e.g. /etc/passwd, ~/docs/file.txt)
        if match := re.search(r"([~/][^\s]+)", text):
            return match.group(1)

        # filename.ext pattern
        if match := re.search(r"(\w+\.\w+)", text):
            return match.group(1)

        # Extract after keywords
        for keyword in ["file", "document", "called", "named"]:
            if keyword in text:
                parts = text.split(keyword)
                if len(parts) > 1:
                    return parts[1].strip().split()[0]

        return ""
    
    def _extract_time_filter(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract time-based filter (e.g., 'yesterday', 'last week')"""
        
        if "yesterday" in text:
            return {"days_ago": 1}
        elif "today" in text:
            return {"days_ago": 0}
        elif match := re.search(r"last\s+(\d+)\s+days?", text):
            return {"days_ago": int(match.group(1))}
        elif "last week" in text:
            return {"days_ago": 7}
        elif "last month" in text:
            return {"days_ago": 30}
        
        return None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract file location/path"""
        # Look for folder names
        for keyword in ["in", "from", "at"]:
            if keyword in text:
                parts = text.split(keyword)
                if len(parts) > 1:
                    location = parts[-1].strip().split()[0]
                    if location:
                        return location
        
        return None
    
    def _extract_destination(self, text: str) -> str:
        """Extract destination path"""
        for keyword in ["to", "into", "destination"]:
            if keyword in text:
                parts = text.split(keyword)
                if len(parts) > 1:
                    return parts[-1].strip().split()[0]
        return ""
    
    def _extract_process_name(self, text: str) -> str:
        """Extract process/application name"""
        # Remove common words
        stop_words = {"the", "a", "an", "this", "that", "process", "application", "program"}
        words = text.split()
        
        for word in words:
            if word not in stop_words and len(word) > 2:
                return word
        
        return ""
    
    def _extract_priority(self, text: str) -> str:
        """Extract priority level"""
        if "high" in text or "urgent" in text:
            return "high"
        elif "low" in text:
            return "low"
        return "normal"
    
    def _extract_package_name(self, text: str) -> str:
        """Extract package name"""
        # Look for quoted strings or words after 'install'
        if match := re.search(r'"([^"]+)"', text):
            return match.group(1)
        
        for keyword in ["install", "package", "called"]:
            if keyword in text:
                parts = text.split(keyword)
                if len(parts) > 1:
                    return parts[1].strip().split()[0]
        
        return ""
    
    def _extract_search_query(self, text: str) -> str:
        """Extract search query"""
        for keyword in ["search for", "look for", "find"]:
            if keyword in text:
                parts = text.split(keyword)
                if len(parts) > 1:
                    return parts[1].strip()
        return text
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for reuse"""
        return {
            "file_find": re.compile(r"find|locate|search for.*?file"),
            "file_move": re.compile(r"move|mv"),
            "process_kill": re.compile(r"kill|stop|terminate"),
        }
    
    def _llm_parse(self, text: str) -> IntentResult:
        """Parse using LLM (fallback for complex queries)"""
        # Placeholder for LLM integration
        # Would call local LLM with structured prompt
        
        logger.debug("LLM parsing not yet implemented")
        return IntentResult(
            intent_type=IntentType.UNKNOWN,
            action="unknown",
            raw_text=text,
            confidence=0.0
        )
    
    def set_llm(self, llm: Any) -> None:
        """Set LLM instance for advanced parsing"""
        self.llm = llm
        self.use_llm = True
        logger.info("LLM backend enabled for intent parsing")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    parser = IntentParser()
    
    test_commands = [
        "find the file I downloaded yesterday",
        "move report.pdf to the work folder",
        "list all processes",
        "install vim",
        "show me memory usage",
        "kill chrome",
        "prioritize the compilation task"
    ]
    
    for cmd in test_commands:
        result = parser.parse(cmd)
        print(f"\n'{cmd}'")
        print(f"  → {result.intent_type.value}: {result.action}")
        print(f"  → params: {result.parameters}")
        print(f"  → confidence: {result.confidence:.2f}")
