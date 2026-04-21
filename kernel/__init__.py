"""
AI-OS Kernel Package
Core operating system components
"""

from kernel.hardware_detection import HardwareDetector, SystemSpecs
from kernel.boot import BootLoader, BootConfig
from kernel.filesystem import FileSystemManager
from kernel.network import NetworkManager
from kernel.system_monitor import SystemMonitor
from kernel.container_runtime import ContainerManager, ContainerConfig, GPUConfig
from kernel.model_manager import ModelManager, ModelMetadata, ModelFramework, ModelType
from kernel.scheduler import JobScheduler, Job, ResourcePool, ResourceRequirements
from kernel.resource_manager import (
    ResourceManager,
    GPUScheduler,
    ResourceQuota,
    TenantUsage,
    TenantRegistry,
    QuotaManager,
    PowerPolicy,
)
from kernel.distributed_training import DistributedCoordinator, DistributedConfig
from kernel.voice_assistant import (
    VoiceOnboardingAssistant,
    VoiceStep,
    DEFAULT_SCRIPT,
    run_voice_onboarding,
    voice_command_repl,
    parse_command,
    PiperWebSocketBackend,
)
from kernel.security import (
    AccessLevel,
    Permission,
    ResourceType,
    AuthFactorType,
    BiometricType,
    AuthFactor,
    AuthPolicy,
    AgentIdentity,
    AuthSession,
    SecurityContext,
    ResourceDescriptor,
    PolicyRule,
    PolicyRegistry,
    AuditEvent,
    AuditLogger,
    AuthService,
    policy_2fa,
    policy_3fa,
    AgentRegistry,
    AuthManager,
    AccessController,
    SecurityManager,
)

__all__ = [
    'HardwareDetector',
    'SystemSpecs',
    'BootLoader',
    'BootConfig',
    'FileSystemManager',
    'NetworkManager',
    'SystemMonitor',
    'ContainerManager',
    'ContainerConfig',
    'GPUConfig',
    'ModelManager',
    'ModelMetadata',
    'ModelFramework',
    'ModelType',
    'JobScheduler',
    'Job',
    'ResourcePool',
    'ResourceRequirements',
    'ResourceManager',
    'GPUScheduler',
    'ResourceQuota',
    'TenantUsage',
    'TenantRegistry',
    'QuotaManager',
    'PowerPolicy',
    'DistributedCoordinator',
    'DistributedConfig',
    'VoiceOnboardingAssistant',
    'VoiceStep',
    'DEFAULT_SCRIPT',
    'run_voice_onboarding',
    'voice_command_repl',
    'parse_command',
    'PiperWebSocketBackend',
    'AccessLevel',
    'Permission',
    'ResourceType',
    'AuthFactorType',
    'BiometricType',
    'AuthFactor',
    'AuthPolicy',
    'AgentIdentity',
    'AuthSession',
    'SecurityContext',
    'ResourceDescriptor',
    'PolicyRule',
    'PolicyRegistry',
    'AuditEvent',
    'AuditLogger',
    'AuthService',
    'policy_2fa',
    'policy_3fa',
    'AgentRegistry',
    'AuthManager',
    'AccessController',
    'SecurityManager',
]
