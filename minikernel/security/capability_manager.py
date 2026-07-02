"""
Capability Manager

Implements capability-based security model
AI agents have scoped permissions, not root access
"""

import logging
from typing import Dict, Set, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger("MiniKernel.Capabilities")


class Capability(Enum):
    """System capabilities"""
    # File operations
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    FILE_DELETE = "file:delete"
    FILE_EXECUTE = "file:execute"
    
    # Process operations
    PROCESS_START = "process:start"
    PROCESS_STOP = "process:stop"
    PROCESS_LIST = "process:list"
    
    # System operations
    SYSTEM_INFO = "system:info"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_SHUTDOWN = "system:shutdown"
    
    # Package operations
    PACKAGE_INSTALL = "package:install"
    PACKAGE_UNINSTALL = "package:uninstall"
    PACKAGE_UPDATE = "package:update"
    
    # Network operations
    NETWORK_CONFIG = "network:config"
    NETWORK_LISTEN = "network:listen"
    NETWORK_CONNECT = "network:connect"


@dataclass
class CapabilityGrant:
    """Represents a granted capability"""
    capability: Capability
    scope: str  # e.g., "/home/user/*" for file operations
    granted_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    revocable: bool = True
    
    def is_valid(self) -> bool:
        """Check if grant is still valid"""
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True
    
    def matches_scope(self, resource: str) -> bool:
        """Check if resource matches this grant's scope"""
        # Simple wildcard matching
        if self.scope == "*":
            return True
        
        if "*" in self.scope:
            prefix = self.scope.replace("*", "")
            return resource.startswith(prefix)
        
        return resource == self.scope


@dataclass
class Agent:
    """Represents an AI agent with capabilities"""
    agent_id: str
    name: str
    capabilities: List[CapabilityGrant] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    enabled: bool = True


class CapabilityManager:
    """
    Capability-Based Security Manager
    
    Instead of traditional user/root model:
    - Agents have specific capabilities
    - Capabilities are scoped to resources
    - Temporary grants with expiration
    - Fine-grained access control
    
    Example:
    - Agent can READ files in /home/user/documents/*
    - Agent can STOP processes named "chrome"
    - Agent can INSTALL packages (with confirmation)
    """
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        
        # Audit log
        self.audit_log: List[Dict] = []
        
        logger.info("Capability Manager initialized")
    
    def register_agent(self, agent_id: str, name: str) -> Agent:
        """Register a new agent"""
        if agent_id in self.agents:
            logger.warning(f"Agent already registered: {agent_id}")
            return self.agents[agent_id]
        
        agent = Agent(agent_id=agent_id, name=name)
        self.agents[agent_id] = agent
        
        logger.info(f"Registered agent: {name} ({agent_id})")
        return agent
    
    def grant_capability(
        self,
        agent_id: str,
        capability: Capability,
        scope: str = "*",
        duration_minutes: Optional[int] = None
    ) -> bool:
        """
        Grant a capability to an agent
        
        Args:
            agent_id: Agent identifier
            capability: Capability to grant
            scope: Resource scope (e.g., "/home/user/*")
            duration_minutes: Grant duration (None = permanent)
            
        Returns:
            True if granted successfully
        """
        if agent_id not in self.agents:
            logger.error(f"Agent not found: {agent_id}")
            return False
        
        agent = self.agents[agent_id]
        
        # Calculate expiration
        expires_at = None
        if duration_minutes:
            expires_at = datetime.now() + timedelta(minutes=duration_minutes)
        
        # Create grant
        grant = CapabilityGrant(
            capability=capability,
            scope=scope,
            expires_at=expires_at
        )
        
        agent.capabilities.append(grant)
        
        # Audit
        self._audit("grant_capability", {
            "agent_id": agent_id,
            "capability": capability.value,
            "scope": scope,
            "duration_minutes": duration_minutes
        })
        
        logger.info(f"Granted {capability.value} to {agent_id} (scope={scope})")
        return True
    
    def revoke_capability(
        self,
        agent_id: str,
        capability: Capability,
        scope: Optional[str] = None
    ) -> bool:
        """
        Revoke a capability from an agent
        
        Args:
            agent_id: Agent identifier
            capability: Capability to revoke
            scope: Specific scope to revoke (None = all)
            
        Returns:
            True if revoked successfully
        """
        if agent_id not in self.agents:
            logger.error(f"Agent not found: {agent_id}")
            return False
        
        agent = self.agents[agent_id]
        
        # Remove matching grants
        original_count = len(agent.capabilities)
        agent.capabilities = [
            g for g in agent.capabilities
            if not (g.capability == capability and 
                   (scope is None or g.scope == scope) and
                   g.revocable)
        ]
        
        removed = original_count - len(agent.capabilities)
        
        # Audit
        self._audit("revoke_capability", {
            "agent_id": agent_id,
            "capability": capability.value,
            "scope": scope,
            "removed": removed
        })
        
        logger.info(f"Revoked {capability.value} from {agent_id} ({removed} grants)")
        return removed > 0
    
    def check_capability(
        self,
        agent_id: str,
        capability: Capability,
        resource: str = ""
    ) -> bool:
        """
        Check if agent has a capability for a resource
        
        Args:
            agent_id: Agent identifier
            capability: Required capability
            resource: Resource being accessed
            
        Returns:
            True if agent has capability
        """
        if agent_id not in self.agents:
            logger.warning(f"Unknown agent: {agent_id}")
            return False
        
        agent = self.agents[agent_id]
        
        if not agent.enabled:
            logger.warning(f"Agent disabled: {agent_id}")
            return False
        
        # Check grants
        for grant in agent.capabilities:
            if not grant.is_valid():
                continue
            
            if grant.capability == capability:
                if grant.matches_scope(resource):
                    logger.debug(f"Capability check passed: {agent_id} → {capability.value}")
                    return True
        
        logger.warning(f"Capability check failed: {agent_id} → {capability.value} on {resource}")
        return False
    
    def get_agent_capabilities(self, agent_id: str) -> List[CapabilityGrant]:
        """Get all capabilities for an agent"""
        if agent_id not in self.agents:
            return []
        
        agent = self.agents[agent_id]
        return [g for g in agent.capabilities if g.is_valid()]
    
    def cleanup_expired(self) -> int:
        """Remove expired grants"""
        count = 0
        
        for agent in self.agents.values():
            original_count = len(agent.capabilities)
            agent.capabilities = [g for g in agent.capabilities if g.is_valid()]
            count += original_count - len(agent.capabilities)
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired grants")
        
        return count
    
    def disable_agent(self, agent_id: str) -> bool:
        """Disable an agent"""
        if agent_id in self.agents:
            self.agents[agent_id].enabled = False
            self._audit("disable_agent", {"agent_id": agent_id})
            logger.info(f"Disabled agent: {agent_id}")
            return True
        return False
    
    def enable_agent(self, agent_id: str) -> bool:
        """Enable an agent"""
        if agent_id in self.agents:
            self.agents[agent_id].enabled = True
            self._audit("enable_agent", {"agent_id": agent_id})
            logger.info(f"Enabled agent: {agent_id}")
            return True
        return False
    
    def _audit(self, action: str, details: Dict) -> None:
        """Log audit event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            **details
        }
        self.audit_log.append(event)
        
        # Keep only last 1000 events
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get recent audit events"""
        return self.audit_log[-limit:]


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    cap_mgr = CapabilityManager()
    
    # Register an agent
    agent = cap_mgr.register_agent("ai_assistant_1", "AI Assistant")
    
    # Grant capabilities
    cap_mgr.grant_capability(
        "ai_assistant_1",
        Capability.FILE_READ,
        scope="/home/user/*"
    )
    
    cap_mgr.grant_capability(
        "ai_assistant_1",
        Capability.PROCESS_LIST,
        scope="*"
    )
    
    # Check capabilities
    can_read = cap_mgr.check_capability(
        "ai_assistant_1",
        Capability.FILE_READ,
        "/home/user/document.txt"
    )
    print(f"Can read file: {can_read}")
    
    can_delete = cap_mgr.check_capability(
        "ai_assistant_1",
        Capability.FILE_DELETE,
        "/home/user/document.txt"
    )
    print(f"Can delete file: {can_delete}")
    
    # Show audit log
    print("\nAudit log:")
    for event in cap_mgr.get_audit_log():
        print(f"  {event}")
