"""
ELF Binary Loader for MiniKernel

Loads and executes ELF (Executable and Linkable Format) binaries.
This enables MiniKernel to run native Linux executables.
"""

import struct
import mmap
import logging
from dataclasses import dataclass
from typing import List, Optional
from enum import IntEnum

logger = logging.getLogger("MiniKernel.ELF")


class ELFClass(IntEnum):
    """ELF file class"""
    ELFCLASS32 = 1
    ELFCLASS64 = 2


class ELFData(IntEnum):
    """ELF data encoding"""
    ELFDATA2LSB = 1  # Little endian
    ELFDATA2MSB = 2  # Big endian


class ELFType(IntEnum):
    """ELF file type"""
    ET_NONE = 0
    ET_REL = 1   # Relocatable
    ET_EXEC = 2  # Executable
    ET_DYN = 3   # Shared object
    ET_CORE = 4  # Core file


class ELFMachine(IntEnum):
    """ELF machine type"""
    EM_X86_64 = 62
    EM_AARCH64 = 183


@dataclass
class ELFHeader:
    """ELF file header"""
    magic: bytes              # 0x7f 'E' 'L' 'F'
    ei_class: int            # 32 or 64 bit
    ei_data: int             # Endianness
    ei_version: int          # ELF version
    e_type: int              # Object file type
    e_machine: int           # Architecture
    e_version: int           # Object file version
    e_entry: int             # Entry point address
    e_phoff: int             # Program header offset
    e_shoff: int             # Section header offset
    e_flags: int             # Processor-specific flags
    e_ehsize: int            # ELF header size
    e_phentsize: int         # Program header size
    e_phnum: int             # Number of program headers
    e_shentsize: int         # Section header size
    e_shnum: int             # Number of section headers
    e_shstrndx: int          # Section header string table index


@dataclass
class ProgramHeader:
    """ELF program header"""
    p_type: int      # Segment type
    p_flags: int     # Segment flags
    p_offset: int    # Offset in file
    p_vaddr: int     # Virtual address
    p_paddr: int     # Physical address
    p_filesz: int    # Size in file
    p_memsz: int     # Size in memory
    p_align: int     # Alignment


class ELFLoader:
    """
    ELF binary loader
    
    Loads ELF executables into memory and prepares them for execution.
    """
    
    def __init__(self):
        self.page_size = 4096
    
    def load(self, path: str) -> 'ELFBinary':
        """
        Load ELF binary from file
        
        Args:
            path: Path to ELF file
        
        Returns:
            Loaded ELF binary
        """
        with open(path, 'rb') as f:
            data = f.read()
        
        # Parse ELF header
        header = self._parse_header(data)
        
        logger.info(f"Loading ELF binary: {path}")
        logger.info(f"  Class: {'64-bit' if header.ei_class == ELFClass.ELFCLASS64 else '32-bit'}")
        logger.info(f"  Type: {ELFType(header.e_type).name}")
        logger.info(f"  Entry: 0x{header.e_entry:x}")
        
        # Parse program headers
        program_headers = self._parse_program_headers(data, header)
        
        logger.info(f"  Program headers: {len(program_headers)}")
        for i, ph in enumerate(program_headers):
            if ph.p_type == 1:  # PT_LOAD
                logger.info(f"    [{i}] LOAD: vaddr=0x{ph.p_vaddr:x} memsz=0x{ph.p_memsz:x}")
        
        return ELFBinary(path, data, header, program_headers)
    
    def _parse_header(self, data: bytes) -> ELFHeader:
        """Parse ELF header"""
        # Check magic number
        if data[:4] != b'\x7fELF':
            raise ValueError("Not a valid ELF file")
        
        ei_class = data[4]
        ei_data = data[5]
        ei_version = data[6]
        
        if ei_class == ELFClass.ELFCLASS64:
            # 64-bit ELF
            fmt = '<HHIQQQIHHHHHH' if ei_data == ELFData.ELFDATA2LSB else '>HHIQQQIHHHHHH'
            fields = struct.unpack_from(fmt, data, 16)
        else:
            # 32-bit ELF
            fmt = '<HHIIIIIHHHHHH' if ei_data == ELFData.ELFDATA2LSB else '>HHIIIIIHHHHHH'
            fields = struct.unpack_from(fmt, data, 16)
        
        return ELFHeader(
            magic=data[:4],
            ei_class=ei_class,
            ei_data=ei_data,
            ei_version=ei_version,
            e_type=fields[0],
            e_machine=fields[1],
            e_version=fields[2],
            e_entry=fields[3],
            e_phoff=fields[4],
            e_shoff=fields[5],
            e_flags=fields[6],
            e_ehsize=fields[7],
            e_phentsize=fields[8],
            e_phnum=fields[9],
            e_shentsize=fields[10],
            e_shnum=fields[11],
            e_shstrndx=fields[12]
        )
    
    def _parse_program_headers(self, data: bytes, header: ELFHeader) -> List[ProgramHeader]:
        """Parse program headers"""
        headers = []
        
        for i in range(header.e_phnum):
            offset = header.e_phoff + (i * header.e_phentsize)
            
            if header.ei_class == ELFClass.ELFCLASS64:
                # 64-bit program header
                fmt = '<IIQQQQQQ' if header.ei_data == ELFData.ELFDATA2LSB else '>IIQQQQQQ'
                fields = struct.unpack_from(fmt, data, offset)
                
                ph = ProgramHeader(
                    p_type=fields[0],
                    p_flags=fields[1],
                    p_offset=fields[2],
                    p_vaddr=fields[3],
                    p_paddr=fields[4],
                    p_filesz=fields[5],
                    p_memsz=fields[6],
                    p_align=fields[7]
                )
            else:
                # 32-bit program header
                fmt = '<IIIIIIII' if header.ei_data == ELFData.ELFDATA2LSB else '>IIIIIIII'
                fields = struct.unpack_from(fmt, data, offset)
                
                ph = ProgramHeader(
                    p_type=fields[0],
                    p_offset=fields[1],
                    p_vaddr=fields[2],
                    p_paddr=fields[3],
                    p_filesz=fields[4],
                    p_memsz=fields[5],
                    p_flags=fields[6],
                    p_align=fields[7]
                )
            
            headers.append(ph)
        
        return headers
    
    def map_binary(self, binary: 'ELFBinary') -> int:
        """
        Map binary into memory
        
        Returns:
            Entry point address
        """
        # For each LOAD segment, map into memory
        for ph in binary.program_headers:
            if ph.p_type != 1:  # Not PT_LOAD
                continue
            
            # Calculate page-aligned address
            base = ph.p_vaddr & ~(self.page_size - 1)
            offset = ph.p_vaddr - base
            size = ph.p_memsz + offset
            
            # Round up to page size
            size = ((size + self.page_size - 1) // self.page_size) * self.page_size
            
            # Determine protection flags
            prot = 0
            if ph.p_flags & 0x1:  # PF_X
                prot |= mmap.PROT_EXEC
            if ph.p_flags & 0x2:  # PF_W
                prot |= mmap.PROT_WRITE
            if ph.p_flags & 0x4:  # PF_R
                prot |= mmap.PROT_READ
            
            logger.debug(f"Mapping segment: vaddr=0x{base:x} size=0x{size:x} prot={prot}")
            
            # Map memory (would use syscall_bridge for real implementation)
            # For now, this is a placeholder
            
        return binary.header.e_entry


@dataclass
class ELFBinary:
    """Loaded ELF binary"""
    path: str
    data: bytes
    header: ELFHeader
    program_headers: List[ProgramHeader]


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    loader = ELFLoader()
    
    # Load /bin/ls
    try:
        binary = loader.load("/bin/ls")
        print(f"\nSuccessfully loaded: {binary.path}")
        print(f"Entry point: 0x{binary.header.e_entry:x}")
    except Exception as e:
        print(f"Error loading binary: {e}")
