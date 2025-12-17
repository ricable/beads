"""
NexusAI Artifact System

Large blob storage for documents, images, and other files.
Artifacts are loaded on-demand to avoid context pollution.

Features:
- Lazy loading
- Content type detection
- Chunked processing for large files
- Reference tracking
"""

from __future__ import annotations

import asyncio
import hashlib
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO

from pydantic import BaseModel, Field


class ArtifactMetadata(BaseModel):
    """Metadata for an artifact"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    content_type: str
    size_bytes: int
    hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accessed_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "hash": self.hash,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "metadata": self.metadata,
            "tags": self.tags,
        }


class Artifact:
    """
    Represents a stored artifact with lazy content loading.
    """

    def __init__(
        self,
        metadata: ArtifactMetadata,
        store: ArtifactStore,
    ):
        self._metadata = metadata
        self._store = store
        self._content: bytes | None = None
        self._loaded = False

    @property
    def id(self) -> str:
        return self._metadata.id

    @property
    def name(self) -> str:
        return self._metadata.name

    @property
    def content_type(self) -> str:
        return self._metadata.content_type

    @property
    def size_bytes(self) -> int:
        return self._metadata.size_bytes

    @property
    def metadata(self) -> ArtifactMetadata:
        return self._metadata

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    async def load(self) -> bytes:
        """Load artifact content"""
        if not self._loaded:
            self._content = await self._store._read_content(self.id)
            self._loaded = True
            self._metadata.accessed_at = datetime.utcnow()
        return self._content or b""

    async def load_text(self, encoding: str = "utf-8") -> str:
        """Load artifact as text"""
        content = await self.load()
        return content.decode(encoding)

    async def iter_chunks(self, chunk_size: int = 8192):
        """Iterate over content in chunks"""
        content = await self.load()
        for i in range(0, len(content), chunk_size):
            yield content[i:i + chunk_size]

    def get_summary(self) -> dict[str, Any]:
        """Get artifact summary without loading content"""
        return {
            "id": self.id,
            "name": self.name,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "loaded": self._loaded,
        }


class ArtifactStore:
    """
    Storage backend for artifacts.

    Stores large files separately from session data to avoid
    context pollution. Supports on-demand loading.
    """

    def __init__(
        self,
        storage_path: Path | str = ".nexus/artifacts",
        max_size_bytes: int = 100 * 1024 * 1024,  # 100MB default
    ):
        self.storage_path = Path(storage_path)
        self.max_size_bytes = max_size_bytes
        self._metadata: dict[str, ArtifactMetadata] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize artifact storage"""
        if self._initialized:
            return

        self.storage_path.mkdir(parents=True, exist_ok=True)
        metadata_path = self.storage_path / "metadata.json"

        if metadata_path.exists():
            import json
            with open(metadata_path, "r") as f:
                data = json.load(f)
                for item in data:
                    meta = ArtifactMetadata(**item)
                    self._metadata[meta.id] = meta

        self._initialized = True

    async def _save_metadata(self) -> None:
        """Save metadata index"""
        import json
        metadata_path = self.storage_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump([m.to_dict() for m in self._metadata.values()], f, indent=2)

    def _get_content_path(self, artifact_id: str) -> Path:
        """Get path for artifact content"""
        return self.storage_path / "content" / artifact_id

    async def _read_content(self, artifact_id: str) -> bytes:
        """Read artifact content from storage"""
        content_path = self._get_content_path(artifact_id)
        if not content_path.exists():
            raise FileNotFoundError(f"Artifact content not found: {artifact_id}")

        with open(content_path, "rb") as f:
            return f.read()

    async def store(
        self,
        content: bytes | BinaryIO,
        name: str,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> Artifact:
        """
        Store an artifact.

        Args:
            content: Bytes or file-like object
            name: Display name for the artifact
            content_type: MIME type (auto-detected if not provided)
            metadata: Additional metadata
            tags: Tags for categorization

        Returns:
            The created Artifact
        """
        await self.initialize()

        # Read content if file-like
        if hasattr(content, "read"):
            content = content.read()

        if len(content) > self.max_size_bytes:
            raise ValueError(
                f"Artifact too large: {len(content)} bytes "
                f"(max: {self.max_size_bytes})"
            )

        # Auto-detect content type
        if not content_type:
            content_type, _ = mimetypes.guess_type(name)
            content_type = content_type or "application/octet-stream"

        # Compute hash
        content_hash = hashlib.sha256(content).hexdigest()

        # Check for duplicates
        for existing in self._metadata.values():
            if existing.hash == content_hash:
                # Return existing artifact
                return Artifact(existing, self)

        # Create metadata
        artifact_meta = ArtifactMetadata(
            name=name,
            content_type=content_type,
            size_bytes=len(content),
            hash=content_hash,
            metadata=metadata or {},
            tags=tags or [],
        )

        # Store content
        content_dir = self.storage_path / "content"
        content_dir.mkdir(parents=True, exist_ok=True)
        content_path = content_dir / artifact_meta.id

        async with self._lock:
            with open(content_path, "wb") as f:
                f.write(content)

            self._metadata[artifact_meta.id] = artifact_meta
            await self._save_metadata()

        return Artifact(artifact_meta, self)

    async def store_file(
        self,
        file_path: Path | str,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> Artifact:
        """Store artifact from file path"""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        name = name or file_path.name

        with open(file_path, "rb") as f:
            return await self.store(
                content=f,
                name=name,
                metadata=metadata,
                tags=tags,
            )

    async def get(self, artifact_id: str) -> Artifact | None:
        """Get artifact by ID"""
        await self.initialize()

        meta = self._metadata.get(artifact_id)
        if meta:
            return Artifact(meta, self)
        return None

    async def find_by_name(self, name: str) -> list[Artifact]:
        """Find artifacts by name (partial match)"""
        await self.initialize()

        results = []
        for meta in self._metadata.values():
            if name.lower() in meta.name.lower():
                results.append(Artifact(meta, self))
        return results

    async def find_by_tag(self, tag: str) -> list[Artifact]:
        """Find artifacts by tag"""
        await self.initialize()

        results = []
        for meta in self._metadata.values():
            if tag in meta.tags:
                results.append(Artifact(meta, self))
        return results

    async def delete(self, artifact_id: str) -> bool:
        """Delete an artifact"""
        await self.initialize()

        async with self._lock:
            if artifact_id not in self._metadata:
                return False

            # Remove content
            content_path = self._get_content_path(artifact_id)
            if content_path.exists():
                content_path.unlink()

            # Remove metadata
            del self._metadata[artifact_id]
            await self._save_metadata()

        return True

    async def list_all(self) -> list[Artifact]:
        """List all artifacts"""
        await self.initialize()
        return [Artifact(meta, self) for meta in self._metadata.values()]

    @property
    def total_size_bytes(self) -> int:
        """Total size of all artifacts"""
        return sum(m.size_bytes for m in self._metadata.values())

    @property
    def count(self) -> int:
        """Number of stored artifacts"""
        return len(self._metadata)
