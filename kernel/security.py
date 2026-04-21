"""
Embedded security for AI-OS
Defines agents, permissions, access control, and authentication policies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path


class AccessLevel(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    STANDARD = "standard"
    RESTRICTED = "restricted"
    GUEST = "guest"


class Permission(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    SHARE = "share"
    EXPORT = "export"
    ADMIN = "admin"
    MANAGE = "manage"


class ResourceType(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    PASSWORD_VAULT = "password_vault"
    BROWSER_HISTORY = "browser_history"
    AUDIO = "audio"
    NETWORK = "network"
    MODEL = "model"
    DATASET = "dataset"
    AGENT = "agent"
    SYSTEM = "system"


class AuthFactorType(Enum):
    KNOWLEDGE = "knowledge"
    POSSESSION = "possession"
    BIOMETRIC = "biometric"
    BEHAVIORAL = "behavioral"


class BiometricType(Enum):
    FINGERPRINT = "fingerprint"
    FACE = "face"
    VOICE = "voice"
    RETINA = "retina"
    IRIS = "iris"
    PALM = "palm"
    CUSTOM_PATTERN = "custom_pattern"


@dataclass
class AuthFactor:
    factor_type: AuthFactorType
    biometric_type: Optional[BiometricType] = None
    label: str = ""
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def is_valid(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        if self.verified_at is None:
            return False
        if self.expires_at and now > self.expires_at:
            return False
        return True


@dataclass
class AuthPolicy:
    required_factors: List[AuthFactorType] = field(default_factory=list)
    min_factors: int = 1
    require_recent_seconds: int = 0
    require_biometric: bool = False
    require_possession: bool = False

    def is_satisfied(self, factors: List[AuthFactor], now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        valid = [f for f in factors if f.is_valid(now)]
        if len(valid) < self.min_factors:
            return False
        present = {f.factor_type for f in valid}
        for req in self.required_factors:
            if req not in present:
                return False
        if self.require_biometric and AuthFactorType.BIOMETRIC not in present:
            return False
        if self.require_possession and AuthFactorType.POSSESSION not in present:
            return False
        if self.require_recent_seconds > 0:
            cutoff = now - timedelta(seconds=self.require_recent_seconds)
            if not any(f.verified_at and f.verified_at >= cutoff for f in valid):
                return False
        return True


@dataclass
class AgentIdentity:
    agent_id: str
    user_name: str
    key_fingerprint: str
    access_level: AccessLevel = AccessLevel.STANDARD
    groups: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    locked: bool = False


@dataclass
class AuthSession:
    agent_id: str
    factors: List[AuthFactor]
    authenticated: bool
    authenticated_at: Optional[datetime] = None
    reason: str = ""


@dataclass
class SecurityContext:
    agent_id: str
    access_level: AccessLevel
    groups: Set[str]
    authenticated_factors: List[AuthFactorType] = field(default_factory=list)
    authenticated_at: Optional[datetime] = None

    @property
    def auth_strength(self) -> int:
        return len(set(self.authenticated_factors))


@dataclass
class ResourceDescriptor:
    resource_type: ResourceType
    resource_id: str
    owner_agent_id: Optional[str] = None
    tags: Set[str] = field(default_factory=set)


@dataclass
class PolicyRule:
    resource_type: ResourceType
    action: Permission
    min_access_level: AccessLevel = AccessLevel.STANDARD
    required_groups: Set[str] = field(default_factory=set)
    require_factors: Set[AuthFactorType] = field(default_factory=set)
    require_all_factors: bool = True
    allow_owner_only: bool = False
    deny_if_locked: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "resource_type": self.resource_type.value,
            "action": self.action.value,
            "min_access_level": self.min_access_level.value,
            "required_groups": sorted(self.required_groups),
            "require_factors": [f.value for f in sorted(self.require_factors, key=lambda x: x.value)],
            "require_all_factors": self.require_all_factors,
            "allow_owner_only": self.allow_owner_only,
            "deny_if_locked": self.deny_if_locked,
            "description": self.description,
        }


@dataclass
class AuditEvent:
    timestamp: str
    agent_id: str
    action: str
    resource_type: str
    resource_id: str
    allowed: bool
    reason: str
    auth_strength: int
    access_level: str


class AuditLogger:
    def __init__(self, log_path: str = "/aios/logs/security_audit.jsonl"):
        self.log_path = Path(log_path)

    def log(self, event: AuditEvent) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(event.__dict__)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(payload + "\n")
        except Exception as e:
            print(f"[SECURITY] Audit log failed: {e}")


class AgentRegistry:
    def __init__(self, registry_path: str = "/aios/etc/agent_registry.json"):
        self._agents: Dict[str, AgentIdentity] = {}
        self._auth_policies: Dict[str, AuthPolicy] = {}
        self._registry_path = Path(registry_path)

    def register_agent(self, identity: AgentIdentity, auth_policy: Optional[AuthPolicy] = None) -> None:
        self._agents[identity.agent_id] = identity
        if auth_policy:
            self._auth_policies[identity.agent_id] = auth_policy
        self.save()

    def get_agent(self, agent_id: str) -> Optional[AgentIdentity]:
        return self._agents.get(agent_id)

    def lock_agent(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.locked = True
        self.save()
        return True

    def unlock_agent(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.locked = False
        self.save()
        return True

    def set_access_level(self, agent_id: str, level: AccessLevel) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.access_level = level
        self.save()
        return True

    def add_group(self, agent_id: str, group: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.groups.add(group)
        self.save()
        return True

    def remove_group(self, agent_id: str, group: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        if group in agent.groups:
            agent.groups.remove(group)
        self.save()
        return True

    def set_auth_policy(self, agent_id: str, policy: AuthPolicy) -> bool:
        if agent_id not in self._agents:
            return False
        self._auth_policies[agent_id] = policy
        self.save()
        return True

    def get_auth_policy(self, agent_id: str) -> Optional[AuthPolicy]:
        return self._auth_policies.get(agent_id)

    def load(self, path: Optional[str] = None) -> bool:
        target = Path(path) if path else self._registry_path
        try:
            if not target.exists():
                return False
            data = json.loads(target.read_text())
            agents = data.get("agents", {})
            policies = data.get("policies", {})
            self._agents = {
                agent_id: AgentIdentity(
                    agent_id=agent_id,
                    user_name=payload.get("user_name", agent_id),
                    key_fingerprint=payload.get("key_fingerprint", ""),
                    access_level=AccessLevel(payload.get("access_level", AccessLevel.STANDARD.value)),
                    groups=set(payload.get("groups", [])),
                    created_at=datetime.fromisoformat(payload.get("created_at")) if payload.get("created_at") else datetime.utcnow(),
                    locked=bool(payload.get("locked", False)),
                )
                for agent_id, payload in agents.items()
            }
            self._auth_policies = {
                agent_id: AuthPolicy(
                    required_factors=[AuthFactorType(f) for f in payload.get("required_factors", [])],
                    min_factors=int(payload.get("min_factors", 1)),
                    require_recent_seconds=int(payload.get("require_recent_seconds", 0)),
                    require_biometric=bool(payload.get("require_biometric", False)),
                    require_possession=bool(payload.get("require_possession", False)),
                )
                for agent_id, payload in policies.items()
            }
            return True
        except Exception as e:
            print(f"[SECURITY] Failed to load agent registry {target}: {e}")
            return False

    def save(self, path: Optional[str] = None) -> bool:
        target = Path(path) if path else self._registry_path
        try:
            payload = {
                "version": 1,
                "agents": {
                    agent_id: {
                        "user_name": identity.user_name,
                        "key_fingerprint": identity.key_fingerprint,
                        "access_level": identity.access_level.value,
                        "groups": sorted(identity.groups),
                        "created_at": identity.created_at.isoformat(),
                        "locked": identity.locked,
                    }
                    for agent_id, identity in self._agents.items()
                },
                "policies": {
                    agent_id: {
                        "required_factors": [f.value for f in policy.required_factors],
                        "min_factors": policy.min_factors,
                        "require_recent_seconds": policy.require_recent_seconds,
                        "require_biometric": policy.require_biometric,
                        "require_possession": policy.require_possession,
                    }
                    for agent_id, policy in self._auth_policies.items()
                },
            }
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2))
            return True
        except Exception as e:
            print(f"[SECURITY] Failed to save agent registry {target}: {e}")
            return False


class AuthManager:
    def evaluate_policy(self, policy: AuthPolicy, factors: List[AuthFactor]) -> bool:
        return policy.is_satisfied(factors)


class AuthService:
    def __init__(self, registry: AgentRegistry, auth_manager: Optional[AuthManager] = None):
        self.registry = registry
        self.auth_manager = auth_manager or AuthManager()

    def register_agent(self, identity: AgentIdentity, auth_policy: Optional[AuthPolicy] = None) -> None:
        if auth_policy is None:
            auth_policy = AuthPolicy(
                min_factors=1,
                required_factors=[AuthFactorType.KNOWLEDGE],
                require_recent_seconds=300,
            )
        self.registry.register_agent(identity, auth_policy)

    def login(self, agent_id: str, factors: List[AuthFactor]) -> AuthSession:
        policy = self.registry.get_auth_policy(agent_id)
        if policy is None:
            policy = AuthPolicy(min_factors=1)
        ok = self.auth_manager.evaluate_policy(policy, factors)
        return AuthSession(
            agent_id=agent_id,
            factors=factors,
            authenticated=ok,
            authenticated_at=datetime.utcnow() if ok else None,
            reason="ok" if ok else "policy_unsatisfied",
        )


class AccessController:
    def __init__(self, rules: Optional[List[PolicyRule]] = None):
        self.rules = rules or default_policy()

    def is_allowed(
        self,
        context: SecurityContext,
        resource: ResourceDescriptor,
        action: Permission,
        owner_agent_id: Optional[str] = None,
        agent_locked: bool = False,
    ) -> Tuple[bool, str]:
        if agent_locked:
            return False, "agent_locked"
        applicable = [r for r in self.rules if r.resource_type == resource.resource_type and r.action == action]
        if not applicable:
            return False, "no_policy_rule"

        for rule in applicable:
            if rule.deny_if_locked and agent_locked:
                continue
            if rule.allow_owner_only:
                if owner_agent_id and context.agent_id != owner_agent_id:
                    continue
            if context.access_level.value not in _access_level_allows(rule.min_access_level):
                continue
            if rule.required_groups and not rule.required_groups.issubset(context.groups):
                continue
            if rule.require_factors:
                present = set(context.authenticated_factors)
                if rule.require_all_factors and not rule.require_factors.issubset(present):
                    continue
                if not rule.require_all_factors and not (rule.require_factors & present):
                    continue
            return True, "allowed"

        return False, "policy_denied"


class SecurityManager:
    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        access_controller: Optional[AccessController] = None,
        policy_registry: Optional["PolicyRegistry"] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.registry = registry or AgentRegistry()
        self.registry.load()
        self.policy_registry = policy_registry or PolicyRegistry()
        self.access_controller = access_controller or AccessController(self.policy_registry.rules())
        self.audit_logger = audit_logger or AuditLogger()
        self.auth_service = AuthService(self.registry)

    def authorize(
        self,
        context: SecurityContext,
        resource: ResourceDescriptor,
        action: Permission,
    ) -> Tuple[bool, str]:
        identity = self.registry.get_agent(context.agent_id)
        agent_locked = identity.locked if identity else False
        allowed, reason = self.access_controller.is_allowed(
            context=context,
            resource=resource,
            action=action,
            owner_agent_id=resource.owner_agent_id,
            agent_locked=agent_locked,
        )
        self.audit_logger.log(
            AuditEvent(
                timestamp=datetime.utcnow().isoformat() + "Z",
                agent_id=context.agent_id,
                action=action.value,
                resource_type=resource.resource_type.value,
                resource_id=resource.resource_id,
                allowed=allowed,
                reason=reason,
                auth_strength=context.auth_strength,
                access_level=context.access_level.value,
            )
        )
        return allowed, reason

    def login(self, agent_id: str, factors: List[AuthFactor]) -> AuthSession:
        return self.auth_service.login(agent_id, factors)

    def register_agent(self, identity: AgentIdentity, auth_policy: Optional[AuthPolicy] = None) -> None:
        self.auth_service.register_agent(identity, auth_policy)

    def load_policy(self, path: Optional[str] = None) -> bool:
        loaded = self.policy_registry.load(path)
        self.access_controller.rules = self.policy_registry.rules()
        return loaded


def _access_level_allows(min_level: AccessLevel) -> Set[str]:
    order = [AccessLevel.OWNER, AccessLevel.ADMIN, AccessLevel.STANDARD, AccessLevel.RESTRICTED, AccessLevel.GUEST]
    if min_level not in order:
        return set()
    idx = order.index(min_level)
    return {lvl.value for lvl in order[: idx + 1]}


def default_policy() -> List[PolicyRule]:
    return [
        PolicyRule(
            resource_type=ResourceType.DIRECTORY,
            action=Permission.READ,
            min_access_level=AccessLevel.GUEST,
        ),
        PolicyRule(
            resource_type=ResourceType.FILE,
            action=Permission.READ,
            min_access_level=AccessLevel.RESTRICTED,
        ),
        PolicyRule(
            resource_type=ResourceType.DIRECTORY,
            action=Permission.WRITE,
            min_access_level=AccessLevel.STANDARD,
            require_factors={AuthFactorType.KNOWLEDGE},
            require_all_factors=False,
        ),
        PolicyRule(
            resource_type=ResourceType.FILE,
            action=Permission.WRITE,
            min_access_level=AccessLevel.STANDARD,
            require_factors={AuthFactorType.KNOWLEDGE},
            require_all_factors=False,
        ),
        PolicyRule(
            resource_type=ResourceType.FILE,
            action=Permission.DELETE,
            min_access_level=AccessLevel.ADMIN,
            require_factors={AuthFactorType.KNOWLEDGE, AuthFactorType.POSSESSION},
        ),
        PolicyRule(
            resource_type=ResourceType.PASSWORD_VAULT,
            action=Permission.READ,
            min_access_level=AccessLevel.OWNER,
            allow_owner_only=True,
            require_factors={AuthFactorType.KNOWLEDGE, AuthFactorType.BIOMETRIC},
        ),
        PolicyRule(
            resource_type=ResourceType.BROWSER_HISTORY,
            action=Permission.READ,
            min_access_level=AccessLevel.OWNER,
            allow_owner_only=True,
            require_factors={AuthFactorType.KNOWLEDGE},
            require_all_factors=False,
        ),
        PolicyRule(
            resource_type=ResourceType.AGENT,
            action=Permission.MANAGE,
            min_access_level=AccessLevel.OWNER,
            allow_owner_only=True,
            require_factors={AuthFactorType.KNOWLEDGE, AuthFactorType.BIOMETRIC, AuthFactorType.POSSESSION},
        ),
        PolicyRule(
            resource_type=ResourceType.AUDIO,
            action=Permission.READ,
            min_access_level=AccessLevel.STANDARD,
            required_groups={"voice"},
            require_factors={AuthFactorType.KNOWLEDGE},
            require_all_factors=False,
            description="Audio capture requires voice group",
        ),
        PolicyRule(
            resource_type=ResourceType.AUDIO,
            action=Permission.WRITE,
            min_access_level=AccessLevel.STANDARD,
            required_groups={"voice"},
            require_factors={AuthFactorType.KNOWLEDGE},
            require_all_factors=False,
            description="Audio playback requires voice group",
        ),
    ]


def policy_2fa(
    require_biometric: bool = False,
    require_possession: bool = False,
    require_recent_seconds: int = 300,
) -> AuthPolicy:
    required = [AuthFactorType.KNOWLEDGE]
    if require_biometric:
        required.append(AuthFactorType.BIOMETRIC)
    if require_possession:
        required.append(AuthFactorType.POSSESSION)
    return AuthPolicy(
        required_factors=required,
        min_factors=max(2, len(required)),
        require_recent_seconds=require_recent_seconds,
        require_biometric=require_biometric,
        require_possession=require_possession,
    )


def policy_3fa(require_recent_seconds: int = 300) -> AuthPolicy:
    return AuthPolicy(
        required_factors=[
            AuthFactorType.KNOWLEDGE,
            AuthFactorType.POSSESSION,
            AuthFactorType.BIOMETRIC,
        ],
        min_factors=3,
        require_recent_seconds=require_recent_seconds,
        require_biometric=True,
        require_possession=True,
    )


class PolicyRegistry:
    def __init__(self, policy_path: Optional[str] = None):
        self._policy_path = Path(policy_path) if policy_path else None
        self._rules: List[PolicyRule] = default_policy()

    def load(self, path: Optional[str] = None) -> bool:
        target = Path(path) if path else self._policy_path
        if not target:
            return False
        try:
            data = json.loads(target.read_text())
            rules_data = data.get("rules", [])
            self._rules = [self._parse_rule(r) for r in rules_data]
            self._rules = [r for r in self._rules if r is not None]
            if not self._rules:
                self._rules = default_policy()
            return True
        except Exception as e:
            print(f"[SECURITY] Failed to load policy file {target}: {e}")
            self._rules = default_policy()
            return False

    def save(self, path: Optional[str] = None) -> bool:
        target = Path(path) if path else self._policy_path
        if not target:
            return False
        try:
            payload = {
                "version": 1,
                "rules": [r.to_dict() for r in self._rules],
            }
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2))
            return True
        except Exception as e:
            print(f"[SECURITY] Failed to save policy file {target}: {e}")
            return False

    def rules(self) -> List[PolicyRule]:
        return list(self._rules)

    def set_rules(self, rules: List[PolicyRule]) -> None:
        self._rules = list(rules)

    def _parse_rule(self, raw: Dict[str, object]) -> Optional[PolicyRule]:
        try:
            resource_type = ResourceType(str(raw.get("resource_type", "")))
            action = Permission(str(raw.get("action", "")))
            min_access_level = AccessLevel(str(raw.get("min_access_level", AccessLevel.STANDARD.value)))
            required_groups = set(raw.get("required_groups", []))
            require_factors = {
                AuthFactorType(str(f)) for f in raw.get("require_factors", [])
            }
            return PolicyRule(
                resource_type=resource_type,
                action=action,
                min_access_level=min_access_level,
                required_groups=required_groups,
                require_factors=require_factors,
                require_all_factors=bool(raw.get("require_all_factors", True)),
                allow_owner_only=bool(raw.get("allow_owner_only", False)),
                deny_if_locked=bool(raw.get("deny_if_locked", True)),
                description=str(raw.get("description", "")),
            )
        except Exception as e:
            print(f"[SECURITY] Invalid policy rule skipped: {e}")
            return None
