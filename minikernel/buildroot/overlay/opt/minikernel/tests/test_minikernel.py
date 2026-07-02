#!/usr/bin/env python3
"""
MiniKernel Integration Tests

Tests the complete system integration
"""

import sys
import pytest
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from minikernel.core.microkernel import MicroKernel, ServicePriority
from minikernel.core.ipc_manager import IPCManager
from minikernel.core.memory_manager import MemoryManager
from minikernel.intent.intent_parser import IntentParser
from minikernel.intent.command_validator import CommandValidator
from minikernel.security.capability_manager import CapabilityManager, Capability


class TestMicrokernel:
    """Test microkernel functionality"""
    
    def test_kernel_creation(self):
        """Test kernel can be created"""
        kernel = MicroKernel()
        assert kernel is not None
        assert kernel.state.value == "uninitialized"
    
    def test_service_registration(self):
        """Test service registration"""
        kernel = MicroKernel()
        ipc = IPCManager()
        
        kernel.register_service("ipc", ipc, ServicePriority.CRITICAL)
        assert "ipc" in kernel.services
    
    def test_kernel_boot(self):
        """Test kernel boot sequence"""
        kernel = MicroKernel()
        
        # Register critical services
        ipc = IPCManager()
        memory = MemoryManager(total_memory_mb=1024)
        
        kernel.register_service("ipc", ipc, ServicePriority.CRITICAL)
        kernel.register_service("memory", memory, ServicePriority.CRITICAL)
        
        # Boot
        assert kernel.boot() == True
        assert kernel.state.value == "running"
        
        # Shutdown
        kernel.shutdown()
        assert kernel.state.value == "halted"


class TestIntentParser:
    """Test intent parsing"""
    
    def test_file_find(self):
        """Test file find intent"""
        parser = IntentParser()
        intent = parser.parse("find the file I downloaded yesterday")
        
        assert intent.intent_type.value == "file_operation"
        assert intent.action == "find"
        assert intent.confidence > 0.7
    
    def test_process_kill(self):
        """Test process kill intent"""
        parser = IntentParser()
        intent = parser.parse("kill chrome")
        
        assert intent.intent_type.value == "process_control"
        assert intent.action == "stop"
        assert "chrome" in str(intent.parameters)
    
    def test_package_install(self):
        """Test package install intent"""
        parser = IntentParser()
        intent = parser.parse("install vim")
        
        assert intent.intent_type.value == "package_management"
        assert intent.action == "install"
        assert "vim" in str(intent.parameters)


class TestCommandValidator:
    """Test command validation"""
    
    def test_safe_command(self):
        """Test safe command validation"""
        parser = IntentParser()
        validator = CommandValidator()
        
        intent = parser.parse("list all files")
        validation = validator.validate(intent)
        
        assert validation.is_valid == True
        assert validation.risk_level.value == "safe"
    
    def test_dangerous_command(self):
        """Test dangerous command blocking"""
        parser = IntentParser()
        validator = CommandValidator()
        
        intent = parser.parse("delete /etc/passwd")
        validation = validator.validate(intent)
        
        assert validation.is_valid == False
        assert len(validation.errors) > 0
    
    def test_confirmation_required(self):
        """Test confirmation requirement"""
        parser = IntentParser()
        validator = CommandValidator()
        
        intent = parser.parse("delete myfile.txt")
        validation = validator.validate(intent)
        
        assert validation.is_valid == True
        assert validation.requires_confirmation == True


class TestCapabilityManager:
    """Test capability-based security"""
    
    def test_agent_registration(self):
        """Test agent registration"""
        cap_mgr = CapabilityManager()
        agent = cap_mgr.register_agent("test_agent", "Test Agent")
        
        assert agent is not None
        assert agent.agent_id == "test_agent"
    
    def test_capability_grant(self):
        """Test capability granting"""
        cap_mgr = CapabilityManager()
        cap_mgr.register_agent("test_agent", "Test Agent")
        
        result = cap_mgr.grant_capability(
            "test_agent",
            Capability.FILE_READ,
            scope="/home/user/*"
        )
        
        assert result == True
    
    def test_capability_check(self):
        """Test capability checking"""
        cap_mgr = CapabilityManager()
        cap_mgr.register_agent("test_agent", "Test Agent")
        cap_mgr.grant_capability("test_agent", Capability.FILE_READ, scope="/home/user/*")
        
        # Should pass
        can_read = cap_mgr.check_capability(
            "test_agent",
            Capability.FILE_READ,
            "/home/user/document.txt"
        )
        assert can_read == True
        
        # Should fail
        can_delete = cap_mgr.check_capability(
            "test_agent",
            Capability.FILE_DELETE,
            "/home/user/document.txt"
        )
        assert can_delete == False


class TestIPCManager:
    """Test IPC functionality"""
    
    def test_process_registration(self):
        """Test process registration"""
        ipc = IPCManager()
        ipc.initialize()
        
        result = ipc.register_process("proc_1")
        assert result == True
        
        ipc.shutdown()
    
    def test_message_passing(self):
        """Test message passing"""
        ipc = IPCManager()
        ipc.initialize()
        
        ipc.register_process("proc_1")
        ipc.register_process("proc_2")
        
        # Send message
        msg_id = ipc.ipc_send("proc_1", "proc_2", {"test": "data"})
        assert msg_id is not None
        
        # Receive message
        msg = ipc.ipc_receive("proc_2", timeout=1.0)
        assert msg is not None
        assert msg.payload["test"] == "data"
        
        ipc.shutdown()


class TestMemoryManager:
    """Test memory management"""
    
    def test_memory_allocation(self):
        """Test memory allocation"""
        mem = MemoryManager(total_memory_mb=1024)
        mem.initialize()
        
        block_id = mem.mem_allocate("test_process", 10 * 1024 * 1024)
        assert block_id is not None
        
        mem.shutdown()
    
    def test_memory_limits(self):
        """Test memory limits"""
        mem = MemoryManager(total_memory_mb=100)
        mem.initialize()
        
        # Set process limit
        mem.set_process_limit("test_process", 50)
        
        # Allocate within limit
        block1 = mem.mem_allocate("test_process", 30 * 1024 * 1024)
        assert block1 is not None
        
        # Try to exceed limit
        block2 = mem.mem_allocate("test_process", 30 * 1024 * 1024)
        assert block2 is None  # Should fail
        
        mem.shutdown()


def test_full_integration():
    """Test full system integration"""
    # Create components
    kernel = MicroKernel()
    ipc = IPCManager()
    memory = MemoryManager(total_memory_mb=1024)
    
    # Register services
    kernel.register_service("ipc", ipc, ServicePriority.CRITICAL)
    kernel.register_service("memory", memory, ServicePriority.CRITICAL)
    
    # Boot
    assert kernel.boot() == True
    
    # Test IPC through kernel
    ipc_service = kernel.get_service("ipc")
    assert ipc_service is not None
    
    # Get stats
    stats = kernel.get_stats()
    assert stats["state"] == "running"
    assert stats["services"] >= 2
    
    # Shutdown
    kernel.shutdown()
    assert kernel.state.value == "halted"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
