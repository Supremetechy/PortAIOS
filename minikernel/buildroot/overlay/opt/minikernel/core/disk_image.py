"""
Disk Image Handler for MiniKernel

Supports VDI (VirtualBox Disk Image) and raw disk images.
Provides block-level access to virtual disks for filesystem implementation.
"""

import struct
import logging
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger("MiniKernel.DiskImage")


class VDIImageType(IntEnum):
    """VDI image types"""
    DYNAMIC = 1
    STATIC = 2
    UNDO = 3
    DIFF = 4


@dataclass
class VDIHeader:
    """VirtualBox Disk Image header"""
    signature: bytes              # VDI signature
    version: tuple                # Version (major, minor)
    header_size: int             # Header size
    image_type: int              # Image type
    image_flags: int             # Image flags
    description: str             # Image description
    offset_blocks: int           # Offset to blocks
    offset_data: int             # Offset to data
    cylinders: int               # Geometry - cylinders
    heads: int                   # Geometry - heads
    sectors: int                 # Geometry - sectors
    sector_size: int             # Sector size
    disk_size: int               # Disk size in bytes
    block_size: int              # Block size
    block_extra: int             # Extra block data
    blocks_total: int            # Total blocks
    blocks_allocated: int        # Allocated blocks


class DiskImage:
    """
    Virtual Disk Image handler
    
    Provides block-level access to disk images (VDI, raw).
    Used by filesystem implementation for persistent storage.
    """
    
    def __init__(self, path: str):
        self.path = Path(path)
        self.fd: Optional[int] = None
        self.is_vdi = False
        self.vdi_header: Optional[VDIHeader] = None
        self.block_map: Optional[list] = None
        self.block_size = 4096
        
    def open(self) -> bool:
        """Open disk image"""
        if not self.path.exists():
            logger.error(f"Disk image not found: {self.path}")
            return False
        
        self.fd = open(self.path, 'r+b')
        
        # Detect format
        magic = self.fd.read(64)
        self.fd.seek(0)
        
        if b'<<< Oracle VM VirtualBox Disk Image >>>' in magic:
            self.is_vdi = True
            logger.info(f"Detected VDI format: {self.path}")
            return self._parse_vdi()
        else:
            logger.info(f"Using raw disk format: {self.path}")
            return True
    
    def close(self):
        """Close disk image"""
        if self.fd:
            self.fd.close()
            self.fd = None
    
    def _parse_vdi(self) -> bool:
        """Parse VDI header"""
        # Read full header (512 bytes minimum)
        self.fd.seek(0)
        header_data = self.fd.read(512)
        
        # Parse header fields
        # VDI v1.1 header format
        signature = header_data[64:96]
        
        # Unpack header (little endian)
        fields = struct.unpack('<IIIIIIII', header_data[0:32])
        
        # Additional fields
        more_fields = struct.unpack('<IIIIIIII', header_data[344:376])
        
        self.vdi_header = VDIHeader(
            signature=signature,
            version=(fields[0], fields[1]),
            header_size=fields[2],
            image_type=fields[3],
            image_flags=fields[4],
            description=header_data[96:352].decode('utf-16le', errors='ignore').strip('\x00'),
            offset_blocks=more_fields[0],
            offset_data=more_fields[1],
            cylinders=0,  # Would parse from geometry
            heads=0,
            sectors=0,
            sector_size=512,
            disk_size=more_fields[2],
            block_size=more_fields[3],
            block_extra=more_fields[4],
            blocks_total=more_fields[5],
            blocks_allocated=more_fields[6]
        )
        
        # Read block allocation table
        self._load_block_map()
        
        logger.info(f"VDI Header:")
        logger.info(f"  Version: {self.vdi_header.version}")
        logger.info(f"  Disk size: {self.vdi_header.disk_size / (1024**3):.2f} GB")
        logger.info(f"  Block size: {self.vdi_header.block_size}")
        logger.info(f"  Blocks total: {self.vdi_header.blocks_total}")
        logger.info(f"  Blocks allocated: {self.vdi_header.blocks_allocated}")
        
        return True
    
    def _load_block_map(self):
        """Load VDI block allocation table"""
        if not self.vdi_header:
            return
        
        # Seek to block map
        self.fd.seek(self.vdi_header.offset_blocks)
        
        # Read block map (array of 32-bit block numbers)
        block_count = self.vdi_header.blocks_total
        block_map_size = block_count * 4
        block_map_data = self.fd.read(block_map_size)
        
        # Unpack to list of integers
        self.block_map = list(struct.unpack(f'<{block_count}I', block_map_data))
        
        logger.debug(f"Loaded block map: {block_count} entries")
    
    def read_block(self, block_num: int) -> bytes:
        """
        Read a block from disk
        
        Args:
            block_num: Logical block number
        
        Returns:
            Block data (4096 bytes by default)
        """
        if self.is_vdi:
            return self._read_vdi_block(block_num)
        else:
            return self._read_raw_block(block_num)
    
    def write_block(self, block_num: int, data: bytes) -> bool:
        """
        Write a block to disk
        
        Args:
            block_num: Logical block number
            data: Block data (must be block_size bytes)
        
        Returns:
            True if successful
        """
        if len(data) != self.block_size:
            logger.error(f"Block data must be {self.block_size} bytes")
            return False
        
        if self.is_vdi:
            return self._write_vdi_block(block_num, data)
        else:
            return self._write_raw_block(block_num, data)
    
    def _read_vdi_block(self, block_num: int) -> bytes:
        """Read block from VDI image"""
        if block_num >= self.vdi_header.blocks_total:
            raise ValueError(f"Block {block_num} out of range")
        
        # Get physical block number
        physical_block = self.block_map[block_num]
        
        if physical_block == 0xFFFFFFFF:
            # Unallocated block (sparse) - return zeros
            return b'\x00' * self.block_size
        
        # Calculate offset in file
        offset = self.vdi_header.offset_data + (physical_block * self.vdi_header.block_size)
        
        # Read block
        self.fd.seek(offset)
        return self.fd.read(self.block_size)
    
    def _write_vdi_block(self, block_num: int, data: bytes) -> bool:
        """Write block to VDI image"""
        if block_num >= self.vdi_header.blocks_total:
            return False
        
        # Get or allocate physical block
        physical_block = self.block_map[block_num]
        
        if physical_block == 0xFFFFFFFF:
            # Need to allocate new block
            physical_block = self._allocate_vdi_block(block_num)
            if physical_block is None:
                return False
        
        # Calculate offset
        offset = self.vdi_header.offset_data + (physical_block * self.vdi_header.block_size)
        
        # Write block
        self.fd.seek(offset)
        self.fd.write(data)
        self.fd.flush()
        
        return True
    
    def _allocate_vdi_block(self, block_num: int) -> Optional[int]:
        """Allocate a new block in VDI image"""
        # Find next available physical block
        physical_block = self.vdi_header.blocks_allocated
        
        # Update block map
        self.block_map[block_num] = physical_block
        
        # Write updated block map entry
        offset = self.vdi_header.offset_blocks + (block_num * 4)
        self.fd.seek(offset)
        self.fd.write(struct.pack('<I', physical_block))
        
        # Update allocated count in header
        self.vdi_header.blocks_allocated += 1
        
        # Write updated header
        # (Would update the full header here)
        
        logger.debug(f"Allocated block {block_num} → physical {physical_block}")
        
        return physical_block
    
    def _read_raw_block(self, block_num: int) -> bytes:
        """Read block from raw disk image"""
        offset = block_num * self.block_size
        self.fd.seek(offset)
        return self.fd.read(self.block_size)
    
    def _write_raw_block(self, block_num: int, data: bytes) -> bool:
        """Write block to raw disk image"""
        offset = block_num * self.block_size
        self.fd.seek(offset)
        self.fd.write(data)
        self.fd.flush()
        return True
    
    def get_size(self) -> int:
        """Get disk size in bytes"""
        if self.is_vdi:
            return self.vdi_header.disk_size
        else:
            return self.path.stat().st_size
    
    def get_block_count(self) -> int:
        """Get total number of blocks"""
        return self.get_size() // self.block_size
    
    def sync(self):
        """Sync disk to storage"""
        if self.fd:
            self.fd.flush()
            import os
            os.fsync(self.fd.fileno())


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Test with a VDI file
    disk = DiskImage("/path/to/disk.vdi")
    
    if disk.open():
        print(f"Disk size: {disk.get_size() / (1024**3):.2f} GB")
        print(f"Block count: {disk.get_block_count()}")
        
        # Read first block
        block = disk.read_block(0)
        print(f"First block: {block[:64].hex()}")
        
        disk.close()
