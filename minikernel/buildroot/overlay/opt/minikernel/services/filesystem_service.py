"""
FileSystem Service

AI-searchable filesystem with semantic search and metadata indexing
Runs in user space, communicates with kernel via IPC
"""

import logging
import os
import json
import sqlite3
import threading
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger("MiniKernel.FileSystem")


@dataclass
class FileEntry:
    """Represents a file with metadata"""
    path: str
    name: str
    size_bytes: int
    modified_time: datetime
    created_time: datetime
    file_type: str
    tags: List[str] = field(default_factory=list)
    content_summary: Optional[str] = None
    
    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)
    
    @property
    def age_days(self) -> int:
        return (datetime.now() - self.modified_time).days


class FileSystemService:
    """
    FileSystem Service for MiniKernel
    
    Features:
    - Semantic file search (by content, date, type)
    - Metadata indexing
    - Tag-based organization
    - AI-friendly file discovery
    
    Unlike traditional filesystems, this indexes files for natural language queries
    """
    
    def __init__(self, index_db_path: str = "/tmp/minikernel_fs.db"):
        self.index_db_path = index_db_path
        self.db: Optional[sqlite3.Connection] = None
        self._index_ready = threading.Event()
        self._index_thread: Optional[threading.Thread] = None

        # Search roots
        self.search_paths = [
            str(Path.home()),
            "/tmp"
        ]

        logger.info("FileSystem Service created")

    def initialize(self) -> None:
        """Initialize filesystem service — DB setup is synchronous, indexing is async."""
        self._init_database()

        # Rebuild the index in the background so boot completes immediately.
        self._index_thread = threading.Thread(
            target=self._rebuild_index_bg, daemon=True, name="FSIndex"
        )
        self._index_thread.start()

        logger.info("FileSystem Service initialized (indexing in background)")

    def _rebuild_index_bg(self) -> None:
        """Background wrapper: open a thread-local connection and rebuild the index."""
        try:
            # SQLite connections must not be shared across threads; open a separate
            # connection here so the main thread's self.db is not touched.
            thread_db = sqlite3.connect(self.index_db_path)
            self._rebuild_index(db=thread_db)
            thread_db.close()
        except Exception as e:
            logger.error("Background index rebuild failed: %s", e)
        finally:
            self._index_ready.set()
    
    def shutdown(self) -> None:
        """Shutdown filesystem service"""
        if self.db:
            self.db.close()
        logger.info("FileSystem Service shutdown")
    
    def _init_database(self) -> None:
        """Initialize SQLite database for file indexing"""
        self.db = sqlite3.connect(self.index_db_path)
        cursor = self.db.cursor()
        
        # Create files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                size_bytes INTEGER,
                modified_time TEXT,
                created_time TEXT,
                file_type TEXT,
                tags TEXT,
                content_summary TEXT,
                indexed_at TEXT
            )
        """)
        
        # Create FTS5 table for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                name,
                path,
                tags,
                content_summary,
                content='files',
                content_rowid='id'
            )
        """)
        
        # Create triggers to keep FTS in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
                INSERT INTO files_fts(rowid, name, path, tags, content_summary)
                VALUES (new.id, new.name, new.path, new.tags, new.content_summary);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
                DELETE FROM files_fts WHERE rowid = old.id;
            END
        """)
        
        self.db.commit()
        logger.debug("Database initialized")
    
    def _rebuild_index(self, db: Optional[sqlite3.Connection] = None) -> None:
        """Rebuild the file index using *db* (defaults to self.db)."""
        logger.info("Rebuilding file index...")

        conn = db or self.db
        if not conn:
            return

        cursor = conn.cursor()
        cursor.execute("DELETE FROM files")
        conn.commit()

        file_count = 0
        for search_path in self.search_paths:
            if os.path.exists(search_path):
                file_count += self._index_directory(search_path, db=conn)

        logger.info(f"Indexed {file_count} files")
    
    def _index_directory(self, path: str, max_depth: int = 3,
                         db: Optional[sqlite3.Connection] = None) -> int:
        """Index files in a directory using *db* (defaults to self.db)."""
        conn = db or self.db
        if not conn:
            return 0

        count = 0
        cursor = conn.cursor()

        try:
            for root, dirs, files in os.walk(path):
                # Check depth
                depth = root[len(path):].count(os.sep)
                if depth > max_depth:
                    continue

                for filename in files:
                    try:
                        filepath = os.path.join(root, filename)
                        stat = os.stat(filepath)
                        file_type = self._get_file_type(filename)

                        cursor.execute("""
                            INSERT OR REPLACE INTO files
                            (path, name, size_bytes, modified_time, created_time, file_type, tags, indexed_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            filepath,
                            filename,
                            stat.st_size,
                            datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            file_type,
                            json.dumps([]),
                            datetime.now().isoformat()
                        ))

                        count += 1

                    except (OSError, PermissionError):
                        continue

            conn.commit()
            
        except Exception as e:
            logger.error(f"Error indexing {path}: {e}")
        
        return count
    
    def search(
        self,
        query: str,
        file_type: Optional[str] = None,
        modified_since: Optional[datetime] = None,
        max_results: int = 50
    ) -> List[FileEntry]:
        """
        Search for files using natural language query
        
        Args:
            query: Search query (filename, content, etc.)
            file_type: Filter by file type
            modified_since: Filter by modification date
            max_results: Maximum number of results
            
        Returns:
            List of matching files
        """
        if not self.db:
            return []
        
        cursor = self.db.cursor()
        
        # Build SQL query
        sql = """
            SELECT f.path, f.name, f.size_bytes, f.modified_time, f.created_time, 
                   f.file_type, f.tags, f.content_summary
            FROM files f
            WHERE 1=1
        """
        params = []
        
        # Full-text search
        if query:
            sql += " AND f.id IN (SELECT rowid FROM files_fts WHERE files_fts MATCH ?)"
            params.append(query)
        
        # File type filter
        if file_type:
            sql += " AND f.file_type = ?"
            params.append(file_type)
        
        # Date filter
        if modified_since:
            sql += " AND f.modified_time >= ?"
            params.append(modified_since.isoformat())
        
        sql += " ORDER BY f.modified_time DESC LIMIT ?"
        params.append(max_results)
        
        cursor.execute(sql, params)
        
        results = []
        for row in cursor.fetchall():
            entry = FileEntry(
                path=row[0],
                name=row[1],
                size_bytes=row[2],
                modified_time=datetime.fromisoformat(row[3]),
                created_time=datetime.fromisoformat(row[4]),
                file_type=row[5],
                tags=json.loads(row[6]) if row[6] else [],
                content_summary=row[7]
            )
            results.append(entry)
        
        logger.debug(f"Search '{query}' returned {len(results)} results")
        return results
    
    def find_recent(self, days: int = 1, file_type: Optional[str] = None) -> List[FileEntry]:
        """Find files modified in the last N days"""
        since = datetime.now() - timedelta(days=days)
        return self.search("", file_type=file_type, modified_since=since)
    
    def get_file_info(self, path: str) -> Optional[FileEntry]:
        """Get information about a specific file"""
        if not self.db:
            return None
        
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT path, name, size_bytes, modified_time, created_time, 
                   file_type, tags, content_summary
            FROM files
            WHERE path = ?
        """, (path,))
        
        row = cursor.fetchone()
        if row:
            return FileEntry(
                path=row[0],
                name=row[1],
                size_bytes=row[2],
                modified_time=datetime.fromisoformat(row[3]),
                created_time=datetime.fromisoformat(row[4]),
                file_type=row[5],
                tags=json.loads(row[6]) if row[6] else [],
                content_summary=row[7]
            )
        
        return None
    
    def add_tag(self, path: str, tag: str) -> bool:
        """Add a tag to a file"""
        if not self.db:
            return False
        
        cursor = self.db.cursor()
        cursor.execute("SELECT tags FROM files WHERE path = ?", (path,))
        row = cursor.fetchone()
        
        if row:
            tags = json.loads(row[0]) if row[0] else []
            if tag not in tags:
                tags.append(tag)
                cursor.execute("UPDATE files SET tags = ? WHERE path = ?", 
                             (json.dumps(tags), path))
                self.db.commit()
                return True
        
        return False
    
    def _get_file_type(self, filename: str) -> str:
        """Determine file type from filename"""
        ext = Path(filename).suffix.lower()
        
        type_map = {
            ".txt": "text",
            ".md": "markdown",
            ".py": "python",
            ".js": "javascript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".pdf": "pdf",
            ".doc": "document",
            ".docx": "document",
            ".jpg": "image",
            ".jpeg": "image",
            ".png": "image",
            ".gif": "image",
            ".mp3": "audio",
            ".mp4": "video",
            ".zip": "archive",
            ".tar": "archive",
            ".gz": "archive"
        }
        
        return type_map.get(ext, "other")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get filesystem statistics"""
        if not self.db:
            return {}
        
        cursor = self.db.cursor()
        
        cursor.execute("SELECT COUNT(*), SUM(size_bytes) FROM files")
        count, total_size = cursor.fetchone()
        
        cursor.execute("""
            SELECT file_type, COUNT(*) 
            FROM files 
            GROUP BY file_type
            ORDER BY COUNT(*) DESC
        """)
        by_type = dict(cursor.fetchall())
        
        return {
            "indexed_files": count or 0,
            "total_size_mb": (total_size or 0) / (1024 * 1024),
            "by_type": by_type,
            "search_paths": self.search_paths
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    fs = FileSystemService()
    fs.initialize()
    
    # Search for Python files
    results = fs.search("python", file_type="python")
    print(f"Found {len(results)} Python files")
    
    # Find recent files
    recent = fs.find_recent(days=7)
    print(f"Found {len(recent)} files from last week")
    
    # Stats
    print(fs.get_stats())
    
    fs.shutdown()
