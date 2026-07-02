"""
System Call Interface for MiniKernel

Provides Python interface to real Linux syscalls via C bridge.
This enables MiniKernel to execute actual system calls instead of simulating them.
"""

import os
import logging
from enum import IntEnum
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger("MiniKernel.Syscalls")

# Try to import native bridge, fall back to ctypes
try:
    from minikernel.core import syscall_bridge
    HAS_NATIVE_BRIDGE = True
    logger.info("Using native syscall bridge (C extension)")
except ImportError:
    import ctypes
    HAS_NATIVE_BRIDGE = False
    logger.warning("Native bridge not available, using ctypes fallback")


# Linux syscall numbers (x86_64)
class Syscall(IntEnum):
    """Linux syscall numbers"""
    READ = 0
    WRITE = 1
    OPEN = 2
    CLOSE = 3
    STAT = 4
    FSTAT = 5
    LSTAT = 6
    POLL = 7
    LSEEK = 8
    MMAP = 9
    MPROTECT = 10
    MUNMAP = 11
    BRK = 12
    
    IOCTL = 16
    PREAD64 = 17
    PWRITE64 = 18
    
    ACCESS = 21
    PIPE = 22
    SELECT = 23
    
    DUP = 32
    DUP2 = 33
    
    FORK = 57
    VFORK = 58
    EXECVE = 59
    EXIT = 60
    WAIT4 = 61
    
    KILL = 62
    UNAME = 63
    
    FCNTL = 72
    FSYNC = 74
    FDATASYNC = 75
    
    GETDENTS = 78
    GETCWD = 79
    CHDIR = 80
    FCHDIR = 81
    RENAME = 82
    MKDIR = 83
    RMDIR = 84
    CREAT = 85
    LINK = 86
    UNLINK = 87
    
    READLINK = 89
    CHMOD = 90
    FCHMOD = 91
    CHOWN = 92
    FCHOWN = 93
    
    GETPID = 39
    GETPPID = 110
    GETUID = 102
    GETEUID = 107
    GETGID = 104
    GETEGID = 108


@dataclass
class SyscallResult:
    """Result of a syscall execution"""
    retval: int
    errno: int = 0
    success: bool = True


class SystemCallInterface:
    """
    Direct system call interface
    
    Provides access to real Linux syscalls from Python.
    Used by MiniKernel to execute actual OS operations instead of simulations.
    """
    
    def __init__(self):
        if HAS_NATIVE_BRIDGE:
            self.bridge = syscall_bridge
        else:
            # Fall back to ctypes
            self.libc = ctypes.CDLL("libc.so.6", use_errno=True)
            self.libc.syscall.restype = ctypes.c_long
            self.libc.syscall.argtypes = [ctypes.c_long] + [ctypes.c_long] * 6
    
    def syscall(self, num: int, *args) -> SyscallResult:
        """
        Execute a raw syscall
        
        Args:
            num: Syscall number
            *args: Syscall arguments (up to 6)
        
        Returns:
            SyscallResult with return value and error code
        """
        # Pad args to 6 elements
        args = list(args) + [0] * (6 - len(args))
        
        try:
            if HAS_NATIVE_BRIDGE:
                result = self.bridge.syscall(num, *args[:6])
                return SyscallResult(retval=result, success=True)
            else:
                result = self.libc.syscall(num, *args[:6])
                if result == -1:
                    err = ctypes.get_errno()
                    return SyscallResult(retval=result, errno=err, success=False)
                return SyscallResult(retval=result, success=True)
        except OSError as e:
            return SyscallResult(retval=-1, errno=e.errno, success=False)
    
    # High-level syscall wrappers
    
    def read(self, fd: int, count: int) -> bytes:
        """Read from file descriptor"""
        if HAS_NATIVE_BRIDGE:
            # Use native bridge with direct memory access
            addr = self.bridge.mmap(count)
            result = self.syscall(Syscall.READ, fd, addr, count)
            if result.success:
                data = self.bridge.read_memory(addr, result.retval)
                self.bridge.munmap(addr, count)
                return data
            self.bridge.munmap(addr, count)
            raise OSError(result.errno, os.strerror(result.errno))
        else:
            # Fall back to os.read
            return os.read(fd, count)
    
    def write(self, fd: int, data: bytes) -> int:
        """Write to file descriptor"""
        if HAS_NATIVE_BRIDGE:
            # Use native bridge
            addr = self.bridge.mmap(len(data))
            self.bridge.write_memory(addr, data)
            result = self.syscall(Syscall.WRITE, fd, addr, len(data))
            self.bridge.munmap(addr, len(data))
            if result.success:
                return result.retval
            raise OSError(result.errno, os.strerror(result.errno))
        else:
            return os.write(fd, data)
    
    def open(self, path: str, flags: int, mode: int = 0o666) -> int:
        """Open file"""
        path_bytes = path.encode('utf-8') + b'\x00'
        
        if HAS_NATIVE_BRIDGE:
            addr = self.bridge.mmap(len(path_bytes))
            self.bridge.write_memory(addr, path_bytes)
            result = self.syscall(Syscall.OPEN, addr, flags, mode)
            self.bridge.munmap(addr, len(path_bytes))
            if result.success:
                return result.retval
            raise OSError(result.errno, os.strerror(result.errno))
        else:
            return os.open(path, flags, mode)
    
    def close(self, fd: int) -> None:
        """Close file descriptor"""
        result = self.syscall(Syscall.CLOSE, fd)
        if not result.success:
            raise OSError(result.errno, os.strerror(result.errno))
    
    def fork(self) -> int:
        """Fork process"""
        result = self.syscall(Syscall.FORK)
        if not result.success:
            raise OSError(result.errno, os.strerror(result.errno))
        return result.retval
    
    def execve(self, filename: str, argv: List[str], envp: List[str]) -> None:
        """Execute program"""
        # This would need complex marshalling of strings
        # For now, use os.execve as fallback
        os.execve(filename, argv, envp)
    
    def exit(self, code: int) -> None:
        """Exit process"""
        self.syscall(Syscall.EXIT, code)
    
    def getpid(self) -> int:
        """Get process ID"""
        result = self.syscall(Syscall.GETPID)
        return result.retval
    
    def getppid(self) -> int:
        """Get parent process ID"""
        result = self.syscall(Syscall.GETPPID)
        return result.retval
    
    def kill(self, pid: int, sig: int) -> None:
        """Send signal to process"""
        result = self.syscall(Syscall.KILL, pid, sig)
        if not result.success:
            raise OSError(result.errno, os.strerror(result.errno))


# Global instance
_syscalls: Optional[SystemCallInterface] = None

def get_syscalls() -> SystemCallInterface:
    """Get global syscall interface"""
    global _syscalls
    if _syscalls is None:
        _syscalls = SystemCallInterface()
    return _syscalls


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    syscalls = get_syscalls()
    
    # Test getpid
    pid = syscalls.getpid()
    print(f"Current PID: {pid}")
    
    # Test getppid
    ppid = syscalls.getppid()
    print(f"Parent PID: {ppid}")
    
    # Test file operations
    fd = syscalls.open("/tmp/test_syscall.txt", os.O_CREAT | os.O_WRONLY, 0o644)
    print(f"Opened file: fd={fd}")
    
    written = syscalls.write(fd, b"Hello from MiniKernel syscalls!\n")
    print(f"Wrote {written} bytes")
    
    syscalls.close(fd)
    print("Closed file")
